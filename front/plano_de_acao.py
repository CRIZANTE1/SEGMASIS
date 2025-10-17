import streamlit as st
import pandas as pd
from datetime import date, timedelta
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

def get_status_color(status: str) -> str:
    """Retorna emoji colorido baseado no status."""
    status_lower = status.lower()
    if status_lower == 'aberto':
        return '🔴'
    elif status_lower == 'em tratamento':
        return '🟡'
    elif status_lower == 'aguardando':
        return '🟠'
    elif status_lower == 'concluído':
        return '🟢'
    elif status_lower == 'cancelado':
        return '⚫'
    else:
        return '⚪'

def get_priority_by_date(prazo) -> tuple:
    """Retorna prioridade e cor baseado no prazo."""
    if not prazo or pd.isna(prazo):
        return ("Sem prazo", "⚪")
    
    prazo_date = pd.to_datetime(prazo).date()
    today = date.today()
    dias_restantes = (prazo_date - today).days
    
    if dias_restantes < 0:
        return (f"Atrasado ({abs(dias_restantes)} dias)", "🔴")
    elif dias_restantes == 0:
        return ("Vence hoje!", "🔴")
    elif dias_restantes <= 7:
        return (f"Urgente ({dias_restantes} dias)", "🟠")
    elif dias_restantes <= 15:
        return (f"Em breve ({dias_restantes} dias)", "🟡")
    else:
        return (f"{dias_restantes} dias", "🟢")

