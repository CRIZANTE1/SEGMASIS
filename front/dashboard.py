import streamlit as st
from datetime import date
import pandas as pd
import logging
from fuzzywuzzy import process

from auth.auth_utils import check_permission
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
    if company_id is None: return "Selecione..."
    try:
        row = companies_df[companies_df['id'] == str(company_id)].iloc[0]
        name, status = row.get('nome', f"ID {company_id}"), str(row.get('status', 'Ativo')).lower()
        return f"️ {name} (Arquivada)" if status == 'arquivado' else f"{name} - {row.get('cnpj', 'N/A')}"
    except (IndexError, KeyError): return f"Empresa ID {company_id} (Não encontrada)"

def display_audit_results(audit_result):
    if not audit_result: return
    summary = audit_result.get("summary", "Indefinido")
    details = audit_result.get("details", [])
    st.markdown("---"); st.markdown("#####  Resultado da Auditoria Rápida")
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
    # ... (código inalterado)
    pass

def show_dashboard_page():
    logger.info("Iniciando a renderização da página do dashboard.")
    
    if st.session_state.get('is_global_view', False):
        st.title(" Dashboard Global - Todas as Unidades")
        #show_global_consolidated_dashboard() # Função movida para administracao.py
        st.info("A visão detalhada do dashboard global está na página de Administração.")
        return
    
    if not st.session_state.get('managers_initialized'):
        st.warning("Selecione uma unidade ou empresa para visualizar o dashboard.")
        return
        
    employee_manager = st.session_state.employee_manager
    docs_manager = st.session_state.docs_manager
    epi_manager = st.session_state.epi_manager
    matrix_manager_unidade = st.session_state.matrix_manager_unidade
    
    is_single_mode = st.session_state.get('is_single_company_mode', False)

    if is_single_mode:
        st.title(f"Dashboard de Conformidade: {st.session_state.get('single_company_name')}")
        selected_company = st.session_state.get('single_company_id')
    else:
        st.title("Dashboard de Conformidade")
        company_options = [None] + employee_manager.companies_df['id'].astype(str).tolist()
        selected_company = st.selectbox(
            "Selecione uma empresa para ver os detalhes:",
            options=company_options,
            format_func=lambda cid: format_company_display(cid, employee_manager.companies_df),
            key="company_selector",
            placeholder="Selecione uma empresa..."
        )

    tab_list = [
        "**Situação Geral**", "Adicionar Doc. Empresa", "Adicionar ASO", 
        "Adicionar Treinamento", "Adicionar Ficha de EPI", "⚙️ Gerenciar Registros"
    ]
    
    tab_situacao, tab_add_doc_empresa, tab_add_aso, tab_add_treinamento, tab_add_epi, tab_manage = st.tabs(tab_list)

    with tab_situacao:
        # ... (código da aba de situação geral permanece inalterado)
        pass

    with tab_add_doc_empresa:
        if not selected_company:
            st.info("Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader("Adicionar Documento da Empresa (PGR, PCMSO, etc.)")
            company_name = employee_manager.get_company_name(selected_company)
            st.info(f"Adicionando documento para: **{company_name}**")
            
            st.file_uploader("Anexar Documento (PDF)", type=['pdf'], key="doc_uploader_tab", on_change=process_company_doc_pdf)
            
            if st.session_state.get('Doc. Empresa_info_para_salvar'):
                doc_info = st.session_state['Doc. Empresa_info_para_salvar']
                
                with st.form("confirm_doc_empresa_form"):
                    st.markdown("### Confirme e Edite as Informações Extraídas")
                    
                    doc_types = ["PGR", "PCMSO", "PPR", "PCA", "Outro"]
                    try:
                        default_index = doc_types.index(doc_info.get('tipo_documento', 'Outro'))
                    except ValueError:
                        default_index = len(doc_types) - 1 # Índice de 'Outro'
                    
                    edited_tipo = st.selectbox("Tipo de Documento", doc_types, index=default_index)
                    edited_data_emissao = st.date_input("Data de Emissão", value=doc_info.get('data_emissao'))

                    display_audit_results(doc_info.get('audit_result'))

                    if st.form_submit_button("Confirmar e Salvar Documento", type="primary"):
                        with st.spinner("Salvando..."):
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
                                    st.success("Documento da empresa salvo com sucesso!")
                                    # Lógica do plano de ação...
                                    # Limpa o estado e recarrega
                                    for key in list(st.session_state.keys()):
                                        if key.startswith('Doc. Empresa_'):
                                            del st.session_state[key]
                                    st.rerun()

    with tab_add_aso:
        if not selected_company:
            st.info("Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader("Adicionar Novo ASO")
            current_employees = employee_manager.get_employees_by_company(selected_company)
            if not current_employees.empty:
                st.selectbox("Funcionário", current_employees['id'].tolist(), format_func=employee_manager.get_employee_name, key="aso_employee_add")
                st.file_uploader("Anexar ASO (PDF)", type=['pdf'], key="aso_uploader_tab", on_change=process_aso_pdf)
                
                if st.session_state.get('ASO_info_para_salvar'):
                    aso_info = st.session_state.ASO_info_para_salvar
                    
                    with st.form("confirm_aso_form"):
                        st.markdown("### Confirme e Edite as Informações Extraídas")
                        
                        edited_data_aso = st.date_input("Data do ASO", value=aso_info.get('data_aso'))
                        aso_types = ['Admissional', 'Periódico', 'Demissional', 'Mudança de Risco', 'Retorno ao Trabalho', 'Monitoramento Pontual', 'Não identificado']
                        try:
                            default_index = aso_types.index(aso_info.get('tipo_aso', 'Não identificado'))
                        except ValueError:
                            default_index = len(aso_types) - 1
                        edited_tipo_aso = st.selectbox("Tipo de ASO", aso_types, index=default_index)
                        edited_vencimento = st.date_input("Vencimento", value=aso_info.get('vencimento'))
                        
                        display_audit_results(aso_info.get('audit_result'))

                        if st.form_submit_button("Confirmar e Salvar ASO", type="primary"):
                            with st.spinner("Salvando..."):
                                anexo = st.session_state.ASO_anexo_para_salvar
                                arquivo_hash = st.session_state.get('ASO_hash_para_salvar')
                                emp_id = st.session_state.ASO_funcionario_para_salvar
                                emp_name = employee_manager.get_employee_name(emp_id)
                                nome_arquivo = f"ASO_{emp_name.replace(' ', '_')}_{edited_data_aso.strftime('%Y%m%d')}.pdf"
                                
                                arquivo_id = employee_manager.upload_documento_e_obter_link(anexo, nome_arquivo)
                                
                                if arquivo_id:
                                    aso_data = {
                                        'funcionario_id': emp_id, 'arquivo_id': arquivo_id, 'arquivo_hash': arquivo_hash,
                                        'data_aso': edited_data_aso, 'tipo_aso': edited_tipo_aso, 'vencimento': edited_vencimento,
                                        'riscos': aso_info.get('riscos', ''), 'cargo': aso_info.get('cargo', '')
                                    }
                                    aso_id = employee_manager.add_aso(aso_data)
                                    if aso_id:
                                        st.success("ASO salvo com sucesso!")
                                        # Lógica do plano de ação...
                                        for key in list(st.session_state.keys()):
                                            if key.startswith('ASO_'):
                                                del st.session_state[key]
                                        st.rerun()
            else:
                st.warning("Cadastre funcionários nesta empresa primeiro.")

    with tab_add_treinamento:
        if not selected_company:
            st.info("Selecione uma empresa na aba 'Situação Geral' primeiro.")
        elif check_permission(level='editor'):
            st.subheader("Adicionar Novo Treinamento")
            mostrar_info_normas()
            current_employees = employee_manager.get_employees_by_company(selected_company)
            if not current_employees.empty:
                st.selectbox("Funcionário", current_employees['id'].tolist(), format_func=employee_manager.get_employee_name, key="training_employee_add")
                st.file_uploader("Anexar Certificado (PDF)", type=['pdf'], key="training_uploader_tab", on_change=process_training_pdf)
                
                if st.session_state.get('Treinamento_info_para_salvar'):
                    training_info = st.session_state['Treinamento_info_para_salvar']
                    
                    with st.form("confirm_training_form"):
                        st.markdown("### Confirme e Edite as Informações Extraídas")

                        edited_data = st.date_input("Data de Realização", value=training_info.get('data'))
                        
                        norma_options = sorted(list(employee_manager.nr_config.keys()) + list(employee_manager.nr20_config.keys()))
                        edited_norma = st.selectbox("Norma", options=norma_options, index=norma_options.index(training_info['norma']) if training_info.get('norma') in norma_options else 0)
                        
                        tipo_options = ["formação", "reciclagem"]
                        edited_tipo = st.selectbox("Tipo de Treinamento", tipo_options, index=tipo_options.index(training_info['tipo_treinamento']) if training_info.get('tipo_treinamento') in tipo_options else 0)

                        edited_ch = st.number_input("Carga Horária (h)", min_value=0, value=training_info.get('carga_horaria', 0))

                        display_audit_results(training_info.get('audit_result'))

                        if st.form_submit_button("Confirmar e Salvar Treinamento", type="primary"):
                            with st.spinner("Salvando..."):
                                vencimento = employee_manager.calcular_vencimento_treinamento(edited_data, edited_norma, training_info.get('modulo'), edited_tipo)
                                if not vencimento:
                                    st.error("Não foi possível calcular o vencimento. Verifique as regras para esta norma.")
                                    st.stop()

                                anexo = st.session_state.Treinamento_anexo_para_salvar
                                arquivo_hash = st.session_state.get('Treinamento_hash_para_salvar')
                                emp_id = st.session_state.Treinamento_funcionario_para_salvar
                                emp_name = employee_manager.get_employee_name(emp_id)
                                nome_arquivo = f"TRAINING_{emp_name.replace(' ', '_')}_{edited_norma}_{edited_data.strftime('%Y%m%d')}.pdf"
                                
                                arquivo_id = employee_manager.upload_documento_e_obter_link(anexo, nome_arquivo)
                                
                                if arquivo_id:
                                    training_data = {
                                        'funcionario_id': emp_id, 'anexo': arquivo_id, 'arquivo_hash': arquivo_hash,
                                        'data': edited_data, 'norma': edited_norma, 'tipo_treinamento': edited_tipo,
                                        'carga_horaria': edited_ch, 'vencimento': vencimento, 'modulo': training_info.get('modulo', 'N/A')
                                    }
                                    training_id = employee_manager.add_training(training_data)
                                    if training_id:
                                        st.success("Treinamento salvo com sucesso!")
                                        # Lógica do plano de ação...
                                        for key in list(st.session_state.keys()):
                                            if key.startswith('Treinamento_'):
                                                del st.session_state[key]
                                        st.rerun()
            else:
                st.warning("Cadastre funcionários nesta empresa primeiro.")

    with tab_add_epi:
        # ... (código da aba EPI permanece inalterado)
        pass

    with tab_manage:
        # ... (código da aba de gerenciamento de registros permanece inalterado)
        pass
    
    #handle_delete_confirmation(docs_manager, employee_manager) # Chamada no final, se necessário