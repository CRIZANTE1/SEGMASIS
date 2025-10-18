import streamlit as st
from datetime import date
import pandas as pd
import logging
from fuzzywuzzy import process

from auth.auth_utils import check_permission, check_feature_permission
from ui.ui_helpers import (
    mostrar_info_normas,
    highlight_expired,
    process_aso_pdf,
    process_training_pdf,
    process_company_doc_pdf,
    process_epi_pdf
)

logger = logging.getLogger('segsisone_app.dashboard')

def format_company_display(company_id, companies_df):
    if company_id is None: 
        return "Selecione..."
    try:
        row = companies_df[companies_df['id'] == str(company_id)].iloc[0]
        name, status = row.get('nome', f"ID {company_id}"), str(row.get('status', 'Ativo')).lower()
        return f"🗃️ {name} (Arquivada)" if status == 'arquivado' else f"{name} - {row.get('cnpj', 'N/A')}"
    except (IndexError, KeyError): 
        return f"Empresa ID {company_id} (Não encontrada)"

def display_audit_results(audit_result):
    if not audit_result: 
        return
    summary = audit_result.get("summary", "Indefinido")
    details = audit_result.get("details", [])
    st.markdown("---")
    st.markdown("##### 🔍 Resultado da Auditoria Rápida")
    
    if summary.lower() == 'conforme':
        st.success(f"**Parecer da IA:** {summary}")
    elif 'não conforme' in summary.lower():
        st.error(f"**Parecer da IA:** {summary}")
        with st.expander("Ver detalhes", expanded=True):
            for item in details:
                if item.get("status", "").lower() == "não conforme":
                    st.markdown(f"- **Item:** {item.get('item_verificacao')}\n- **Observação:** {item.get('observacao')}")
    else:
        st.info(f"**Parecer da IA:** {summary}")

def handle_delete_confirmation(docs_manager, employee_manager):
    """Gerencia a confirmação de exclusão de documentos."""
    if 'show_delete_dialog' in st.session_state and st.session_state.show_delete_dialog:
        item_info = st.session_state.get('item_to_delete')
        
        @st.dialog("⚠️ Confirmar Exclusão")
        def confirm_delete_dialog():
            st.warning(f"Tem certeza que deseja excluir este item?")
            st.info(f"**Tipo:** {item_info['type']}\n\n**ID:** {item_info['id']}")
            
            col1, col2 = st.columns(2)
            if col1.button("✅ Sim, Excluir", type="primary", width='stretch'):
                success = False
                if item_info['type'] == 'ASO':
                    success = employee_manager.delete_aso(item_info['id'], item_info.get('file_url'))
                elif item_info['type'] == 'Treinamento':
                    success = employee_manager.delete_training(item_info['id'], item_info.get('file_url'))
                elif item_info['type'] == 'Doc. Empresa':
                    success = docs_manager.delete_company_document(item_info['id'], item_info.get('file_url'))
                elif item_info['type'] == 'EPI':
                    epi_manager = st.session_state.epi_manager
                    success = epi_manager.delete_epi(item_info['id'], item_info.get('file_url'))
                
                if success:
                    st.success("✅ Item excluído com sucesso!")
                    del st.session_state.show_delete_dialog
                    del st.session_state.item_to_delete
                    st.rerun()
                else:
                    st.error("❌ Falha ao excluir o item.")
            
            if col2.button("❌ Cancelar", width='stretch'):
                del st.session_state.show_delete_dialog
                del st.session_state.item_to_delete
                st.rerun()
        
        confirm_delete_dialog()

