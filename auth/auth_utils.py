import streamlit as st
from managers.matrix_manager import MatrixManager
from operations.supabase_operations import SupabaseOperations # <-- ADICIONE ESTA IMPORTAÇÃO
from operations.audit_logger import log_action # <-- MOVA PARA CIMA

def is_oidc_available():
    """Verifica se o login OIDC está configurado e disponível."""
    return hasattr(st, 'user') and hasattr(st.user, 'is_logged_in')

def is_user_logged_in():
    """Verifica se o usuário está logado."""
    return is_oidc_available() and st.user.is_logged_in

def get_user_email() -> str | None:
    """Retorna o e-mail do usuário logado."""
    if is_user_logged_in() and hasattr(st.user, 'email'):
        return st.user.email.lower().strip()
    return None

def get_user_display_name() -> str:
    """Retorna o nome de exibição do usuário."""
    if is_user_logged_in() and hasattr(st.user, 'name'):
        return st.user.name
    return get_user_email() or "Usuário Desconhecido"

def authenticate_user() -> bool:
    """Verifica o usuário na base de dados. Retorna False se não autorizado."""
    user_email = get_user_email()
    if not user_email:
        return False

    if st.session_state.get('authenticated_user_email') == user_email:
        return True

    matrix_manager = MatrixManager()
    user_info = matrix_manager.get_user_info(user_email)

    if not user_info:
        # ✅ MUDANÇA: Não mostra o erro aqui, apenas retorna False
        # st.error(f"Acesso negado. Seu e-mail ({user_email}) não está autorizado.")
        # st.session_state.clear()
        return False

    # ... (resto do código de autenticação bem-sucedida, inalterado)
    st.session_state.user_info = user_info
    st.session_state.role = user_info.get('role', 'viewer')
    st.session_state.is_single_company_mode = False 

    unit_id = user_info.get('unidade_associada')

    if not unit_id or str(unit_id).strip() == '*':
        st.session_state.unit_name = 'Global'
        st.session_state.unit_id = None
        st.session_state.folder_id = None
    else:
        unit_info = matrix_manager.get_unit_info(unit_id)
        if not unit_info:
            st.error(f"Erro: A unidade associada não foi encontrada.")
            st.session_state.clear()
            return False
        
        st.session_state.unit_name = unit_info.get('nome_unidade')
        st.session_state.unit_id = unit_id
        st.session_state.folder_id = unit_info.get('folder_id')

        try:
            # Lazy import para evitar circular dependency
            from operations.cached_loaders import load_all_unit_data
            unit_data = load_all_unit_data(unit_id)
            companies_df = unit_data.get('companies')
            if companies_df is not None and len(companies_df) == 1:
                company_name = companies_df.iloc[0]['nome']
                if st.session_state.unit_name == company_name:
                    st.session_state.is_single_company_mode = True
                    st.session_state.single_company_id = str(companies_df.iloc[0]['id'])
                    st.session_state.single_company_name = company_name
        except Exception as e:
            st.warning(f"Não foi possível verificar o modo de empresa única: {e}")

    st.session_state.authenticated_user_email = user_email
    
    log_action(
        action="USER_LOGIN",
        details={
            "message": f"Usuário '{user_email}' logado com sucesso.",
            "assigned_role": st.session_state.role,
            "assigned_unit": st.session_state.unit_name,
            "is_single_company_mode": st.session_state.is_single_company_mode
        }
    )
    
    return True

# ✅ NOVA FUNÇÃO: Salvar solicitação de acesso no Supabase
def save_access_request(user_name: str, user_email: str, message: str) -> bool:
    """Salva uma nova solicitação de acesso na tabela 'solicitacoes_acesso'."""
    try:
        # Usa SupabaseOperations sem unit_id para acesso global
        global_ops = SupabaseOperations(unit_id=None)
        
        request_data = {
            "nome_usuario": user_name,
            "email_usuario": user_email,
            "mensagem": message,
            "status": "Pendente"
        }
        
        result = global_ops.insert_row("solicitacoes_acesso", request_data)
        
        if result:
            log_action("ACCESS_REQUEST_SUBMITTED", {"user_email": user_email})
            return True
        else:
            # Verifica se a solicitação já existe (erro de UNIQUE constraint)
            existing = global_ops.get_by_field("solicitacoes_acesso", "email_usuario", user_email)
            if not existing.empty:
                st.warning("Você já possui uma solicitação pendente. Nossa equipe entrará em contato em breve.")
                return True # Retorna True para a UI mostrar a mensagem de sucesso
            st.error("Falha ao enviar a solicitação. Tente novamente.")
            return False
            
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
        return False

def get_user_role() -> str:
    """Retorna o papel (role) do usuário."""
    return st.session_state.get('role', 'viewer')

def is_admin() -> bool:
    """Verifica se o usuário tem o papel de 'admin'."""
    return get_user_role() == 'admin'

def can_edit() -> bool:
    """Verifica se o usuário tem permissão para editar."""
    return get_user_role() in ['admin', 'editor']

def check_permission(level: str = 'editor'):
    """Verifica o nível de permissão e bloqueia a página se não for atendido."""
    if level == 'admin':
        if not is_admin():
            st.error("Acesso restrito a Administradores.")
            st.stop()
    elif level == 'editor':
        if not can_edit():
            st.error("Você não tem permissão para editar. Contate um administrador.")
            st.stop()
    return True

def get_user_unit_id() -> str | None:
    """Retorna o ID da unidade do usuário logado."""
    return st.session_state.get('unit_id')

def get_user_unit_name() -> str:
    """Retorna o nome da unidade do usuário logado."""
    return st.session_state.get('unit_name', 'Nenhuma')

def check_feature_permission(feature_level: str) -> bool:
    """
    Verifica se o usuário atual tem permissão para acessar uma funcionalidade.
    feature_level: 'pro' ou 'premium_ia'
    """
    user_info = st.session_state.get('user_info', {})
    user_role = user_info.get('role')
    user_plan = user_info.get('plano')
    user_status = user_info.get('status_assinatura')

    # 1. Super Admin sempre tem acesso a tudo.
    if user_role == 'admin':
        return True
    
    # 2. Usuário precisa ter uma assinatura ativa ou em trial.
    if user_status not in ['ativo', 'trial']:
        return False
        
    # 3. Verifica o nível do plano.
    plan_hierarchy = {'pro': 1, 'premium_ia': 2}
    
    user_plan_level = plan_hierarchy.get(user_plan, 0)
    required_level = plan_hierarchy.get(feature_level, 99) # Nível alto se a feature não existir

    return user_plan_level >= required_level
