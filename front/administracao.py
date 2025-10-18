import streamlit as st
import pandas as pd
import logging
from datetime import date, datetime, timedelta
from managers.matrix_manager import MatrixManager as GlobalMatrixManager
from auth.auth_utils import check_permission, get_user_email
from ui.metrics import display_minimalist_metrics
from operations.audit_logger import log_action
from operations.cached_loaders import load_nr_rules_data
from operations.supabase_operations import SupabaseOperations

logger = logging.getLogger('segsisone_app.administracao')

def show_compliance_rules_management(matrix_manager: GlobalMatrixManager):
    """
    Interface para gerenciamento de regras de conformidade de treinamentos
    """
    st.header("📜 Gerenciador de Regras de Conformidade")
    st.info("""
    Esta área permite visualizar e gerenciar as regras de validação de treinamentos.
    - **Regras Globais:** Aplicáveis a todas as unidades
    - **Regras Unitárias:** Específicas por cliente
    """)

    # Carregar regras do banco
    try:
        rules_df = load_nr_rules_data()
        if rules_df.empty:
            st.info("Nenhuma regra de conformidade configurada ainda.")
            with st.expander("⚙️ Configurar Primeira Regra", expanded=True):
                with st.form("first_rule_form"):
                    st.write("**Regra Global de Exemplo**")
                    norma = st.text_input("Norma (ex: NR-10)", value="NR-10")
                    titulo = st.text_input("Treinamento (ex: Básico)", value="Básico")
                    ch_min = st.number_input("C.H. Mínima (horas)", value=40)
                    rec_anos = st.number_input("Reciclagem (anos)", value=2)
                    if st.form_submit_button("💾 Criar Primeira Regra"):
                        # TODO: Implementar criação da primeira regra
                        st.success("Funcionalidade em desenvolvimento!")
            return

        # Visão Geral
        total_regras = len(rules_df)
        global_regras = len(rules_df[rules_df['unit_id'].isnull()])
        unit_regras = total_regras - global_regras

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Regras", total_regras)
        col2.metric("Regras Globais", global_regras)
        col3.metric("Regras Unitárias", unit_regras)

        # Ações de Regras
        st.subheader("📋 Regras Configuradas")
        col_add1, col_add2 = st.columns([3, 1])
        with col_add1:
            if st.button("➕ Nova Regra Global", use_container_width=True, type="primary"):
                st.session_state.show_rule_dialog = True
                st.session_state.rule_to_edit = None
                st.session_state.target_unit_id = None
                st.rerun()

        with col_add2:
            all_units = matrix_manager.get_all_units()
            selected_unit = st.selectbox(
                "Adicionar para unidade:",
                options=[""] + [u['nome_unidade'] for u in all_units],
                format_func=lambda x: "Selecionar unidade..." if x == "" else x,
                label_visibility="collapsed"
            )
            if selected_unit and st.button("➕ Nova Regra Unitária", use_container_width=True):
                unit_id = next(u['id'] for u in all_units if u['nome_unidade'] == selected_unit)
                st.session_state.show_rule_dialog = True
                st.session_state.rule_to_edit = None
                st.session_state.target_unit_id = str(unit_id)
                st.rerun()

        # Visualizar Regras
        if not rules_df.empty:
            display_df = rules_df.copy()
            display_df['unidade'] = display_df['unit_id'].fillna('Global')
            display_df = display_df[['norma', 'titulo', 'unidade', 'carga_horaria_minima_horas', 'reciclagem_anos', 'treinamento_is_active']]
            display_df.columns = ['Norma', 'Treinamento', 'Escopo', 'C.H. Mínima', 'Reciclagem', 'Ativo']

            st.dataframe(display_df, use_container_width=True)

            # Botão para editar regras existentes
            st.markdown("#### Editar Regra Existente")
            selected_rule = st.selectbox(
                "Selecionar regra para editar:",
                options=[''] + [f"{row['norma']} - {row['titulo']} ({row['unit_id'] or 'Global'})" for _, row in rules_df.iterrows()],
                format_func=lambda x: "Selecione uma regra..." if x == "" else x
            )

            if selected_rule and st.button("✏️ Editar Regra Selecionada", type="secondary"):
                # Encontrar a regra selecionada
                for _, row in rules_df.iterrows():
                    rule_label = f"{row['norma']} - {row['titulo']} ({row['unit_id'] or 'Global'})"
                    if rule_label == selected_rule:
                        st.session_state.show_rule_dialog = True
                        st.session_state.rule_to_edit = row.to_dict()
                        st.session_state.target_unit_id = row['unit_id']
                        st.rerun()
                        break

    except Exception as e:
        st.error(f"Erro ao carregar regras: {e}")

    # Renderiza o diálogo se necessário
    if st.session_state.get('show_rule_dialog'):
        handle_rule_dialog(matrix_manager)



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

