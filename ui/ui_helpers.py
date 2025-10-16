import streamlit as st
import pandas as pd
from datetime import datetime, date
from operations.file_hash import calcular_hash_arquivo
from auth.auth_utils import check_feature_permission # <-- ADICIONADO

def mostrar_info_normas():
    # ... (código inalterado)

def highlight_expired(row):
    # ... (código inalterado)

def style_audit_table(row):
    # ... (código inalterado)

def _run_analysis_and_audit(manager, analysis_method_name, uploader_key, doc_type_str, employee_id_key=None):
    # ... (código inalterado)

def process_aso_pdf():
    """Função de callback para o uploader de ASO."""
    # --- INÍCIO DA ALTERAÇÃO ---
    if not check_feature_permission('premium_ia'):
        st.error("Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'aso_uploader_tab' in st.session_state:
            st.session_state.aso_uploader_tab = None # Limpa o uploader
        return
    # --- FIM DA ALTERAÇÃO ---

    if 'employee_manager' in st.session_state:
        _run_analysis_and_audit(
            manager=st.session_state.employee_manager,
            analysis_method_name='analyze_aso_pdf',
            uploader_key='aso_uploader_tab',
            doc_type_str='ASO',
            employee_id_key='aso_employee_add'
        )

def process_training_pdf():
    """Função de callback para o uploader de Treinamento."""
    # --- INÍCIO DA ALTERAÇÃO ---
    if not check_feature_permission('premium_ia'):
        st.error("Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'training_uploader_tab' in st.session_state:
            st.session_state.training_uploader_tab = None # Limpa o uploader
        return
    # --- FIM DA ALTERAÇÃO ---

    if 'employee_manager' in st.session_state:
        _run_analysis_and_audit(
            manager=st.session_state.employee_manager,
            analysis_method_name='analyze_training_pdf',
            uploader_key='training_uploader_tab',
            doc_type_str='Treinamento',
            employee_id_key='training_employee_add'
        )

def process_company_doc_pdf():
    """Função de callback para o uploader de Documento da Empresa."""
    # --- INÍCIO DA ALTERAÇÃO ---
    if not check_feature_permission('premium_ia'):
        st.error("Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'doc_uploader_tab' in st.session_state:
            st.session_state.doc_uploader_tab = None # Limpa o uploader
        return
    # --- FIM DA ALTERAÇÃO ---

    if 'docs_manager' in st.session_state:
        _run_analysis_and_audit(
            manager=st.session_state.docs_manager,
            analysis_method_name='analyze_company_doc_pdf',
            uploader_key='doc_uploader_tab',
            doc_type_str='Doc. Empresa'
        )

def process_epi_pdf():
    """Função de callback para o uploader de Ficha de EPI."""
    if not check_feature_permission('premium_ia'):
        st.error("Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'epi_uploader_tab' in st.session_state:
            st.session_state.epi_uploader_tab = None
        return
    
    if st.session_state.get('epi_uploader_tab') and 'epi_manager' in st.session_state:
        epi_manager = st.session_state.epi_manager
        anexo = st.session_state.epi_uploader_tab
        
        with st.spinner("Analisando ficha de EPI com IA..."):
            epi_info = epi_manager.analyze_epi_pdf(anexo)
            
            if epi_info:
                arquivo_hash = calcular_hash_arquivo(anexo)
                
                st.session_state.epi_info_para_salvar = epi_info
                st.session_state.epi_anexo_para_salvar = anexo
                st.session_state.epi_hash_para_salvar = arquivo_hash
                st.session_state.epi_funcionario_para_salvar = st.session_state.get('epi_employee_add')
                
                st.success("Análise de EPI concluída!")
            else:
                st.error("Não foi possível extrair informações da ficha de EPI.")