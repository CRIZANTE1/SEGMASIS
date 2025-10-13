import streamlit as st
from gdrive.matrix_manager import MatrixManager

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
    """Verifica o usuário na base de dados e carrega o contexto da unidade."""
    user_email = get_user_email()
    if not user_email:
        return False

    if st.session_state.get('authenticated_user_email') == user_email:
        return True

    matrix_manager = MatrixManager()
    user_info = matrix_manager.get_user_info(user_email)

    if not user_info:
        st.error(f"Acesso negado. Seu e-mail ({user_email}) não está autorizado.")
        st.session_state.clear()
        return False

    st.session_state.user_info = user_info
    st.session_state.role = user_info.get('role', 'viewer')
    
    # ✅ TRATAMENTO CORRETO do '*'
    unit_id = user_info.get('unidade_associada')
    
    if not unit_id or unit_id == '*':
        # Usuário global (admin)
        st.session_state.unit_name = 'Global'
        st.session_state.unit_id = None
        st.session_state.folder_id = None
    else:
        # Usuário de unidade específica
        unit_info = matrix_manager.get_unit_info(unit_id)
        if not unit_info:
            st.error(f"Erro: A unidade associada não foi encontrada.")
            st.session_state.clear()
            return False
        
        st.session_state.unit_name = unit_info.get('nome_unidade')
        st.session_state.unit_id = unit_id
        st.session_state.folder_id = unit_info.get('folder_id')

    st.session_state.authenticated_user_email = user_email
    
    from operations.audit_logger import log_action
    log_action(
        action="USER_LOGIN",
        details={
            "message": f"Usuário '{user_email}' logado com sucesso.",
            "assigned_role": st.session_state.role,
            "assigned_unit": st.session_state.unit_name
        }
    )
    
    return True

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