def show_plano_acao_page():
    st.title("📋 Plano de Ação")
    
    if not is_user_logged_in():
        st.warning("⚠️ Faça login para acessar esta página.")
        return
    
    if not authenticate_user():
        return
    
    is_global_view = st.session_state.get('unit_name') == 'Global'
    
    if is_global_view:
        st.info("📊 Visão Global do Plano de Ação")
        st.warning("⚠️ A visão global consolidada ainda não foi implementada. Selecione uma unidade específica no menu lateral.")
        return
    
    if not st.session_state.get('managers_initialized'):
        st.warning("⏳ Aguardando inicialização dos dados da unidade...")
        return
    
    action_plan_manager = st.session_state.action_plan_manager
    employee_manager = st.session_state.employee_manager
    docs_manager = st.session_state.docs_manager
    
    # Filtros no topo
    col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])
    
    with col_filter1:
        # Seletor de empresa
        company_options = [None] + employee_manager.companies_df['id'].astype(str).tolist()
        selected_company_id = st.selectbox(
            "🏢 Selecione uma empresa:",
            options=company_options,
            format_func=lambda cid: format_company_display(cid, employee_manager.companies_df),
            key="company_selector_plano"
        )
    
    with col_filter2:
        # Filtro de status
        status_filter = st.selectbox(
            "🎯 Filtrar por Status:",
            options=['Todos', 'Aberto', 'Em Tratamento', 'Aguardando', 'Concluído', 'Cancelado'],
            key="status_filter_plano"
        )
    
    with col_filter3:
        # Ordenação
        sort_by = st.selectbox(
            "📊 Ordenar por:",
            options=['Data de Criação ⬇️', 'Prazo ⬆️', 'Status'],
            key="sort_filter_plano"
        )
    
    if not selected_company_id:
        st.info("👈 Selecione uma empresa para visualizar o plano de ação.")
        return
    
    company_name = employee_manager.get_company_name(selected_company_id)
    st.header(f"📋 Plano de Ação: {company_name}")
    
    # Busca itens do plano de ação
    action_items_df = action_plan_manager.get_action_items_by_company(selected_company_id)
    
    if action_items_df.empty:
        st.success("🎉 Nenhum item no plano de ação para esta empresa!")
        st.balloons()
        return
    
    # Aplica filtro de status
    if status_filter != 'Todos':
        if status_filter == 'Aberto':
            action_items_df = action_items_df[
                ~action_items_df['status'].str.lower().isin(['concluído', 'cancelado'])
            ]
        else:
            action_items_df = action_items_df[
                action_items_df['status'].str.lower() == status_filter.lower()
            ]
    
    # Aplica ordenação
    if sort_by == 'Data de Criação ⬇️':
        action_items_df = action_items_df.sort_values('data_criacao', ascending=False)
    elif sort_by == 'Prazo ⬆️':
        action_items_df = action_items_df.sort_values('prazo', ascending=True, na_position='last')
    elif sort_by == 'Status':
        action_items_df = action_items_df.sort_values('status')
    
    if action_items_df.empty:
        st.info(f"ℹ️ Nenhum item encontrado com o filtro: **{status_filter}**")
        return
    
    # Estatísticas do plano
    st.markdown("---")
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    total_items = len(action_items_df)
    abertos = len(action_items_df[action_items_df['status'].str.lower() == 'aberto'])
    em_tratamento = len(action_items_df[action_items_df['status'].str.lower() == 'em tratamento'])
    concluidos = len(action_items_df[action_items_df['status'].str.lower() == 'concluído'])
    
    col_stat1.metric("📊 Total de Itens", total_items)
    col_stat2.metric("🔴 Abertos", abertos, delta_color="inverse")
    col_stat3.metric("🟡 Em Tratamento", em_tratamento)
    col_stat4.metric("🟢 Concluídos", concluidos, delta_color="off")
    
    st.markdown("---")
    
    # Exibe os itens
    for idx, (_, row) in enumerate(action_items_df.iterrows(), 1):
        with st.container(border=True):
            # Cabeçalho do item
            col_header1, col_header2, col_header3 = st.columns([4, 1, 1])
            
            with col_header1:
                status_emoji = get_status_color(row.get('status', 'Aberto'))
                st.markdown(f"### {status_emoji} Item #{idx}: {row.get('status', 'Aberto')}")
            
            with col_header2:
                # Prioridade por prazo
                prazo = row.get('prazo')
                if prazo and pd.notna(prazo):
                    priority_text, priority_emoji = get_priority_by_date(prazo)
                    st.markdown(f"**{priority_emoji} {priority_text}**")
            
            with col_header3:
                # Link para o PDF original
                doc_id = row.get('id_documento_original')
                if doc_id:
                    doc_link = get_document_link(doc_id, employee_manager, docs_manager)
                    if doc_link:
                        st.link_button("📄 Ver PDF", doc_link, use_container_width=True)
            
            # Descrição da não conformidade
            st.markdown("#### 📌 Não Conformidade")
            st.info(row['item_nao_conforme'])
            
            # Referência normativa
            ref_normativa = row.get('referencia_normativa', 'N/A')
            if ref_normativa and ref_normativa != 'N/A':
                st.caption(f"📖 **Referência Normativa:** {ref_normativa}")
            
            # Informações adicionais em colunas
            col_info1, col_info2, col_info3 = st.columns(3)
            
            with col_info1:
                st.markdown("**🏢 Empresa**")
                st.text(company_name)
            
            with col_info2:
                employee_id = row.get('id_funcionario')
                if employee_id and str(employee_id).strip() and str(employee_id) != 'None':
                    employee_name = employee_manager.get_employee_name(employee_id)
                    if employee_name and not employee_name.startswith("ID "):
                        st.markdown("**👤 Funcionário**")
                        st.text(employee_name)
            
            with col_info3:
                doc_id = row.get('id_documento_original', 'N/A')
                st.markdown("**📄 ID do Documento**")
                st.text(doc_id if doc_id != 'None' else 'N/A')
            
            # Plano de ação atual (se existir)
            plano_atual = row.get('plano_de_acao', '')
            responsavel_atual = row.get('responsavel', '')
            prazo_atual = row.get('prazo')
            evidencia_url = row.get('evidencia_arquivo_id')  # ✅ ADICIONAR

            if plano_atual or responsavel_atual or prazo_atual or evidencia_url:  # ✅ MODIFICAR
                st.markdown("---")
                st.markdown("#### 📝 Plano de Ação Atual")

                col_plano1, col_plano2 = st.columns([2, 1])

                with col_plano1:
                    if plano_atual:
                        st.markdown("**Ação Definida:**")
                        st.success(plano_atual)

                with col_plano2:
                    if responsavel_atual:
                        st.markdown("**Responsável:**")
                        st.text(responsavel_atual)
                    if prazo_atual and pd.notna(prazo_atual):
                        st.markdown("**Prazo:**")
                        prazo_formatado = pd.to_datetime(prazo_atual).strftime('%d/%m/%Y')
                        st.text(prazo_atual)

                # ✅ ADICIONAR: Seção de evidência
                if evidencia_url and pd.notna(evidencia_url):
                    st.markdown("---")
                    col_ev1, col_ev2 = st.columns([3, 1])
                    with col_ev1:
                        st.markdown("**📎 Evidência Anexada:**")
                        st.link_button("📄 Ver Evidência", evidencia_url, use_container_width=True)
                    with col_ev2:
                        if st.button("🗑️ Remover", key=f"remove_ev_{row['id']}", use_container_width=True):
                            success, msg = action_plan_manager.delete_evidencia(str(row['id']))
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
            
            # Data de criação e conclusão
            col_date1, col_date2 = st.columns(2)
            
            with col_date1:
                data_criacao = row.get('data_criacao')
                if data_criacao and pd.notna(data_criacao):
                    st.caption(f"📅 Criado em: {pd.to_datetime(data_criacao).strftime('%d/%m/%Y')}")
            
            with col_date2:
                data_conclusao = row.get('data_conclusao')
                if data_conclusao and pd.notna(data_conclusao):
                    st.caption(f"✅ Concluído em: {pd.to_datetime(data_conclusao).strftime('%d/%m/%Y')}")
            
            # Botões de ação
            st.markdown("---")
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([2, 1, 1, 1])  # ✅ MODIFICAR: 4 colunas

            with col_btn1:
                if st.button("✏️ Editar Item", key=f"treat_{row['id']}", use_container_width=True, type="primary"):
                    st.session_state.current_item_to_treat = row.to_dict()
                    st.rerun()

            with col_btn2:
                if row.get('status', '').lower() not in ['concluído', 'cancelado']:
                    plano_vazio = not plano_atual or str(plano_atual).strip() == ''

                    if plano_vazio:
                        st.button(
                            "✅ Concluir",
                            key=f"complete_{row['id']}",
                            use_container_width=True,
                            disabled=True,
                            help="⚠️ Defina um plano de ação primeiro"
                        )
                    else:
                        if st.button("✅ Concluir", key=f"complete_{row['id']}", use_container_width=True):
                            with st.spinner("Concluindo item..."):
                                updates = {
                                    'status': 'Concluído',
                                    'data_conclusao': date.today().strftime("%Y-%m-%d")
                                }

                                if action_plan_manager.update_action_item(str(row['id']), updates):
                                    from operations.cached_loaders import load_all_unit_data
                                    load_all_unit_data.clear()
                                    st.cache_data.clear()
                                    st.session_state.force_reload_managers = True

                                    st.success("✅ Item marcado como concluído!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ Falha ao concluir o item.")

            # ✅ ADICIONAR: Botão de evidência
            with col_btn3:
                if row.get('status', '').lower() not in ['concluído', 'cancelado']:
                    if st.button("📎 Evidência", key=f"evidence_{row['id']}", use_container_width=True):
                        st.session_state.show_evidence_dialog = True
                        st.session_state.evidence_item_id = row['id']
                        st.rerun()

            with col_btn4:
                if st.button("🗑️ Excluir", key=f"delete_{row['id']}", use_container_width=True):
                    st.session_state.show_delete_action_item = True
                    st.session_state.action_item_to_delete = row['id']
                    st.rerun()
    
    # Diálogo de edição
    if 'current_item_to_treat' in st.session_state:
        show_treatment_dialog(action_plan_manager)
    
    # Diálogo de exclusão
    if st.session_state.get('show_delete_action_item'):
        show_delete_dialog(action_plan_manager)

    # ✅ ADICIONAR: Diálogo de evidência
    if st.session_state.get('show_evidence_dialog'):
        show_evidence_dialog(action_plan_manager)

