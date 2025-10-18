import pandas as pd
from operations.file_hash import calcular_hash_arquivo, verificar_hash_seguro
import streamlit as st
from datetime import datetime, date, timedelta
from operations.file_utils import infer_doc_type
from AI.api_Operation import PDFQA
import tempfile
import os
import re
import locale
import json
from dateutil.relativedelta import relativedelta
from operations.audit_logger import log_action
from auth.auth_utils import get_user_email
from difflib import SequenceMatcher
import logging
from typing import Optional, Union
from operations.cached_loaders import load_all_unit_data
from operations.utils import format_date_safe
from operations.nr_rules_manager import NRRulesManager  # <-- NOVA IMPORTAÇÃO

def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    pass

logger = logging.getLogger('segsisone_app.employee_manager')

from operations.supabase_operations import SupabaseOperations

class EmployeeManager:
    def __init__(self, unit_id: str, folder_id: str = ""):
        logger.info(f"Inicializando EmployeeManager para unit_id: ...{unit_id[-6:]}")
        self.unit_id = unit_id
        self.supabase_ops = SupabaseOperations(unit_id)
        self.folder_id = folder_id
        self._pdf_analyzer = None
        self.data_loaded_successfully = False

        self.nr_rules_manager = NRRulesManager(self.unit_id)

        # ✅ MUDANÇA: Lazy loading - não carrega na inicialização
        self._companies_df = None
        self._employees_df = None
        self._aso_df = None
        self._training_df = None
        
        # NÃO chamar load_data() aqui
        # self.load_data()

    # ✅ NOVO: Properties para lazy loading
    @property
    def companies_df(self):
        if self._companies_df is None:
            self._load_companies()
        return self._companies_df

    @property
    def employees_df(self):
        if self._employees_df is None:
            self._load_employees()
        return self._employees_df

    @property
    def aso_df(self):
        if self._aso_df is None:
            self._load_asos()
        return self._aso_df

    @property
    def training_df(self):
        if self._training_df is None:
            self._load_trainings()
        return self._training_df

    @property
    def pdf_analyzer(self):
        if self._pdf_analyzer is None:
            self._pdf_analyzer = PDFQA()
        return self._pdf_analyzer

    # ✅ NOVO: Métodos de carregamento individuais
    def _load_companies(self):
        try:
            data = load_all_unit_data(self.unit_id)
            self._companies_df = data.get('companies', pd.DataFrame())
            if not self._companies_df.empty:
                self._companies_df['id'] = self._companies_df['id'].astype(str)
                self._companies_df.set_index('id', inplace=True, drop=False)
        except Exception as e:
            logger.error(f"Erro ao carregar empresas: {e}")
            self._companies_df = pd.DataFrame()

    def _load_employees(self):
        try:
            data = load_all_unit_data(self.unit_id)
            self._employees_df = data.get('employees', pd.DataFrame())
            if not self._employees_df.empty:
                self._employees_df[['id', 'empresa_id']] = self._employees_df[
                    ['id', 'empresa_id']
                ].astype(str)
                self._employees_df.set_index('id', inplace=True, drop=False)
                self._employees_by_company = self._employees_df.groupby('empresa_id')
        except Exception as e:
            logger.error(f"Erro ao carregar funcionários: {e}")
            self._employees_df = pd.DataFrame()

    def _load_asos(self):
        try:
            data = load_all_unit_data(self.unit_id)
            self._aso_df = data.get('asos', pd.DataFrame())
            if not self._aso_df.empty:
                self._aso_df[['id', 'funcionario_id']] = self._aso_df[
                    ['id', 'funcionario_id']
                ].astype(str)
                self._asos_by_employee = self._aso_df.groupby('funcionario_id')
        except Exception as e:
            logger.error(f"Erro ao carregar ASOs: {e}")
            self._aso_df = pd.DataFrame()

    def _load_trainings(self):
        try:
            data = load_all_unit_data(self.unit_id)
            self._training_df = data.get('trainings', pd.DataFrame())
            if not self._training_df.empty:
                self._training_df[['id', 'funcionario_id']] = self._training_df[
                    ['id', 'funcionario_id']
                ].astype(str)
                self._trainings_by_employee = self._training_df.groupby('funcionario_id')
        except Exception as e:
            logger.error(f"Erro ao carregar treinamentos: {e}")
            self._training_df = pd.DataFrame()

    def upload_documento_e_obter_link(self, arquivo, novo_nome: str):
        if not self.unit_id:
            st.error("O ID da unidade não está definido.")
            logger.error("Tentativa de upload sem unit_id definido")
            return None
        
        try:
            from managers.supabase_storage import SupabaseStorageManager
            storage_manager = SupabaseStorageManager(self.unit_id)
            logger.info(f"Iniciando upload: '{novo_nome}' para unidade ...{self.unit_id[-6:]}")
            return storage_manager.upload_file_simple(arquivo, novo_nome)
        except ImportError as e:
            logger.error(f"Módulo SupabaseStorageManager não encontrado: {e}")
            st.error("❌ Erro de configuração do sistema")
            return None
        except Exception as e:
            logger.error(f"Erro ao fazer upload: {e}", exc_info=True)
            st.error(f"Erro ao fazer upload: {str(e)}")
            return None

    def load_data(self):
        """Mantido para compatibilidade - agora apenas seta flag"""
        self.data_loaded_successfully = True

    def _parse_flexible_date(self, date_string: str) -> date | None:
        try:
            if not date_string or not isinstance(date_string, str) or date_string.lower() == 'n/a': 
                return None
            
            date_string = str(date_string).strip()
            if not date_string:
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
        except Exception as e:
            logger.error(f"Erro ao parsear data '{date_string}': {e}")
            return None

    def analyze_aso_pdf(self, pdf_file):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_file.getvalue())
                temp_path = temp_file.name
            
            structured_prompt = """        
            Você é um assistente de extração de dados para documentos de Saúde e Segurança do Trabalho. Sua tarefa é analisar o ASO em PDF e extrair as informações abaixo.
            REGRAS OBRIGATÓRIAS:
            1.Responda APENAS com um bloco de código JSON válido. Não inclua a palavra "json" ou qualquer outro texto antes ou depois do bloco JSON.
            2.Para todas as chaves de data, use ESTRITAMENTE o formato DD/MM/AAAA.
            3.Se uma informação não for encontrada de forma clara e inequívoca, o valor da chave correspondente no JSON deve ser null (sem aspas).
            4.IMPORTANTE: Os valores das chaves no JSON NÃO DEVEM conter o nome da chave.
            ERRADO: "cargo": "Cargo: Operador"
            CORRETO: "cargo": "Operador"
            JSON a ser preenchido:
            {
            "data_aso": "A data de emissão ou realização do exame clínico. Formato: DD/MM/AAAA.",
            "vencimento_aso": "A data de vencimento explícita no ASO, se houver. Formato: DD/MM/AAAA.",
            "riscos": "Uma string contendo os riscos ocupacionais listados, separados por vírgula.",
            "cargo": "O cargo ou função do trabalhador.",
            "tipo_aso": "O tipo de exame. Identifique como um dos seguintes: 'Admissional', 'Periódico', 'Demissional', 'Mudança de Risco', 'Retorno ao Trabalho', 'Monitoramento Pontual'."
            }
            """
            answer, _ = self.pdf_analyzer.answer_question([temp_path], structured_prompt)
            os.unlink(temp_path)
            if not answer: return None

            cleaned_answer = answer.strip().replace("```json", "").replace("```", "")
            data = json.loads(cleaned_answer)
            data_aso = self._parse_flexible_date(data.get('data_aso'))
            vencimento = self._parse_flexible_date(data.get('vencimento_aso'))
            if not data_aso: return None
                
            tipo_aso = str(data.get('tipo_aso', 'Não identificado'))
            if not vencimento and tipo_aso != 'Demissional':
                if tipo_aso in ['Admissional', 'Periódico', 'Mudança de Risco', 'Retorno ao Trabalho']:
                    vencimento = data_aso + relativedelta(years=1)
                elif tipo_aso == 'Monitoramento Pontual':
                    vencimento = data_aso + relativedelta(months=6)
            
            return {'data_aso': data_aso, 'vencimento': vencimento, 'riscos': data.get('riscos', ""), 'cargo': data.get('cargo', ""), 'tipo_aso': tipo_aso}
        except Exception as e:
            st.error(f"Erro ao analisar PDF do ASO: {e}")
            return None

    def analyze_training_pdf(self, pdf_file):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_file.getvalue())
                temp_path = temp_file.name
            
            structured_prompt = """
            Você é um especialista em análise de documentos de Saúde e Segurança do Trabalho.
            **REGRAS CRÍTICAS:**
            1.  Responda **APENAS com JSON válido**.
            2.  Datas no formato **DD/MM/AAAA**.
            3.  Para a chave "norma":
                - Se mencionar "SEP", "Sistema Elétrico de Potência", "Alta Tensão" ou "Subestação", retorne **"NR-10 SEP"**
                - Se for NR-10 sem menção a SEP, retorne **"NR-10"**
            4.  Para a chave "modulo":
                - Se for NR-10 SEP, retorne **"SEP"**
                - Se for NR-10 comum, retorne **"Básico"** ou **"N/A"**
                - Para NR-20, identifique: **"Básico"**, **"Intermediário"**, **"Avançado I"** ou **"Avançado II"**
                - Para NR-33, identifique: **"Trabalhador Autorizado"** ou **"Supervisor"**
                - Para outros, extraia o módulo ou retorne **"N/A"**
            **JSON:**
            ```json
            {
              "norma": "Nome da norma (ex: 'NR-10 SEP' se for SEP, 'NR-10' se for básico)",
              "modulo": "Módulo específico (ex: 'SEP', 'Básico', 'Intermediário')",
              "data_realizacao": "DD/MM/AAAA",
              "tipo_treinamento": "'formação' ou 'reciclagem'",
              "carga_horaria": "Número inteiro de horas"
            }
            """
            answer, _ = self.pdf_analyzer.answer_question([temp_path], structured_prompt)
            os.unlink(temp_path)
            if not answer: return None

            cleaned_answer = answer.strip().replace("```json", "").replace("```", "")
            try:
                data = json.loads(cleaned_answer)
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON do treinamento: {e}")
                st.error("❌ A IA retornou um formato inválido")
                return None

            required_keys = ['data_realizacao', 'norma', 'tipo_treinamento']
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                logger.error(f"JSON do treinamento faltando chaves: {missing_keys}")
                st.error(f"❌ Dados incompletos: {', '.join(missing_keys)}")
                return None

            data_realizacao = self._parse_flexible_date(data.get('data_realizacao'))
            if not data_realizacao: 
                st.error("❌ Data de realização inválida ou não encontrada")
                return None
                
            norma_padronizada = self._padronizar_norma(data.get('norma'))
            modulo = str(data.get('modulo', 'N/A')).strip()
            tipo_treinamento = str(data.get('tipo_treinamento', 'formação')).lower()
            carga_horaria = int(data.get('carga_horaria', 0)) if data.get('carga_horaria') is not None else 0
            
            if 'SEP' in norma_padronizada:
                modulo = 'SEP'
            elif norma_padronizada == 'NR-10' and modulo in ['N/A', '', 'nan']:
                modulo = 'Básico'

            # ✅ REMOVIDO: Lógica que dependia de self.nr20_config - será tratada pelo NRRulesManager nas validações
            
            return {
                'data': data_realizacao,
                'norma': norma_padronizada,
                'modulo': modulo,
                'tipo_treinamento': tipo_treinamento,
                'carga_horaria': carga_horaria
            }
        except Exception as e:
            st.error(f"Erro ao analisar PDF do Treinamento: {e}")
            return None

    def add_company(self, nome, cnpj):
        if not self.companies_df.empty and cnpj in self.companies_df['cnpj'].values:
            return None, "CNPJ já cadastrado."
        new_data = {'nome': nome, 'cnpj': cnpj, 'status': "Ativo"}
        # ✅ CORREÇÃO: insert_row retorna apenas string do ID
        company_id = self.supabase_ops.insert_row("empresas", new_data)
        if company_id:
            # Após operação bem-sucedida:
            load_all_unit_data.clear()  # Limpa cache da função
            st.cache_data.clear()        # Limpa cache do Streamlit
            st.session_state.force_reload_managers = True  # Força reload managers
            logger.info("✅ Empresa adicionada. Reinicialização agendada.")
            return company_id, "Empresa cadastrada com sucesso"
        return None, "Falha ao cadastrar empresa."

    def add_employee(self, nome, cargo, data_admissao, empresa_id):
        new_data = {'nome': nome, 'cargo': cargo, 'data_admissao': format_date_safe(data_admissao), 'empresa_id': empresa_id, 'status': 'Ativo'}
        employee_id = self.supabase_ops.insert_row("funcionarios", new_data)
        if employee_id:
            # Após operação bem-sucedida:
            load_all_unit_data.clear()  # Limpa cache da função
            st.cache_data.clear()        # Limpa cache do Streamlit
            st.session_state.force_reload_managers = True  # Força reload managers
            logger.info("✅ Funcionário adicionado. Reinicialização agendada.")
            return employee_id, "Funcionário adicionado com sucesso"
        return None, "Erro ao adicionar funcionário."

    def add_aso(self, aso_data: dict):
        funcionario_id = str(aso_data.get('funcionario_id'))
        arquivo_hash = aso_data.get('arquivo_hash')

        if arquivo_hash and verificar_hash_seguro(self.aso_df, 'arquivo_hash'):
            duplicata = self.aso_df[
                (self.aso_df['funcionario_id'] == funcionario_id) &
                (self.aso_df['arquivo_hash'] == arquivo_hash)
            ]
            if not duplicata.empty:
                st.warning(f"⚠️ Este arquivo PDF já foi cadastrado anteriormente para este funcionário (ASO do tipo '{duplicata.iloc[0]['tipo_aso']}').")
                return None

        new_data = {
            'funcionario_id': funcionario_id,
            'data_aso': format_date_safe(aso_data.get('data_aso')),
            'vencimento': format_date_safe(aso_data.get('vencimento')),
            'arquivo_id': str(aso_data.get('arquivo_id')),
            'arquivo_hash': arquivo_hash or '',
            'riscos': aso_data.get('riscos', 'N/A'),
            'cargo': aso_data.get('cargo', 'N/A'),
            'tipo_aso': aso_data.get('tipo_aso', 'N/A')
        }
        aso_id = self.supabase_ops.insert_row("asos", new_data)
        if aso_id:
            # Após operação bem-sucedida:
            load_all_unit_data.clear()  # Limpa cache da função
            st.cache_data.clear()        # Limpa cache do Streamlit
            st.session_state.force_reload_managers = True  # Força reload managers
            logger.info("✅ ASO adicionado. Reinicialização agendada.")
        return aso_id

    def add_training(self, training_data: dict):
        try:
            is_valid, validation_msg = self.validate_training_data(training_data)
            if not is_valid:
                st.error(f"❌ Validação falhou: {validation_msg}")
                logger.warning(f"Treinamento rejeitado: {validation_msg}")
                return None
            
            funcionario_id = str(training_data.get('funcionario_id'))
            norma = self._padronizar_norma(training_data.get('norma'))
            modulo = str(training_data.get('modulo', 'N/A')).strip()
            
            if norma == 'NR-10 SEP' and modulo in ['N/A', '', 'nan']:
                modulo = 'SEP'
            elif norma == 'NR-10' and modulo in ['N/A', '', 'nan']:
                modulo = 'Básico'

            vencimento = training_data.get('vencimento')
            if not vencimento or not isinstance(vencimento, (date, datetime)):
                logger.error(f"Vencimento inválido: {type(vencimento)}")
                st.error("❌ Erro: Vencimento do treinamento inválido")
                return None

            new_data = {
                'funcionario_id': funcionario_id,
                'data': format_date_safe(training_data.get('data')),
                'vencimento': format_date_safe(vencimento),
                'norma': norma,
                'modulo': modulo,
                'status': "Válido",
                'anexo': str(training_data.get('anexo')),
                'arquivo_hash': training_data.get('arquivo_hash', ''),
                'tipo_treinamento': str(training_data.get('tipo_treinamento', 'formação')),
                'carga_horaria': str(training_data.get('carga_horaria', '0'))
            }
                    
            logger.info(f"Salvando treinamento: {norma} - {modulo} para funcionário {funcionario_id}")
            
            # ✅ CORREÇÃO: Nome correto da tabela
            training_id = self.supabase_ops.insert_row("treinamentos", new_data)
            
            if training_id:
                log_action("ADD_TRAINING", {
                    "training_id": training_id,
                    "employee_id": funcionario_id,
                    "norma": norma,
                    "modulo": modulo,
                    "tipo": training_data.get('tipo_treinamento'),
                    "carga_horaria": training_data.get('carga_horaria')
                })
                st.cache_data.clear()
                self.load_data()
                logger.info(f"✅ Treinamento {training_id} salvo com sucesso")
                return training_id
            else:
                st.error("❌ Falha ao salvar no Supabase")
                logger.error(f"Supabase ops retornou None para treinamento {norma}")
                return None                
        except Exception as e:
            logger.error(f"Erro crítico ao adicionar treinamento: {e}", exc_info=True)
            st.error(f"❌ Erro inesperado: {str(e)}")
            st.info("💡 Tente novamente ou contate o suporte se o erro persistir")
            return None

    def _set_status(self, table_name: str, item_id: str, status: str):
        if self.supabase_ops.update_row(table_name, item_id, {'status': status}):
            self.load_data()
            return True
        return False

    def archive_company(self, company_id: str): return self._set_status("empresas", company_id, "Arquivado")
    def unarchive_company(self, company_id: str): return self._set_status("empresas", company_id, "Ativo")
    def archive_employee(self, employee_id: str): return self._set_status("funcionarios", employee_id, "Arquivado")
    def unarchive_employee(self, employee_id: str): return self._set_status("funcionarios", employee_id, "Ativo")

    def get_latest_aso_by_employee(self, employee_id):
        if not employee_id or not isinstance(employee_id, (str, int)):
            logger.error(f"employee_id tem tipo inválido: {type(employee_id)}")
            return pd.DataFrame()
        
        try:
            if not hasattr(self, '_asos_by_employee'):
                logger.debug("Nenhum ASO registrado para esta unidade. Retornando vazio.")
                return pd.DataFrame()
            
            aso_docs = self._asos_by_employee.get_group(str(employee_id)).copy()
            if aso_docs.empty: return pd.DataFrame()
            
            aso_docs['data_aso'] = pd.to_datetime(aso_docs['data_aso'], errors='coerce')
            aso_docs['vencimento'] = pd.to_datetime(aso_docs['vencimento'], errors='coerce')
            aso_docs.dropna(subset=['data_aso'], inplace=True)
            if aso_docs.empty: return pd.DataFrame()

            aso_docs['tipo_aso'] = aso_docs['tipo_aso'].fillna('N/A')
            return aso_docs.sort_values('data_aso', ascending=False).groupby('tipo_aso').head(1)
        except KeyError:
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao buscar ASOs: {e}")
            return pd.DataFrame()

    def get_all_trainings_by_employee(self, employee_id):
        try:
            if not hasattr(self, '_trainings_by_employee'):
                logger.debug(f"Atributo '_trainings_by_employee' não encontrado.")
                return pd.DataFrame()

            # ✅ CORREÇÃO: Validar se o grupo existe antes de usar .copy()
            try:
                training_docs = self._trainings_by_employee.get_group(str(employee_id))
                if training_docs is None or training_docs.empty:
                    return pd.DataFrame()
                training_docs = training_docs.copy()
            except KeyError:
                return pd.DataFrame()

            if training_docs.empty:
                return pd.DataFrame()
            
            training_docs.dropna(subset=['data'], inplace=True)
            if training_docs.empty: 
                return pd.DataFrame()

            # ✅ CORREÇÃO: Normalização de colunas com validação
            for col in ['norma', 'modulo', 'tipo_treinamento']:
                if col not in training_docs.columns:
                    training_docs[col] = 'N/A'
                training_docs[col] = training_docs[col].fillna('N/A')

            # ✅ CORREÇÃO: Verificar existência das colunas antes de usar
            if 'norma' not in training_docs.columns:
                logger.error("Coluna 'norma' não encontrada no DataFrame de treinamentos")
                return pd.DataFrame()

            if 'modulo' not in training_docs.columns:
                training_docs['modulo'] = 'N/A'

            training_docs['norma_normalizada'] = training_docs['norma'].fillna('').astype(str).str.strip().str.upper()
            training_docs['modulo_normalizado'] = training_docs['modulo'].fillna('N/A').astype(str).str.strip().str.title()
            
            # ✅ CORREÇÃO: Função com try-except para segurança
            def normalizar_modulo_especial(row):
                try:
                    # ✅ CORREÇÃO: Validação antes de usar
                    norma = str(row.get('norma_normalizada', '')).strip().upper()
                    modulo = str(row.get('modulo_normalizado', '')).strip().title()

                    # Se algum valor for vazio/inválido, retorna o módulo como está
                    if not norma or norma in ['NAN', 'NONE', '']:
                        return modulo if modulo not in ['Nan', 'N/A', ''] else 'N/A'

                    # Dicionário de mapeamentos
                    normalizacao_map = {
                        'NR-10': {
                            'sep_keywords': ['SEP'],
                            'sep_value': 'SEP',
                            'default': 'Básico'
                        },
                        'NR-33': {
                            'supervisor': ['SUPERVISOR'],
                            'trabalhador': ['TRABALHADOR', 'AUTORIZADO'],
                            'values': {
                                'supervisor': 'Supervisor',
                                'trabalhador': 'Trabalhador Autorizado'
                            }
                        },
                        'NR-20': {
                            'validos': ['Básico', 'Intermediário', 'Avançado I', 'Avançado II']
                        },
                        'PERMISSÃO': {
                            'emitente': ['EMITENTE'],
                            'requisitante': ['REQUISITANTE'],
                            'values': {
                                'emitente': 'Emitente',
                                'requisitante': 'Requisitante'
                            }
                        }
                    }

                    # NR-10
                    if 'NR-10' in norma:
                        if any(kw in norma or kw in modulo.upper() for kw in normalizacao_map['NR-10']['sep_keywords']):
                            return normalizacao_map['NR-10']['sep_value']
                        elif modulo in ['N/A', 'Nan', '']:
                            return normalizacao_map['NR-10']['default']
                        return modulo

                    # NR-33
                    if 'NR-33' in norma:
                        modulo_upper = modulo.upper()
                        if any(kw in modulo_upper for kw in normalizacao_map['NR-33']['supervisor']):
                            return normalizacao_map['NR-33']['values']['supervisor']
                        elif any(kw in modulo_upper for kw in normalizacao_map['NR-33']['trabalhador']):
                            return normalizacao_map['NR-33']['values']['trabalhador']
                        return modulo

                    # NR-20
                    if 'NR-20' in norma:
                        for valido in normalizacao_map['NR-20']['validos']:
                            if valido.upper() in modulo.upper():
                                return valido
                        return modulo

                    # Permissão de Trabalho
                    if 'PERMISSÃO' in norma or 'PT' in norma:
                        modulo_upper = modulo.upper()
                        if any(kw in modulo_upper for kw in normalizacao_map['PERMISSÃO']['emitente']):
                            return normalizacao_map['PERMISSÃO']['values']['emitente']
                        elif any(kw in modulo_upper for kw in normalizacao_map['PERMISSÃO']['requisitante']):
                            return normalizacao_map['PERMISSÃO']['values']['requisitante']
                        return modulo

                    return modulo

                except Exception as e:
                    logger.error(f"Erro ao normalizar módulo: {e}")
                    return 'N/A'
            
            training_docs['modulo_final'] = training_docs.apply(normalizar_modulo_especial, axis=1)
            training_docs['data_dt'] = pd.to_datetime(training_docs['data'], errors='coerce')
            training_docs = training_docs[training_docs['data_dt'].notna()]

            if training_docs.empty:
                logger.debug(f"Nenhum treinamento com data válida para employee_id {employee_id}")
                return pd.DataFrame()

            # ✅ CORREÇÃO: Agrupa corretamente por norma E módulo
            latest_trainings = training_docs.sort_values(
                'data_dt', ascending=False
            ).groupby(['norma_normalizada', 'modulo_final'], dropna=False).head(1)
            
            latest_trainings = latest_trainings.drop(
                columns=['norma_normalizada', 'modulo_normalizado', 'modulo_final', 'data_dt']
            )
            return latest_trainings
            
        except KeyError:
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao buscar treinamentos: {e}", exc_info=True)
            return pd.DataFrame()

    def get_company_name(self, company_id):
        if self.companies_df.empty: return f"ID {company_id}"
        # Acessa o DataFrame pelo índice (que agora é uma string)
        try:
            return self.companies_df.loc[str(company_id), 'nome']
        except KeyError:
            return f"ID {company_id} (Não encontrado)"

    def get_employee_name(self, employee_id):
        if self.employees_df.empty: return f"ID {employee_id}"
        # Acessa o DataFrame pelo índice (que agora é uma string)
        try:
            return self.employees_df.loc[str(employee_id), 'nome']
        except KeyError:
            return f"ID {employee_id} (Não encontrado)"

    def get_employees_by_company(self, company_id: str, include_archived: bool = False):
        if not hasattr(self, '_employees_by_company'):
            logger.debug("Nenhum funcionário registrado para esta unidade.")
            return pd.DataFrame()
        
        try:
            company_employees = self._employees_by_company.get_group(str(company_id))
            if include_archived or 'status' not in company_employees.columns:
                return company_employees
            return company_employees[company_employees['status'].str.lower() == 'ativo']
        except KeyError:
            logger.debug(f"Empresa {company_id} não tem funcionários")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao buscar funcionários: {e}")
            return pd.DataFrame()

    def validate_training_data(self, training_data: dict) -> tuple[bool, str]:
        try:
            norma = training_data.get('norma')
            data = training_data.get('data')
            vencimento = training_data.get('vencimento')

            # Validações básicas
            if not all([norma, isinstance(data, (date, datetime)), isinstance(vencimento, (date, datetime))]):
                return False, "❌ Faltam campos obrigatórios ou datas inválidas"

            hoje = date.today()
            data_date = data.date() if isinstance(data, datetime) else data
            if data_date > hoje:
                return False, f"❌ Data de realização ({format_date_safe(data, '%d/%m/%Y')}) não pode ser futura"

            venc_date = vencimento.date() if isinstance(vencimento, datetime) else vencimento
            if venc_date <= data_date:
                return False, f"❌ Vencimento deve ser após a data de realização"

            # ✅ CORREÇÃO: Validar carga horária usando NRRulesManager
            carga_horaria = training_data.get('carga_horaria', 0)
            modulo = training_data.get('modulo', 'N/A')
            tipo_treinamento = training_data.get('tipo_treinamento', 'formação')

            # Busca a regra no banco
            norma_padronizada = self._padronizar_norma(norma)
            rule = self.nr_rules_manager.find_training_rule(
                norma_nome=norma_padronizada,
                modulo_nome=modulo
            )

            if rule is None:
                # Se não há regra, permite (backward compatibility)
                logger.warning(f"Nenhuma regra encontrada para '{norma_padronizada}'. Aprovando.")
                return True, "✅ Sem regra específica - carga horária aceita"

            # Determina carga horária mínima
            if tipo_treinamento == 'formação':
                ch_minima = rule.get('carga_horaria_minima_horas')
            else:  # reciclagem
                ch_minima = rule.get('reciclagem_carga_horaria_horas')

            # Se ch_minima é NaN/None, aceita qualquer valor > 0
            if pd.isna(ch_minima):
                if carga_horaria <= 0:
                    return False, "❌ Carga horária deve ser maior que zero"
                return True, "✅ Carga horária definida pelo empregador"

            # Se há mínimo definido, valida
            if carga_horaria < ch_minima:
                return False, f"❌ C.H. mínima para {tipo_treinamento} é {int(ch_minima)}h (fornecido: {carga_horaria}h)"

            # Verifica duplicatas por hash
            arquivo_hash = training_data.get('arquivo_hash')
            funcionario_id = str(training_data.get('funcionario_id'))
            if arquivo_hash and verificar_hash_seguro(self.training_df, 'arquivo_hash'):
                duplicata = self.training_df[
                    (self.training_df['funcionario_id'] == funcionario_id) &
                    (self.training_df['arquivo_hash'] == arquivo_hash)
                ]
                if not duplicata.empty:
                    return False, "❌ Este PDF já foi cadastrado anteriormente"

            return True, "✅ Validação aprovada"

        except Exception as e:
            logger.error(f"Erro crítico na validação: {e}", exc_info=True)
            return False, f"❌ Erro na validação: {str(e)}"

    def _padronizar_norma(self, norma: str) -> str:
        """
        ✅ FUNÇÃO ATUALIZADA: Padroniza o nome da norma de forma contextual.
        """
        if not norma or not isinstance(norma, str):
            return "N/A"

        norma_upper = str(norma).strip().upper()

        # 1. Casos especiais compostos (ordem importa!)
        if "10" in norma_upper and "SEP" in norma_upper:
            return "NR-10 SEP"

        if any(term in norma_upper for term in ["BRIGADA", "INCÊNDIO", "IT-17", "NR-23"]):
            return "BRIGADA DE INCÊNDIO"

        # ✅ CORREÇÃO: Normaliza NBR-16710 com qualquer sufixo
        if "16710" in norma_upper or "NBR" in norma_upper and "RESGATE" in norma_upper:
            # Preserva o sufixo se houver (Nível Operacional, Supervisor, etc)
            if "OPERACIONAL" in norma_upper:
                return "NBR-16710 RESGATE TÉCNICO - OPERACIONAL"
            elif "SUPERVISOR" in norma_upper:
                return "NBR-16710 RESGATE TÉCNICO - SUPERVISOR"
            else:
                return "NBR-16710 RESGATE TÉCNICO"

        if "PERMISSÃO" in norma_upper or re.search(r'\bPT\b', norma_upper):
            return "PERMISSÃO DE TRABALHO (PT)"

        # 2. Padrão genérico NR-XX
        match = re.search(r'NR\s?-?(\d+)', norma_upper)
        if match and match.group(1):
            try:
                nr_number = int(match.group(1))
                return f"NR-{nr_number:02d}"
            except (ValueError, TypeError) as e:
                logger.error(f"Erro ao converter NR number: {match.group(1)} - {e}")
                return norma_upper

        # 3. Retorna original se nenhuma regra se aplicar
        return norma_upper

    def calcular_vencimento_treinamento(self, data, norma, modulo=None, tipo_treinamento='formação'):
        """
        ✅ REFATORADO: Agora usa o NRRulesManager para buscar as regras dinamicamente do banco de dados.
        """
        if not isinstance(data, (date, datetime)): return None
        norma_padronizada = self._padronizar_norma(norma)

        # Busca a regra específica no banco de dados
        rule = self.nr_rules_manager.find_training_rule(norma_nome=norma_padronizada, modulo_nome=str(modulo or 'N/A'))

        if rule is None:
            st.warning(f"Regras de vencimento não encontradas no banco de dados para '{norma_padronizada}'.")
            return None

        # Verifica se há período de reciclagem definido
        if pd.notna(rule.get('reciclagem_anos')):
            anos_validade = rule['reciclagem_anos']
            if anos_validade == 0.5:  # Tratamento especial para 6 meses (NR 17)
                return data + relativedelta(months=6)
            elif anos_validade > 0:
                return data + relativedelta(years=int(anos_validade))

        # Se não há reciclagem_anos, o treinamento não tem vencimento fixo
        st.warning(f"Treinamento '{norma_padronizada}' não possui regra de vencimento em anos definida no sistema.")
        return None

    def delete_aso(self, aso_id: str, file_url: str):
        """
        ✅ CORREÇÃO (#1): Deleta um ASO e seu arquivo associado na ordem correta.
        Primeiro deleta do banco de dados, depois do storage para manter integridade.
        """
        aso_id_str = str(aso_id)
        
        aso_info = self.aso_df[self.aso_df['id'] == aso_id_str]
        if not aso_info.empty:
            details = {
                "deleted_item_id": aso_id_str,
                "item_type": "ASO",
                "employee_id": str(aso_info.iloc[0].get('funcionario_id')),
                "aso_type": aso_info.iloc[0].get('tipo_aso'),
                "aso_date": str(aso_info.iloc[0].get('data_aso')),
                "file_url": file_url
            }
            log_action("DELETE_ASO", details)

        # 1. Deleta do banco de dados PRIMEIRO
        db_deleted = self.supabase_ops.delete_row("asos", aso_id_str)
        
        if not db_deleted:
            logger.error(f"Falha ao deletar ASO {aso_id_str} do banco.")
            return False

        # 2. Se o banco foi deletado com sucesso, tenta deletar o arquivo do storage
        if file_url and pd.notna(file_url):
            try:
                from managers.supabase_storage import SupabaseStorageManager
                storage_manager = SupabaseStorageManager(self.unit_id)
                storage_manager.delete_file_by_url(file_url)
            except Exception as e:
                # Loga como aviso, pois o registro do DB já foi removido (estado consistente)
                logger.warning(f"Arquivo órfão no storage: {file_url}. Erro: {e}")
        
        st.cache_data.clear()
        self.load_data()
        return True

    def delete_training(self, training_id: str, file_url: str):
        """
        ✅ CORREÇÃO (#1): Deleta um treinamento e seu arquivo associado na ordem correta.
        Primeiro deleta do banco de dados, depois do storage para manter integridade.
        """
        training_id_str = str(training_id)
        
        training_info = self.training_df[self.training_df['id'] == training_id_str]
        if not training_info.empty:
            details = {
                "deleted_item_id": training_id_str,
                "item_type": "Treinamento",
                "employee_id": str(training_info.iloc[0].get('funcionario_id')),
                "norma": training_info.iloc[0].get('norma'),
                "training_date": str(training_info.iloc[0].get('data')),
                "file_url": file_url
            }
            log_action("DELETE_TRAINING", details)
            
        # 1. Deleta do banco de dados PRIMEIRO
        db_deleted = self.supabase_ops.delete_row("treinamentos", training_id_str)

        if not db_deleted:
            logger.error(f"Falha ao deletar treinamento {training_id_str} do banco.")
            return False
            
        # 2. Se o banco foi deletado com sucesso, tenta deletar o arquivo do storage
        if file_url and pd.notna(file_url):
            try:
                from managers.supabase_storage import SupabaseStorageManager
                storage_manager = SupabaseStorageManager(self.unit_id)
                storage_manager.delete_file_by_url(file_url)
            except Exception as e:
                # Loga como aviso, pois o registro do DB já foi removido (estado consistente)
                logger.warning(f"Arquivo órfão no storage: {file_url}. Erro: {e}")

        st.cache_data.clear()
        self.load_data()
        return True

    def validar_treinamento(self, norma, modulo, tipo_treinamento, carga_horaria):
        """
        ✅ REFATORADO: Agora usa o NRRulesManager para buscar as regras dinamicamente do banco de dados.
        """
        norma_padronizada = self._padronizar_norma(norma)
        tipo_treinamento = str(tipo_treinamento).lower()

        # 1. Busca a regra específica no banco de dados
        rule = self.nr_rules_manager.find_training_rule(norma_nome=norma_padronizada, modulo_nome=modulo)

        if rule is None:
            # Se não encontrei regra específica, comportamento seguro: aprova
            logger.warning(f"Nenhuma regra encontrada para '{norma_padronizada}'. Aprovando carga horária por segurança.")
            return True, f"Regra para '{norma_padronizada}' não encontrada no sistema. Carga horária aceita."

        # 2. Determina qual coluna de carga horária usar baseado no tipo de treinamento
        if tipo_treinamento == 'formação':
            ch_minima_rule = rule.get('carga_horaria_minima_horas')
        elif tipo_treinamento == 'reciclagem':
            ch_minima_rule = rule.get('reciclagem_carga_horaria_horas')
        else:
            ch_minima_rule = None

        # 3. VALIDAÇÃO PRINCIPAL: Se ch_minima_rule é Nulo/NaN, carga horária é definida pelo empregador
        if pd.isna(ch_minima_rule):
            if carga_horaria > 0:
                return True, f"Carga horária para '{norma_padronizada}' pode ser definida pelo empregador. Valor {carga_horaria}h aceito."
            else:
                return False, "Carga horária deve ser maior que zero."

        # 4. VALIDAÇÃO: Se há uma carga horária mínima definida, compara com a informada
        if carga_horaria < ch_minima_rule:
            return False, f"Carga horária para {tipo_treinamento} ({norma_padronizada}) deve ser de no mínimo {int(ch_minima_rule)}h, mas foi de {carga_horaria}h."

        return True, "Carga horária conforme à regulamentação."
