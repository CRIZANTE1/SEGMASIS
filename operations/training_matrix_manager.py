import streamlit as st
import pandas as pd
import json
import re
import logging
import tempfile
import os
from typing import Optional, Tuple, List
from operations.supabase_operations import SupabaseOperations
from AI.api_Operation import PDFQA
from fuzzywuzzy import process

logger = logging.getLogger('segsisone_app.training_matrix_manager')

class MatrixManager:
    def __init__(self, unit_id: str):
        """
        Inicializa o gerenciador da Matriz de Treinamentos para uma unidade.

        Args:
            unit_id: ID da unidade operacional
        """
        # ✅ CORREÇÃO (#2): Validação de entrada robusta.
        if not unit_id or not isinstance(unit_id, str) or unit_id.strip() in ['', 'None', 'none', 'null']:
            logger.error(f"MatrixManager inicializado com unit_id inválido: {unit_id}")
            raise ValueError("unit_id não pode ser vazio ou None")

        self.unit_id = unit_id.strip()

        # ✅ REMOVIDO: Todos os dicionários hardcoded movidos para NRRulesManager
        from operations.nr_rules_manager import NRRulesManager
        self.nr_rules_manager = NRRulesManager(self.unit_id)

        self.supabase_ops = SupabaseOperations(self.unit_id)

        # Definição de colunas esperadas
        self.columns_functions = ['id', 'nome_funcao', 'descricao']
        self.columns_matrix = ['id', 'id_funcao', 'norma_obrigatoria']

        # Cache interno
        self._functions_df = None
        self._matrix_df = None

        # Inicializa analisador de PDF
        try:
            self.pdf_analyzer = PDFQA()
            logger.info(f"MatrixManager inicializado para unit_id: ...{self.unit_id[-6:]}")
        except Exception as e:
            logger.error(f"Erro ao inicializar PDFQA: {e}")
            raise

    @property
    def functions_df(self) -> pd.DataFrame:
        """
        Carrega o DataFrame de funções sob demanda.
        
        Returns:
            DataFrame com as funções cadastradas
        """
        if self._functions_df is None:
            self._load_functions_data()
        return self._functions_df if self._functions_df is not None else pd.DataFrame(columns=self.columns_functions)

    @property
    def matrix_df(self) -> pd.DataFrame:
        """
        Carrega o DataFrame da matriz sob demanda.
        
        Returns:
            DataFrame com os mapeamentos de treinamentos
        """
        if self._matrix_df is None:
            self._load_matrix_data()
        return self._matrix_df if self._matrix_df is not None else pd.DataFrame(columns=self.columns_matrix)

    def _load_functions_data(self):
        """Carrega os dados da tabela 'funcoes'."""
        try:
            self._functions_df = self.supabase_ops.get_table_data("funcoes")
            
            # ✅ CORREÇÃO: Validação do DataFrame carregado
            if self._functions_df is None:
                logger.warning("get_table_data retornou None para 'funcoes'")
                self._functions_df = pd.DataFrame(columns=self.columns_functions)
            elif self._functions_df.empty:
                logger.info("Tabela 'funcoes' está vazia")
            else:
                logger.debug(f"Carregadas {len(self._functions_df)} funções")
                
        except Exception as e:
            logger.error(f"Erro ao carregar funções: {e}")
            self._functions_df = pd.DataFrame(columns=self.columns_functions)
        
    def _load_matrix_data(self):
        """Carrega os dados da tabela 'matriz_treinamentos'."""
        try:
            self._matrix_df = self.supabase_ops.get_table_data("matriz_treinamentos")
            
            # ✅ CORREÇÃO: Validação do DataFrame carregado
            if self._matrix_df is None:
                logger.warning("get_table_data retornou None para 'matriz_treinamentos'")
                self._matrix_df = pd.DataFrame(columns=self.columns_matrix)
            elif self._matrix_df.empty:
                logger.info("Tabela 'matriz_treinamentos' está vazia")
            else:
                logger.debug(f"Carregados {len(self._matrix_df)} mapeamentos")
                
        except Exception as e:
            logger.error(f"Erro ao carregar matriz: {e}")
            self._matrix_df = pd.DataFrame(columns=self.columns_matrix)

    def add_function(self, name: str, description: str) -> tuple[str | None, str]:
        # ... validações ...
        
        try:
            # ✅ CORREÇÃO: insert_row retorna apenas string do ID
            function_id = self.supabase_ops.insert_row("funcoes", new_data)
            if function_id:
                self._functions_df = None
                st.cache_data.clear()
                logger.info(f"Função '{name}' adicionada com sucesso.")
                return function_id, "Função adicionada com sucesso."
                
            return None, "Falha ao adicionar função."
            
        except Exception as e:
            logger.error(f"Erro ao adicionar função: {e}")
            return None, f"Erro ao adicionar função: {str(e)}"

    def add_training_to_function(self, function_id: str, required_norm: str) -> tuple[str | None, str]:
        # ... validações ...
        
        try:
            # ✅ CORREÇÃO: insert_row retorna apenas string do ID
            mapping_id = self.supabase_ops.insert_row("matriz_treinamentos", new_data)
            if mapping_id:
                self._matrix_df = None
                st.cache_data.clear()
                logger.info(f"Treinamento '{required_norm}' mapeado para função {function_id}")
                return mapping_id, "Treinamento mapeado com sucesso."
                
            return None, "Falha ao mapear treinamento."
            
        except Exception as e:
            logger.error(f"Erro ao mapear treinamento: {e}")
            return None, f"Erro ao mapear treinamento: {str(e)}"

    def get_required_trainings_for_function(self, function_name: str) -> list:
        """Retorna treinamentos obrigatórios para uma função."""
        if not function_name or not isinstance(function_name, str):
            logger.warning("Nome da função não fornecido ou inválido")
            return []

        if self.functions_df.empty or self.matrix_df.empty:
            return []
        
        function = self.functions_df[
            self.functions_df['nome_funcao'].str.lower() == function_name.lower()
        ]
        if function.empty:
            return []
            
        function_id = function.iloc[0]['id']
        required_df = self.matrix_df[self.matrix_df['id_funcao'] == function_id]

        if required_df.empty:
            return []

        # ✅ Remove valores None, vazios e duplicatas
        trainings = required_df['norma_obrigatoria'].dropna().tolist()
        trainings = [t.strip() for t in trainings if t and str(t).strip()]
        trainings = list(set(trainings))  # Remove duplicatas

        return sorted(trainings)  # Retorna ordenado

    def analyze_matrix_pdf(self, pdf_file):
        """Analisa PDF de matriz de treinamentos."""
        prompt = """
        **Persona:** Você é um especialista em RH e Segurança do Trabalho...
        **Estrutura JSON de Saída Obrigatória:**
```json
        [
          {
            "funcao": "Eletricista de Manutenção",
            "normas_obrigatorias": ["NR-10", "NR-35"]
          }
        ]
    **Importante:** Responda APENAS com o bloco de código JSON.
    """
        try:
            response_text, _ = self.pdf_analyzer.answer_question([pdf_file], prompt, task_type='extraction')
            if not response_text:
                return None, "A IA não retornou uma resposta."
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not match:
                return None, "A resposta da IA não estava no formato JSON esperado."
            matrix_data = json.loads(match.group(0))
            return matrix_data, "Dados extraídos com sucesso."
        except (json.JSONDecodeError, Exception) as e:
            return None, f"Ocorreu um erro ao analisar o PDF: {e}"

    def save_extracted_matrix(self, extracted_data: list):
        """Salva matriz extraída usando Supabase."""
        if not extracted_data:
            return 0, 0
        
        current_functions_df = self.functions_df.copy()
        new_functions_to_add = []
        new_mappings_to_add = []

        # Prepara novas funções
        for item in extracted_data:
            function_name = item.get("funcao")
            if function_name and function_name.lower() not in current_functions_df['nome_funcao'].str.lower().values:
                if function_name not in [f['nome_funcao'] for f in new_functions_to_add]:
                    new_functions_to_add.append({
                        'nome_funcao': function_name,
                        'descricao': "Importado via IA"
                    })
        
        # Insere novas funções
        if new_functions_to_add:
            self.supabase_ops.insert_batch("funcoes", new_functions_to_add)
            self._load_functions_data()  # ✅ Recarrega imediatamente

        updated_functions_df = self.functions_df.copy()
        current_matrix_df = self.matrix_df.copy()
        
        # Prepara novos mapeamentos
        for item in extracted_data:
            function_name = item.get("funcao")
            required_norms = item.get("normas_obrigatorias", [])
            if not function_name or not required_norms:
                continue
            
            function_entry = updated_functions_df[
                updated_functions_df['nome_funcao'].str.lower() == function_name.lower()
            ]
            if function_entry.empty:
                continue
            function_id = function_entry.iloc[0]['id']

            for norm in required_norms:
                is_duplicate = not current_matrix_df[
                    (current_matrix_df['id_funcao'] == str(function_id)) & 
                    (current_matrix_df['norma_obrigatoria'] == norm)
                ].empty
                
                if not is_duplicate:
                    new_mappings_to_add.append({
                        'id_funcao': str(function_id),
                        'norma_obrigatoria': norm
                    })

        # Insere novos mapeamentos
        if new_mappings_to_add:
            self.supabase_ops.insert_batch("matriz_treinamentos", new_mappings_to_add)
            self._matrix_df = None

        return len(new_functions_to_add), len(new_mappings_to_add)

    def update_function_mappings(self, function_id, new_required_norms: list):
        """Atualiza mapeamentos de uma função."""
        try:
            # ✅ CORREÇÃO: Acesso seguro ao nome da função
            function_query = self.functions_df[self.functions_df['id'] == function_id]
            if function_query.empty:
                return False, f"Função com ID {function_id} não encontrada"
                
            function_name = function_query['nome_funcao'].iloc[0]
            if not function_name:
                return False, "Nome da função não encontrado"
                
            current_mappings = self.get_required_trainings_for_function(function_name)

            to_add = [norm for norm in new_required_norms if norm not in current_mappings]
            to_remove = [norm for norm in current_mappings if norm not in new_required_norms]

            added_count, removed_count = 0, 0

            for norm in to_add:
                if self.add_training_to_function(function_id, norm)[0]:
                    added_count += 1
            
            for norm in to_remove:
                mapping_to_delete = self.matrix_df[
                    (self.matrix_df['id_funcao'] == str(function_id)) & (self.matrix_df['norma_obrigatoria'] == norm)
                ]
                if not mapping_to_delete.empty:
                    mapping_id = mapping_to_delete.iloc[0]['id']
                    if self.supabase_ops.delete_row("matriz_treinamentos", mapping_id):
                        removed_count += 1
    
            self._matrix_df = None
            return True, f"Mapeamentos atualizados! {added_count} adicionado(s), {removed_count} removido(s)."
            
        except Exception as e:
            return False, f"Erro ao atualizar mapeamentos: {e}"

    def find_closest_function(
        self, 
        employee_cargo: str, 
        score_cutoff: int = 90
    ) -> Optional[str]:
        """
        Encontra a função mais próxima usando fuzzy matching.
        
        Args:
            employee_cargo: Cargo do funcionário
            score_cutoff: Pontuação mínima para aceitar match (0-100)
            
        Returns:
            Nome da função mais próxima ou None
        """
        # ✅ VALIDAÇÕES MELHORADAS
        if not employee_cargo or not isinstance(employee_cargo, str):
            logger.debug("Cargo do funcionário não fornecido ou inválido")
            return None
        
        # Remove espaços e valida novamente
        employee_cargo = employee_cargo.strip()
        if not employee_cargo:
            logger.debug("Cargo vazio após strip()")
            return None
        
        try:
            # ✅ Acessa a property (carrega dados se necessário)
            df = self.functions_df
            
            # ✅ Validações do DataFrame
            if df is None or df.empty:
                logger.debug("DataFrame de funções está vazio")
                return None
            
            if 'nome_funcao' not in df.columns:
                logger.error("Coluna 'nome_funcao' não existe no DataFrame")
                return None
            
            # Obtém lista de funções e remove nulos
            function_names = df['nome_funcao'].dropna().tolist()
            
            if not function_names:
                logger.debug("Nenhuma função disponível para matching")
                return None

            # ✅ Importação dinâmica por segurança
            try:
                from fuzzywuzzy import process as fuzz_process
            except ImportError:
                logger.error("Módulo fuzzywuzzy não instalado")
                return None
            
            # Faz o fuzzy matching
            best_match = fuzz_process.extractOne(employee_cargo, function_names)
            
            if not best_match:
                logger.debug(f"Nenhum match encontrado para '{employee_cargo}'")
                return None
            
            match_name, score = best_match
            logger.info(f"Fuzzy match para '{employee_cargo}': '{match_name}' (score: {score})")
            
            if score >= score_cutoff:
                logger.info(f"Match aceito (score {score} >= {score_cutoff})")
                return match_name
            else:
                logger.info(f"Match rejeitado (score {score} < {score_cutoff})")
                return None
                
        except Exception as e:
            logger.error(f"Erro no fuzzy matching: {e}", exc_info=True)
            return None
        
    def get_training_recommendations_for_function(
        self, 
        function_name: str, 
        nr_analyzer
    ) -> Tuple[Optional[List[dict]], str]:
        """
        Obtém recomendações de treinamentos usando IA.
        
        Args:
            function_name: Nome da função
            nr_analyzer: Instância do NRAnalyzer para busca semântica
            
        Returns:
            tuple: (lista de recomendações, mensagem de status)
        """
        # ✅ CORREÇÃO: Validações
        if not function_name or not isinstance(function_name, str):
            return None, "Nome da função não fornecido ou inválido"
        
        if not nr_analyzer:
            return None, "Analisador de NR não fornecido"
        
        prompt_template = """
        **Persona:** Você é um Engenheiro de Segurança do Trabalho Sênior especializado em análise de riscos ocupacionais.

        **Contexto:** Base de Conhecimento Normativa
        ---
        {relevant_knowledge}
        ---

        **Tarefa:** Para a função de "{function_name}", identifique os treinamentos de segurança obrigatórios com base nas Normas Regulamentadoras brasileiras.

        **Estrutura JSON de Saída Obrigatória:**
        ```json
        [
          {{
            "treinamento_recomendado": "NR-10",
            "justificativa_normativa": "A função envolve interação com instalações elétricas, conforme item 10.8.1 da NR-10."
          }}
        ]
        ```

        **Importante:** 
        1. Responda APENAS com o bloco de código JSON
        2. Use nomenclatura oficial das NRs
        3. Base as justificativas nos trechos da Base de Conhecimento fornecida
        4. Liste apenas treinamentos realmente obrigatórios para a função
        """
        
        try:
            # Busca conhecimento relevante
            query = f"Riscos, atividades e treinamentos de segurança obrigatórios para a função de {function_name}"
            logger.info(f"Buscando conhecimento para função '{function_name}'")
            
            relevant_knowledge = nr_analyzer._find_semantically_relevant_chunks(query, top_k=10)
            
            if "indisponível" in relevant_knowledge.lower() or "erro" in relevant_knowledge.lower():
                return None, "Base de conhecimento indisponível"
            
            # Monta o prompt final
            final_prompt = prompt_template.format(
                function_name=function_name,
                relevant_knowledge=relevant_knowledge
            )
            
            # Chama a IA
            logger.info("Gerando recomendações com IA...")
            response_text, _ = self.pdf_analyzer.answer_question(
                [], 
                final_prompt, 
                task_type='audit'
            )
            
            if not response_text:
                return None, "A IA não retornou uma resposta."

            # ✅ CORREÇÃO: Parse mais robusto
            try:
                # Tenta extrair JSON com marcadores
                json_match = re.search(r'```json\s*(\[.*?\])\s*```', response_text, re.DOTALL)
                if not json_match:
                    # Tenta sem marcadores
                    json_match = re.search(r'(\[.*?\])', response_text, re.DOTALL)
                
                if not json_match:
                    logger.warning(f"JSON não encontrado na resposta: {response_text[:200]}")
                    return None, f"A resposta da IA não estava no formato esperado."
                
                json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
                recommendations = json.loads(json_str)
                
                # Valida estrutura
                if not isinstance(recommendations, list):
                    return None, "Formato de recomendações inválido"
                
                # Valida cada recomendação
                valid_recs = []
                for rec in recommendations:
                    if isinstance(rec, dict) and 'treinamento_recomendado' in rec and 'justificativa_normativa' in rec:
                        valid_recs.append(rec)
                
                if not valid_recs:
                    return None, "Nenhuma recomendação válida foi gerada"
                
                logger.info(f"Geradas {len(valid_recs)} recomendações válidas")
                return valid_recs, "Recomendações geradas com sucesso"

            except json.JSONDecodeError as e:
                logger.error(f"Erro ao fazer parse do JSON: {e}")
                return None, "Erro ao interpretar a resposta da IA"
            except Exception as e:
                logger.error(f"Erro ao processar recomendações: {e}", exc_info=True)
                return None, f"Erro ao processar recomendações: {str(e)}"
                
        except Exception as e:
            logger.error(f"Erro ao obter recomendações: {e}", exc_info=True)
            return None, f"Erro ao obter recomendações: {str(e)}"
