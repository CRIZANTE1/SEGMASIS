import streamlit as st
from .auth_utils import is_oidc_available, is_user_logged_in, get_user_display_name, get_user_email
from operations.audit_logger import log_action

def validate_auth_config():
    """
    Valida se a configuração de autenticação está correta.
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    required_keys = ['provider', 'client_id', 'client_secret', 'cookie_secret', 'redirect_uri']
    
    # Verifica se secrets existe
    if not hasattr(st, 'secrets'):
        return False, "Arquivo secrets.toml não encontrado"
    
    # Verifica se a seção [auth] existe
    if 'auth' not in st.secrets:
        return False, "Seção [auth] não encontrada no secrets.toml. Use [auth] em vez de [oidc]"
    
    auth_config = st.secrets.auth
    
    # Verifica chaves faltando
    missing = [key for key in required_keys if key not in auth_config]
    if missing:
        return False, f"Chaves faltando na seção [auth]: {', '.join(missing)}"
    
    # Valida tamanho do cookie_secret
    cookie_secret = auth_config.cookie_secret
    if len(cookie_secret) < 32:
        return False, f"cookie_secret muito curto ({len(cookie_secret)} caracteres, mínimo: 32)"
    
    if len(cookie_secret) < 64:
        st.warning(f"⚠️ cookie_secret tem apenas {len(cookie_secret)} caracteres. Recomendado: 64+")
    
    # Valida formato do client_id para Google
    if auth_config.provider.lower() == 'google':
        if not auth_config.client_id.endswith('.apps.googleusercontent.com'):
            return False, "client_id do Google deve terminar com .apps.googleusercontent.com"
    
    # Valida redirect_uri
    redirect_uri = auth_config.redirect_uri
    if not redirect_uri.startswith('http'):
        return False, f"redirect_uri inválido: {redirect_uri}"
    
    return True, "✅ Configuração válida"

def show_login_page():
    """Mostra a página de login"""
    
    if not is_oidc_available():
        st.error("O sistema de autenticação não está disponível!")
        st.markdown("""
        ### Requisitos para o Sistema de Login
        """)
        return False
        
    if not is_user_logged_in():
        st.markdown("### Acesso ao Sistema")
        st.write("Por favor, faça login para acessar o sistema.")

        # Valida configuração antes de mostrar botão
        is_valid, validation_message = validate_auth_config()

        if not is_valid:
            st.error(f"❌ Erro de configuração: {validation_message}")
            with st.expander("📖 Como configurar corretamente"):
                st.code("""
# .streamlit/secrets.toml

[auth]
provider = "google"
client_id = "seu-id.apps.googleusercontent.com"
client_secret = "seu-secret"
cookie_secret = "gere-um-secret-com-64-caracteres"
redirect_uri = "https://sua-app.streamlit.app"
                """, language="toml")
            st.stop()

        st.success(validation_message)
        
        # Botão de login
        if st.button("Fazer Login com Google"):
            try:
                st.login()
            except Exception as e:
                st.error(f"Erro ao iniciar login: {str(e)}")
                st.warning("Verifique se as configurações OIDC estão corretas no arquivo secrets.toml")
        return False
        
    return True

def show_user_header():
    """Mostra o cabeçalho com informações do usuário"""
    st.write(f"Bem-vindo, {get_user_display_name()}!")

def show_logout_button():
    """Mostra o botão de logout no sidebar e registra o evento."""
    with st.sidebar:
        if st.button("Sair do Sistema"):
            # Coleta o e-mail ANTES de fazer o logout
            user_email_to_log = get_user_email()
            
            # Registra o evento de logout
            if user_email_to_log:
                log_action(
                    action="USER_LOGOUT",
                    details={
                        "message": f"Usuário '{user_email_to_log}' deslogado do sistema."
                    }
                )
            
            # Continua com a lógica de logout
            try:
                st.logout()
                # Limpar a sessão manualmente como fallback
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao fazer logout: {str(e)}")
                # Força a limpeza da sessão em caso de erro
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

