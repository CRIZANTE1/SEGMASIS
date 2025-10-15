import streamlit as st
import pandas as pd
import logging
from datetime import date, timedelta
from managers.matrix_manager import MatrixManager as GlobalMatrixManager
from auth.auth_utils import check_permission
from ui.metrics import display_minimalist_metrics
from operations.audit_logger import log_action

logger = logging.getLogger('segsisone_app.administracao')

# --- Funções Auxiliares para o Super Admin ---

@st.cache_data(ttl=300, show_spinner="Carregando dados globais...")
def load_global_data():
    try:
        from operations.cached_loaders import load_all_units_consolidated_data
        return load_all_units_consolidated_data()
    except Exception as e:
        st.error(f"Falha ao carregar dados consolidados: {e}")
        return {}

def display_global_dashboard(data):
    st.header(" Dashboard Executivo Global")
    # ... (código da função inalterado)

def show_user_management(matrix_manager):
    st.header(" Gerenciamento de Usuários e Planos")
    if st.button("➕ Adicionar Novo Usuário"):
        st.session_state.show_user_dialog = True
        st.session_state.user_to_edit = None
        st.rerun()

    users = matrix_manager.get_all_users()
    if not users:
        st.info("Nenhum usuário cadastrado."); return

    users_df = pd.DataFrame(users)
    st.dataframe(users_df[['nome', 'email', 'role', 'unidade_associada']], use_container_width=True, hide_index=True)
    
    selected_email = st.selectbox("Selecione um usuário para ações:", options=[''] + users_df['email'].tolist())
    if selected_email:
        user_data = users_df[users_df['email'] == selected_email].iloc[0].to_dict()
        col1, col2 = st.columns(2)
        if col1.button("✏️ Editar", key=f"edit_{user_data['id']}"):
            st.session_state.show_user_dialog = True
            st.session_state.user_to_edit = user_data
            st.rerun()
        if col2.button("❌ Remover", key=f"delete_{user_data['id']}"):
            st.session_state.show_delete_dialog = True
            st.session_state.user_to_delete = user_data
            st.rerun()

def handle_user_dialog(matrix_manager):
    if 'show_user_dialog' in st.session_state and st.session_state.show_user_dialog:
        user_data = st.session_state.get('user_to_edit')
        is_edit = user_data is not None

        @st.dialog("Gerenciar Usuário", on_dismiss=lambda: st.session_state.pop('show_user_dialog', None))
        def user_form():
            with st.form("user_form"):
                email = st.text_input("E-mail", value=user_data['email'] if is_edit else "", disabled=is_edit)
                nome = st.text_input("Nome", value=user_data['nome'] if is_edit else "")
                roles = ["admin", "editor", "viewer"]
                current_role_index = roles.index(user_data['role']) if is_edit and user_data.get('role') in roles else 0
                role = st.selectbox("Papel (Role)", roles, index=current_role_index)
                
                all_units = matrix_manager.get_all_units()
                unit_names = [unit['nome_unidade'] for unit in all_units] + ["*"]
                all_units_map = {unit['id']: unit['nome_unidade'] for unit in all_units}
                all_units_map['*'] = '*'
                unit_id_to_name = {v: k for k, v in all_units_map.items()}

                current_unit_name = all_units_map.get(user_data['unidade_associada'], '*') if is_edit else '*'
                try:
                    current_unit_index = unit_names.index(current_unit_name)
                except ValueError:
                    current_unit_index = len(unit_names) - 1

                unidade_selecionada_nome = st.selectbox("Unidade Associada", unit_names, index=current_unit_index)
                unidade_associada_id = unit_id_to_name.get(unidade_selecionada_nome, '*')

                st.markdown("---")
                st.subheader("Assinatura e Plano")

                # Oculta opções de plano para o Super Admin para evitar confusão
                if user_data and user_data.get('unidade_associada') == '*':
                    st.info("O Super Administrador tem acesso total por padrão e não possui um plano de assinatura formal.")
                    # Mantém os valores como None para não tentar salvá-los
                    plano = None
                    status_assinatura = None
                    data_fim_trial = None
                else:
                    # Mostra as opções para usuários normais
                    plan_options = ["pro", "premium_ia"] # Remove "basico"
                    current_plan = user_data.get('plano', 'pro')
                    current_plan_index = plan_options.index(current_plan) if is_edit and current_plan in plan_options else 0
                    plano = st.selectbox("Plano de Assinatura:", plan_options, index=current_plan_index)

                    status_options = ["ativo", "inativo", "trial", "cancelado"]
                    current_status = user_data.get('status_assinatura', 'inativo')
                    current_status_index = status_options.index(current_status) if is_edit and current_status in status_options else 0
                    status_assinatura = st.selectbox("Status da Assinatura:", status_options, index=current_status_index)

                    data_fim_trial_val = pd.to_datetime(user_data.get('data_fim_trial')).date() if is_edit and pd.notna(user_data.get('data_fim_trial')) else None
                    data_fim_trial = st.date_input("Data de Fim do Trial (se aplicável):", value=data_fim_trial_val)

                if st.form_submit_button("Salvar"):
                    if not email or not nome:
                        st.error("E-mail e Nome são obrigatórios.")
                        return

                    updates = {
                        "nome": nome, 
                        "role": role, 
                        "unidade_associada": unidade_associada_id,
                        "plano": plano,
                        "status_assinatura": status_assinatura,
                        "data_fim_trial": data_fim_trial.isoformat() if data_fim_trial else None
                    }
                    if is_edit:
                        if matrix_manager.update_user(user_data['id'], updates):
                            st.success("Usuário atualizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Falha ao atualizar usuário.")
                    else:
                        if matrix_manager.get_user_info(email):
                            st.error(f"O e-mail '{email}' já está cadastrado.")
                        else:
                            fim_trial = date.today() + timedelta(days=14)

                        new_user_data = {
                            "email": request['email_usuario'],
                            "nome": request['nome_usuario'],
                            "role": role, # O role (editor/viewer) ainda define as permissões
                            "unidade_associada": unit_id,
                            "plano": "premium_ia", # Sempre inicia o trial no plano máximo
                            "status_assinatura": "trial", # Status correto para período de teste
                            "data_fim_trial": fim_trial.isoformat()
                        }
                                st.success(f"Usuário '{nome}' adicionado com sucesso!")
                                st.rerun()
                            else:
                                st.error("Falha ao adicionar usuário.")
        user_form()

