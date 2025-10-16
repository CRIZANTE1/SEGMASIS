import streamlit as st
import pandas as pd
import json
import tempfile
import os
import re
import logging
from operations.supabase_operations import SupabaseOperations
from AI.api_Operation import PDFQA

from operations.file_hash import calcular_hash_arquivo, verificar_hash_seguro
from managers.supabase_storage import SupabaseStorageManager


logger = logging.getLogger('segsisone_app.epi_manager')

class EPIManager:
    def __init__(self, unit_id: str):
        # ✅ VALIDAÇÃO DE ENTRADA
        if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
            logger.error("EPIManager inicializado sem unit_id válido")
            raise ValueError("unit_id não pode ser vazio")
        
        self.supabase_ops = SupabaseOperations(unit_id)
        self.unit_id = unit_id
        self.storage_manager = SupabaseStorageManager(unit_id)
        self._pdf_analyzer = None
        self.data_loaded_successfully = False
        self.epi_df = pd.DataFrame()
        self.load_epi_data()

    @property
    def pdf_analyzer(self):
        if self._pdf_analyzer is None:
            self._pdf_analyzer = PDFQA()
        return self._pdf_analyzer

    def load_epi_data(self):
        """Carrega os dados de EPIs"""
        try:
            self.epi_df = self.supabase_ops.get_table_data("fichas_epi")
            
            if self.epi_df is None:
                logger.warning("load_epis_df retornou None")
                self.epi_df = pd.DataFrame()
                self.data_loaded_successfully = False
            elif self.epi_df.empty:
                logger.info("Tabela 'fichas_epi' está vazia para esta unidade")
                self.data_loaded_successfully = True
            else:
                logger.info(f"✅ {len(self.epi_df)} registro(s) de EPI carregado(s)")
                self.data_loaded_successfully = True
                
        except Exception as e:
            logger.error(f"Erro ao carregar dados de EPI: {e}", exc_info=True)
            self.epi_df = pd.DataFrame()
            self.data_loaded_successfully = False

    def get_epi_by_employee(self, employee_id):
        """Retorna o registro mais recente para cada tipo de EPI."""
        if self.epi_df.empty:
            return pd.DataFrame()
            
        epi_docs = self.epi_df[self.epi_df['funcionario_id'] == str(employee_id)].copy()
        if epi_docs.empty:
            return pd.DataFrame()
    
        if 'data_entrega' not in epi_docs.columns:
            return pd.DataFrame()
    
        epi_docs['data_entrega_dt'] = pd.to_datetime(epi_docs['data_entrega'], errors='coerce')
        epi_docs.dropna(subset=['data_entrega_dt'], inplace=True)
        if epi_docs.empty: 
            return pd.DataFrame()
    
        epi_docs['descricao_normalizada'] = epi_docs['descricao_epi'].astype(str).str.strip().str.lower()
        epi_docs = epi_docs.sort_values('data_entrega_dt', ascending=False)        
        latest_epis = epi_docs.groupby('descricao_normalizada').head(1).copy()        
        latest_epis = latest_epis.drop(columns=['data_entrega_dt', 'descricao_normalizada'])
        
        return latest_epis.sort_values('data_entrega', ascending=False)

    def analyze_epi_pdf(self, pdf_file):
        """Analisa o PDF da Ficha de EPI usando IA."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_file.getvalue())
                temp_path = temp_file.name

            structured_prompt = """
            Você é um especialista em análise de Fichas de Controle de EPI. Sua tarefa é analisar o documento e extrair as informações da tabela de equipamentos fornecidos e o nome do funcionário.

            **REGRAS OBRIGATÓRIAS:**
            1.  Responda **APENAS com um bloco de código JSON válido**. Não inclua nenhum texto antes ou depois do JSON.
            2.  O JSON principal deve ter duas chaves: "nome_funcionario" e "itens_epi".
            3.  A chave "itens_epi" deve conter um **array de objetos**.
            4.  Cada objeto no array deve representar um item da ficha e conter as chaves: "item_numero", "descricao", "data_entrega" (formato DD/MM/AAAA) e "ca".
            5.  Se um valor não for encontrado para uma chave (ex: CA), o valor no JSON deve ser **null** ou uma string vazia.
            6.  Ignore as linhas vazias da tabela.

            **Exemplo de JSON de Saída:**
