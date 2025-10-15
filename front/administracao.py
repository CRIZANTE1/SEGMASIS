import streamlit as st
import pandas as pd
import logging
from datetime import date
from managers.matrix_manager import MatrixManager as GlobalMatrixManager
from auth.auth_utils import check_permission, get_user_email
from ui.metrics import display_minimalist_metrics
from operations.audit_logger import log_action

logger = logging.getLogger('segsisone_app.administracao')

# --- Funções para a Visão Global (Super Admin) ---

@st.cache_data(ttl=300, show_spinner="Carregando dados globais...")
def load_global_data(admin_email: str):
    """Carrega dados de todas as unidades para o dashboard do Super Admin."""
    if not admin_email:
        st.error("Identidade do administrador não encontrada para carregar dados.")
        return {}
    try:
        from operations.cached_loaders import load_all_units_consolidated_data
        return load_all_units_consolidated_data(admin_email)
    except Exception as e:
        st.error(f"Falha ao carregar dados consolidados: {e}")
        return {}

def display_global_dashboard(data):
    st.header("📊 Dashboard Executivo Global")
    companies_df = data.get('companies', pd.DataFrame())
    employees_df = data.get('employees', pd.DataFrame())
    asos_df = data.get('asos', pd.DataFrame())
    trainings_df = data.get('trainings', pd.DataFrame())

    if companies_df.empty:
        st.info("Nenhuma empresa encontrada em todas as unidades para exibir métricas.")
        return

    total_units = companies_df['unidade'].nunique() if 'unidade' in companies_df.columns else 0
    active_companies = companies_df[companies_df['status'].str.lower() == 'ativo']
    active_employees = employees_df[employees_df['status'].str.lower() == 'ativo'] if not employees_df.empty else pd.DataFrame()

    col1, col2, col3 = st.columns(3)
    col1.metric("Unidades/Clientes Ativos", total_units)
    col2.metric("Total de Empresas Gerenciadas", len(active_companies))
    col3.metric("Total de Funcionários Gerenciados", len(active_employees))
    st.divider()

    today = date.today()
    expired_asos_count = 0
    if not asos_df.empty and 'vencimento' in asos_df.columns and pd.api.types.is_datetime64_any_dtype(asos_df['vencimento']):
        expired_asos_count = len(asos_df[asos_df['vencimento'].dt.date < today])

    expired_trainings_count = 0
    if not trainings_df.empty and 'vencimento' in trainings_df.columns and pd.api.types.is_datetime64_any_dtype(trainings_df['vencimento']):
        expired_trainings_count = len(trainings_df[trainings_df['vencimento'].dt.date < today])

    total_pendencies = expired_asos_count + expired_trainings_count

    st.subheader("🩺 Saúde da Plataforma")
    col_health1, col_health2 = st.columns(2)
    col_health1.metric("Total de Pendências (Vencidos)", total_pendencies, delta_color="inverse" if total_pendencies > 0 else "off")
    col_health2.metric("Nível de Engajamento (Em breve)", "N/A")