def show_treatment_dialog(action_plan_manager):
    """Diálogo aprimorado para editar itens do plano de ação."""
    
    @st.dialog("✏️ Editar Item de Não Conformidade", width="large")
    def treatment_form():
        item = st.session_state.current_item_to_treat
        
        st.markdown(f"### 📌 {item['item_nao_conforme'][:100]}...")
        st.caption(f"**ID:** {item['id']}")

        # ✅ ADICIONAR: Mostrar evidência se existir
        evidencia_url = item.get('evidencia_arquivo_id')
        if evidencia_url and pd.notna(evidencia_url):
            st.info("📎 Este item já possui uma evidência anexada")
            st.link_button("📄 Ver Evidência Atual", evidencia_url)

        with st.form("treatment_form"):
            st.markdown("#### 📝 Plano de Ação")
            
            # Plano de ação
            plano_acao = st.text_area(
                "Descrição das Ações Corretivas *",
                value=item.get('plano_de_acao', ''),
                height=120,
                placeholder="Descreva as ações que serão tomadas para resolver esta não conformidade...",
                help="Seja específico sobre as ações que serão realizadas"
            )
            
            # Responsável e Prazo
            col1, col2 = st.columns(2)
            
            with col1:
                responsavel = st.text_input(
                    "👤 Responsável pela Execução",
                    value=item.get('responsavel', ''),
                    placeholder="Nome do responsável",
                    help="Quem será responsável por executar as ações"
                )
            
            with col2:
                prazo_val = pd.to_datetime(item.get('prazo')).date() if pd.notna(item.get('prazo')) else None
                prazo = st.date_input(
                    "📅 Prazo para Conclusão",
                    value=prazo_val if prazo_val else date.today() + timedelta(days=30),
                    min_value=date.today(),
                    help="Data limite para concluir as ações"
                )
            
            # Status
            st.markdown("#### 🎯 Status do Item")
            
            status_options = ["Aberto", "Em Tratamento", "Aguardando", "Concluído", "Cancelado"]
            current_status = item.get('status', 'Aberto')
            current_status_index = status_options.index(current_status) if current_status in status_options else 0
            novo_status = st.selectbox(
                "Status Atual",
                status_options,
                index=current_status_index,
                help="Atualize o status conforme o andamento"
            )
            
            # Observações adicionais
            observacoes = st.text_area(
                "💬 Observações / Histórico",
                placeholder="Registre aqui atualizações, dificuldades encontradas, ou qualquer informação relevante...",
                height=80,
                help="Campo opcional para registrar o histórico de tratamento"
            )
            
            # Informações de referência (somente leitura)
            with st.expander("📋 Informações de Referência"):
                st.markdown(f"**Referência Normativa:** {item.get('referencia_normativa', 'N/A')}")
                st.markdown(f"**ID Documento Original:** {item.get('id_documento_original', 'N/A')}")
                st.markdown(f"**ID Funcionário:** {item.get('id_funcionario', 'N/A') if item.get('id_funcionario') else 'N/A'}")
                st.markdown(f"**Criado em:** {pd.to_datetime(item.get('data_criacao')).strftime('%d/%m/%Y') if pd.notna(item.get('data_criacao')) else 'N/A'}")
            
            st.markdown("---")
            
            # Botões de ação
            col_save, col_cancel = st.columns([3, 1])
            
            with col_save:
                save_button = st.form_submit_button(
                    "💾 Salvar Alterações",
                    type="primary",
                    use_container_width=True
                )
            
            with col_cancel:
                cancel_button = st.form_submit_button(
                    "❌ Cancelar",
                    use_container_width=True
                )
            
            if cancel_button:
                del st.session_state.current_item_to_treat
                st.rerun()
            
            if save_button:
                # Validações
                if not plano_acao.strip():
                    st.error("❌ O plano de ação não pode estar vazio!")
                    st.stop()
                
                if not responsavel.strip():
                    st.warning("⚠️ É recomendado definir um responsável pela ação.")
                
                # Prepara atualizações
                updates = {
                    'plano_de_acao': plano_acao.strip(),
                    'responsavel': responsavel.strip(),
                    'status': novo_status,
                    'prazo': prazo.strftime("%Y-%m-%d") if prazo else None
                }
                
                # Se marcar como concluído, adiciona data de conclusão
                if novo_status == "Concluído" and item.get('status') != "Concluído":
                    updates['data_conclusao'] = date.today().strftime("%Y-%m-%d")
                    st.info("✅ Item será marcado como concluído")
                
                # Salva as alterações
                with st.spinner("💾 Salvando alterações..."):
                    if action_plan_manager.update_action_item(str(item['id']), updates):
                        st.success("✅ Item atualizado com sucesso!")
                        del st.session_state.current_item_to_treat
                        st.rerun()
                    else:
                        st.error("❌ Falha ao atualizar o item. Tente novamente.")
    
    treatment_form()

