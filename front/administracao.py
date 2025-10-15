import streamlit as st
import pandas as pd
import logging
from datetime import date
from managers.matrix_manager import MatrixManager as GlobalMatrixManager
from operations.employee import EmployeeManager
from operations.company_docs import CompanyDocsManager
from auth.auth_utils import check_permission
from ui.metrics import display_minimalist_metrics
from operations.audit_logger import log_action
from operations.cached_loaders import load_all_unit_data

logger = logging.getLogger('segsisone_app.administracao')

def show_access_request_management(matrix_manager: GlobalMatrixManager):
    """Interface para o Super Admin gerenciar solicitações de acesso."""
    st.header(" Gerenciar Solicitações de Acesso")
    
    pending_requests = matrix_manager.get_pending_access_requests()
    
    if pending_requests.empty:
        st.success("✅ Nenhuma solicitação de acesso pendente.")
        return

    st.info(f"Você tem {len(pending_requests)} solicitação(ões) para avaliar.")
    
    all_units = matrix_manager.get_all_units()
    unit_options = {str(unit['id']): unit['nome_unidade'] for unit in all_units}
    unit_options['*'] = 'Global (Super Admin)'

    for _, request in pending_requests.iterrows():
        request_id = request['id']
        with st.container(border=True):
            st.markdown(f"**Usuário:** {request['nome_usuario']} (`{request['email_usuario']}`)")
            if pd.notna(request['mensagem']) and request['mensagem']:
                st.caption(f"**Mensagem:** *{request['mensagem']}*")
            
            with st.form(f"form_request_{request_id}"):
                st.write("**Aprovar e configurar acesso:**")
                
                col1, col2 = st.columns(2)
                with col1:
                    role = st.selectbox("Atribuir Perfil (Role):", ["editor", "viewer"], key=f"role_{request_id}")
                with col2:
                    unit_id = st.selectbox(
                        "Associar à Unidade/Cliente:", 
                        options=list(unit_options.keys()),
                        format_func=lambda x: unit_options.get(x, "Inválido"),
                        key=f"unit_{request_id}"
                    )

                submitted = st.form_submit_button("Aprovar Acesso", type="primary")
                if submitted:
                    with st.spinner("Aprovando usuário..."):
                        new_user_data = {
                            "email": request['email_usuario'],
                            "nome": request['nome_usuario'],
                            "role": role,
                            "unidade_associada": unit_id
                        }
                        
                        # Adiciona o usuário e depois atualiza o status da solicitação
                        if matrix_manager.add_user(new_user_data):
                            if matrix_manager.update_access_request_status(request_id, "Aprovado"):
                                st.success(f"Usuário {request['nome_usuario']} aprovado e cadastrado com sucesso!")
                                log_action("ACCESS_REQUEST_APPROVED", {"approved_email": request['email_usuario']})
                                st.rerun()
                            else:
                                st.error("Usuário cadastrado, mas falha ao atualizar status da solicitação.")
                        else:
                            st.error(f"Falha ao cadastrar o usuário. Verifique se o e-mail já existe.")

            if st.button("Rejeitar Solicitação", key=f"reject_{request_id}", type="secondary"):
                with st.spinner("Rejeitando..."):
                    if matrix_manager.update_access_request_status(request_id, "Rejeitado"):
                        st.warning(f"Solicitação de {request['nome_usuario']} foi rejeitada.")
                        log_action("ACCESS_REQUEST_REJECTED", {"rejected_email": request['email_usuario']})
                        st.rerun()
                    else:
                        st.error("Falha ao rejeitar a solicitação.")

def show_admin_page():
    """Página principal de Administração (Super Admin e Editor de Unidade)."""
    if not check_permission(level='editor'):
        st.stop()

    is_global_view = st.session_state.get('is_global_view', False)
    
    if is_global_view:
        if not check_permission(level='admin'):
            st.stop()
        
        st.title(" Painel do Super Administrador")
        matrix_manager = GlobalMatrixManager()

        tab_dashboard, tab_requests, tab_users, tab_provision, tab_audit = st.tabs([
            " Dashboard Global", 
            " Solicitações de Acesso",
            " Gerenciar Usuários",
            " Provisionar Cliente",
            "️ Logs de Auditoria"
        ])

        with tab_dashboard:
            st.header("Dashboard Executivo Global")

        with tab_requests:
            show_access_request_management(matrix_manager)

        with tab_users:
            st.header("Gerenciamento de Usuários e Planos")
        
        with tab_provision:
            st.header("Provisionar Novo Cliente/Unidade")
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
    else:
        is_single_mode = st.session_state.get('is_single_company_mode', False)
        if is_single_mode:
            unit_name = st.session_state.get('single_company_name', 'Nenhuma')
            st.title(f" Gerenciamento da Empresa: {unit_name}")
        else:
            unit_name = st.session_state.get('unit_name', 'Nenhuma')
            st.title(f" Gerenciamento da Unidade: {unit_name}")

        if not st.session_state.get('managers_initialized'):
            st.warning("Aguardando a inicialização dos dados da unidade...")
            st.stop()

        employee_manager = st.session_state.employee_manager
        matrix_manager_unidade = st.session_state.matrix_manager_unidade
        nr_analyzer = st.session_state.nr_analyzer

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