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
    current_plan = user_info.get('plano')

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

            if st.form_submit_button(" Salvar Alterações", type="primary", width='stretch'):
                if new_name and new_name.strip():
                    updates = {'nome': new_name.strip()}
                    if matrix_manager.update_user(user_info['id'], updates):
                        st.success("✅ Perfil atualizado com sucesso!"); log_action("UPDATE_PROFILE", {"updated_fields": ["nome"]}); st.rerun()
                    else:
                        st.error("❌ Erro ao atualizar perfil.")
                else:
                    st.error("❌ O nome não pode estar vazio.")

    with tab_plan:
        st.header("📊 Meu Plano e Limites de IA")

        # ✅ Definir informações dos planos baseadas nos limites REAIS da API
        limits_info = {
            'admin': {
                'name': '👑 Super Administrador',
                'model': 'Acesso a ambos os modelos',
                'api_limit_minute': 'Ilimitado',
                'api_limit_day': 'Ilimitado',
                'color': 'gold',
                'features': [
                    '✅ Análises ilimitadas com IA',
                    '✅ Gemini 2.5 Flash para extrações rápidas',
                    '✅ Gemini 2.5 Pro para auditorias complexas',
                    '✅ Acesso a todas as funcionalidades',
                    '✅ Gerenciamento global do sistema',
                    '✅ Sem restrições de uso'
                ]
            },
            'premium_ia': {
                'name': '💎 Premium IA',
                'model': 'Gemini 2.5 Pro',
                'api_limit_minute': '5 análises/minuto',
                'api_limit_day': '100 análises/dia',
                'color': 'purple',
                'features': [
                    '✅ Gemini 2.5 Pro (modelo mais avançado)',
                    '✅ 5 análises por minuto',
                    '✅ 100 análises por dia',
                    '✅ Auditoria avançada de documentos',
                    '✅ Análise profunda de conformidade',
                    '✅ Análise de Fichas de EPI',
                    '✅ Prioridade no processamento',
                    '⚡ Ideal para auditorias complexas'
                ]
            },
            'pro': {
                'name': '🚀 Pro',
                'model': 'Gemini 2.5 Flash',
                'api_limit_minute': '10 análises/minuto',
                'api_limit_day': '250 análises/dia',
                'color': 'blue',
                'features': [
                    '✅ Gemini 2.5 Flash (rápido e eficiente)',
                    '✅ 10 análises por minuto',
                    '✅ 250 análises por dia',
                    '✅ Análise de ASOs e Treinamentos',
                    '✅ Extração rápida de dados',
                    '✅ Dashboard completo',
                    '⚡ Ideal para extração de dados em volume'
                ]
            }
        }

        # ✅ Obter informações do plano atual
        if current_role == 'admin':
            plan_key = 'admin'
        elif current_plan in ['pro', 'premium_ia']:
            plan_key = current_plan
        else:
            # Usuário sem plano
            st.error("""
            ❌ **Você não possui um plano ativo**

            Para usar as funcionalidades de IA, você precisa de um dos planos:
            - **Pro**: Para extração rápida de dados (10/min, 250/dia)
            - **Premium IA**: Para auditorias complexas (5/min, 100/dia)

            Entre em contato com o administrador para ativar seu plano.
            """)
            return

        plan_info = limits_info[plan_key]

        # ✅ Exibir em cards estilizados
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {plan_info['color']} 0%, {plan_info['color']}33 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        ">
            <h2 style="margin: 0; color: white;">{plan_info['name']}</h2>
            <p style="margin: 5px 0 0 0; color: white; opacity: 0.9;">
                Modelo: {plan_info['model']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "⚡ Limite por Minuto",
                plan_info['api_limit_minute'],
                help="Número máximo de análises com IA por minuto"
            )

        with col2:
            st.metric(
                "📊 Limite Diário",
                plan_info['api_limit_day'],
                help="Número máximo de análises com IA por dia"
            )

        st.markdown("---")
        st.markdown("#### 🎯 Recursos do Seu Plano")

        for feature in plan_info['features']:
            st.markdown(f"- {feature}")

        # ✅ Comparação de planos (se não for admin)
        if current_role != 'admin':
            st.markdown("---")
            st.markdown("#### 📊 Comparação de Planos")

            comparison_df = pd.DataFrame({
                'Recurso': [
                    'Modelo de IA',
                    'Análises/minuto',
                    'Análises/dia',
                    'Extração de Dados',
                    'Auditoria Avançada',
                    'Análise de EPIs',
                    'Velocidade'
                ],
                '🚀 Pro': [
                    'Gemini 2.5 Flash',
                    '10',
                    '250',
                    '✅ Sim',
                    '⚠️ Básica',
                    '❌ Não',
                    '⚡ Muito Rápida'
                ],
                '💎 Premium IA': [
                    'Gemini 2.5 Pro',
                    '5',
                    '100',
                    '✅ Sim',
                    '✅ Completa',
                    '✅ Sim',
                    '🎯 Precisa'
                ]
            })

            st.dataframe(comparison_df, width='stretch', hide_index=True)

            # ✅ Botão de upgrade
            if current_plan == 'pro':
                st.info("""
                💡 **Quer análises mais profundas?**

                O plano **Premium IA** oferece:
                - Gemini 2.5 Pro para auditorias mais precisas
                - Análise de conformidade avançada
                - Suporte a Fichas de EPI

                Entre em contato com o administrador para fazer upgrade!
                """)
            else:
                st.success("""
                🎉 **Você está no nosso melhor plano!**

                Aproveite todas as funcionalidades avançadas do sistema.
                """)

        # ✅ Add real-time usage monitoring
        if current_role != 'admin' and current_plan in ['pro', 'premium_ia']:
            st.markdown("---")
            st.markdown("#### 📊 Seu Uso em Tempo Real")

            # Criar instância do rate limiter
            from AI.api_Operation import PDFQA

            rate_limiter = PDFQA._rate_limiters.get(current_plan)

            if rate_limiter:
                # Obter estatísticas
                stats = rate_limiter.get_usage_stats(user_email)
                remaining = rate_limiter.get_remaining_calls(user_email, current_role)

                # Métricas
                col_use1, col_use2 = st.columns(2)

                with col_use1:
                    # Uso por minuto
                    pct_minute = (stats['calls_last_minute'] / stats['rpm_limit']) * 100
                    st.metric(
                        "⚡ Uso no Último Minuto",
                        f"{stats['calls_last_minute']}/{stats['rpm_limit']}",
                        f"{remaining['per_minute'] if isinstance(remaining, dict) else '∞'} restantes"
                    )
                    st.progress(pct_minute / 100)

                with col_use2:
                    # Uso diário
                    pct_day = (stats['calls_today'] / stats['rpd_limit']) * 100
                    st.metric(
                        "📅 Uso Hoje",
                        f"{stats['calls_today']}/{stats['rpd_limit']}",
                        f"{remaining['per_day'] if isinstance(remaining, dict) else '∞'} restantes"
                    )
                    st.progress(pct_day / 100)

                # Alertas
                if isinstance(remaining, dict) and remaining['per_minute'] <= 2:
                    st.warning("⚠️ Você está próximo do limite por minuto!")

                if isinstance(remaining, dict) and remaining['per_day'] <= 10:
                    st.warning("⚠️ Você está próximo do limite diário!")

                # Botão de refresh
                if st.button("🔄 Atualizar Estatísticas", key="refresh_stats"):
                    st.rerun()

    with tab_support:
        st.header(" Central de Suporte")
        with st.form("support_form"):
            st.subheader(" Enviar Solicitação de Suporte")
            support_type = st.selectbox("Tipo da Solicitação", ["Dúvida", "Problema Técnico", "Sugestão"])
            subject = st.text_input("Assunto *", placeholder="Descreva brevemente sua solicitação")
            message = st.text_area("Descrição Detalhada *", height=150)
            
            if st.form_submit_button(" Enviar Solicitação", type="primary", width='stretch'):
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