def show_delete_dialog(action_plan_manager):
    """Diálogo de confirmação para exclusão de item."""
    
    @st.dialog("⚠️ Confirmar Exclusão")
    def delete_confirmation():
        item_id = st.session_state.action_item_to_delete
        
        st.warning("⚠️ Tem certeza que deseja **excluir permanentemente** este item do plano de ação?")
        st.error("🚨 Esta ação **não pode ser desfeita**!")
        
        col1, col2 = st.columns(2)
        
        if col1.button("✅ Sim, Excluir", type="primary", use_container_width=True):
            # Implementar lógica de exclusão quando o método estiver disponível
            from operations.supabase_operations import SupabaseOperations
            unit_id = st.session_state.get('unit_id')
            supabase_ops = SupabaseOperations(unit_id)
            
            if supabase_ops.delete_row("plano_acao", str(item_id)):
                st.success("✅ Item excluído com sucesso!")
                del st.session_state.show_delete_action_item
                del st.session_state.action_item_to_delete
                st.rerun()
            else:
                st.error("❌ Falha ao excluir o item.")
        
        if col2.button("❌ Cancelar", use_container_width=True):
            del st.session_state.show_delete_action_item
            del st.session_state.action_item_to_delete
            st.rerun()
    
    delete_confirmation()