def show_user_management(matrix_manager):
    st.header("👤 Gerenciamento de Usuários e Planos")
    if st.button("➕ Adicionar Novo Usuário"):
        st.session_state.show_user_dialog = True
        st.session_state.user_to_edit = None
        st.rerun()

    users = matrix_manager.get_all_users()
    if not users:
        st.info("Nenhum usuário cadastrado."); return

    users_df = pd.DataFrame(users)
    st.dataframe(users_df[['nome', 'email', 'role', 'unidade_associada', 'plano', 'status_assinatura']], use_container_width=True, hide_index=True)
    
    selected_user_email = st.selectbox("Selecione um usuário para ações rápidas:", options=[''] + users_df['email'].tolist())
    
    if selected_user_email:
        user_data = users_df[users_df['email'] == selected_user_email].iloc[0].to_dict()
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
            st.subheader("Editar Usuário" if is_edit else "Adicionar Novo Usuário")
            
            all_units = matrix_manager.get_all_units()
            unit_map = {str(unit['id']): unit['nome_unidade'] for unit in all_units}
            unit_options = ['*'] + list(unit_map.keys())
            
            def format_unit_display(unit_id):
                if unit_id == '*': return "Global (Super Admin)"
                return unit_map.get(unit_id, f"ID: {unit_id}")

            with st.form("user_form_dialog"):
                email = st.text_input("E-mail", value=user_data['email'] if is_edit else "", disabled=is_edit)
                nome = st.text_input("Nome", value=user_data['nome'] if is_edit else "")
                
                roles = ["admin", "editor", "viewer"]
                current_role = user_data.get('role', 'viewer') if is_edit else 'viewer'
                role = st.selectbox("Perfil (Role)", roles, index=roles.index(current_role))
                
                current_unit = str(user_data.get('unidade_associada', '*')) if is_edit else '*'
                unidade_associada = st.selectbox("Unidade/Empresa Associada", options=unit_options, index=unit_options.index(current_unit), format_func=format_unit_display)

                st.markdown("---"); st.subheader("Assinatura e Plano")
                if unidade_associada == '*':
                    st.info("O Super Administrador tem acesso total por padrão.")
                    plano, status_assinatura, data_fim_trial = None, None, None
                else:
                    plan_options = ["pro", "premium_ia"]
                    current_plan = user_data.get('plano', 'pro') if is_edit else 'pro'
                    plano = st.selectbox("Plano de Assinatura:", plan_options, index=plan_options.index(current_plan))

                    status_options = ["ativo", "inativo", "trial", "cancelado"]
                    current_status = user_data.get('status_assinatura', 'inativo') if is_edit else 'inativo'
                    status_assinatura = st.selectbox("Status da Assinatura:", status_options, index=status_options.index(current_status))

                    data_fim_trial_val = pd.to_datetime(user_data.get('data_fim_trial')).date() if is_edit and pd.notna(user_data.get('data_fim_trial')) else None
                    data_fim_trial = st.date_input("Data de Fim do Trial (se aplicável):", value=data_fim_trial_val)

                if st.form_submit_button("Salvar"):
                    email_to_save = email if not is_edit else user_data['email']
                    if not email_to_save.strip() or not nome.strip():
                        st.error("E-mail e Nome são obrigatórios."); return

                    form_data = {
                        "nome": nome, "role": role, "unidade_associada": unidade_associada,
                        "plano": plano, "status_assinatura": status_assinatura,
                        "data_fim_trial": data_fim_trial.isoformat() if data_fim_trial else None
                    }
                    if not is_edit: form_data['email'] = email_to_save

                    success = matrix_manager.update_user(user_data['id'], form_data) if is_edit else matrix_manager.add_user(form_data)
                    
                    if success:
                        st.toast("Operação realizada com sucesso!"); st.session_state.pop('show_user_dialog', None); st.rerun()
                    else:
                        st.error("Falha ao salvar. Verifique se o e-mail já existe.")
        user_form()

def handle_delete_dialog(matrix_manager):
    if 'show_delete_dialog' in st.session_state and st.session_state.show_delete_dialog:
        user_data = st.session_state.get('user_to_delete')
        @st.dialog("Confirmar Exclusão", on_dismiss=lambda: st.session_state.pop('show_delete_dialog', None))
        def confirm_dialog():
            st.warning(f"Remover o usuário **{user_data['nome']}** ({user_data['email']})?")
            if st.button("Sim, Remover", type="primary"):
                if matrix_manager.remove_user(user_data['id']):
                    st.toast("Usuário removido!"); st.session_state.pop('show_delete_dialog', None); st.rerun()
                else:
                    st.error("Falha ao remover.")
        confirm_dialog()