def handle_delete_dialog(matrix_manager):
    if 'show_delete_dialog' in st.session_state and st.session_state.show_delete_dialog:
        user_data = st.session_state.get('user_to_delete')
        @st.dialog("Confirmar Exclusão", on_dismiss=lambda: st.session_state.pop('show_delete_dialog', None))
        def confirm_dialog():
            st.warning(f"Você tem certeza que deseja remover permanentemente o usuário **{user_data['email']}**?")
            st.caption("Esta ação não pode ser desfeita.")
            
            col1, col2 = st.columns(2)
            if col1.button("Cancelar", use_container_width=True): st.rerun()
            if col2.button("Sim, Remover", type="primary", use_container_width=True):
                if matrix_manager.remove_user(user_data['id']):
                    st.success(f"Usuário '{user_data['email']}' removido com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao remover usuário.")
        confirm_dialog()

# --- Função Principal da Página ---

def show_super_admin_view():
    """Renderiza a UI completa para o Super Admin."""
    st.title(" Painel do Super Administrador")
    matrix_manager = GlobalMatrixManager()

    tab_dashboard, tab_users, tab_provision, tab_audit = st.tabs([
        " Dashboard Global", " Gerenciar Usuários",
        " Provisionar Cliente", "️ Logs de Auditoria"
    ])

    with tab_dashboard:
        global_data = load_global_data()
        if global_data:
            display_global_dashboard(global_data)

    with tab_users:
        show_user_management(matrix_manager)
    
    with tab_provision:
        st.header(" Provisionar Novo Cliente/Unidade")
        with st.form("provision_form"):
            new_unit_name = st.text_input("Nome da Unidade ou Empresa Cliente")
            new_unit_email = st.text_input("E-mail de Contato Principal")
            is_single_tenant = st.checkbox("Este é um cliente de empresa única (Single-Tenant)?")
            cnpj = st.text_input("CNPJ da Empresa (Obrigatório para modo empresa única)", disabled=not is_single_tenant)

            if st.form_submit_button("Provisionar"):
                pass
    
    with tab_audit:
        st.header("️ Logs de Auditoria do Sistema")
        logs_df = matrix_manager.get_audit_logs()
        if not logs_df.empty:
            st.dataframe(logs_df.sort_values(by='timestamp', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro de log encontrado.")
            
    handle_user_dialog(matrix_manager)
    handle_delete_dialog(matrix_manager)

def show_unit_admin_view():
    """Renderiza a UI completa para o Admin/Editor de Unidade."""
    is_single_mode = st.session_state.get('is_single_company_mode', False)
    if is_single_mode:
        unit_name = st.session_state.get('single_company_name', 'Nenhuma')
        st.title(f" Gerenciamento da Empresa: {unit_name}")
    else:
        unit_name = st.session_state.get('unit_name', 'Nenhuma')
        st.title(f" Gerenciamento da Unidade: {unit_name}")

    if not st.session_state.get('managers_initialized'):
        st.warning("Aguardando a inicialização dos dados..."); st.stop()

    employee_manager = st.session_state.employee_manager
    matrix_manager_unidade = st.session_state.matrix_manager_unidade

    st.subheader("Visão Geral de Pendências")
    display_minimalist_metrics(employee_manager)
    st.divider()

    tab_list = ["Gerenciar Empresas", "Gerenciar Funcionários", "Gerenciar Matriz"]
    if is_single_mode:
        tab_list.pop(0)
        tab_funcionario, tab_matriz = st.tabs(tab_list)
    else:
        tab_empresa, tab_funcionario, tab_matriz = st.tabs(tab_list)
    
    if not is_single_mode:
        with tab_empresa:
            with st.expander("➕ Cadastrar Nova Empresa"):
                with st.form("form_add_company", clear_on_submit=True):
                    company_name = st.text_input("Nome da Empresa")
                    company_cnpj = st.text_input("CNPJ")
                    if st.form_submit_button("Cadastrar Empresa"):
                        if company_name and company_cnpj:
                            _, message = employee_manager.add_company(company_name, company_cnpj)
                            st.success(message); st.rerun()
            st.subheader("Empresas Cadastradas na Unidade")
            df_to_show = employee_manager.companies_df
            if not df_to_show.empty:
                for _, row in df_to_show.sort_values('nome').iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3,2,1])
                        c1.markdown(f"**{row['nome']}**")
                        c2.caption(f"CNPJ: {row['cnpj']} | Status: {row['status']}")
                        with c3:
                            if str(row['status']).lower() == 'ativo':
                                if st.button("Arquivar", key=f"archive_{row['id']}"):
                                    employee_manager.archive_company(row['id']); st.rerun()
                            else:
                                if st.button("Reativar", key=f"unarchive_{row['id']}", type="primary"):
                                    employee_manager.unarchive_company(row['id']); st.rerun()

    with tab_funcionario:
        company_id = st.session_state.get('single_company_id') if is_single_mode else None
        if not is_single_mode:
            active_companies = employee_manager.companies_df[employee_manager.companies_df['status'].str.lower() == 'ativo']
            if not active_companies.empty:
                company_id = st.selectbox("Selecione a Empresa para cadastrar um funcionário:", options=active_companies['id'], format_func=employee_manager.get_company_name)
        
        with st.expander("➕ Cadastrar Novo Funcionário"):
            if not company_id:
                st.warning("Nenhuma empresa ativa disponível.")
            else:
                with st.form("form_add_employee", clear_on_submit=True):
                    name = st.text_input("Nome do Funcionário")
                    role = st.text_input("Cargo")
                    adm_date = st.date_input("Data de Admissão")
                    if st.form_submit_button("Cadastrar"):
                        if all([name, role, adm_date, company_id]):
                            _, msg = employee_manager.add_employee(name, role, adm_date, company_id)
                            st.success(msg); st.rerun()
        
        st.subheader("Funcionários Cadastrados")
        company_filter = company_id if is_single_mode else st.selectbox("Filtrar por Empresa:", options=['Todas'] + employee_manager.companies_df['id'].tolist(), format_func=lambda x: 'Todas' if x == 'Todas' else employee_manager.get_company_name(x))
        
        employees_to_show = employee_manager.employees_df
        if company_filter and company_filter != 'Todas':
            employees_to_show = employees_to_show[employees_to_show['empresa_id'] == str(company_filter)]

        if not employees_to_show.empty:
            for _, row in employees_to_show.sort_values('nome').iterrows():
                 with st.container(border=True):
                    c1,c2,c3 = st.columns([3,2,1])
                    c1.markdown(f"**{row['nome']}**")
                    c2.caption(f"Cargo: {row['cargo']} | Status: {row['status']}")
                    with c3:
                        if str(row['status']).lower() == 'ativo':
                            if st.button("Arquivar", key=f"archive_emp_{row['id']}"):
                                employee_manager.archive_employee(row['id']); st.rerun()
                        else:
                            if st.button("Reativar", key=f"unarchive_emp_{row['id']}", type="primary"):
                                employee_manager.unarchive_employee(row['id']); st.rerun()

    with tab_matriz:
        st.header("Matriz de Treinamento por Função")


def show_admin_page():
    """Função principal que roteia para a visão correta."""
    if not check_permission(level='editor'):
        st.stop()

    is_global_view = st.session_state.get('is_global_view', False)
    
    if is_global_view:
        show_super_admin_view()
    else:
        show_unit_admin_view()