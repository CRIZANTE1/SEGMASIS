import streamlit as st
import pandas as pd
from datetime import date
from auth.auth_utils import is_user_logged_in, authenticate_user

def format_company_display(cid, companies_df):
    if cid is None:
        return "Selecione uma empresa..."
    
    cid_str = str(cid)
    if companies_df.empty:
        return f"ID: {cid_str}"
    
    company_row = companies_df[companies_df['id'] == cid_str]
    if company_row.empty:
        return f"ID: {cid_str} (Não encontrado)"
        
    company_name = company_row.iloc[0]['nome']
    return company_name

def get_document_link(doc_id: str, employee_manager, docs_manager) -> str | None:
    """
    Busca o link do documento original usando o ID.
    Verifica em ASOs, Treinamentos e Documentos da Empresa.
    """
    if not doc_id or str(doc_id).strip() == "" or str(doc_id) == 'None':
        return None
    
    doc_id_str = str(doc_id)
    
    # Busca em ASOs
    if not employee_manager.aso_df.empty:
        aso_match = employee_manager.aso_df[employee_manager.aso_df['id'] == doc_id_str]
        if not aso_match.empty:
            link = aso_match.iloc[0].get('arquivo_id')
            if link and str(link).strip():
                return str(link)
    
    # Busca em Treinamentos
    if not employee_manager.training_df.empty:
        training_match = employee_manager.training_df[employee_manager.training_df['id'] == doc_id_str]
        if not training_match.empty:
            link = training_match.iloc[0].get('anexo')
            if link and str(link).strip():
                return str(link)
    
    # Busca em Documentos da Empresa
    if not docs_manager.docs_df.empty:
        doc_match = docs_manager.docs_df[docs_manager.docs_df['id'] == doc_id_str]
        if not doc_match.empty:
            link = doc_match.iloc[0].get('arquivo_id')
            if link and str(link).strip():
                return str(link)
    
    return None

def show_plano_acao_page():
    st.title("📋 Plano de Ação")
    
    if not is_user_logged_in():
        st.warning("Faça login para acessar esta página.")
        return
    
    if not authenticate_user():
        return
    
    is_global_view = st.session_state.get('unit_name') == 'Global'
    
    if is_global_view:
        st.info("📊 Visão Global do Plano de Ação")
        st.warning("A visão global consolidada ainda não foi implementada. Selecione uma unidade específica no menu lateral.")
        return
    
    if not st.session_state.get('managers_initialized'):
        st.warning("Aguardando inicialização dos dados da unidade...")
        return
    
    action_plan_manager = st.session_state.action_plan_manager
    employee_manager = st.session_state.employee_manager
    docs_manager = st.session_state.docs_manager
    
    # ✅ CORREÇÃO: Garante que os IDs das empresas sejam strings para o selectbox
    company_options = [None] + employee_manager.companies_df['id'].astype(str).tolist()
    selected_company_id = st.selectbox(
        "Selecione uma empresa:",
        options=company_options,
        format_func=lambda cid: format_company_display(cid, employee_manager.companies_df),
        key="company_selector_plano"
    )
    
    if selected_company_id:
        company_name = employee_manager.get_company_name(selected_company_id)
        st.header(f"Itens Pendentes para: {company_name}")
        
        action_items_df = action_plan_manager.get_action_items_by_company(selected_company_id)
        
        pending_items = pd.DataFrame()
        if not action_items_df.empty and 'status' in action_items_df.columns:
            pending_items = action_items_df[
                ~action_items_df['status'].str.lower().isin(['concluído', 'cancelado'])
            ]
        
        if pending_items.empty:
            st.success("🎉 Nenhuma não conformidade pendente para esta empresa!")
        else:
            for _, row in pending_items.iterrows():
                with st.container(border=True):
                    col_title, col_link = st.columns([5, 1])
                    
                    with col_title:
                        st.markdown(f"**Item:** {row['item_nao_conforme']}")
                    
                    with col_link:
                        doc_id = row.get('id_documento_original')
                        if doc_id:
                            doc_link = get_document_link(doc_id, employee_manager, docs_manager)
                            if doc_link:
                                st.link_button("📄 PDF", doc_link, use_container_width=True)
                    
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.caption(f"🏢 **Empresa:** {company_name}")
                        st.caption(f"📋 **ID Doc:** {row.get('id_documento_original', 'N/A')}")
                    
                    with col_info2:
                        employee_id = row.get('id_funcionario')
                        if employee_id and str(employee_id).strip() and str(employee_id) != 'None':
                            employee_name = employee_manager.get_employee_name(employee_id)
                            if employee_name and not employee_name.startswith("ID "):
                                st.caption(f"👤 **Funcionário:** {employee_name}")
                                st.caption(f"🆔 **ID Func:** {employee_id}")
                            else:
                                st.caption(f"👤 **Funcionário:** ID {employee_id}")
                    
                    ref_normativa = row.get('referencia_normativa', 'N/A')
                    if ref_normativa and ref_normativa != 'N/A':
                        st.info(f"📖 **Referência Normativa:** {ref_normativa}")
                    
                    col1, col2 = st.columns([4, 1])
                    status = row.get('status', 'Aberto')
                    status_color = {'aberto': '🔴', 'em tratamento': '🟡', 'aguardando': '🟠'}
                    emoji = status_color.get(status.lower(), '⚪')
                    col1.markdown(f"**Status:** {emoji} {status}")
                    
                    if col2.button("⚙️ Tratar", key=f"treat_{row['id']}", use_container_width=True):
                        st.session_state.current_item_to_treat = row.to_dict()
                        st.rerun()
    
    if 'current_item_to_treat' in st.session_state:
        show_treatment_dialog(action_plan_manager)

def show_treatment_dialog(action_plan_manager):
    @st.dialog("Tratar Item de Não Conformidade")
    def treatment_form():
        item = st.session_state.current_item_to_treat
        
        st.markdown(f"**Item:** {item['item_nao_conforme']}")
        st.caption(f"**ID:** {item['id']}")
        
        with st.form("treatment_form"):
            plano_acao = st.text_area("Plano de Ação", value=item.get('plano_de_acao', ''))
            responsavel = st.text_input("Responsável", value=item.get('responsavel', ''))
            
            # ✅ CORREÇÃO: Lida com datas que podem ser None ou NaT (Not a Time)
            prazo_val = pd.to_datetime(item.get('prazo')).date() if pd.notna(item.get('prazo')) else None
            prazo = st.date_input("Prazo", value=prazo_val)
            
            status_options = ["Aberto", "Em Tratamento", "Aguardando", "Concluído", "Cancelado"]
            current_status = item.get('status', 'Aberto')
            current_status_index = status_options.index(current_status) if current_status in status_options else 0
            novo_status = st.selectbox("Status", status_options, index=current_status_index)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                    updates = {
                        'plano_de_acao': plano_acao,
                        'responsavel': responsavel,
                        'status': novo_status,
                        'prazo': prazo.strftime("%Y-%m-%d") if prazo else None
                    }
                    
                    if novo_status == "Concluído":
                        updates['data_conclusao'] = date.today().strftime("%Y-%m-%d")
                    
                    if action_plan_manager.update_action_item(str(item['id']), updates):
                        st.success("Item atualizado com sucesso!")
                        del st.session_state.current_item_to_treat
                        st.rerun()
                    else:
                        st.error("Falha ao atualizar o item.")
            
            with col2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    del st.session_state.current_item_to_treat
                    st.rerun()
    
    treatment_form()
