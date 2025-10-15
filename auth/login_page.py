import streamlit as st
from .auth_utils import is_oidc_available, is_user_logged_in, get_user_display_name, get_user_email, save_access_request
from operations.audit_logger import log_action

def validate_auth_config():
    """Valida se a configuração de autenticação está correta."""
    # ... (código inalterado)
    return True, "Configuração OK"

# ✅ FUNÇÃO MOVIDA PARA O LUGAR CORRETO
def show_access_denied_page():
    """Exibe a página para usuários autenticados mas não autorizados."""
    st.title("SEGMA-SIS | Gestão Inteligente")
    st.header("Acesso Restrito")
    
    user_name = get_user_display_name()
    user_email = get_user_email()

    st.warning(f" Olá, **{user_name}**. Você está autenticado, mas seu e-mail (`{user_email}`) ainda não está cadastrado em nosso sistema.")

    col1, col2 = st.columns([1.5, 1])
    with col2:
        if st.button(" Sair / Trocar de Conta", use_container_width=True):
            try:
                st.logout()
            except Exception:
                st.rerun()

    st.session_state.setdefault('request_submitted', False)

    if st.session_state.request_submitted:
        st.success("✅ Sua solicitação de acesso foi enviada! Nossa equipe avaliará seu pedido e você será notificado por e-mail em breve.")
    else:
        st.markdown("---")
        st.subheader("Solicite seu Acesso")
        st.write("Para obter acesso ao sistema, envie a solicitação abaixo. Sua conta será avaliada e liberada por um administrador.")

        with st.form("access_request_form"):
            message = st.text_area(
                "Deixe uma mensagem (Opcional)", 
                placeholder="Ex: Gostaria de testar o sistema para a minha empresa."
            )
            
            submitted = st.form_submit_button("Enviar Solicitação de Acesso", type="primary")

            if submitted:
                with st.spinner("Enviando solicitação..."):
                    if save_access_request(user_name, user_email, message):
                        st.session_state.request_submitted = True
                        st.rerun()

def show_login_page():
    """Mostra a página de login inicial."""
    st.title("SEGMA-SIS | Gestão Inteligente")
    st.write("Por favor, faça login para acessar o sistema.")
    
    if st.button("Fazer Login com Google"):
        try:
            st.login()
        except Exception as e:
            st.error(f"Erro ao iniciar login: {e}")

def show_user_header():
    """Mostra o cabeçalho com informações do usuário"""
    st.write(f"Bem-vindo, {get_user_display_name()}!")

def show_logout_button():
    """Mostra o botão de logout no sidebar e registra o evento."""
    with st.sidebar:
        if st.button("Sair do Sistema"):
            user_email_to_log = get_user_email()
            
            if user_email_to_log:
                log_action("USER_LOGOUT", {"message": f"Usuário '{user_email_to_log}' deslogado."})
            
            try:
                st.logout()
            except Exception as e:
                st.error(f"Erro ao fazer logout: {str(e)}")
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()