def show_access_request_management(matrix_manager):
    """Gerencia solicitações de acesso pendentes."""
    st.header(" 📬 Solicitações de Acesso Pendentes")
    
    pending_requests = matrix_manager.get_pending_access_requests()
    if pending_requests.empty:
        st.info("Não há solicitações de acesso pendentes.")
        return
        
    for _, request in pending_requests.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Nome:** {request['nome_usuario']}")
                st.markdown(f"**E-mail:** {request['email_usuario']}")
                if request.get('mensagem'):
                    st.markdown(f"**Mensagem:** {request['mensagem']}")
                st.caption(f"Solicitação enviada em: {request.get('created_at', 'N/A')}")
            
            with col2:
                if st.button("✅ Aprovar", key=f"approve_{request['id']}"):
                    # Lógica para adicionar usuário com acesso básico
                    user_data = {
                        "email": request['email_usuario'],
                        "nome": request['nome_usuario'],
                        "role": "viewer",  # Acesso básico
                        "unidade_associada": "*",  # Pode ser modificado pelo admin depois
                        "plano": "pro",
                        "status_assinatura": "trial",
                        "data_fim_trial": (datetime.now() + timedelta(days=30)).date().isoformat()
                    }
                    
                    if matrix_manager.add_user(user_data):
                        # Atualiza o status da solicitação
                        matrix_manager.update_access_request_status(request['id'], "Aprovado")
                        st.toast("✅ Usuário aprovado com sucesso!", icon="✅")
                        st.rerun()
                    else:
                        st.error("Erro ao adicionar usuário. Verifique se o e-mail já existe.")
                
                if st.button("❌ Rejeitar", key=f"reject_{request['id']}"):
                    if matrix_manager.update_access_request_status(request['id'], "Rejeitado"):
                        st.toast("Solicitação rejeitada", icon="✅")
                        st.rerun()