```json
            {
              "nome_funcionario": "ALAN LIMA FREITAS",
              "itens_epi": [
                {
                  "item_numero": "1",
                  "descricao": "BOTINA NOB CAD BI B/PLAS 42",
                  "data_entrega": "29/10/2024",
                  "ca": "45611"
                }
              ]
            }
        """
            answer, _ = self.pdf_analyzer.answer_question([temp_path], structured_prompt)

        except Exception as e:
            st.error(f"Erro ao processar o PDF da Ficha de EPI: {str(e)}")
            return None
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)

        if not answer:
            st.error("A IA não retornou uma resposta para a Ficha de EPI.")
            return None

        try:
            cleaned_answer = re.search(r'\{.*\}', answer, re.DOTALL).group(0)
            data = json.loads(cleaned_answer)
            
            if 'nome_funcionario' not in data or 'itens_epi' not in data:
                st.error("O JSON retornado pela IA não contém as chaves esperadas.")
                st.code(answer)
                return None
                
            return data

        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            st.error(f"Erro ao processar a resposta da IA para a Ficha de EPI: {e}")
            st.code(f"Resposta recebida da IA:\n{answer}")
            return None
        
    def add_epi_records(self, funcionario_id, arquivo_id, itens_epi, arquivo_hash=None):
        """Adiciona múltiplos registros de EPI usando Supabase."""
        funcionario_id_str = str(funcionario_id)
        
        if arquivo_hash and verificar_hash_seguro(self.epi_df, 'arquivo_hash'):
            duplicata = self.epi_df[
                (self.epi_df['funcionario_id'] == funcionario_id_str) &
                (self.epi_df['arquivo_hash'] == arquivo_hash)
            ]
            
            if not duplicata.empty:
                st.warning(f"⚠️ Esta ficha de EPI já foi cadastrada anteriormente.")
                return None
        
        saved_ids = []
        for item in itens_epi:
            new_data = {
                'funcionario_id': funcionario_id_str,
                'item_id': str(item.get('item_numero', '')),
                'descricao_epi': str(item.get('descricao', '')),
                'ca_epi': str(item.get('ca', '')),
                'data_entrega': str(item.get('data_entrega', '')),
                'arquivo_id': str(arquivo_id),
                'arquivo_hash': arquivo_hash or ''
            }
            try:
                # ✅ CORREÇÃO: insert_row retorna apenas string do ID
                epi_id = self.supabase_ops.insert_row("fichas_epi", new_data)
                if epi_id:
                    saved_ids.append(epi_id)
            except Exception as e:
                st.error(f"Erro ao adicionar o item '{item.get('descricao')}': {e}")
                continue
        
        if saved_ids:
            st.cache_data.clear()
            self.load_epi_data()
            return saved_ids
        
        return None

    def delete_epi(self, epi_id: str, file_url: str):
        """Deleta um registro de EPI e, se for o último, o arquivo associado."""
        if not epi_id:
            return False

        # 1. Deleta o registro do EPI
        if not self.supabase_ops.delete_row("fichas_epi", epi_id):
            st.error("Falha ao deletar o registro do EPI.")
            return False

        # 2. Verifica se há outros EPIs usando o mesmo arquivo
        if file_url and pd.notna(file_url):
            outros_epis_com_mesmo_arquivo = self.epi_df[
                (self.epi_df['arquivo_id'] == file_url) & 
                (self.epi_df['id'] != epi_id)
            ]
            
            # 3. Se não houver mais nenhum, deleta o arquivo
            if outros_epis_com_mesmo_arquivo.empty:
                try:
                    from managers.supabase_storage import SupabaseStorageManager
                    storage_manager = SupabaseStorageManager(self.unit_id)
                    storage_manager.delete_file_by_url(file_url)
                    logger.info(f"Arquivo {file_url} deletado pois era o último EPI associado.")
                except Exception as e:
                    logger.error(f"Erro ao deletar arquivo do storage: {e}")
                    st.warning("Registro do EPI deletado, mas o arquivo no storage pode não ter sido removido.")

        st.cache_data.clear()
        self.load_epi_data()
        return True
    
    def get_all_epis(self):
        """Retorna todos os EPIs, opcionalmente filtrados."""
        return self.epi_df
    
    def get_epi_details(self, epi_id):
        """Retorna os detalhes de um EPI específico."""
        if self.epi_df.empty:
            return None
        
        details = self.epi_df[self.epi_df['id'] == epi_id]
        return details.iloc[0].to_dict() if not details.empty else None
    
    def update_epi(self, epi_id, updates):
        """Atualiza um registro de EPI."""
        if not epi_id or not updates:
            return False
            
        if self.supabase_ops.update_row("fichas_epi", epi_id, updates):
            self.load_epi_data()
            return True
        return False
    
    def get_ca_details_from_api(self, ca_number: str):
        """Busca detalhes de um CA em uma API externa."""
        # Implementação futura
        pass
    
    def get_ca_vencimento(self, ca: str):
        """Busca a data de vencimento de um CA."""
        # Implementação futura
        pass
    
    def get_employee_epis_with_ca_vencimento(self, employee_id: str):
        """Retorna os EPIs de um funcionário com o vencimento do CA."""
        # Implementação futura
        pass
    
    def get_expired_ca_epis(self):
        """Retorna todos os EPIs com CA vencido."""
        # Implementação futura
        pass
    
    def get_epis_nearing_expiration(self, days=30):
        """Retorna EPIs com CA próximo do vencimento."""
        # Implementação futura
        pass
    
    def get_epi_usage_history(self, ca: str):
        """Retorna o histórico de uso de um EPI (por CA)."""
        # Implementação futura
        pass
    
    def get_last_epi_delivery_date(self, employee_id: str, epi_description: str):
        """Retorna a data da última entrega de um EPI específico para um funcionário."""
        # Implementação futura
        pass
    
    def get_employees_without_epi(self, epi_description: str):
        """Retorna funcionários que nunca receberam um EPI específico."""
        # Implementação futura
        pass
    
    def get_epi_stock_count(self, epi_description: str):
        """Retorna a contagem de um EPI em estoque (simulado)."""
        # Implementação futura
        pass
    
    def add_epi_to_stock(self, epi_description: str, quantity: int):
        """Adiciona EPI ao estoque (simulado)."""
        # Implementação futura
        pass
    
    def remove_epi_from_stock(self, epi_description: str, quantity: int):
        """Remove EPI do estoque (simulado)."""
        # Implementação futura
        pass
    
    def get_epi_replacement_suggestions(self):
        """Sugere a reposição de EPIs com base no uso e vencimento."""
        # Implementação futura
        pass
    
    def generate_epi_report(self, employee_id: str = None, start_date: str = None, end_date: str = None):
        """Gera um relatório de entrega de EPIs."""
        # Implementação futura
        pass
    
    def get_epi_costs(self, start_date: str = None, end_date: str = None):
        """Calcula os custos com EPI em um período."""
        # Implementação futura
        pass
        
    def get_most_used_epis(self, limit=10):
        """Retorna os EPIs mais utilizados."""
        # Implementação futura
        pass
    
    def get_employees_with_most_epi_replacements(self, limit=10):
        """Retorna os funcionários com mais trocas de EPI."""
        # Implementação futura
        pass
    
    def get_ca_validation_status(self, ca: str):
        """Verifica se um CA é válido."""
        # Implementação futura
        pass
    
    def get_epi_image(self, ca: str):
        """Retorna a imagem de um EPI a partir do CA."""
        # Implementação futura
        pass
    
    def get_related_epis(self, epi_description: str):
        """Retorna EPIs relacionados a um EPI específico."""
        # Implementação futura
        pass
    
    def get_epi_provider_info(self, ca: str):
        """Retorna informações do fornecedor de um EPI."""
        # Implementação futura
        pass
    
    def get_epi_technical_sheet(self, ca: str):
        """Retorna a ficha técnica de um EPI."""
        # Implementação futura
        pass
    
    def get_epi_by_risk(self, risk: str):
        """Retorna EPIs recomendados para um determinado risco."""
        # Implementação futura
        pass
    
    def get_epi_by_function(self, function: str):
        """Retorna EPIs recomendados para uma determinada função."""
        # Implementação futura
        pass
    
    def get_epi_by_department(self, department: str):
        """Retorna EPIs recomendados para um determinado setor."""
        # Implementação futura
        pass
    
    def get_epi_by_company(self, company_id: str):
        """Retorna todos os EPIs de uma empresa."""
        # Implementação futura
        pass
    
    def get_epi_by_ca(self, ca: str):
        """Retorna todos os registros de um EPI específico (por CA)."""
        # Implementação futura
        pass
    
    def get_epi_by_description(self, description: str):
        """Retorna todos os registros de um EPI específico (por descrição)."""
        # Implementação futura
        pass
    
    def get_epi_by_date_range(self, start_date: str, end_date: str):
        """Retorna todos os EPIs entregues em um período."""
        # Implementação futura
        pass
    
    def get_epi_by_employee_and_date_range(self, employee_id: str, start_date: str, end_date: str):
        """Retorna os EPIs de um funcionário em um período."""
        # Implementação futura
        pass
    
    def get_epi_by_employee_and_description(self, employee_id: str, description: str):
        """Retorna os registros de um EPI específico para um funcionário."""
        # Implementação futura
        pass
    
    def get_epi_by_employee_and_ca(self, employee_id: str, ca: str):
        """Retorna os registros de um EPI específico (por CA) para um funcionário."""
        # Implementação futura
        pass
    
    def get_epi_by_employee_and_status(self, employee_id: str, status: str):
        """Retorna os EPIs de um funcionário com um determinado status (ex: vencido)."""
        # Implementação futura
        pass
    
    def get_epi_by_status(self, status: str):
        """Retorna todos os EPIs com um determinado status."""
        # Implementação futura
        pass
    
    def get_epi_by_provider(self, provider: str):
        """Retorna todos os EPIs de um fornecedor."""
        # Implementação futura
        pass
    
    def get_epi_by_manufacturer(self, manufacturer: str):
        """Retorna todos os EPIs de um fabricante."""
        # Implementação futura
        pass
    
    def get_epi_by_material(self, material: str):
        """Retorna todos os EPIs de um determinado material."""
        # Implementação futura
        pass
    
    def get_epi_by_body_part(self, body_part: str):
        """Retorna todos os EPIs para uma parte do corpo específica."""
        # Implementação futura
        pass
    
    def get_epi_by_standard(self, standard: str):
        """Retorna todos os EPIs que atendem a uma norma específica."""
        # Implementação futura
        pass
    
    def get_epi_by_color(self, color: str):
        """Retorna todos os EPIs de uma cor específica."""
        # Implementação futura
        pass
    
    def get_epi_by_size(self, size: str):
        """Retorna todos os EPIs de um tamanho específico."""
        # Implementação futura
        pass
    
    def get_epi_by_gender(self, gender: str):
        """Retorna todos os EPIs para um gênero específico."""
        # Implementação futura
        pass
    
    def get_epi_by_age_group(self, age_group: str):
        """Retorna todos os EPIs para uma faixa etária específica."""
        # Implementação futura
        pass
    
    def get_epi_by_weight(self, weight: str):
        """Retorna todos os EPIs para uma faixa de peso específica."""
        # Implementação futura
        pass
    
    def get_epi_by_height(self, height: str):
        """Retorna todos os EPIs para uma faixa de altura específica."""
        # Implementação futura
        pass
    
    def get_epi_by_shoe_size(self, shoe_size: str):
        """Retorna todos os EPIs para um tamanho de calçado específico."""
        # Implementação futura
        pass
    
    def get_epi_by_glove_size(self, glove_size: str):
        """Retorna todos os EPIs para um tamanho de luva específico."""
        # Implementação futura
        pass
    
    def get_epi_by_helmet_size(self, helmet_size: str):
        """Retorna todos os EPIs para um tamanho de capacete específico."""
        # Implementação futura
        pass
    
    def get_epi_by_clothing_size(self, clothing_size: str):
        """Retorna todos os EPIs para um tamanho de roupa específico."""
        # Implementação futura
        pass
    
    def get_epi_by_protection_level(self, protection_level: str):
        """Retorna todos os EPIs com um nível de proteção específico."""
        # Implementação futura
        pass
    
    def get_epi_by_certification(self, certification: str):
        """Retorna todos os EPIs com uma certificação específica."""
        # Implementação futura
        pass
    
    def get_epi_by_application(self, application: str):
        """Retorna todos os EPIs para uma aplicação específica."""
        # Implementação futura
        pass
    
    def get_epi_by_sector(self, sector: str):
        """Retorna todos os EPIs para um setor específico."""
        # Implementação futura
        pass
