import streamlit as st
import pandas as pd
from datetime import datetime, date
from operations.file_hash import calcular_hash_arquivo
from auth.auth_utils import check_feature_permission

def mostrar_info_normas():
    """Exibe informações sobre as normas regulamentadoras."""
    with st.expander("ℹ️ Informações sobre Normas Regulamentadoras"):
        st.markdown("""
        ### Principais Normas de Treinamento
        
        - **NR-10**: Segurança em Instalações e Serviços em Eletricidade (40h inicial, 40h reciclagem a cada 2 anos)
        - **NR-10 SEP**: Sistema Elétrico de Potência (requisito adicional para alta tensão)
        - **NR-11**: Transporte, Movimentação, Armazenagem e Manuseio de Materiais (16h)
        - **NR-20**: Segurança e Saúde no Trabalho com Inflamáveis e Combustíveis
          - Básico: 8h inicial, 4h reciclagem (3 anos)
          - Intermediário: 16h inicial, 4h reciclagem (2 anos)
          - Avançado I: 20h inicial, 4h reciclagem (2 anos)
          - Avançado II: 32h inicial, 4h reciclagem (1 ano)
        - **NR-33**: Segurança e Saúde nos Trabalhos em Espaços Confinados
          - Trabalhador Autorizado: 16h inicial, 8h reciclagem (1 ano)
          - Supervisor: 40h inicial, 8h reciclagem (1 ano)
        - **NR-35**: Trabalho em Altura (8h inicial, 8h reciclagem a cada 2 anos)
        
        **Nota**: As cargas horárias e prazos são baseados nas normas vigentes.
        """)

def highlight_expired(row):
    """Aplica estilo a linhas com documentos vencidos."""
    try:
        if 'vencimento_dt' not in row.index:
            return [''] * len(row)
        
        vencimento = row['vencimento_dt']
        if pd.isna(vencimento):
            return [''] * len(row)
        
        today = date.today()
        if vencimento < today:
            return ['background-color: #ffcccc'] * len(row)
        elif vencimento <= today + pd.Timedelta(days=30):
            return ['background-color: #fff4cc'] * len(row)
        else:
            return [''] * len(row)
    except Exception:
        return [''] * len(row)

def style_audit_table(row):
    """Aplica estilo às linhas da tabela de auditoria."""
    try:
        status = str(row.get('status', '')).lower()
        if 'não conforme' in status:
            return ['background-color: #ffcccc'] * len(row)
        elif 'conforme' in status:
            return ['background-color: #ccffcc'] * len(row)
        else:
            return [''] * len(row)
    except Exception:
        return [''] * len(row)

def _run_analysis_and_audit(manager, analysis_method_name, uploader_key, doc_type_str, employee_id_key=None):
    """
    Função auxiliar que executa a análise de PDF e auditoria com IA.
    
    Args:
        manager: Manager que contém o método de análise
        analysis_method_name: Nome do método de análise (ex: 'analyze_aso_pdf')
        uploader_key: Chave do uploader no session_state
        doc_type_str: Tipo do documento (ex: 'ASO', 'Treinamento')
        employee_id_key: Chave opcional do employee_id no session_state
    """
    if not st.session_state.get(uploader_key):
        return
    
    anexo = st.session_state[uploader_key]
    
    with st.spinner(f"🤖 Analisando {doc_type_str} com IA..."):
        # Chama o método de análise do manager
        analysis_method = getattr(manager, analysis_method_name)
        doc_info = analysis_method(anexo)
        
        if not doc_info:
            st.error(f"❌ Não foi possível extrair informações do {doc_type_str}.")
            return
        
        # Calcula hash do arquivo
        arquivo_hash = calcular_hash_arquivo(anexo)
        
        # Executa auditoria se disponível
        audit_result = None
        if hasattr(st.session_state, 'nr_analyzer') and st.session_state.nr_analyzer:
            try:
                with st.spinner("🔍 Executando auditoria de conformidade..."):
                    nr_analyzer = st.session_state.nr_analyzer
                    
                    # Prepara informações para auditoria
                    audit_doc_info = {
                        "type": doc_type_str,
                        "norma": doc_info.get('norma', doc_info.get('tipo_documento', ''))
                    }
                    
                    audit_result = nr_analyzer.perform_initial_audit(audit_doc_info, anexo.getvalue())
                    
                    if audit_result:
                        doc_info['audit_result'] = audit_result
                        st.success("✅ Auditoria concluída!")
            except Exception as e:
                st.warning(f"⚠️ Auditoria não disponível: {str(e)}")
        
        # Armazena no session_state
        st.session_state[f'{doc_type_str}_info_para_salvar'] = doc_info
        st.session_state[f'{doc_type_str}_anexo_para_salvar'] = anexo
        st.session_state[f'{doc_type_str}_hash_para_salvar'] = arquivo_hash
        
        if employee_id_key and employee_id_key in st.session_state:
            st.session_state[f'{doc_type_str}_funcionario_para_salvar'] = st.session_state[employee_id_key]
        
        st.success(f"✅ Análise de {doc_type_str} concluída!")

def process_aso_pdf():
    """Função de callback para o uploader de ASO."""
    if not check_feature_permission('premium_ia'):
        st.error("❌ Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'aso_uploader_tab' in st.session_state:
            st.session_state.aso_uploader_tab = None
        return

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
    if not check_feature_permission('premium_ia'):
        st.error("❌ Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'training_uploader_tab' in st.session_state:
            st.session_state.training_uploader_tab = None
        return

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
    if not check_feature_permission('premium_ia'):
        st.error("❌ Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'doc_uploader_tab' in st.session_state:
            st.session_state.doc_uploader_tab = None
        return

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
        st.error("❌ Você não tem permissão para usar a análise com IA. Upgrade para o plano Premium.")
        if 'epi_uploader_tab' in st.session_state:
            st.session_state.epi_uploader_tab = None
        return
    
    if st.session_state.get('epi_uploader_tab') and 'epi_manager' in st.session_state:
        epi_manager = st.session_state.epi_manager
        anexo = st.session_state.epi_uploader_tab
        
        with st.spinner("🤖 Analisando ficha de EPI com IA..."):
            epi_info = epi_manager.analyze_epi_pdf(anexo)
            
            if epi_info:
                arquivo_hash = calcular_hash_arquivo(anexo)
                
                st.session_state.epi_info_para_salvar = epi_info
                st.session_state.epi_anexo_para_salvar = anexo
                st.session_state.epi_hash_para_salvar = arquivo_hash
                st.session_state.epi_funcionario_para_salvar = st.session_state.get('epi_employee_add')
                
                st.success("✅ Análise de EPI concluída!")
            else:
                st.error("❌ Não foi possível extrair informações da ficha de EPI.")