def show_dashboard_page():
    logger.info("Iniciando a renderização da página do dashboard.")
    
    if st.session_state.get('is_global_view', False):
        st.title("📊 Dashboard Global - Todas as Unidades")
        st.info("A visão detalhada do dashboard global está na página de Administração.")
        return
    
    if not st.session_state.get('managers_initialized'):
        st.warning("⏳ Selecione uma unidade ou empresa para visualizar o dashboard.")
        return
        
    employee_manager = st.session_state.employee_manager
    docs_manager = st.session_state.docs_manager
    epi_manager = st.session_state.epi_manager
    matrix_manager_unidade = st.session_state.matrix_manager_unidade
    
    is_single_mode = st.session_state.get('is_single_company_mode', False)

    if is_single_mode:
        st.title(f"📊 Dashboard de Conformidade: {st.session_state.get('single_company_name')}")
        selected_company = st.session_state.get('single_company_id')
    else:
        st.title("📊 Dashboard de Conformidade")
        company_options = [None] + employee_manager.companies_df['id'].astype(str).tolist()
        selected_company = st.selectbox(
            "🏢 Selecione uma empresa para ver os detalhes:",
            options=company_options,
            format_func=lambda cid: format_company_display(cid, employee_manager.companies_df),
            key="company_selector",
            placeholder="Selecione uma empresa..."
        )

    # ✅ DEFINIÇÃO DAS ABAS
    tab_list = [
        "📊 Situação Geral", 
        "📄 Adicionar Doc. Empresa", 
        "🩺 Adicionar ASO", 
        "🎓 Adicionar Treinamento", 
        "🦺 Adicionar Ficha de EPI", 
        "⚙️ Gerenciar Registros"
    ]
    
    tabs = st.tabs(tab_list)
    tab_situacao = tabs[0]
    tab_add_doc_empresa = tabs[1]
    tab_add_aso = tabs[2]
    tab_add_treinamento = tabs[3]
    tab_add_epi = tabs[4]
    tab_manage = tabs[5]

    # =============================================
    # ABA: SITUAÇÃO GERAL
    # ============================================
    with tab_situacao:
        if not selected_company:
            st.info("👈 Selecione uma empresa no menu acima para visualizar sua situação de conformidade.")
        else:
            try:
                company_name = employee_manager.get_company_name(selected_company)
                st.header(f"📊 Situação Geral: {company_name}")
                
                # === DOCUMENTOS DA EMPRESA ===
                st.subheader("📄 Documentos da Empresa")
                company_docs = docs_manager.get_docs_by_company(selected_company).copy()
                expected_doc_cols = ["tipo_documento", "data_emissao", "vencimento", "arquivo_id"]
                
                if isinstance(company_docs, pd.DataFrame) and not company_docs.empty:
                    company_docs['vencimento_dt'] = pd.to_datetime(company_docs['vencimento']).dt.date
                    st.dataframe(
                        company_docs.style.apply(highlight_expired, axis=1),
                        column_config={
                            "tipo_documento": "Documento",
                            "data_emissao": st.column_config.DateColumn("Emissão", format="DD/MM/YYYY"),
                            "vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                            "arquivo_id": st.column_config.LinkColumn("Anexo", display_text="📄 PDF"),
                            "vencimento_dt": None
                        },
                        column_order=expected_doc_cols,
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("ℹ️ Nenhum documento (ex: PGR, PCMSO) cadastrado para esta empresa.")
                
                st.markdown("---")
                
                # === FUNCIONÁRIOS ===
                st.subheader("👥 Funcionários")
                employees = employee_manager.get_employees_by_company(selected_company)
                
                if not employees.empty:
                    for index, employee in employees.iterrows():
                        employee_id = employee.get('id')
                        employee_name = employee.get('nome', 'N/A')
                        employee_cargo = employee.get('cargo', 'N/A')
                        today = date.today()
                        
                        # === VERIFICA ASO ===
                        aso_status, aso_vencimento = 'Não encontrado', None
                        latest_asos = employee_manager.get_latest_aso_by_employee(employee_id)
                        
                        if isinstance(latest_asos, pd.DataFrame) and not latest_asos.empty:
                            aptitude_asos = latest_asos[~latest_asos['tipo_aso'].str.lower().isin(['demissional'])].copy()
                            if not aptitude_asos.empty:
                                current_aso = aptitude_asos.sort_values('data_aso', ascending=False).iloc[0]
                                vencimento_obj = current_aso.get('vencimento')
                                if pd.notna(vencimento_obj):
                                    aso_vencimento = pd.to_datetime(vencimento_obj)
                                    aso_status = 'Válido' if aso_vencimento.date() >= today else 'Vencido'
                                else:
                                    aso_status = 'Venc. Inválido'
                            else:
                                aso_status = 'Apenas Demissional'
                        
                        # === VERIFICA TREINAMENTOS ===
                        all_trainings = employee_manager.get_all_trainings_by_employee(employee_id)
                        trainings_total, trainings_expired_count = 0, 0
                        
                        if isinstance(all_trainings, pd.DataFrame) and not all_trainings.empty:
                            trainings_total = len(all_trainings)
                            all_trainings['vencimento_date'] = pd.to_datetime(all_trainings['vencimento']).dt.date
                            trainings_expired_count = (all_trainings['vencimento_date'] < today).sum()
                        
                        # === STATUS GERAL ===
                        overall_status = 'Em Dia' if aso_status != 'Vencido' and trainings_expired_count == 0 else 'Pendente'
                        status_icon = "✅" if overall_status == 'Em Dia' else "⚠️"
                        
                        # === EXPANDER DO FUNCIONÁRIO ===
                        with st.expander(f"{status_icon} **{employee_name}** - *{employee_cargo}*"):
                            num_pendencias = trainings_expired_count + (1 if aso_status == 'Vencido' else 0)
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric(
                                "Status Geral",
                                overall_status,
                                f"{num_pendencias} pendência(s)" if num_pendencias > 0 else "Nenhuma",
                                delta_color="inverse" if overall_status != 'Em Dia' else "off"
                            )
                            col2.metric(
                                "Status do ASO",
                                aso_status,
                                help=f"Vencimento: {aso_vencimento.strftime('%d/%m/%Y') if aso_vencimento else 'N/A'}"
                            )
                            col3.metric(
                                "Treinamentos Vencidos",
                                f"{trainings_expired_count} de {trainings_total}"
                            )
                            
                            st.markdown("---")
                            
                            # === ASOs ===
                            st.markdown("##### 🩺 ASO (Mais Recente por Tipo)")
                            if isinstance(latest_asos, pd.DataFrame) and not latest_asos.empty:
                                latest_asos['vencimento_dt'] = pd.to_datetime(latest_asos['vencimento'], errors='coerce').dt.date
                                st.dataframe(
                                    latest_asos.style.apply(highlight_expired, axis=1),
                                    column_config={
                                        "tipo_aso": "Tipo",
                                        "data_aso": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                                        "vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                                        "arquivo_id": st.column_config.LinkColumn("Anexo", display_text="📄 PDF"),
                                        "vencimento_dt": None
                                    },
                                    column_order=["tipo_aso", "data_aso", "vencimento", "arquivo_id"],
                                    hide_index=True,
                                    use_container_width=True
                                )
                            else:
                                st.info(f"ℹ️ Nenhum ASO encontrado para {employee_name}.")
                            
                            # === TREINAMENTOS ===
                            st.markdown("##### 🎓 Treinamentos (Mais Recente por Norma/Módulo)")
                            if isinstance(all_trainings, pd.DataFrame) and not all_trainings.empty:
                                all_trainings['vencimento_dt'] = pd.to_datetime(all_trainings['vencimento'], errors='coerce').dt.date
                                
                                # Formata display do treinamento
                                def format_training_display(row):
                                    try:
                                        norma = str(row.get('norma', 'N/A')).strip() if 'norma' in row.index else 'N/A'
                                        modulo = str(row.get('modulo', 'N/A')).strip() if 'modulo' in row.index else 'N/A'
                                        tipo = str(row.get('tipo_treinamento', 'N/A')).strip().title() if 'tipo_treinamento' in row.index else 'N/A'
                                        
                                        # NR-10 SEP
                                        if 'NR-10' in norma.upper() or 'NR-10' in modulo.upper():
                                            if 'SEP' in norma.upper() or 'SEP' in modulo.upper():
                                                return f"⚡ NR-10 SEP ({tipo})"
                                            else:
                                                return f"⚡ NR-10 ({tipo})"
                                        
                                        # Normas com módulos
                                        if modulo and modulo not in ['N/A', 'nan', '', 'Nan']:
                                            modulo_exibicao = modulo.title()
                                            return f"{norma} - {modulo_exibicao} ({tipo})"
                                        
                                        # Normas simples
                                        return f"{norma} ({tipo})"
                                        
                                    except Exception as e:
                                        logger.error(f"Erro ao formatar display de treinamento: {e}")
                                        return "Erro ao exibir"
                                
                                all_trainings['treinamento_completo'] = all_trainings.apply(format_training_display, axis=1)
                                
                                st.dataframe(
                                    all_trainings.style.apply(highlight_expired, axis=1),
                                    column_config={
                                        "treinamento_completo": st.column_config.TextColumn(
                                            "Treinamento",
                                            help="Norma, módulo e tipo do treinamento",
                                            width="large"
                                        ),
                                        "data": st.column_config.DateColumn("Realização", format="DD/MM/YYYY"),
                                        "vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                                        "anexo": st.column_config.LinkColumn("Anexo", display_text="📄 PDF"),
                                        "vencimento_dt": None,
                                        "norma": None,
                                        "modulo": None,
                                        "tipo_treinamento": None
                                    },
                                    column_order=["treinamento_completo", "data", "vencimento", "anexo"],
                                    hide_index=True,
                                    use_container_width=True
                                )
                            else:
                                st.info(f"ℹ️ Nenhum treinamento encontrado para {employee_name}.")
                            
                            # === EPIs ===
                            st.markdown("##### 🦺 Equipamentos de Proteção Individual (EPIs)")
                            all_epis = epi_manager.get_epi_by_employee(employee_id)
                            
                            if isinstance(all_epis, pd.DataFrame) and not all_epis.empty:
                                st.dataframe(
                                    all_epis,
                                    column_config={
                                        "descricao_epi": "Equipamento",
                                        "ca_epi": "C.A.",
                                        "data_entrega": st.column_config.DateColumn("Data de Entrega", format="DD/MM/YYYY"),
                                        "arquivo_id": st.column_config.LinkColumn("Ficha", display_text="📄 PDF")
                                    },
                                    column_order=["descricao_epi", "ca_epi", "data_entrega", "arquivo_id"],
                                    hide_index=True,
                                    use_container_width=True
                                )
                            else:
                                st.info(f"ℹ️ Nenhuma Ficha de EPI encontrada para {employee_name}.")
                            
                            st.markdown("---")
                            
                            # === MATRIZ DE CONFORMIDADE ===
                            st.markdown("##### 📋 Matriz de Conformidade de Treinamentos")
                            
                            if not employee_cargo or employee_cargo == 'N/A':
                                st.info("ℹ️ Cargo não definido, impossibilitando análise de matriz.")
                            else:
                                matched_function = matrix_manager_unidade.find_closest_function(employee_cargo)
                                
                                if not matched_function:
                                    st.success(f"✅ O cargo '{employee_cargo}' não possui treinamentos obrigatórios na matriz da unidade.")
                                else:
                                    if matched_function.lower() != employee_cargo.lower():
                                        st.caption(f"💡 Analisando com base na função da matriz mais próxima: **'{matched_function}'**")
                                    
                                    required_trainings = matrix_manager_unidade.get_required_trainings_for_function(matched_function)
                                    
                                    if not required_trainings:
                                        st.success(f"✅ Nenhum treinamento obrigatório mapeado para a função '{matched_function}'.")
                                    else:
                                        # Cria lista de treinamentos realizados
                                        completed_trainings = []
                                        
                                        if isinstance(all_trainings, pd.DataFrame) and not all_trainings.empty:
                                            for _, row in all_trainings.iterrows():
                                                norma = str(row.get('norma', '')).strip().upper()
                                                modulo = str(row.get('modulo', 'N/A')).strip().title()
                                                
                                                # Normalização especial para NR-10
                                                if 'NR-10' in norma:
                                                    if 'SEP' in norma or 'SEP' in modulo.upper():
                                                        completed_trainings.append('nr-10 sep')
                                                        completed_trainings.append('nr-10-sep')
                                                    else:
                                                        completed_trainings.append('nr-10')
                                                        completed_trainings.append('nr-10 básico')
                                                
                                                # Normalização para NR-33
                                                elif 'NR-33' in norma:
                                                    if 'SUPERVISOR' in modulo.upper():
                                                        completed_trainings.append('nr-33 supervisor')
                                                    elif 'TRABALHADOR' in modulo.upper() or 'AUTORIZADO' in modulo.upper():
                                                        completed_trainings.append('nr-33 trabalhador autorizado')
                                                    completed_trainings.append('nr-33')
                                                
                                                # Outras normas
                                                else:
                                                    completed_trainings.append(norma.lower())
                                                    if modulo and modulo not in ['N/A', 'nan', '']:
                                                        completed_trainings.append(f"{norma} - {modulo}".lower())
                                                        completed_trainings.append(f"{norma} {modulo}".lower())
                                                        completed_trainings.append(f"{norma}-{modulo}".lower())
                                        
                                        # Verifica treinamentos faltantes
                                        missing = []
                                        try:
                                            for req in required_trainings:
                                                if not req or not isinstance(req, str):
                                                    logger.warning(f"Treinamento requerido inválido: {req}")
                                                    continue
                                                
                                                req_lower = req.lower().strip()
                                                
                                                # CRÍTICO: NR-10 Básico NÃO cobre NR-10 SEP
                                                if 'nr-10 sep' in req_lower or 'nr-10-sep' in req_lower:
                                                    has_sep = any('sep' in comp for comp in completed_trainings if 'nr-10' in comp)
                                                    if not has_sep:
                                                        missing.append(req)
                                                    continue
                                                
                                                # Verifica match direto
                                                has_match = any(
                                                    req_lower == comp or
                                                    req_lower in comp or
                                                    comp in req_lower
                                                    for comp in completed_trainings
                                                )
                                                
                                                # Fuzzy matching se não houver match direto
                                                if not has_match and completed_trainings:
                                                    try:
                                                        from fuzzywuzzy import process as fuzz_process  # ✅ Import local seguro
                                                        best_match = fuzz_process.extractOne(req_lower, completed_trainings)
                                                        if best_match and best_match[1] > 85:
                                                            has_match = True
                                                    except ImportError:
                                                        logger.warning("fuzzywuzzy não disponível para fuzzy matching")
                                                        pass
                                                
                                                if not has_match:
                                                    missing.append(req)
                                            
                                        except Exception as e:
                                            logger.error(f"Erro ao verificar treinamentos faltantes: {e}")
                                            st.warning("⚠️ Erro ao verificar conformidade de treinamentos")
                                        
                                        # Exibe resultado
                                        if not missing:
                                            st.success("✅ Todos os treinamentos obrigatórios foram realizados.")
                                        else:
                                            st.error(f"⚠️ **{len(missing)} Treinamento(s) Faltante(s):**")
                                            
                                            for treinamento in sorted(missing):
                                                if 'SEP' in treinamento.upper():
                                                    st.markdown(f"- ⚡ **{treinamento}** *(Sistema Elétrico de Potência)*")
                                                elif any(x in treinamento.upper() for x in ['BÁSICO', 'INTERMEDIÁRIO', 'AVANÇADO']):
                                                    st.markdown(f"- 🎯 **{treinamento}**")
                                                else:
                                                    st.markdown(f"- 📋 {treinamento}")
                else:
                    st.error(f"❌ Nenhum funcionário encontrado para esta empresa (ID: {selected_company}).")
                    st.info(f"💡 **Ação necessária:** Verifique se existem funcionários cadastrados com `empresa_id` igual a `{selected_company}`.")
            
            except Exception as e:
                logger.error(f"ERRO CRÍTICO ao renderizar dashboard para empresa {selected_company}: {e}", exc_info=True)
                st.error("❌ Ocorreu um erro inesperado ao tentar exibir os detalhes desta empresa.")
                st.exception(e)

    # =============================================
    # ABA: ADICIONAR DOCUMENTO DA EMPRESA
    # ============================================
    with tab_add_doc_empresa:
        if not selected_company:
            st.info("👈 Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader("📄 Adicionar Documento da Empresa (PGR, PCMSO, etc.)")
            company_name = employee_manager.get_company_name(selected_company)
            st.info(f"📌 Adicionando documento para: **{company_name}**")
            
            # Verifica se tem acesso à IA
            has_ai_access = check_feature_permission('premium_ia')
            
            # Escolhe modo de entrada
            if has_ai_access:
                entry_mode = st.radio(
                    "Escolha o modo de entrada:",
                    options=["🤖 Upload com IA (Automático)", "✍️ Entrada Manual"],
                    horizontal=True,
                    key="doc_entry_mode"
                )
            else:
                entry_mode = "✍️ Entrada Manual"
                st.info("💡 **Modo Manual Ativo** | Upgrade para Premium IA para análise automática de PDFs")
            
            # ========== MODO IA ==========            
            if "Upload com IA" in entry_mode:
                st.file_uploader(
                    "📎 Anexar Documento (PDF) - A IA extrairá os dados automaticamente", 
                    type=['pdf'], 
                    key="doc_uploader_tab", 
                    on_change=process_company_doc_pdf,
                    help="Faça upload e aguarde a extração automática"
                )
                
                if st.session_state.get('Doc. Empresa_info_para_salvar'):
                    doc_info = st.session_state['Doc. Empresa_info_para_salvar']
                    
                    with st.form("confirm_doc_empresa_form"):
                        st.markdown("### ✏️ Confirme e Edite as Informações Extraídas pela IA")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            doc_types = ["PGR", "PCMSO", "PPR", "PCA", "LTCAT", "LAUDO", "AET", "Outro"]
                            try:
                                default_index = doc_types.index(doc_info.get('tipo_documento', 'Outro'))
                            except ValueError:
                                default_index = len(doc_types) - 1
                            
                            edited_tipo = st.selectbox(
                                "📋 Tipo de Documento *", 
                                doc_types, 
                                index=default_index,
                                help="Extraído pela IA - você pode alterar"
                            )
                        
                        with col2:
                            edited_data_emissao = st.date_input(
                                "📅 Data de Emissão *", 
                                value=doc_info.get('data_emissao'),
                                help="Extraído pela IA - você pode alterar"
                            )
                        
                        st.markdown("#### ⏰ Vencimento")
                        
                        if edited_tipo == "PGR":
                            vencimento_padrao = edited_data_emissao + pd.DateOffset(years=2)
                            st.info("💡 PGR: Validade padrão de **2 anos**")
                        elif edited_tipo in ["LTCAT", "LAUDO"]:
                            vencimento_padrao = edited_data_emissao + pd.DateOffset(years=2)
                            st.info(f"💡 {edited_tipo}: Validade padrão de **2 anos**")
                        else:
                            vencimento_padrao = edited_data_emissao + pd.DateOffset(years=1)
                            st.info(f"💡 {edited_tipo}: Validade padrão de **1 ano**")
                        
                        edited_vencimento = st.date_input(
                            "Data de Vencimento *",
                            value=vencimento_padrao.date() if isinstance(vencimento_padrao, pd.Timestamp) else vencimento_padrao,
                            help="Calculado automaticamente - você pode alterar"
                        )
                        
                        observacoes = st.text_area(
                            "📝 Observações (opcional)",
                            placeholder="Ex: Documento revisado, atualização parcial, etc.",
                            help="Campo livre para anotações"
                        )

                        display_audit_results(doc_info.get('audit_result'))

                        col_confirm, col_cancel = st.columns([3, 1])
                        
                        with col_confirm:
                            confirm_button = st.form_submit_button(
                                "💾 Confirmar e Salvar Documento", 
                                type="primary",
                                use_container_width=True
                            )
                        
                        with col_cancel:
                            cancel_button = st.form_submit_button(
                                "❌ Cancelar",
                                use_container_width=True
                            )
                        
                        if cancel_button:
                            for key in list(st.session_state.keys()):
                                if key.startswith('Doc. Empresa_'):
                                    del st.session_state[key]
                            st.rerun()
                        
                        if confirm_button:
                            if edited_vencimento <= edited_data_emissao:
                                st.error("❌ A data de vencimento deve ser posterior à data de emissão!")
                                st.stop()
                            
                            with st.spinner("💾 Salvando documento..."):
                                anexo = st.session_state['Doc. Empresa_anexo_para_salvar']
                                arquivo_hash = st.session_state.get('Doc. Empresa_hash_para_salvar')
                                nome_arquivo = f"{edited_tipo}_{company_name.replace(' ', '_')}_{edited_data_emissao.strftime('%Y%m%d')}.pdf"
                                
                                arquivo_id = employee_manager.upload_documento_e_obter_link(anexo, nome_arquivo)
                                
                                if arquivo_id:
                                    doc_id = docs_manager.add_company_document(
                                        selected_company, 
                                        edited_tipo, 
                                        edited_data_emissao, 
                                        edited_vencimento,
                                        arquivo_id, 
                                        arquivo_hash
                                    )
                                    
                                    if doc_id:
                                        st.success("✅ Documento da empresa salvo com sucesso!")
                                        
                                        # Plano de ação
                                        audit_result = doc_info.get('audit_result')
                                        if audit_result and 'não conforme' in audit_result.get('summary', '').lower():
                                            nr_analyzer = st.session_state.get('nr_analyzer')
                                            if nr_analyzer:
                                                items_added = nr_analyzer.create_action_plan_from_audit(
                                                    audit_result, selected_company, doc_id
                                                )
                                                if items_added > 0:
                                                    st.info(f"📋 {items_added} não conformidade(s) adicionada(s) ao Plano de Ação")
                                        
                                        for key in list(st.session_state.keys()):
                                            if key.startswith('Doc. Empresa_'):
                                                del st.session_state[key]
                                        st.balloons()
                                        st.rerun()
                                    else:
                                        st.error("❌ Falha ao salvar no banco de dados.")
            
            # ========== MODO MANUAL ==========            
            else:  # Entrada Manual
                st.markdown("### ✍️ Cadastro Manual de Documento")
                
                with st.form("manual_doc_empresa_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        doc_types = ["PGR", "PCMSO", "PPR", "PCA", "LTCAT", "LAUDO", "AET", "Outro"]
                        manual_tipo = st.selectbox(
                            "📋 Tipo de Documento *",
                            doc_types,
                            help="Selecione o tipo de documento regulatório"
                        )
                    
                    with col2:
                        manual_data_emissao = st.date_input(
                            "📅 Data de Emissão *",
                            value=date.today(),
                            max_value=date.today(),
                            help="Data em que o documento foi emitido"
                        )
                    
                    st.markdown("#### ⏰ Vencimento")
                    
                    if manual_tipo == "PGR":
                        vencimento_sugerido = manual_data_emissao + pd.DateOffset(years=2)
                        st.info("💡 PGR: Validade padrão de **2 anos**")
                    elif manual_tipo in ["LTCAT", "LAUDO"]:
                        vencimento_sugerido = manual_data_emissao + pd.DateOffset(years=2)
                        st.info(f"💡 {manual_tipo}: Validade padrão de **2 anos**")
                    else:
                        vencimento_sugerido = manual_data_emissao + pd.DateOffset(years=1)
                        st.info(f"💡 {manual_tipo}: Validade padrão de **1 ano**")
                    
                    manual_vencimento = st.date_input(
                        "Data de Vencimento *",
                        value=vencimento_sugerido.date() if isinstance(vencimento_sugerido, pd.Timestamp) else vencimento_sugerido,
                        min_value=manual_data_emissao + pd.DateOffset(days=1),
                        help="Você pode alterar o vencimento se necessário"
                    )
                    
                    manual_arquivo = st.file_uploader(
                        "📎 Anexar Arquivo PDF *",
                        type=['pdf'],
                        key="manual_doc_file",
                        help="Faça upload do documento em PDF"
                    )
                    
                    manual_observacoes = st.text_area(
                        "📝 Observações (opcional)",
                        placeholder="Ex: Documento revisado, atualização parcial, etc.",
                        help="Campo livre para anotações"
                    )
                    
                    col_submit, col_cancel = st.columns([3, 1])
                    
                    with col_submit:
                        submit_manual_doc = st.form_submit_button(
                            "💾 Salvar Documento",
                            type="primary",
                            use_container_width=True
                        )
                    
                    with col_cancel:
                        cancel_manual_doc = st.form_submit_button(
                            "❌ Cancelar",
                            use_container_width=True
                        )
                    
                    if cancel_manual_doc:
                        st.rerun()
                    
                    if submit_manual_doc:
                        if not manual_arquivo:
                            st.error("❌ É obrigatório anexar o arquivo PDF!")
                            st.stop()
                        
                        if manual_vencimento <= manual_data_emissao:
                            st.error("❌ A data de vencimento deve ser posterior à data de emissão!")
                            st.stop()
                        
                        with st.spinner("💾 Salvando documento..."):
                            from operations.file_hash import calcular_hash_arquivo
                            arquivo_hash = calcular_hash_arquivo(manual_arquivo)
                            
                            nome_arquivo = f"{manual_tipo}_{company_name.replace(' ', '_')}_{manual_data_emissao.strftime('%Y%m%d')}.pdf"
                            
                            arquivo_id = employee_manager.upload_documento_e_obter_link(manual_arquivo, nome_arquivo)
                            
                            if arquivo_id:
                                doc_id = docs_manager.add_company_document(
                                    selected_company,
                                    manual_tipo,
                                    manual_data_emissao,
                                    manual_vencimento,
                                    arquivo_id,
                                    arquivo_hash
                                )
                                
                                if doc_id:
                                    st.success("✅ Documento salvo com sucesso!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ Falha ao salvar no banco de dados.")
                            else:
                                st.error("❌ Falha ao fazer upload do arquivo.")

    # =============================================
    # ABA: ADICIONAR ASO
    # ============================================
    with tab_add_aso:
        if not selected_company:
            st.info("👈 Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader("🩺 Adicionar Novo ASO")
            current_employees = employee_manager.get_employees_by_company(selected_company)
            
            if not current_employees.empty:
                selected_employee_aso = st.selectbox(
                    "👤 Funcionário *",
                    current_employees['id'].tolist(),
                    format_func=employee_manager.get_employee_name,
                    key="aso_employee_add",
                    help="Selecione o funcionário para vincular o ASO"
                )
                
                has_ai_access = check_feature_permission('premium_ia')
                
                if has_ai_access:
                    entry_mode_aso = st.radio(
                        "Escolha o modo de entrada:",
                        options=["🤖 Upload com IA (Automático)", "✍️ Entrada Manual"],
                        horizontal=True,
                        key="aso_entry_mode"
                    )
                else:
                    entry_mode_aso = "✍️ Entrada Manual"
                    st.info("💡 **Modo Manual Ativo** | Upgrade para Premium IA para análise automática")
                
                # ========== MODO IA ==========                
                if "Upload com IA" in entry_mode_aso:
                    st.file_uploader(
                        "📎 Anexar ASO (PDF) - A IA extrairá os dados automaticamente",
                        type=['pdf'],
                        key="aso_uploader_tab",
                        on_change=process_aso_pdf,
                        help="Faça upload e aguarde a extração automática"
                    )
                    
                    if st.session_state.get('ASO_info_para_salvar'):
                        aso_info = st.session_state.ASO_info_para_salvar
                        
                        with st.form("confirm_aso_form"):
                            st.markdown("### ✏️ Confirme e Edite as Informações Extraídas pela IA")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                edited_data_aso = st.date_input(
                                    "📅 Data do ASO *", 
                                    value=aso_info.get('data_aso'),
                                    help="Extraído pela IA - você pode alterar"
                                )
                            
                            with col2:
                                aso_types = [
                                    'Admissional', 
                                    'Periódico', 
                                    'Demissional', 
                                    'Mudança de Risco', 
                                    'Retorno ao Trabalho', 
                                    'Monitoramento Pontual'
                                ]
                                try:
                                    default_index = aso_types.index(aso_info.get('tipo_aso', 'Periódico'))
                                except ValueError:
                                    default_index = 1
                                
                                edited_tipo_aso = st.selectbox(
                                    "📋 Tipo de ASO *", 
                                    aso_types, 
                                    index=default_index,
                                    help="Extraído pela IA - você pode alterar"
                                )
                            
                            st.markdown("#### ⏰ Vencimento")
                            
                            vencimento_sugerido = aso_info.get('vencimento')
                            if not vencimento_sugerido and edited_tipo_aso != 'Demissional':
                                from dateutil.relativedelta import relativedelta
                                if edited_tipo_aso in ['Admissional', 'Periódico', 'Mudança de Risco', 'Retorno ao Trabalho']:
                                    vencimento_sugerido = edited_data_aso + relativedelta(years=1)
                                elif edited_tipo_aso == 'Monitoramento Pontual':
                                    vencimento_sugerido = edited_data_aso + relativedelta(months=6)
                            
                            if edited_tipo_aso == 'Demissional':
                                st.info("💡 ASO Demissional não possui vencimento")
                                edited_vencimento = None
                            else:
                                edited_vencimento = st.date_input(
                                    "Data de Vencimento *",
                                    value=vencimento_sugerido if vencimento_sugerido else edited_data_aso + relativedelta(years=1),
                                    help="Calculado automaticamente - você pode alterar"
                                )
                            
                            col3, col4 = st.columns(2)
                            
                            with col3:
                                edited_cargo = st.text_input(
                                    "💼 Cargo",
                                    value=aso_info.get('cargo', ''),
                                    help="Extraído pela IA - você pode alterar"
                                )
                            
                            with col4:
                                edited_riscos = st.text_area(
                                    "⚠️ Riscos Ocupacionais",
                                    value=aso_info.get('riscos', ''),
                                    height=100,
                                    help="Extraído pela IA - você pode alterar"
                                )
                            
                            observacoes_aso = st.text_area(
                                "📝 Observações (opcional)",
                                placeholder="Ex: Resultado de exames complementares, restrições, etc."
                            )

                            display_audit_results(aso_info.get('audit_result'))

                            col_confirm, col_cancel = st.columns([3, 1])
                            
                            with col_confirm:
                                confirm_button = st.form_submit_button(
                                    "💾 Confirmar e Salvar ASO", 
                                    type="primary",
                                    use_container_width=True
                                )
                            
                            with col_cancel:
                                cancel_button = st.form_submit_button(
                                    "❌ Cancelar",
                                    use_container_width=True
                                )
                            
                            if cancel_button:
                                for key in list(st.session_state.keys()):
                                    if key.startswith('ASO_'):
                                        del st.session_state[key]
                                st.rerun()
                            
                            if confirm_button:
                                if edited_tipo_aso != 'Demissional' and edited_vencimento:
                                    if edited_vencimento <= edited_data_aso:
                                        st.error("❌ A data de vencimento deve ser posterior à data do ASO!")
                                        st.stop()
                                
                                with st.spinner("💾 Salvando ASO..."):
                                    anexo = st.session_state.ASO_anexo_para_salvar
                                    arquivo_hash = st.session_state.get('ASO_hash_para_salvar')
                                    emp_id = st.session_state.ASO_funcionario_para_salvar
                                    emp_name = employee_manager.get_employee_name(emp_id)
                                    nome_arquivo = f"ASO_{emp_name.replace(' ', '_')}_{edited_data_aso.strftime('%Y%m%d')}.pdf"
                                    
                                    arquivo_id = employee_manager.upload_documento_e_obter_link(anexo, nome_arquivo)
                                    
                                    if arquivo_id:
                                        aso_data = {
                                            'funcionario_id': emp_id, 
                                            'arquivo_id': arquivo_id, 
                                            'arquivo_hash': arquivo_hash,
                                            'data_aso': edited_data_aso, 
                                            'tipo_aso': edited_tipo_aso, 
                                            'vencimento': edited_vencimento,
                                            'riscos': edited_riscos.strip(), 
                                            'cargo': edited_cargo.strip()
                                        }
                                        
                                        aso_id = employee_manager.add_aso(aso_data)
                                        
                                        if aso_id:
                                            st.success("✅ ASO salvo com sucesso!")
                                            
                                            audit_result = aso_info.get('audit_result')
                                            if audit_result and 'não conforme' in audit_result.get('summary', '').lower():
                                                nr_analyzer = st.session_state.get('nr_analyzer')
                                                if nr_analyzer:
                                                    items_added = nr_analyzer.create_action_plan_from_audit(
                                                        audit_result, selected_company, aso_id, employee_id=emp_id
                                                    )
                                                    if items_added > 0:
                                                        st.info(f"📋 {items_added} não conformidade(s) adicionada(s) ao Plano de Ação")
                                            
                                            for key in list(st.session_state.keys()):
                                                if key.startswith('ASO_'):
                                                    del st.session_state[key]
                                            st.balloons()
                                            st.rerun()
                                        else:
                                            st.error("❌ Falha ao salvar no banco de dados.")
                
                # ========== MODO MANUAL ==========                
                else:  # Entrada Manual
                    st.markdown("### ✍️ Cadastro Manual de ASO")
                    
                    with st.form("manual_aso_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            manual_data_aso = st.date_input(
                                "📅 Data do ASO *",
                                value=date.today(),
                                max_value=date.today(),
                                help="Data de realização do exame clínico"
                            )
                        
                        with col2:
                            aso_types = [
                                'Admissional',
                                'Periódico',
                                'Demissional',
                                'Mudança de Risco',
                                'Retorno ao Trabalho',
                                'Monitoramento Pontual'
                            ]
                            manual_tipo_aso = st.selectbox(
                                "📋 Tipo de ASO *",
                                aso_types,
                                index=1,  # Periódico como padrão
                                help="Tipo de exame realizado"
                            )
                        
                        st.markdown("#### ⏰ Vencimento")
                        
                        if manual_tipo_aso == 'Demissional':
                            st.info("💡 ASO Demissional não possui vencimento")
                            manual_vencimento = None
                        else:
                            from dateutil.relativedelta import relativedelta
                            
                            if manual_tipo_aso in ['Admissional', 'Periódico', 'Mudança de Risco', 'Retorno ao Trabalho']:
                                venc_sugerido = manual_data_aso + relativedelta(years=1)
                                st.info("💡 Validade padrão: **1 ano**")
                            elif manual_tipo_aso == 'Monitoramento Pontual':
                                venc_sugerido = manual_data_aso + relativedelta(months=6)
                                st.info("💡 Validade padrão: **6 meses**")
                            else:
                                venc_sugerido = manual_data_aso + relativedelta(years=1)
                            
                            manual_vencimento = st.date_input(
                                "Data de Vencimento *",
                                value=venc_sugerido,
                                min_value=manual_data_aso + relativedelta(days=1),
                                help="Data em que o ASO perde validade"
                            )
                        
                        col3, col4 = st.columns(2)
                        
                        with col3:
                            manual_cargo = st.text_input(
                                "💼 Cargo",
                                help="Cargo do funcionário no momento do ASO"
                            )
                        
                        with col4:
                            manual_riscos = st.text_area(
                                "⚠️ Riscos Ocupacionais",
                                height=100,
                                placeholder="Ex: Ruído, Ergonômico, Químico...",
                                help="Riscos identificados (separe por vírgula)"
                            )
                        
                        manual_aso_arquivo = st.file_uploader(
                            "📎 Anexar ASO em PDF *",
                            type=['pdf'],
                            key="manual_aso_file",
                            help="Faça upload do ASO em PDF"
                        )
                        
                        manual_obs_aso = st.text_area(
                            "📝 Observações (opcional)",
                            placeholder="Ex: Resultado de exames complementares, restrições, etc."
                        )
                        
                        col_submit, col_cancel = st.columns([3, 1])
                        
                        with col_submit:
                            submit_manual_aso = st.form_submit_button(
                                "💾 Salvar ASO",
                                type="primary",
                                use_container_width=True
                            )
                        
                        with col_cancel:
                            cancel_manual_aso = st.form_submit_button(
                                "❌ Cancelar",
                                use_container_width=True
                            )
                        
                        if cancel_manual_aso:
                            st.rerun()
                        
                        if submit_manual_aso:
                            if not manual_aso_arquivo:
                                st.error("❌ É obrigatório anexar o arquivo PDF do ASO!")
                                st.stop()
                            
                            if manual_tipo_aso != 'Demissional' and manual_vencimento:
                                if manual_vencimento <= manual_data_aso:
                                    st.error("❌ A data de vencimento deve ser posterior à data do ASO!")
                                    st.stop()
                            
                            with st.spinner("💾 Salvando ASO..."):
                                from operations.file_hash import calcular_hash_arquivo
                                arquivo_hash = calcular_hash_arquivo(manual_aso_arquivo)
                                
                                emp_name = employee_manager.get_employee_name(selected_employee_aso)
                                nome_arquivo = f"ASO_{emp_name.replace(' ', '_')}_{manual_data_aso.strftime('%Y%m%d')}.pdf"
                                
                                arquivo_id = employee_manager.upload_documento_e_obter_link(manual_aso_arquivo, nome_arquivo)
                                
                                if arquivo_id:
                                    aso_data = {
                                        'funcionario_id': selected_employee_aso,
                                        'arquivo_id': arquivo_id,
                                        'arquivo_hash': arquivo_hash,
                                        'data_aso': manual_data_aso,
                                        'tipo_aso': manual_tipo_aso,
                                        'vencimento': manual_vencimento,
                                        'riscos': manual_riscos.strip(),
                                        'cargo': manual_cargo.strip()
                                    }
                                    
                                    aso_id = employee_manager.add_aso(aso_data)
                                    
                                    if aso_id:
                                        st.success("✅ ASO salvo com sucesso!")
                                        st.balloons()
                                        st.rerun()
                                    else:
                                        st.error("❌ Falha ao salvar no banco de dados.")
                                else:
                                    st.error("❌ Falha ao fazer upload do arquivo.")
            else:
                st.warning("⚠️ Cadastre funcionários nesta empresa primeiro.")

    # =============================================
    # ABA: ADICIONAR TREINAMENTO
    # ============================================
    with tab_add_treinamento:
        if not selected_company:
            st.info("👈 Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader("🎓 Adicionar Novo Treinamento")
            mostrar_info_normas()
            current_employees = employee_manager.get_employees_by_company(selected_company)
            
            if not current_employees.empty:
                selected_employee_training = st.selectbox(
                    "👤 Funcionário *", 
                    current_employees['id'].tolist(), 
                    format_func=employee_manager.get_employee_name, 
                    key="training_employee_add",
                    help="Selecione o funcionário que realizou o treinamento"
                )
                
                has_ai_access = check_feature_permission('premium_ia')
                
                if has_ai_access:
                    entry_mode_training = st.radio(
                        "Escolha o modo de entrada:",
                        ["🤖 Upload com IA (Automático)", "✍️ Entrada Manual"],
                        horizontal=True,
                        key="training_entry_mode"
                    )
                else:
                    entry_mode_training = "✍️ Entrada Manual"
                    st.info("💡 **Modo Manual Ativo** | Upgrade para Premium IA para análise automática de certificados.")
                
                # --- MODO IA ---
                if "Upload com IA" in entry_mode_training:
                    st.file_uploader(
                        "📎 Anexar Certificado (PDF)", 
                        type=['pdf'], 
                        key="training_uploader_tab", 
                        on_change=process_training_pdf,
                        help="Faça upload do certificado de treinamento em PDF"
                    )
                    
                    if st.session_state.get('Treinamento_info_para_salvar'):
                        training_info = st.session_state['Treinamento_info_para_salvar']
                        
                        with st.form("confirm_training_form"):
                            st.markdown("### ✏️ Confirme e Edite as Informações Extraídas")

                            col1, col2 = st.columns(2)
                            
                            with col1:
                                edited_data = st.date_input(
                                    "📅 Data de Realização *",
                                    value=training_info.get('data'),
                                    help="Data em que o treinamento foi concluído"
                                )

                            with col2:
                                # ✅ LÓGICA DINÂMICA PARA NORMAS
                                norma_options = employee_manager.nr_rules_manager.get_norma_options()

                                current_norma = training_info.get('norma', '')
                                try:
                                    default_norma_index = norma_options.index(current_norma)
                                except ValueError:
                                    default_norma_index = 0

                                edited_norma = st.selectbox(
                                    "📋 Norma *",
                                    options=norma_options,
                                    index=default_norma_index,
                                    help="Norma Regulamentadora do treinamento"
                                )

                            col3, col4 = st.columns(2)

                            with col3:
                                # ✅ LÓGICA DINÂMICA PARA MÓDULOS
                                module_options = employee_manager.nr_rules_manager.get_module_options_for_norma(edited_norma)

                                # Se a norma tem múltiplos treinamentos, mostramos um selectbox.
                                if len(module_options) > 1:
                                    current_modulo_title = training_info.get('titulo', training_info.get('modulo'))

                                    # Tenta encontrar o índice do módulo extraído pela IA
                                    try:
                                        # Usa fuzzy matching para encontrar a melhor opção
                                        from fuzzywuzzy import process
                                        best_match, _ = process.extractOne(current_modulo_title, module_options)
                                        default_mod_index = module_options.index(best_match)
                                    except (ValueError, TypeError):
                                        default_mod_index = 0

                                    edited_modulo = st.selectbox(
                                        f"🎯 Módulo Específico ({edited_norma}) *",
                                        module_options,
                                        index=default_mod_index
                                    )
                                else:
                                    # Se há apenas um treinamento ou nenhum, um campo de texto é suficiente.
                                    edited_modulo = st.text_input(
                                        "🎯 Módulo (opcional)",
                                        value=training_info.get('modulo', 'N/A')
                                    )
                            
                            with col4:
                                tipo_options = ["formação", "reciclagem"]
                                current_tipo = training_info.get('tipo_treinamento', 'formação').lower()
                                try:
                                    default_tipo_index = tipo_options.index(current_tipo)
                                except ValueError:
                                    default_tipo_index = 0
                                
                                edited_tipo = st.selectbox(
                                    "🔄 Tipo *", 
                                    tipo_options, 
                                    index=default_tipo_index,
                                    help="Formação inicial ou reciclagem"
                                )
                            
                            current_ch = training_info.get('carga_horaria', 0)
                            edited_ch = st.number_input(
                                "⏱️ Carga Horária (horas) *", 
                                min_value=0, 
                                max_value=200,
                                value=int(current_ch) if current_ch else 0,
                                help="Carga horária total do treinamento"
                            )
                            
                            st.markdown("#### ⏰ Vencimento")
                            
                            vencimento_calculado = employee_manager.calcular_vencimento_treinamento(
                                edited_data, edited_norma, edited_modulo, edited_tipo
                            )
                            
                            if vencimento_calculado:
                                st.success(f"✅ Vencimento calculado automaticamente: **{vencimento_calculado.strftime('%d/%m/%Y')}**")
                                edited_vencimento = st.date_input(
                                    "Data de Vencimento * (editável)",
                                    value=vencimento_calculado,
                                    help="Vencimento calculado pela norma - você pode ajustar se necessário"
                                )
                            else:
                                st.warning("⚠️ Não foi possível calcular o vencimento automaticamente")
                                edited_vencimento = st.date_input(
                                    "Data de Vencimento *",
                                    value=edited_data + pd.DateOffset(years=2),
                                    help="Defina manualmente a data de vencimento"
                                )
                            
                            observacoes_training = st.text_area(
                                "📝 Observações (opcional)",
                                placeholder="Ex: Treinamento realizado in company, instrutor específico, etc.",
                                help="Campo livre para anotações sobre este treinamento"
                            )

                            display_audit_results(training_info.get('audit_result'))

                            col_confirm, col_cancel = st.columns([3, 1])
                            
                            with col_confirm:
                                confirm_button = st.form_submit_button(
                                    "💾 Confirmar e Salvar Treinamento", 
                                    type="primary",
                                    use_container_width=True
                                )
                            
                            with col_cancel:
                                cancel_button = st.form_submit_button(
                                    "❌ Cancelar",
                                    use_container_width=True
                                )
                            
                            if cancel_button:
                                for key in list(st.session_state.keys()):
                                    if key.startswith('Treinamento_'):
                                        del st.session_state[key]
                                st.rerun()
                            
                            if confirm_button:
                                if edited_vencimento <= edited_data:
                                    st.error("❌ A data de vencimento deve ser posterior à data de realização!")
                                    st.stop()
                                
                                if edited_ch <= 0:
                                    st.error("❌ A carga horária deve ser maior que zero!")
                                    st.stop()
                                
                                with st.spinner("💾 Salvando treinamento..."):
                                    anexo = st.session_state.Treinamento_anexo_para_salvar
                                    arquivo_hash = st.session_state.get('Treinamento_hash_para_salvar')
                                    emp_id = st.session_state.Treinamento_funcionario_para_salvar
                                    emp_name = employee_manager.get_employee_name(emp_id)
                                    nome_arquivo = f"TRAINING_{emp_name.replace(' ', '_')}_{edited_norma.replace('-', '')}_{edited_data.strftime('%Y%m%d')}.pdf"
                                    
                                    arquivo_id = employee_manager.upload_documento_e_obter_link(anexo, nome_arquivo)
                                    
                                    if arquivo_id:
                                        training_data = {
                                            'funcionario_id': emp_id, 
                                            'anexo': arquivo_id, 
                                            'arquivo_hash': arquivo_hash,
                                            'data': edited_data, 
                                            'norma': edited_norma, 
                                            'tipo_treinamento': edited_tipo,
                                            'carga_horaria': edited_ch, 
                                            'vencimento': edited_vencimento, 
                                            'modulo': edited_modulo
                                        }
                                        
                                        training_id = employee_manager.add_training(training_data)
                                        
                                        if training_id:
                                            st.success("✅ Treinamento salvo com sucesso!")
                                            
                                            audit_result = training_info.get('audit_result')
                                            if audit_result and 'não conforme' in audit_result.get('summary', '').lower():
                                                nr_analyzer = st.session_state.get('nr_analyzer')
                                                if nr_analyzer:
                                                    items_added = nr_analyzer.create_action_plan_from_audit(
                                                        audit_result, selected_company, training_id, employee_id=emp_id
                                                    )
                                                    if items_added > 0:
                                                        st.info(f"📋 {items_added} não conformidade(s) adicionada(s) ao Plano de Ação")
                                            
                                            for key in list(st.session_state.keys()):
                                                if key.startswith('Treinamento_'):
                                                    del st.session_state[key]
                                            st.rerun()
                                        else:
                                            st.error("❌ Falha ao salvar o treinamento no banco de dados.")
                                    else:
                                        st.error("❌ Falha ao fazer upload do arquivo.")
                
                # --- MODO MANUAL ---
                else:
                    st.markdown("### ✍️ Cadastro Manual de Treinamento")
                    with st.form("manual_training_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            manual_data = st.date_input("📅 Data de Realização *", value=date.today(), max_value=date.today())
                        with col2:
                            # ✅ PASSO 2: Busca as normas disponíveis dinamicamente
                            norma_options = employee_manager.nr_rules_manager.get_norma_options()
                            manual_norma = st.selectbox("📋 Norma *", options=norma_options, key="manual_norma_select")

                        # ✅ PASSO 2: Cria o selectbox de módulo dinâmico
                        module_options = employee_manager.nr_rules_manager.get_module_options_for_norma(manual_norma)

                        col3, col4 = st.columns(2)
                        with col3:
                            # Se a norma selecionada tiver múltiplos treinamentos (módulos), exibe um selectbox
                            if len(module_options) > 1:
                                manual_modulo = st.selectbox("🎯 Módulo Específico *", options=module_options, key="manual_module_select")
                            else:
                                # Caso contrário, exibe um campo de texto livre para módulos não-padrão
                                manual_modulo = st.text_input("🎯 Módulo (opcional)", key="manual_module_text")
                        with col4:
                            manual_tipo = st.selectbox("🔄 Tipo *", ["formação", "reciclagem"])

                        manual_ch = st.number_input("⏱️ Carga Horária (horas) *", min_value=1, max_value=200, value=8)

                        st.markdown("#### ⏰ Vencimento")

                        # O cálculo do vencimento já usa a nova lógica, então não precisa de alteração aqui
                        vencimento_manual_calc = employee_manager.calcular_vencimento_treinamento(manual_data, manual_norma, manual_modulo, manual_tipo)

                        # Se o cálculo retornar uma data, use-a como padrão. Caso contrário, default de 1 ano.
                        default_vencimento = vencimento_manual_calc if vencimento_manual_calc else manual_data + pd.DateOffset(years=1)
                        manual_vencimento = st.date_input("Data de Vencimento *", value=default_vencimento)

                        manual_training_arquivo = st.file_uploader("📎 Anexar Certificado em PDF *", type=['pdf'], key="manual_training_file")

                        col_submit, col_cancel = st.columns([3, 1])

                        with col_submit:
                            submit_manual_training = st.form_submit_button("💾 Salvar Treinamento", type="primary", use_container_width=True)

                        with col_cancel:
                            cancel_manual_training = st.form_submit_button("❌ Cancelar", use_container_width=True)

                        if cancel_manual_training:
                            st.rerun()

                        if submit_manual_training:
                            if not manual_training_arquivo:
                                st.error("❌ É obrigatório anexar o certificado em PDF!")
                                st.stop()
                            if manual_vencimento <= manual_data:
                                st.error("❌ O vencimento deve ser após a data de realização!")
                                st.stop()

                            # A validação da carga horária já usa a nova lógica, então não precisa de alteração aqui
                            is_valid, validation_msg = employee_manager.validar_treinamento(
                                manual_norma, manual_modulo, manual_tipo, manual_ch
                            )

                            if not is_valid:
                                st.error(f"❌ Validação falhou: {validation_msg}")
                                st.stop()

                            with st.spinner("💾 Salvando..."):
                                from operations.file_hash import calcular_hash_arquivo
                                arquivo_hash = calcular_hash_arquivo(manual_training_arquivo)
                                emp_name = employee_manager.get_employee_name(selected_employee_training)
                                nome_arquivo = f"TRAINING_{emp_name.replace(' ', '_')}_{manual_norma.replace('-', '')}_{manual_data.strftime('%Y%m%d')}.pdf"
                                arquivo_id = employee_manager.upload_documento_e_obter_link(manual_training_arquivo, nome_arquivo)

                                if arquivo_id:
                                    training_data = {
                                        'funcionario_id': selected_employee_training,
                                        'anexo': arquivo_id,
                                        'arquivo_hash': arquivo_hash,
                                        'data': manual_data,
                                        'norma': manual_norma,
                                        'tipo_treinamento': manual_tipo,
                                        'carga_horaria': manual_ch,
                                        'vencimento': manual_vencimento,
                                        'modulo': manual_modulo
                                    }
                                    if employee_manager.add_training(training_data):
                                        st.success("✅ Treinamento salvo com sucesso!")
                                        st.rerun()
                                    else:
                                        # A função add_training já exibe um st.error mais específico
                                        pass
                                else:
                                    st.error("❌ Falha no upload do arquivo.")
            else:
                st.warning("⚠️ Cadastre funcionários nesta empresa primeiro.")

    # =============================================
    # ABA: ADICIONAR FICHA DE EPI
    # ============================================
    with tab_add_epi:
        if not selected_company:
            st.info("👈 Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader("🦺 Adicionar Ficha de EPI")
            
            if check_feature_permission('premium_ia'):
                current_employees = employee_manager.get_employees_by_company(selected_company)
                
                if not current_employees.empty:
                    st.selectbox(
                        "👤 Funcionário", 
                        current_employees['id'].tolist(), 
                        format_func=employee_manager.get_employee_name, 
                        key="epi_employee_add"
                    )
                    st.file_uploader(
                        "📎 Anexar Ficha de EPI (PDF)", 
                        type=['pdf'], 
                        key="epi_uploader_tab", 
                        on_change=process_epi_pdf,
                        help="Faça upload da ficha de controle de entrega de EPI em PDF"
                    )
                    
                    if st.session_state.get('epi_info_para_salvar'):
                        epi_info = st.session_state['epi_info_para_salvar']
                        
                        if epi_info:
                            with st.form("confirm_epi_form"):
                                st.markdown("### ✏️ Confirme as Informações Extraídas")
                                
                                nome_funcionario = epi_info.get('nome_funcionario', 'N/A')
                                st.info(f"👤 **Funcionário identificado no PDF:** {nome_funcionario}")
                                
                                itens_epi = epi_info.get('itens_epi', [])
                                
                                if itens_epi:
                                    st.markdown(f"**Total de itens encontrados:** {len(itens_epi)}")
                                    epi_df = pd.DataFrame(itens_epi)
                                    st.dataframe(epi_df, use_container_width=True, hide_index=True)
                                    
                                    if st.form_submit_button("💾 Confirmar e Salvar Ficha de EPI", type="primary"):
                                        with st.spinner("💾 Salvando..."):
                                            anexo = st.session_state.epi_anexo_para_salvar
                                            arquivo_hash = st.session_state.get('epi_hash_para_salvar')
                                            emp_id = st.session_state.epi_funcionario_para_salvar
                                            emp_name = employee_manager.get_employee_name(emp_id)
                                            nome_arquivo = f"EPI_{emp_name.replace(' ', '_')}_{date.today().strftime('%Y%m%d')}.pdf"
                                            
                                            arquivo_id = employee_manager.upload_documento_e_obter_link(anexo, nome_arquivo)
                                            
                                            if arquivo_id:
                                                saved_ids = epi_manager.add_epi_records(
                                                    emp_id, arquivo_id, itens_epi, arquivo_hash
                                                )
                                                
                                                if saved_ids:
                                                    st.success(f"✅ Ficha de EPI salva com sucesso! {len(saved_ids)} item(ns) cadastrado(s).")
                                                    
                                                    for key in list(st.session_state.keys()):
                                                        if key.startswith('epi_'):
                                                            del st.session_state[key]
                                                    st.rerun()
                                                else:
                                                    st.error("❌ Falha ao salvar os itens de EPI.")
                                else:
                                    st.warning("⚠️ Nenhum item de EPI foi identificado no PDF.")
                        else:
                            st.error("❌ Não foi possível extrair informações da Ficha de EPI.")
                else:
                    st.warning("⚠️ Cadastre funcionários nesta empresa primeiro.")
            else:
                st.info("💡 A análise automática de Fichas de EPI é um recurso do plano **Premium IA**.")
                st.warning("Para cadastrar EPIs, por favor, contate o administrador ou faça upgrade do seu plano.")

    # =============================================
    # ABA: GERENCIAR REGISTROS
    # ============================================
    with tab_manage:
        if not selected_company:
            st.info("👈 Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.header("⚙️ Gerenciar Registros Existentes")
            
            manage_tabs = st.tabs(["🩺 ASOs", "🎓 Treinamentos", "📄 Docs. Empresa", "🦺 Fichas de EPI"])
            
            # === GERENCIAR ASOs ===
            with manage_tabs[0]:
                st.subheader("🩺 ASOs Cadastrados")
                
                employees = employee_manager.get_employees_by_company(selected_company)
                if employees.empty:
                    st.info("Nenhum funcionário cadastrado.")
                else:
                    employee_filter = st.selectbox(
                        "Filtrar por Funcionário:",
                        options=['Todos'] + employees['id'].tolist(),
                        format_func=lambda x: 'Todos os Funcionários' if x == 'Todos' else employee_manager.get_employee_name(x),
                        key="aso_employee_filter"
                    )
                    
                    all_asos = []
                    employees_to_check = employees if employee_filter == 'Todos' else employees[employees['id'] == employee_filter]
                    
                    for _, emp in employees_to_check.iterrows():
                        emp_asos = employee_manager.get_latest_aso_by_employee(emp['id'])
                        if not emp_asos.empty:
                            emp_asos['nome_funcionario'] = emp['nome']
                            all_asos.append(emp_asos)
                    
                    if all_asos:
                        asos_df = pd.concat(all_asos, ignore_index=True)
                        asos_df['vencimento_dt'] = pd.to_datetime(asos_df['vencimento']).dt.date
                        
                        display_df = asos_df[['nome_funcionario', 'tipo_aso', 'data_aso', 'vencimento', 'cargo']].copy()
                        display_df['vencimento_dt'] = asos_df['vencimento_dt']
                        
                        st.dataframe(
                            display_df.style.apply(highlight_expired, axis=1),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        st.markdown("---")
                        st.subheader("🗑️ Excluir ASO")
                        
                        aso_to_delete = st.selectbox(
                            "Selecione o ASO para excluir:",
                            options=asos_df['id'].tolist(),
                            format_func=lambda x: f"{asos_df[asos_df['id']==x]['nome_funcionario'].values[0]} - {asos_df[asos_df['id']==x]['tipo_aso'].values[0]} - {asos_df[asos_df['id']==x]['data_aso'].values[0]}",
                            key="aso_delete_select"
                        )
                        
                        if st.button("🗑️ Excluir ASO Selecionado", type="secondary"):
                            aso_row = asos_df[asos_df['id'] == aso_to_delete].iloc[0]
                            st.session_state.show_delete_dialog = True
                            st.session_state.item_to_delete = {
                                'type': 'ASO',
                                'id': aso_to_delete,
                                'file_url': aso_row.get('arquivo_id')
                            }
                            st.rerun()
                    else:
                        st.info("Nenhum ASO cadastrado para os funcionários selecionados.")
            
            # === GERENCIAR TREINAMENTOS ===
            with manage_tabs[1]:
                st.subheader("🎓 Treinamentos Cadastrados")
                
                employees = employee_manager.get_employees_by_company(selected_company)
                if employees.empty:
                    st.info("Nenhum funcionário cadastrado.")
                else:
                    employee_filter = st.selectbox(
                        "Filtrar por Funcionário:",
                        options=['Todos'] + employees['id'].tolist(),
                        format_func=lambda x: 'Todos os Funcionários' if x == 'Todos' else employee_manager.get_employee_name(x),
                        key="training_employee_filter"
                    )
                    
                    all_trainings = []
                    employees_to_check = employees if employee_filter == 'Todos' else employees[employees['id'] == employee_filter]
                    
                    for _, emp in employees_to_check.iterrows():
                        emp_trainings = employee_manager.get_all_trainings_by_employee(emp['id'])
                        if not emp_trainings.empty:
                            emp_trainings['nome_funcionario'] = emp['nome']
                            all_trainings.append(emp_trainings)
                    
                    if all_trainings:
                        trainings_df = pd.concat(all_trainings, ignore_index=True)
                        trainings_df['vencimento_dt'] = pd.to_datetime(trainings_df['vencimento']).dt.date
                        
                        display_df = trainings_df[['nome_funcionario', 'norma', 'modulo', 'data', 'vencimento', 'tipo_treinamento']].copy()
                        display_df['vencimento_dt'] = trainings_df['vencimento_dt']
                        
                        st.dataframe(
                            display_df.style.apply(highlight_expired, axis=1),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        st.markdown("---")
                        st.subheader("🗑️ Excluir Treinamento")
                        
                        training_to_delete = st.selectbox(
                            "Selecione o Treinamento para excluir:",
                            options=trainings_df['id'].tolist(),
                            format_func=lambda x: f"{trainings_df[trainings_df['id']==x]['nome_funcionario'].values[0]} - {trainings_df[trainings_df['id']==x]['norma'].values[0]} - {trainings_df[trainings_df['id']==x]['data'].values[0]}",
                            key="training_delete_select"
                        )
                        
                        if st.button("🗑️ Excluir Treinamento Selecionado", type="secondary"):
                            training_row = trainings_df[trainings_df['id'] == training_to_delete].iloc[0]
                            st.session_state.show_delete_dialog = True
                            st.session_state.item_to_delete = {
                                'type': 'Treinamento',
                                'id': training_to_delete,
                                'file_url': training_row.get('anexo')
                            }
                            st.rerun()
                    else:
                        st.info("Nenhum treinamento cadastrado para os funcionários selecionados.")
            
            # === GERENCIAR DOCUMENTOS DA EMPRESA ===
            with manage_tabs[2]:
                st.subheader("📄 Documentos da Empresa")
                
                company_docs = docs_manager.get_docs_by_company(selected_company)
                
                if company_docs.empty:
                    st.info("Nenhum documento da empresa cadastrado.")
                else:
                    company_docs['vencimento_dt'] = pd.to_datetime(company_docs['vencimento']).dt.date
                    
                    display_df = company_docs[['tipo_documento', 'data_emissao', 'vencimento']].copy()
                    display_df['vencimento_dt'] = company_docs['vencimento_dt']
                    
                    st.dataframe(
                        display_df.style.apply(highlight_expired, axis=1),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("---")
                    st.subheader("🗑️ Excluir Documento")
                    
                    doc_to_delete = st.selectbox(
                        "Selecione o Documento para excluir:",
                        options=company_docs['id'].tolist(),
                        format_func=lambda x: f"{company_docs[company_docs['id']==x]['tipo_documento'].values[0]} - Emissão: {company_docs[company_docs['id']==x]['data_emissao'].values[0]}",
                        key="doc_delete_select"
                    )
                    
                    if st.button("🗑️ Excluir Documento Selecionado", type="secondary"):
                        doc_row = company_docs[company_docs['id'] == doc_to_delete].iloc[0]
                        st.session_state.show_delete_dialog = True
                        st.session_state.item_to_delete = {
                            'type': 'Doc. Empresa',
                            'id': doc_to_delete,
                            'file_url': doc_row.get('arquivo_id')
                        }
                        st.rerun()
            
            # === GERENCIAR FICHAS DE EPI ===
            with manage_tabs[3]:
                st.subheader("🦺 Fichas de EPI Cadastradas")
                
                employees = employee_manager.get_employees_by_company(selected_company)
                if employees.empty:
                    st.info("Nenhum funcionário cadastrado.")
                else:
                    employee_filter = st.selectbox(
                        "Filtrar por Funcionário:",
                        options=['Todos'] + employees['id'].tolist(),
                        format_func=lambda x: 'Todos os Funcionários' if x == 'Todos' else employee_manager.get_employee_name(x),
                        key="epi_employee_filter"
                    )
                    
                    all_epis = []
                    employees_to_check = employees if employee_filter == 'Todos' else employees[employees['id'] == employee_filter]
                    
                    for _, emp in employees_to_check.iterrows():
                        emp_epis = epi_manager.get_epi_by_employee(emp['id'])
                        if not emp_epis.empty:
                            emp_epis['nome_funcionario'] = emp['nome']
                            all_epis.append(emp_epis)
                    
                    if all_epis:
                        epis_df = pd.concat(all_epis, ignore_index=True)
                        
                        display_df = epis_df[['nome_funcionario', 'descricao_epi', 'ca_epi', 'data_entrega']].copy()
                        
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        st.markdown("---")
                        st.subheader("🗑️ Excluir Item de EPI")
                        
                        epi_to_delete = st.selectbox(
                            "Selecione o Item de EPI para excluir:",
                            options=epis_df['id'].tolist(),
                            format_func=lambda x: f"{epis_df[epis_df['id']==x]['nome_funcionario'].values[0]} - {epis_df[epis_df['id']==x]['descricao_epi'].values[0]} - CA: {epis_df[epis_df['id']==x]['ca_epi'].values[0]}",
                            key="epi_delete_select"
                        )
                        
                        if st.button("🗑️ Excluir Item de EPI Selecionado", type="secondary"):
                            epi_row = epis_df[epis_df['id'] == epi_to_delete].iloc[0]
                            st.session_state.show_delete_dialog = True
                            st.session_state.item_to_delete = {
                                'type': 'EPI',
                                'id': epi_to_delete,
                                'file_url': epi_row.get('arquivo_id')
                            }
                            st.rerun()
                    else:
                        st.info("Nenhum item de EPI cadastrado para os funcionários selecionados.")
    
    # Gerencia o diálogo de confirmação de exclusão
    handle_delete_confirmation(docs_manager, employee_manager)
