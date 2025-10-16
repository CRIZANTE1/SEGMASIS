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
        return f"️ {name} (Arquivada)" if status == 'arquivado' else f"{name} - {row.get('cnpj', 'N/A')}"
    except (IndexError, KeyError): 
        return f"Empresa ID {company_id} (Não encontrada)"

def display_audit_results(audit_result):
    if not audit_result: 
        return
    summary = audit_result.get("summary", "Indefinido")
    details = audit_result.get("details", [])
    st.markdown("---")
    st.markdown("#####  Resultado da Auditoria Rápida")
    
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
            if col1.button("✅ Sim, Excluir", type="primary", use_container_width=True):
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
            
            if col2.button("❌ Cancelar", use_container_width=True):
                del st.session_state.show_delete_dialog
                del st.session_state.item_to_delete
                st.rerun()
        
        confirm_delete_dialog()

def show_dashboard_page():
    logger.info("Iniciando a renderização da página do dashboard.")
    
    if st.session_state.get('is_global_view', False):
        st.title(" Dashboard Global - Todas as Unidades")
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
        st.title(f" Dashboard de Conformidade: {st.session_state.get('single_company_name')}")
        selected_company = st.session_state.get('single_company_id')
    else:
        st.title(" Dashboard de Conformidade")
        company_options = [None] + employee_manager.companies_df['id'].astype(str).tolist()
        selected_company = st.selectbox(
            " Selecione uma empresa para ver os detalhes:",
            options=company_options,
            format_func=lambda cid: format_company_display(cid, employee_manager.companies_df),
            key="company_selector",
            placeholder="Selecione uma empresa..."
        )

    tab_list = [
        " Situação Geral", 
        " Adicionar Doc. Empresa", 
        " Adicionar ASO", 
        " Adicionar Treinamento", 
        " Adicionar Ficha de EPI", 
        "⚙️ Gerenciar Registros"
    ]
    
    tab_situacao, tab_add_doc_empresa, tab_add_aso, tab_add_treinamento, tab_add_epi, tab_manage = st.tabs(tab_list)

    # ============================================
    # ABA: SITUAÇÃO GERAL
    # ============================================
    with tab_situacao:
        if not selected_company:
            st.info(" Selecione uma empresa no menu acima para visualizar sua situação de conformidade.")
        else:
            company_name = employee_manager.get_company_name(selected_company)
            st.header(f" Situação Geral: {company_name}")
            
            employees = employee_manager.get_employees_by_company(selected_company)
            
            if employees.empty:
                st.warning("⚠️ Nenhum funcionário cadastrado nesta empresa.")
            else:
                st.success(f" **Total de Funcionários Ativos:** {len(employees)}")
                
                today = date.today()
                
                # === ASOs ===
                st.subheader(" Situação dos ASOs")
                total_asos = 0
                asos_vencidos = 0
                asos_proximos = 0
                
                for _, emp in employees.iterrows():
                    emp_asos = employee_manager.get_latest_aso_by_employee(emp['id'])
                    if not emp_asos.empty:
                        for _, aso in emp_asos.iterrows():
                            total_asos += 1
                            vencimento = pd.to_datetime(aso['vencimento']).date()
                            if vencimento < today:
                                asos_vencidos += 1
                            elif vencimento <= today + pd.Timedelta(days=30):
                                asos_proximos += 1
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de ASOs", total_asos)
                col2.metric(" Vencidos", asos_vencidos, delta_color="inverse")
                col3.metric(" Vencem em 30 dias", asos_proximos, delta_color="normal")
                
                # === Treinamentos ===
                st.subheader(" Situação dos Treinamentos")
                total_trainings = 0
                trainings_vencidos = 0
                trainings_proximos = 0
                
                for _, emp in employees.iterrows():
                    emp_trainings = employee_manager.get_all_trainings_by_employee(emp['id'])
                    if not emp_trainings.empty:
                        for _, training in emp_trainings.iterrows():
                            total_trainings += 1
                            vencimento = pd.to_datetime(training['vencimento']).date()
                            if vencimento < today:
                                trainings_vencidos += 1
                            elif vencimento <= today + pd.Timedelta(days=30):
                                trainings_proximos += 1
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Treinamentos", total_trainings)
                col2.metric(" Vencidos", trainings_vencidos, delta_color="inverse")
                col3.metric(" Vencem em 30 dias", trainings_proximos, delta_color="normal")
                
                # === Documentos da Empresa ===
                st.subheader(" Documentos da Empresa")
                company_docs = docs_manager.get_docs_by_company(selected_company)
                
                if company_docs.empty:
                    st.info("ℹ️ Nenhum documento da empresa cadastrado.")
                else:
                    docs_vencidos = 0
                    docs_proximos = 0
                    
                    for _, doc in company_docs.iterrows():
                        vencimento = pd.to_datetime(doc['vencimento']).date()
                        if vencimento < today:
                            docs_vencidos += 1
                        elif vencimento <= today + pd.Timedelta(days=30):
                            docs_proximos += 1
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total de Documentos", len(company_docs))
                    col2.metric(" Vencidos", docs_vencidos, delta_color="inverse")
                    col3.metric(" Vencem em 30 dias", docs_proximos, delta_color="normal")
                    
                    with st.expander(" Ver Documentos Cadastrados"):
                        docs_display = company_docs[['tipo_documento', 'data_emissao', 'vencimento']].copy()
                        docs_display['vencimento_dt'] = pd.to_datetime(docs_display['vencimento']).dt.date
                        docs_display['Status'] = docs_display['vencimento_dt'].apply(
                            lambda x: ' Vencido' if x < today else (' Próximo' if x <= today + pd.Timedelta(days=30) else ' Válido')
                        )
                        st.dataframe(
                            docs_display[['tipo_documento', 'data_emissao', 'vencimento', 'Status']]
                            .style.apply(highlight_expired, axis=1),
                            use_container_width=True,
                            hide_index=True
                        )
                
                # === Funcionários com Pendências ===
                st.subheader(" Funcionários com Pendências")
                
                pendencias_funcionarios = []
                for _, emp in employees.iterrows():
                    pendencias = []
                    
                    emp_asos = employee_manager.get_latest_aso_by_employee(emp['id'])
                    if emp_asos.empty:
                        pendencias.append("ASO ausente")
                    else:
                        for _, aso in emp_asos.iterrows():
                            vencimento = pd.to_datetime(aso['vencimento']).date()
                            if vencimento < today:
                                pendencias.append(f"ASO {aso['tipo_aso']} vencido")
                    
                    emp_trainings = employee_manager.get_all_trainings_by_employee(emp['id'])
                    if not emp_trainings.empty:
                        for _, training in emp_trainings.iterrows():
                            vencimento = pd.to_datetime(training['vencimento']).date()
                            if vencimento < today:
                                pendencias.append(f"{training['norma']} vencido")
                    
                    if pendencias:
                        pendencias_funcionarios.append({
                            'Funcionário': emp['nome'],
                            'Cargo': emp['cargo'],
                            'Pendências': ', '.join(pendencias)
                        })
                
                if pendencias_funcionarios:
                    st.warning(f"⚠️ {len(pendencias_funcionarios)} funcionário(s) com pendências")
                    pendencias_df = pd.DataFrame(pendencias_funcionarios)
                    st.dataframe(pendencias_df, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Todos os funcionários estão com documentação em dia!")
                
                # === Gráfico de Vencimentos ===
                if st.checkbox(" Mostrar gráfico de vencimentos"):
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name='ASOs',
                        x=['Válidos', 'Vencidos', 'Próximos (30d)'],
                        y=[total_asos - asos_vencidos - asos_proximos, asos_vencidos, asos_proximos],
                        marker_color=['green', 'red', 'orange']
                    ))
                    fig.add_trace(go.Bar(
                        name='Treinamentos',
                        x=['Válidos', 'Vencidos', 'Próximos (30d)'],
                        y=[total_trainings - trainings_vencidos - trainings_proximos, trainings_vencidos, trainings_proximos],
                        marker_color=['green', 'red', 'orange']
                    ))
                    
                    fig.update_layout(
                        title='Status de Documentação',
                        xaxis_title='Status',
                        yaxis_title='Quantidade',
                        barmode='group'
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # ============================================
    # ABA: ADICIONAR DOCUMENTO DA EMPRESA
    # ============================================
    with tab_add_doc_empresa:
        if not selected_company:
            st.info(" Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader(" Adicionar Documento da Empresa (PGR, PCMSO, etc.)")
            company_name = employee_manager.get_company_name(selected_company)
            st.info(f" Adicionando documento para: **{company_name}**")
            
            st.file_uploader(
                " Anexar Documento (PDF)", 
                type=['pdf'], 
                key="doc_uploader_tab", 
                on_change=process_company_doc_pdf,
                help="Faça upload do documento em formato PDF"
            )
            
            if st.session_state.get('Doc. Empresa_info_para_salvar'):
                doc_info = st.session_state['Doc. Empresa_info_para_salvar']
                
                with st.form("confirm_doc_empresa_form"):
                    st.markdown("### ✏️ Confirme e Edite as Informações Extraídas")
                    
                    doc_types = ["PGR", "PCMSO", "PPR", "PCA", "Outro"]
                    try:
                        default_index = doc_types.index(doc_info.get('tipo_documento', 'Outro'))
                    except ValueError:
                        default_index = len(doc_types) - 1
                    
                    edited_tipo = st.selectbox(" Tipo de Documento", doc_types, index=default_index)
                    edited_data_emissao = st.date_input(" Data de Emissão", value=doc_info.get('data_emissao'))

                    display_audit_results(doc_info.get('audit_result'))

                    if st.form_submit_button(" Confirmar e Salvar Documento", type="primary"):
                        with st.spinner(" Salvando..."):
                            vencimento = edited_data_emissao + pd.DateOffset(years=2) if edited_tipo == "PGR" else edited_data_emissao + pd.DateOffset(years=1)
                            
                            anexo = st.session_state['Doc. Empresa_anexo_para_salvar']
                            arquivo_hash = st.session_state.get('Doc. Empresa_hash_para_salvar')
                            nome_arquivo = f"{edited_tipo}_{company_name.replace(' ', '_')}_{edited_data_emissao.strftime('%Y%m%d')}.pdf"
                            
                            arquivo_id = employee_manager.upload_documento_e_obter_link(anexo, nome_arquivo)
                            
                            if arquivo_id:
                                doc_id = docs_manager.add_company_document(
                                    selected_company, edited_tipo, 
                                    edited_data_emissao, vencimento.date(), arquivo_id, arquivo_hash
                                )
                                if doc_id:
                                    st.success("✅ Documento da empresa salvo com sucesso!")
                                    
                                    # Adiciona ao plano de ação se houver não conformidades
                                    audit_result = doc_info.get('audit_result')
                                    if audit_result and 'não conforme' in audit_result.get('summary', '').lower():
                                        nr_analyzer = st.session_state.get('nr_analyzer')
                                        if nr_analyzer:
                                            nr_analyzer.create_action_plan_from_audit(
                                                audit_result, selected_company, doc_id
                                            )
                                    
                                    for key in list(st.session_state.keys()):
                                        if key.startswith('Doc. Empresa_'):
                                            del st.session_state[key]
                                    st.rerun()
                                else:
                                    st.error("❌ Falha ao salvar o documento no banco de dados.")

    # ============================================
    # ABA: ADICIONAR ASO
    # ============================================
    with tab_add_aso:
        if not selected_company:
            st.info(" Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader(" Adicionar Novo ASO")
            current_employees = employee_manager.get_employees_by_company(selected_company)
            
            if not current_employees.empty:
                st.selectbox(
                    " Funcionário", 
                    current_employees['id'].tolist(), 
                    format_func=employee_manager.get_employee_name, 
                    key="aso_employee_add"
                )
                st.file_uploader(
                    " Anexar ASO (PDF)", 
                    type=['pdf'], 
                    key="aso_uploader_tab", 
                    on_change=process_aso_pdf,
                    help="Faça upload do Atestado de Saúde Ocupacional em PDF"
                )
                
                if st.session_state.get('ASO_info_para_salvar'):
                    aso_info = st.session_state.ASO_info_para_salvar
                    
                    with st.form("confirm_aso_form"):
                        st.markdown("### ✏️ Confirme e Edite as Informações Extraídas")
                        
                        edited_data_aso = st.date_input(" Data do ASO", value=aso_info.get('data_aso'))
                        aso_types = ['Admissional', 'Periódico', 'Demissional', 'Mudança de Risco', 'Retorno ao Trabalho', 'Monitoramento Pontual', 'Não identificado']
                        try:
                            default_index = aso_types.index(aso_info.get('tipo_aso', 'Não identificado'))
                        except ValueError:
                            default_index = len(aso_types) - 1
                        edited_tipo_aso = st.selectbox(" Tipo de ASO", aso_types, index=default_index)
                        edited_vencimento = st.date_input("⏰ Vencimento", value=aso_info.get('vencimento'))
                        
                        display_audit_results(aso_info.get('audit_result'))

                        if st.form_submit_button(" Confirmar e Salvar ASO", type="primary"):
                            with st.spinner(" Salvando..."):
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
                                        'riscos': aso_info.get('riscos', ''), 
                                        'cargo': aso_info.get('cargo', '')
                                    }
                                    aso_id = employee_manager.add_aso(aso_data)
                                    if aso_id:
                                        st.success("✅ ASO salvo com sucesso!")
                                        
                                        # Adiciona ao plano de ação se houver não conformidades
                                        audit_result = aso_info.get('audit_result')
                                        if audit_result and 'não conforme' in audit_result.get('summary', '').lower():
                                            nr_analyzer = st.session_state.get('nr_analyzer')
                                            if nr_analyzer:
                                                nr_analyzer.create_action_plan_from_audit(
                                                    audit_result, selected_company, aso_id, employee_id=emp_id
                                                )
                                        
                                        for key in list(st.session_state.keys()):
                                            if key.startswith('ASO_'):
                                                del st.session_state[key]
                                        st.rerun()
                                    else:
                                        st.error("❌ Falha ao salvar o ASO.")
            else:
                st.warning("⚠️ Cadastre funcionários nesta empresa primeiro.")

    # ============================================
    # ABA: ADICIONAR TREINAMENTO
    # ============================================
    with tab_add_treinamento:
        if not selected_company:
            st.info(" Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader(" Adicionar Novo Treinamento")
            mostrar_info_normas()
            current_employees = employee_manager.get_employees_by_company(selected_company)
            
            if not current_employees.empty:
                st.selectbox(
                    " Funcionário", 
                    current_employees['id'].tolist(), 
                    format_func=employee_manager.get_employee_name, 
                    key="training_employee_add"
                )
                
                if check_feature_permission('premium_ia'):
                    st.file_uploader(
                        " Anexar Certificado (PDF)", 
                        type=['pdf'], 
                        key="training_uploader_tab", 
                        on_change=process_training_pdf,
                        help="Faça upload do certificado de treinamento em PDF"
                    )
                else:
                    st.warning("⚠️ Análise de PDF com IA é um recurso do Plano Premium.")
                    st.info(" Para usar esta funcionalidade, faça o upgrade do seu plano ou entre em contato com o suporte.")
                
                if st.session_state.get('Treinamento_info_para_salvar'):
                    training_info = st.session_state['Treinamento_info_para_salvar']
                    
                    with st.form("confirm_training_form"):
                        st.markdown("### ✏️ Confirme e Edite as Informações Extraídas")

                        edited_data = st.date_input(" Data de Realização", value=training_info.get('data'))
                        
                        norma_options = sorted(list(employee_manager.nr_config.keys()) + list(employee_manager.nr20_config.keys()))
                        edited_norma = st.selectbox(
                            " Norma", 
                            options=norma_options, 
                            index=norma_options.index(training_info['norma']) if training_info.get('norma') in norma_options else 0
                        )
                        
                        tipo_options = ["formação", "reciclagem"]
                        edited_tipo = st.selectbox(
                            " Tipo de Treinamento", 
                            tipo_options, 
                            index=tipo_options.index(training_info['tipo_treinamento']) if training_info.get('tipo_treinamento') in tipo_options else 0
                        )

                        edited_ch = st.number_input("⏱️ Carga Horária (h)", min_value=0, value=training_info.get('carga_horaria', 0))

                        display_audit_results(training_info.get('audit_result'))

                        if st.form_submit_button(" Confirmar e Salvar Treinamento", type="primary"):
                            with st.spinner(" Salvando..."):
                                vencimento = employee_manager.calcular_vencimento_treinamento(
                                    edited_data, edited_norma, training_info.get('modulo'), edited_tipo
                                )
                                
                                if not vencimento:
                                    st.error("❌ Não foi possível calcular o vencimento. Verifique as regras para esta norma.")
                                    st.stop()

                                anexo = st.session_state.Treinamento_anexo_para_salvar
                                arquivo_hash = st.session_state.get('Treinamento_hash_para_salvar')
                                emp_id = st.session_state.Treinamento_funcionario_para_salvar
                                emp_name = employee_manager.get_employee_name(emp_id)
                                nome_arquivo = f"TRAINING_{emp_name.replace(' ', '_')}_{edited_norma}_{edited_data.strftime('%Y%m%d')}.pdf"
                                
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
                                        'vencimento': vencimento, 
                                        'modulo': training_info.get('modulo', 'N/A')
                                    }
                                    training_id = employee_manager.add_training(training_data)
                                    
                                    if training_id:
                                        st.success("✅ Treinamento salvo com sucesso!")
                                        
                                        # Adiciona ao plano de ação se houver não conformidades
                                        audit_result = training_info.get('audit_result')
                                        if audit_result and 'não conforme' in audit_result.get('summary', '').lower():
                                            nr_analyzer = st.session_state.get('nr_analyzer')
                                            if nr_analyzer:
                                                nr_analyzer.create_action_plan_from_audit(
                                                    audit_result, selected_company, training_id, employee_id=emp_id
                                                )
                                        
                                        for key in list(st.session_state.keys()):
                                            if key.startswith('Treinamento_'):
                                                del st.session_state[key]
                                        st.rerun()
                                    else:
                                        st.error("❌ Falha ao salvar o treinamento.")
            else:
                st.warning("⚠️ Cadastre funcionários nesta empresa primeiro.")

    # ============================================
    # ABA: ADICIONAR FICHA DE EPI
    # ============================================
    with tab_add_epi:
        if not selected_company:
            st.info(" Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader(" Adicionar Ficha de EPI")
            current_employees = employee_manager.get_employees_by_company(selected_company)
            
            if not current_employees.empty:
                st.selectbox(
                    " Funcionário", 
                    current_employees['id'].tolist(), 
                    format_func=employee_manager.get_employee_name, 
                    key="epi_employee_add"
                )
                st.file_uploader(
                    " Anexar Ficha de EPI (PDF)", 
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
                            st.info(f" **Funcionário identificado no PDF:** {nome_funcionario}")
                            
                            itens_epi = epi_info.get('itens_epi', [])
                            
                            if itens_epi:
                                st.markdown(f"**Total de itens encontrados:** {len(itens_epi)}")
                                
                                # Exibe tabela com os itens
                                epi_df = pd.DataFrame(itens_epi)
                                st.dataframe(epi_df, use_container_width=True, hide_index=True)
                                
                                if st.form_submit_button(" Confirmar e Salvar Ficha de EPI", type="primary"):
                                    with st.spinner(" Salvando..."):
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

    # ============================================
    # ABA: GERENCIAR REGISTROS
    # ============================================
    with tab_manage:
        if not selected_company:
            st.info(" Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.header("⚙️ Gerenciar Registros Existentes")
            
            manage_tabs = st.tabs([" ASOs", " Treinamentos", " Docs. Empresa", " Fichas de EPI"])
            
            # === GERENCIAR ASOs ===
            with manage_tabs[0]:
                st.subheader(" ASOs Cadastrados")
                
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
                        st.subheader("️ Excluir ASO")
                        
                        aso_to_delete = st.selectbox(
                            "Selecione o ASO para excluir:",
                            options=asos_df['id'].tolist(),
                            format_func=lambda x: f"{asos_df[asos_df['id']==x]['nome_funcionario'].values[0]} - {asos_df[asos_df['id']==x]['tipo_aso'].values[0]} - {asos_df[asos_df['id']==x]['data_aso'].values[0]}",
                            key="aso_delete_select"
                        )
                        
                        if st.button("️ Excluir ASO Selecionado", type="secondary"):
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
                st.subheader(" Treinamentos Cadastrados")
                
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
                        st.subheader("️ Excluir Treinamento")
                        
                        training_to_delete = st.selectbox(
                            "Selecione o Treinamento para excluir:",
                            options=trainings_df['id'].tolist(),
                            format_func=lambda x: f"{trainings_df[trainings_df['id']==x]['nome_funcionario'].values[0]} - {trainings_df[trainings_df['id']==x]['norma'].values[0]} - {trainings_df[trainings_df['id']==x]['data'].values[0]}",
                            key="training_delete_select"
                        )
                        
                        if st.button("️ Excluir Treinamento Selecionado", type="secondary"):
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
                st.subheader(" Documentos da Empresa")
                
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
                    st.subheader("️ Excluir Documento")
                    
                    doc_to_delete = st.selectbox(
                        "Selecione o Documento para excluir:",
                        options=company_docs['id'].tolist(),
                        format_func=lambda x: f"{company_docs[company_docs['id']==x]['tipo_documento'].values[0]} - Emissão: {company_docs[company_docs['id']==x]['data_emissao'].values[0]}",
                        key="doc_delete_select"
                    )
                    
                    if st.button("️ Excluir Documento Selecionado", type="secondary"):
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
                st.subheader(" Fichas de EPI Cadastradas")
                
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
                        st.subheader("️ Excluir Item de EPI")
                        
                        epi_to_delete = st.selectbox(
                            "Selecione o Item de EPI para excluir:",
                            options=epis_df['id'].tolist(),
                            format_func=lambda x: f"{epis_df[epis_df['id']==x]['nome_funcionario'].values[0]} - {epis_df[epis_df['id']==x]['descricao_epi'].values[0]} - CA: {epis_df[epis_df['id']==x]['ca_epi'].values[0]}",
                            key="epi_delete_select"
                        )
                        
                        if st.button("️ Excluir Item de EPI Selecionado", type="secondary"):
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