def show_super_admin_view():
    st.title("👑 Painel do Super Administrador")
    matrix_manager = GlobalMatrixManager()

    # Gerenciador de solicitações de acesso
    pending_requests = matrix_manager.get_pending_access_requests()
    pending_count = len(pending_requests)

    tab_dashboard, tab_requests, tab_users, tab_provision, tab_matrix, tab_rules, tab_audit = st.tabs([
        f"📊 Dashboard Global",
        f"📬 Solicitações de Acesso ({pending_count})" if pending_count > 0 else "📬 Solicitações de Acesso",
        "👤 Gerenciar Usuários",
        "🚀 Provisionar Cliente",
        "🏗️ Matriz Global",
        "📜 Regras de Conformidade",
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

                            # Aplicar automaticamente a matriz global para a nova unidade
                            new_unit_info = matrix_manager.get_unit_info_by_name(new_unit_name)
                            if new_unit_info:
                                with st.spinner("Aplicando matriz global automaticamente..."):
                                    success, message = matrix_manager.auto_apply_global_matrix_on_unit_creation(str(new_unit_info['id']))
                                    if success:
                                        st.success(f"✅ {message}")
                                    else:
                                        st.warning(f"Aviso na aplicação da matriz: {message}")

                            if is_single_tenant:
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

    with tab_matrix:
        st.header("🏗️ Gerenciamento da Matriz Global de Treinamentos")
        st.info("""
        Esta área permite gerenciar a matriz global de treinamentos que serve como base para todas as unidades.
        - **Matriz Global:** Funções e treinamentos base aplicáveis a novas unidades
        - **Aplicação em Massa:** Propagar mudanças para unidades existentes
        """)

        # Visualizar Matriz Global
        try:
            from operations.training_matrix_manager import MatrixManager as TrainingMatrixManager
            global_matrix_manager = TrainingMatrixManager("global")
            global_functions = global_matrix_manager.get_all_functions_global()

            if global_functions:
                st.subheader("📋 Funções da Matriz Global")
                functions_df = pd.DataFrame(global_functions)
                st.dataframe(functions_df[['nome_funcao', 'descricao']], use_container_width=True, hide_index=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🚀 Aplicação em Massa")
                    all_units = matrix_manager.get_all_units()
                    if st.button("🔄 Aplicar Matriz Global a Todas as Unidades", type="primary", use_container_width=True):
                        with st.spinner("Aplicando matriz global..."):
                            success, message = matrix_manager.bulk_apply_global_matrix_to_all_units()
                            if success:
                                st.success(message)
                            else:
                                st.error(message)

                with col2:
                    st.subheader("📍 Aplicação Individual")
                    unit_names = [u['nome_unidade'] for u in all_units]
                    selected_unit_name = st.selectbox("Selecionar unidade para aplicar matriz:", options=[''] + unit_names)
                    if selected_unit_name and st.button(f"🎯 Aplicar para {selected_unit_name}", use_container_width=True):
                        selected_unit = next(u for u in all_units if u['nome_unidade'] == selected_unit_name)
                        with st.spinner(f"Aplicando matriz para {selected_unit_name}..."):
                            success, message = matrix_manager.bulk_apply_global_matrix_to_unit(selected_unit['id'])
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
            else:
                st.info("Nenhuma função cadastrada na matriz global ainda.")

        except Exception as e:
            st.error(f"Erro ao carregar matriz global: {e}")

    with tab_rules:
        show_compliance_rules_management(matrix_manager)

    with tab_audit:
        st.header("🛡️ Logs de Auditoria do Sistema")
        logs_df = matrix_manager.get_audit_logs()
        if not logs_df.empty:
            st.dataframe(logs_df.sort_values(by='timestamp', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro de log encontrado.")
            
    handle_user_dialog(matrix_manager)
    handle_delete_dialog(matrix_manager)

def handle_rule_dialog(matrix_manager: GlobalMatrixManager):
    """Manipula o diálogo de criação/edição de regras"""
    if not st.session_state.get('show_rule_dialog'):
        return

    rule_data = st.session_state.get('rule_to_edit')
    target_unit_id = st.session_state.get('target_unit_id')
    is_edit = rule_data is not None

    @st.dialog("Gerenciar Regra de Conformidade", width="large")
    def rule_form_dialog():
        st.subheader("Editar Regra" if is_edit else "Adicionar Nova Regra")

        if target_unit_id:
            all_units = matrix_manager.get_all_units()
            unit_name = next((u['nome_unidade'] for u in all_units if str(u['id']) == str(target_unit_id)), "Cliente")
            st.info(f"Esta regra será aplicada **apenas** à unidade: {unit_name}")
        else:
            st.warning("Esta é uma **Regra Global** e será aplicada a todas as unidades que não tiverem uma regra customizada.")

        with st.form("rule_form"):
            norma = st.text_input(
                "Norma (ex: NR-10, NR-35)",
                value=rule_data.get('norma') if rule_data else "NR-"
            ).upper()

            titulo = st.text_input(
                "Título do Treinamento (ex: Básico, SEP, Especializado)",
                value=rule_data.get('titulo') if rule_data else ""
            )

            st.markdown("---")
            st.markdown("##### 📚 Formação Inicial")

            ch_form_def_emp = st.checkbox(
                "Carga horária definida pelo empregador",
                value=pd.isna(rule_data.get('carga_horaria_minima_horas')) if rule_data else False,  # ✅ Padrão: False
                key="ch_form_checkbox"
            )
            ch_formacao = st.number_input(
                "Carga horária mínima (horas)",
                min_value=0,
                value=int(rule_data.get('carga_horaria_minima_horas', 0)) if rule_data and not pd.isna(rule_data.get('carga_horaria_minima_horas')) else 0,
                disabled=ch_form_def_emp,  # ✅ Desabilita APENAS se o checkbox estiver marcado
                key="ch_form_input"
            )

            st.markdown("---")
            st.markdown("##### 🔄 Reciclagem")

            rec_anos_na = st.checkbox(
                "Não se aplica / Período variável",
                value=pd.isna(rule_data.get('reciclagem_anos')) if rule_data else False,  # ✅ Padrão: False
                key="rec_anos_checkbox"
            )
            rec_anos = st.number_input(
                "Periodicidade (anos)",
                min_value=0.0,
                step=0.5,
                format="%.1f",
                value=float(rule_data.get('reciclagem_anos', 0.0)) if rule_data and not pd.isna(rule_data.get('reciclagem_anos')) else 0.0,
                disabled=rec_anos_na,  # ✅ Desabilita APENAS se o checkbox estiver marcado
                key="rec_anos_input"
            )

            ch_rec_def_emp = st.checkbox(
                "Carga horária de reciclagem definida pelo empregador",
                value=pd.isna(rule_data.get('reciclagem_carga_horaria_horas')) if rule_data else False,  # ✅ Padrão: False
                key="ch_rec_checkbox"
            )
            ch_reciclagem = st.number_input(
                "Carga horária mínima reciclagem (horas)",
                min_value=0,
                value=int(rule_data.get('reciclagem_carga_horaria_horas', 0)) if rule_data and not pd.isna(rule_data.get('reciclagem_carga_horaria_horas')) else 0,
                disabled=ch_rec_def_emp,  # ✅ Desabilita APENAS se o checkbox estiver marcado
                key="ch_rec_input"
            )

            st.markdown("---")
            is_active = st.checkbox(
                "Regra Ativa",
                value=rule_data.get('treinamento_is_active', True) if rule_data else True
            )

            col_save, col_cancel = st.columns(2)

            with col_save:
                submit = st.form_submit_button("💾 Salvar Regra", type="primary", use_container_width=True)

            with col_cancel:
                cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

            if cancel:
                st.session_state.pop('show_rule_dialog', None)
                st.session_state.pop('rule_to_edit', None)
                st.session_state.pop('target_unit_id', None)
                st.rerun()

            if submit:
                if not norma or not titulo:
                    st.error("Norma e Título são obrigatórios.")
                    return

                # Preparar dados da regra
                training_payload = {
                    'titulo': titulo,
                    'carga_horaria_minima_horas': None if ch_form_def_emp else int(ch_formacao),
                    'reciclagem_anos': None if rec_anos_na else float(rec_anos),
                    'reciclagem_carga_horaria_horas': None if ch_rec_def_emp else int(ch_reciclagem),
                    'is_active': is_active
                }

                supabase_ops = SupabaseOperations(unit_id=None)

                with st.spinner("Salvando regra..."):
                    success = False

                    if is_edit:
                        # UPDATE: Editar regra existente
                        success = supabase_ops.update_row(
                            "regras_treinamentos",
                            rule_data['treinamento_id'],
                            training_payload
                        )

                        if success:
                            st.success("✅ Regra atualizada com sucesso!")
                        else:
                            st.error("❌ Falha ao atualizar a regra.")
                    else:
                        # INSERT: Criar nova regra
                        # 1. Encontra ou cria a norma pai
                        existing_normas = supabase_ops.get_by_field("regras_normas", "norma", norma)

                        # Filtrar pela unidade específica
                        if target_unit_id:
                            existing_normas = existing_normas[existing_normas['unit_id'] == target_unit_id]
                        else:
                            existing_normas = existing_normas[existing_normas['unit_id'].isnull()]

                        if not existing_normas.empty:
                            id_norma = existing_normas.iloc[0]['id']
                        else:
                            # Criar nova norma
                            norma_payload = {
                                "norma": norma,
                                "unit_id": target_unit_id,
                                "is_active": True
                            }
                            id_norma = supabase_ops.insert_row("regras_normas", norma_payload)

                        if id_norma:
                            training_payload['id_norma'] = id_norma
                            training_id = supabase_ops.insert_row("regras_treinamentos", training_payload)

                            if training_id:
                                st.success("✅ Nova regra criada com sucesso!")
                                success = True
                            else:
                                st.error("❌ Falha ao salvar o treinamento.")
                        else:
                            st.error("❌ Falha ao encontrar ou criar a norma pai.")

                if success:
                    # Limpar cache
                    from operations.cached_loaders import load_nr_rules_data
                    load_nr_rules_data.clear()

                    # Limpar session state
                    st.session_state.pop('show_rule_dialog', None)
                    st.session_state.pop('rule_to_edit', None)
                    st.session_state.pop('target_unit_id', None)

                    st.rerun()

    # Renderiza o diálogo
    rule_form_dialog()

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

    tab_list = ["Gerenciar Empresas", "Gerenciar Funcionários", "Gerenciar Matriz"]
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
        
        # 1. Adicionar Nova Função
        with st.expander("➕ Adicionar Nova Função à Matriz"):
            with st.form("form_add_funcao", clear_on_submit=True):
                new_func_name = st.text_input("Nome da Função/Cargo")
                new_func_desc = st.text_area("Breve descrição da Função")
                if st.form_submit_button("💾 Salvar Função"):
                    if new_func_name:
                        _, msg = matrix_manager_unidade.add_function(new_func_name, new_func_desc)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error("O nome da função é obrigatório.")

        st.divider()

        # 2. Gerenciar Funções Existentes
        st.subheader("⚙️ Gerenciar Funções e Treinamentos")
        
        functions_df = matrix_manager_unidade.functions_df
        
        if functions_df.empty:
            st.info("Nenhuma função cadastrada para esta unidade. Adicione uma função acima.")
            return

        # Selecionar a função para editar
        func_options = functions_df['nome_funcao'].tolist()
        selected_function_name = st.selectbox(
            "Selecione a função para gerenciar os treinamentos:",
            options=[''] + func_options,
            format_func=lambda x: "Selecione..." if x == '' else x
        )

        if selected_function_name:
            selected_function_id = functions_df[functions_df['nome_funcao'] == selected_function_name].iloc[0]['id']
            
            st.markdown(f"#### Treinamentos para: **{selected_function_name}**")

            # Carregar todos os treinamentos disponíveis (regras)
            all_rules_df = matrix_manager_unidade.nr_rules_manager.all_rules_df
            if not all_rules_df.empty:
                # Criar uma lista de treinamentos no formato "NORMA - TÍTULO"
                available_trainings = all_rules_df.apply(
                    lambda row: f"{row['norma']} - {row['titulo']}", axis=1
                ).unique().tolist()

                # Carregar treinamentos já associados à função
                required_trainings_raw = matrix_manager_unidade.get_required_trainings_for_function(selected_function_name)
                
                st.json(required_trainings_raw)

                # Filtrar os treinamentos requeridos para garantir que eles existam na lista de disponíveis
                required_trainings = [t for t in required_trainings_raw if t in available_trainings]

                # Multi-select para associar/desassociar treinamentos
                selected_trainings = st.multiselect(
                    "Selecione os treinamentos obrigatórios para esta função:",
                    options=available_trainings,
                    default=required_trainings,
                    help="Adicione ou remova treinamentos da lista."
                )

                if st.button("💾 Salvar Mapeamento", type="primary"):
                    with st.spinner("Atualizando..."):
                        success, message = matrix_manager_unidade.update_function_mappings(selected_function_id, selected_trainings)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
            else:
                st.warning("Nenhuma regra de treinamento configurada. Vá para 'Regras de Conformidade' no painel de Super Admin para criá-las.")

def show_admin_page():
    if not check_permission(level='editor'):
        st.stop()
    if st.session_state.get('is_global_view', False):
        show_super_admin_view()
    else:
        show_unit_admin_view()
