import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, date
import re
import logging
from operations.supabase_operations import SupabaseOperations
from AI.api_Operation import PDFQA
import tempfile
import os
from operations.audit_logger import log_action
from operations.cached_loaders import load_all_unit_data
from managers.supabase_storage import SupabaseStorageManager
from operations.file_hash import calcular_hash_arquivo, verificar_hash_seguro

logger = logging.getLogger('segsisone_app.company_docs_manager')

class CompanyDocsManager:
    def __init__(self, unit_id: str):
        self.supabase_ops = SupabaseOperations(unit_id)
        self.unit_id = unit_id
        self.storage_manager = SupabaseStorageManager(unit_id)
        self.data_loaded_successfully = False
        self.docs_df = pd.DataFrame()
        self.load_company_data()
        self._pdf_analyzer = None

    def upload_documento_e_obter_link(self, arquivo, novo_nome: str):
        """Faz o upload de um arquivo para o Supabase Storage."""
        if not self.unit_id:
            st.error("O ID da unidade não está definido.")
            logger.error("Tentativa de upload sem unit_id definido")
            return None
        
        try:
            result = self.storage_manager.upload_file(
                file_content=arquivo.getvalue(),
                filename=novo_nome,
                doc_type='doc_empresa',
                content_type=arquivo.type
            )
            
            if result and 'url' in result:
                return result['url']
            else:
                logger.error(f"Upload falhou: resultado = {result}")
                st.error("Falha no upload do documento")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao fazer upload: {e}", exc_info=True)
            st.error(f"Erro ao fazer upload: {str(e)}")
            return None

    @property
    def pdf_analyzer(self):
        if self._pdf_analyzer is None:
            self._pdf_analyzer = PDFQA()
        return self._pdf_analyzer

    def load_company_data(self):
        logger.info("Carregando dados de documentos...")
        try:
            data = load_all_unit_data(self.unit_id)
            self.docs_df = data['company_docs']
            self.data_loaded_successfully = True
        except Exception as e:
            logger.error(f"Erro: {e}", exc_info=True)
            self.docs_df = pd.DataFrame()
            self.data_loaded_successfully = False
    
    def get_docs_by_company(self, company_id):
        if self.docs_df.empty: 
            return pd.DataFrame()
        return self.docs_df[self.docs_df['empresa_id'] == str(company_id)]
        
    def _parse_flexible_date(self, date_string: str) -> date | None:
        if not date_string or date_string.lower() == 'n/a': 
            return None
        match = re.search(r'(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})|(\d{1,2} de \w+ de \d{4})|(\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})', date_string, re.IGNORECASE)
        if not match: 
            return None
        clean_date_string = match.group(0).replace('.', '/')
        formats = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%d de %B de %Y', '%Y-%m-%d']
        for fmt in formats:
            try: 
                return datetime.strptime(clean_date_string, fmt).date()
            except ValueError: 
                continue
        return None

    def analyze_company_doc_pdf(self, pdf_file):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_file.getvalue())
                temp_path = temp_file.name
            
            combined_question = """
            Por favor, analise o documento e responda as seguintes perguntas, uma por linha:
            1. Qual o tipo deste documento? Responda 'PGR', 'PCMSO', 'PPR', 'PCA' ou 'Outro'.
            2. Qual a data de emissão, vigência ou elaboração do documento? Responda a data no formato DD/MM/AAAA.
            """
            answer, _ = self.pdf_analyzer.answer_question([temp_path], combined_question)
            os.unlink(temp_path)
            
            if not answer: 
                return None
            
            lines = answer.strip().split('\n')
            results = {}
            for line in lines:
                match = re.match(r'\s*\*?\s*(\d+)\s*\.?\s*(.*)', line)
                if match:
                    key = int(match.group(1))
                    value = match.group(2).strip()
                    results[key] = value

            doc_type_str = results.get(1, "Outro").upper()
            data_emissao = self._parse_flexible_date(results.get(2, ''))

            if not data_emissao:
                st.error("Não foi possível extrair a data de emissão do documento.")
                return None

            if "PGR" in doc_type_str: 
                doc_type = "PGR"
            elif "PCMSO" in doc_type_str: 
                doc_type = "PCMSO"
            elif "PPR" in doc_type_str: 
                doc_type = "PPR"
            elif "PCA" in doc_type_str: 
                doc_type = "PCA"
            else: 
                doc_type = "Outro"
            
            if doc_type == "PGR":
                vencimento = data_emissao + timedelta(days=2*365)
                st.info("Documento identificado como PGR. Vencimento calculado para 2 anos.")
            else:
                vencimento = data_emissao + timedelta(days=365)
                st.info(f"Documento identificado como {doc_type}. Vencimento calculado para 1 ano.")
            
            return {
                'tipo_documento': doc_type,
                'data_emissao': data_emissao, 
                'vencimento': vencimento
            }
        except Exception as e:
            st.error(f"Erro ao analisar o PDF do documento: {e}")
            return None

    def add_company_document(self, empresa_id, tipo_documento, data_emissao, vencimento, arquivo_id, arquivo_hash=None):
        """Adiciona documento da empresa usando Supabase."""
        empresa_id_str = str(empresa_id)
        
        if arquivo_hash and verificar_hash_seguro(self.docs_df, 'arquivo_hash'):
            duplicata = self.docs_df[
                (self.docs_df['empresa_id'] == empresa_id_str) &
                (self.docs_df['arquivo_hash'] == arquivo_hash)
            ]
            
            if not duplicata.empty:
                st.warning(f"⚠️ Este arquivo PDF já foi cadastrado anteriormente para esta empresa.")
                return None
        
        new_data = {
            'empresa_id': empresa_id_str,
            'tipo_documento': str(tipo_documento),
            'data_emissao': data_emissao.strftime("%Y-%m-%d"),
            'vencimento': vencimento.strftime("%Y-%m-%d"),
            'arquivo_id': str(arquivo_id),
            'arquivo_hash': arquivo_hash or ''
        }
        
        try:
            result = self.supabase_ops.insert_row("documentos_empresa", new_data)
            if result:
                st.cache_data.clear()
                self.load_company_data()
                return result['id']
            return None
        except Exception as e:
            st.error(f"Erro ao adicionar documento da empresa: {e}")
            return None

    def delete_company_document(self, doc_id: str, file_url: str):
        """Deleta um documento da empresa."""
        doc_info = self.docs_df[self.docs_df['id'] == doc_id]
        if not doc_info.empty:
            details = {
                "deleted_item_id": doc_id,
                "item_type": "Documento da Empresa",
                "company_id": doc_info.iloc[0].get('empresa_id'),
                "doc_type": doc_info.iloc[0].get('tipo_documento'),
                "issue_date": str(doc_info.iloc[0].get('data_emissao')),
                "file_url": file_url
            }
            log_action("DELETE_COMPANY_DOC", details)

        if file_url and pd.notna(file_url):
            try:
                self.storage_manager.delete_file_by_url(file_url)
            except Exception as e:
                logger.error(f"Erro ao deletar arquivo do storage: {e}")
        
        if self.supabase_ops.delete_row("documentos_empresa", doc_id):
            st.cache_data.clear()
            self.load_company_data()
            return True
        return False