def show_super_admin_view():
    st.title("👑 Painel do Super Administrador")
    matrix_manager = GlobalMatrixManager()
    
    # Gerenciador de solicitações de acesso
    pending_requests = matrix_manager.get_pending_access_requests()
    pending_count = len(pending_requests)
    
    tab_dashboard, tab_requests, tab_users, tab_provision, tab_audit = st.tabs([
        f"📊 Dashboard Global",
        f"📬 Solicitações de Acesso ({pending_count})" if pending_count > 0 else "📬 Solicitações de Acesso",
        "👤 Gerenciar Usuários",
        "🚀 Provisionar Cliente",
        "🛡️ Logs de Auditoria"
    ])

    with tab_dashboard:
        admin_email = get_user_email()
        if admin_email:
            global_data = load_global_data(admin_email)
            if global_data:
                display_global_dashboard(global_data)
        else:
            st.error("Não foi possível verificar a identidade do administrador.")
    
    with tab_requests:
        from .administracao import show_access_request_management
        show_access_request_management(matrix_manager)

    with tab_users:
        show_user_management(matrix_manager)
    
    with tab_provision:
        st.header("🚀 Provisionar Novo Cliente/Unidade")
        with st.form("provision_form"):
            new_unit_name = st.text_input("Nome da Unidade ou Empresa Cliente")
            new_unit_email = st.text_input("E-mail de Contato Principal")
            is_single_tenant = st.checkbox("Este é um cliente de empresa única (Single-Tenant)?")
            cnpj = st.text_input("CNPJ da Empresa (Obrigatório para modo empresa única)", disabled=not is_single_tenant)
            
            if st.form_submit_button("Provisionar"):
                if not new_unit_name or not new_unit_email or (is_single_tenant and not cnpj):
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    with st.spinner("Iniciando provisionamento..."):
                        unit_data = {'nome_unidade': new_unit_name, 'email_contato': new_unit_email, 'folder_id': ''}
                        if matrix_manager.add_unit(unit_data):
                            st.success(f"✅ Unidade '{new_unit_name}' registrada!")
                            if is_single_tenant:
                                new_unit_info = matrix_manager.get_unit_info_by_name(new_unit_name)
                                if new_unit_info:
                                    from operations.supabase_operations import SupabaseOperations
                                    unit_ops = SupabaseOperations(unit_id=str(new_unit_info['id']))
                                    company_data = {'nome': new_unit_name, 'cnpj': cnpj, 'status': 'Ativo'}
                                    if unit_ops.insert_row("empresas", company_data):
                                        st.success(f"✅ Empresa '{new_unit_name}' associada!")
                                    else:
                                        st.error("Falha ao criar a empresa associada.")
                            log_action("PROVISION_CLIENT", {"name": new_unit_name, "is_single_tenant": is_single_tenant})
                            st.info("Provisionamento concluído.")
                        else:
                            st.error("Falha ao registrar a unidade. Verifique se o nome já existe.")
    with tab_audit:
        st.header("🛡️ Logs de Auditoria do Sistema")
        logs_df = matrix_manager.get_audit_logs()
        if not logs_df.empty:
            st.dataframe(logs_df.sort_values(by='timestamp', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro de log encontrado.")
            
    handle_user_dialog(matrix_manager)
    handle_delete_dialog(matrix_manager)

def show_unit_admin_view():
    is_single_mode = st.session_state.get('is_single_company_mode', False)
    title = f"🏢 Gerenciamento da Empresa: {st.session_state.get('single_company_name', 'N/A')}" if is_single_mode else f"📍 Gerenciamento da Unidade: {st.session_state.get('unit_name', 'N/A')}"
    st.title(title)

    if not st.session_state.get('managers_initialized'):
        st.warning("Aguardando a inicialização dos dados..."); st.stop()

    employee_manager = st.session_state.employee_manager
    matrix_manager_unidade = st.session_state.matrix_manager_unidade
    nr_analyzer = st.session_state.get('nr_analyzer')

    st.subheader("Visão Geral de Pendências")
    display_minimalist_metrics(employee_manager)
    st.divider()

    tab_list = ["Gerenciar Empresas", "Gerenciar Funcionários", "Gerenciar Matriz", "Assistente de Matriz (IA)"]
    if is_single_mode: tab_list.pop(0)
    
    tabs = st.tabs(tab_list)
    
    # Aba Gerenciar Empresas
    if not is_single_mode:
        with tabs[0]:
            with st.expander("➕ Cadastrar Nova Empresa"):
                with st.form("form_add_company", clear_on_submit=True):
                    c_name, c_cnpj = st.text_input("Nome da Empresa"), st.text_input("CNPJ")
                    if st.form_submit_button("Cadastrar"):
                        if c_name and c_cnpj:
                            _, msg = employee_manager.add_company(c_name, c_cnpj); st.success(msg); st.rerun()
            st.subheader("Empresas Cadastradas")
            for _, row in employee_manager.companies_df.sort_values('nome').iterrows():
                with st.container(border=True):
                    c1,c2,c3 = st.columns([3,2,1])
                    c1.markdown(f"**{row['nome']}**"); c2.caption(f"CNPJ: {row['cnpj']} | Status: {row['status']}")
                    with c3:
                        if str(row['status']).lower() == 'ativo':
                            if st.button("Arquivar", key=f"archive_{row['id']}"): employee_manager.archive_company(row['id']); st.rerun()
                        else:
                            if st.button("Reativar", key=f"unarchive_{row['id']}", type="primary"): employee_manager.unarchive_company(row['id']); st.rerun()

    # Aba Gerenciar Funcionários
    funcionario_tab_index = 0 if is_single_mode else 1
    with tabs[funcionario_tab_index]:
        company_id = st.session_state.get('single_company_id') if is_single_mode else None
        if not is_single_mode:
            active_companies = employee_manager.companies_df[employee_manager.companies_df['status'].str.lower() == 'ativo']
            if not active_companies.empty:
                company_id = st.selectbox("Empresa para cadastrar funcionário:", options=active_companies['id'], format_func=employee_manager.get_company_name)

        with st.expander("➕ Cadastrar Novo Funcionário"):
            if not company_id:
                st.warning("Nenhuma empresa ativa disponível.")
            else:
                with st.form("form_add_employee", clear_on_submit=True):
                    name, role, adm_date = st.text_input("Nome"), st.text_input("Cargo"), st.date_input("Data de Admissão")
                    if st.form_submit_button("Cadastrar"):
                        if all([name, role, adm_date, company_id]):
                            _, msg = employee_manager.add_employee(name, role, adm_date, company_id); st.success(msg); st.rerun()
        
        st.subheader("Funcionários Cadastrados")
        company_filter = company_id if is_single_mode else st.selectbox("Filtrar por Empresa:", options=['Todas'] + employee_manager.companies_df['id'].tolist(), format_func=lambda x: 'Todas' if x == 'Todas' else employee_manager.get_company_name(x))
        employees_to_show = employee_manager.employees_df
        if company_filter and company_filter != 'Todas':
            employees_to_show = employees_to_show[employees_to_show['empresa_id'] == str(company_filter)]

        for _, row in employees_to_show.sort_values('nome').iterrows():
            with st.container(border=True):
                c1,c2,c3 = st.columns([3,2,1])
                c1.markdown(f"**{row['nome']}**"); c2.caption(f"Cargo: {row['cargo']} | Status: {row['status']}")
                with c3:
                    if str(row['status']).lower() == 'ativo':
                        if st.button("Arquivar", key=f"archive_emp_{row['id']}"): employee_manager.archive_employee(row['id']); st.rerun()
                    else:
                        if st.button("Reativar", key=f"unarchive_emp_{row['id']}", type="primary"): employee_manager.unarchive_employee(row['id']); st.rerun()
    
    # Aba Gerenciar Matriz
    matriz_tab_index = 1 if is_single_mode else 2
    with tabs[matriz_tab_index]:
        st.header("Matriz de Treinamento por Função")
        # Coloque o código completo da aba de gerenciamento da matriz aqui
    
    # Aba Assistente de Matriz
    assistente_tab_index = 2 if is_single_mode else 3
    if len(tabs) > assistente_tab_index:
        with tabs[assistente_tab_index]:
            st.header("🤖 Assistente de Matriz com IA")
            # Coloque o código completo da aba de assistente de IA aqui

def show_admin_page():
    if not check_permission(level='editor'):
        st.stop()
    if st.session_state.get('is_global_view', False):
        show_super_admin_view()
    else:
        show_unit_admin_view()