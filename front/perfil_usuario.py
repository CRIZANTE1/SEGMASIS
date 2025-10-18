import streamlit as st
import pandas as pd
from datetime import datetime
import logging

from auth.auth_utils import get_user_email, get_user_display_name
from managers.matrix_manager import MatrixManager
from operations.audit_logger import log_action

logger = logging.getLogger('segsisone_app.perfil_usuario')

def show_profile_page():
    st.title(" Meu Perfil e Configurações")

    user_email = get_user_email()
    if not user_email:
        st.error("❌ Usuário não autenticado."); st.stop()

    matrix_manager = MatrixManager()
    user_info = matrix_manager.get_user_info(user_email)
    
    if not user_info:
        st.error("❌ Não foi possível carregar as informações do usuário."); st.stop()

    user_name = user_info.get('nome', get_user_display_name())
    current_role = user_info.get('role', 'viewer')

    tab_profile, tab_plan, tab_support = st.tabs([
        " Meus Dados", 
        " Meu Acesso", 
        " Suporte"
    ])

    with tab_profile:
        st.header(" Informações do Perfil")
        plan_display = {"admin": "Super Admin", "editor": "Editor", "viewer": "Visualizador"}.get(current_role, "Desconhecido")
        st.metric("Nível de Acesso (Role)", plan_display)
        
        with st.form("profile_form"):
            st.subheader("✏️ Editar Meus Dados")
            new_name = st.text_input("Nome Completo *", value=user_name)
            st.text_input("Email", value=user_email, disabled=True)

            if st.form_submit_button(" Salvar Alterações", type="primary", use_container_width=True):
                if new_name.strip():
                    updates = {'nome': new_name.strip()}
                    if matrix_manager.update_user(user_info['id'], updates):
                        st.success("✅ Perfil atualizado com sucesso!"); log_action("UPDATE_PROFILE", {"updated_fields": ["nome"]}); st.rerun()
                    else:
                        st.error("❌ Erro ao atualizar perfil.")
                else:
                    st.error("❌ O nome não pode estar vazio.")

    with tab_plan:
        st.header(" Meu Nível de Acesso")
        st.info("A funcionalidade de upgrade de plano e pagamento será implementada em breve.")
        st.subheader(f"Seu nível de acesso atual: **{plan_display}**")
        st.markdown("""
        - **Visualizador (Viewer):** Pode ver todos os dashboards e dados, mas não pode adicionar ou editar registros.
        - **Editor:** Tem permissões completas para gerenciar todos os dados da unidade/empresa associada.
        - **Super Admin:** Tem acesso global a todas as unidades e pode gerenciar o sistema.
        \nPara alterar seu nível de acesso, por favor, entre em contato com o administrador do sistema.
        """)

    with tab_support:
        st.header(" Central de Suporte")
        with st.form("support_form"):
            st.subheader(" Enviar Solicitação de Suporte")
            support_type = st.selectbox("Tipo da Solicitação", ["Dúvida", "Problema Técnico", "Sugestão"])
            subject = st.text_input("Assunto *", placeholder="Descreva brevemente sua solicitação")
            message = st.text_area("Descrição Detalhada *", height=150)
            
            if st.form_submit_button(" Enviar Solicitação", type="primary", use_container_width=True):
                if subject.strip() and message.strip():
                    try:
                        from operations.supabase_operations import SupabaseOperations
                        global_ops = SupabaseOperations(unit_id=None)
                        support_data = {
                            "email_usuario": user_email, "nome_usuario": user_name,
                            "tipo_solicitacao": support_type, "assunto": subject.strip(),
                            "mensagem": message.strip(), "status": "Pendente"
                        }
                        if global_ops.insert_row("solicitacoes_suporte", support_data):
                            st.success(f"✅ Solicitação enviada com sucesso!"); log_action("SUPPORT_REQUEST", {"subject": subject.strip()})
                        else: st.error("❌ Erro ao enviar solicitação.")
                    except Exception as e:
                        st.error(f"❌ Erro: {e}"); logger.error(f"Erro ao criar ticket de suporte: {e}")
                else:
                    st.error("❌ Assunto e mensagem são obrigatórios.")