# ✅ ADICIONAR: Nova função para diálogo de evidência
def show_evidence_dialog(action_plan_manager):
    """Diálogo para upload de evidência."""

    @st.dialog("📎 Anexar Evidência", width="large")
    def evidence_form():
        item_id = st.session_state.evidence_item_id

        st.markdown("### Upload de Evidência")
        st.info("""
        Anexe um arquivo que comprove a conclusão da ação corretiva.

        **Formatos aceitos:** PDF, Imagem (JPG, PNG), Documentos (DOCX, XLSX)
        """)

        arquivo = st.file_uploader(
            "Selecione o arquivo de evidência:",
            type=['pdf', 'jpg', 'jpeg', 'png', 'docx', 'xlsx', 'doc', 'xls'],
            key="evidence_uploader"
        )

        col1, col2 = st.columns(2)

        if col1.button("📤 Fazer Upload", type="primary", use_container_width=True, disabled=not arquivo):
            if arquivo:
                with st.spinner("Fazendo upload..."):
                    success, msg = action_plan_manager.upload_evidencia(item_id, arquivo)

                    if success:
                        st.success(msg)
                        del st.session_state.show_evidence_dialog
                        del st.session_state.evidence_item_id

                        # Limpa cache
                        from operations.cached_loaders import load_all_unit_data
                        load_all_unit_data.clear()
                        st.cache_data.clear()
                        st.session_state.force_reload_managers = True

                        st.rerun()
                    else:
                        st.error(msg)

        if col2.button("❌ Cancelar", use_container_width=True):
            del st.session_state.show_evidence_dialog
            del st.session_state.evidence_item_id
            st.rerun()

    evidence_form()
