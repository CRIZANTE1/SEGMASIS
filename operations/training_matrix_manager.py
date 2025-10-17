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
        # ✅ CORREÇÃO: Validações de entrada
        if not name or not isinstance(name, str) or not name.strip():
            return None, "Nome da função não pode ser vazio"

        name = name.strip()
        description = str(description).strip() if description else ""

        # ✅ CORREÇÃO: Verifica duplicatas
        if not self.functions_df.empty:
            existing = self.functions_df[
                self.functions_df['nome_funcao'].str.lower() == name.lower()
            ]
            if not existing.empty:
                return None, f"Função '{name}' já existe"

        new_data = {
            'nome_funcao': name,
            'descricao': description
        }

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
        # ✅ CORREÇÃO: Validações de entrada
        if not function_id or not required_norm:
            return None, "ID da função e norma obrigatória são necessários"

        required_norm = str(required_norm).strip()
        if not required_norm:
            return None, "Norma obrigatória não pode ser vazia"

        # ✅ CORREÇÃO: Verifica se já existe mapeamento
        if not self.matrix_df.empty:
            existing = self.matrix_df[
                (self.matrix_df['id_funcao'] == str(function_id)) &
                (self.matrix_df['norma_obrigatoria'].str.lower() == required_norm.lower())
            ]
            if not existing.empty:
                return None, f"Treinamento '{required_norm}' já mapeado para esta função"

        new_data = {
            'id_funcao': str(function_id),
            'norma_obrigatoria': required_norm
        }

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
        

    # ==================== GLOBAL MATRIX FUNCTIONS ====================

    def get_all_functions_global(self) -> List[dict]:
        """
        Retorna todas as funções da matriz global (unit_id = NULL).

        Returns:
            Lista de dicionários com funções globais
        """
        try:
            # Usar operações globais (unit_id=None)
            global_supabase_ops = SupabaseOperations(unit_id=None)

            # Buscar funções da tabela 'funcoes' onde unit_id é NULL ou vazio
            functions_df = global_supabase_ops.get_table_data("funcoes")

            # Filtrar para unit_id NULL/Vazio (matriz global)
            if not functions_df.empty:
                # Verificar se há coluna unit_id, senão assumir que tudo é global
                if 'unit_id' in functions_df.columns:
                    global_functions = functions_df[functions_df['unit_id'].isnull() | (functions_df['unit_id'] == '')]
                else:
                    global_functions = functions_df

                return global_functions.to_dict('records')
            else:
                return []
        except Exception as e:
            logger.error(f"Erro ao buscar funções globais: {e}")
            return []

    def import_function_from_global(self, global_function_id: str, target_unit_id: str = None) -> Tuple[bool, str]:
        """
        Importa uma função da matriz global para uma unidade específica.

        Args:
            global_function_id: ID da função na matriz global
            target_unit_id: ID da unidade alvo (usa self.unit_id se None)

        Returns:
            tuple: (sucesso, mensagem)
        """
        if not global_function_id:
            return False, "ID da função global não informado"

        target_unit = target_unit_id or self.unit_id
        if not target_unit:
            return False, "ID da unidade alvo não informado"

        try:
            # Verificar se a função global existe
            global_supabase_ops = SupabaseOperations(unit_id=None)
            function_data = global_supabase_ops.get_by_id("funcoes", global_function_id)

            if function_data.empty:
                return False, "Função global não encontrada"

            function_record = function_data.iloc[0]

            # Verificar se já existe na unidade alvo
            if not self.functions_df.empty:
                existing = self.functions_df[
                    self.functions_df['nome_funcao'].str.lower() == function_record['nome_funcao'].lower()
                ]
                if not existing.empty:
                    return False, f"Função '{function_record['nome_funcao']}' já existe na unidade"

            # Preparar dados para importação (adicionar unit_id se necessário)
            import_data = {
                'nome_funcao': function_record['nome_funcao'],
                'descricao': function_record.get('descricao', ''),
                'unit_id': target_unit  # Adicionar referência à unidade
            }

            # Inserir na unidade alvo
            function_id = self.supabase_ops.insert_row("funcoes", import_data)
            if function_id:
                self._functions_df = None  # Forçar recarregamento
                logger.info(f"Função '{function_record['nome_funcao']}' importada para unidade {target_unit}")
                return True, f"Função '{function_record['nome_funcao']}' importada com sucesso"

            return False, "Falha ao importar função"

        except Exception as e:
            logger.error(f"Erro ao importar função global: {e}")
            return False, f"Erro ao importar função: {str(e)}"

    def import_function_matrix_from_global(self, global_function_id: str, target_function_id: str) -> Tuple[bool, str]:
        """
        Importa todos os treinamentos de uma função da matriz global.

        Args:
            global_function_id: ID da função na matriz global
            target_function_id: ID da função na unidade alvo

        Returns:
            tuple: (sucesso, mensagem)
        """
        if not global_function_id or not target_function_id:
            return False, "IDs das funções não informados"

        try:
            # Buscar treinamentos da função global
            global_supabase_ops = SupabaseOperations(unit_id=None)
            global_matrix_df = global_supabase_ops.get_table_data("matriz_treinamentos")

            if global_matrix_df.empty:
                return False, "Nenhum treinamento encontrado na matriz global"

            # Filtrar treinamentos da função global
            global_trainings = global_matrix_df[global_matrix_df['id_funcao'] == global_function_id]

            if global_trainings.empty:
                return False, "Nenhum treinamento encontrado para esta função na matriz global"

            # Importar treinamentos
            imported_count = 0

            for _, training in global_trainings.iterrows():
                norma_obrigatoria = training.get('norma_obrigatoria')
                if not norma_obrigatoria:
                    continue

                # Verificar se já existe na unidade
                if not self.matrix_df.empty:
                    existing = self.matrix_df[
                        (self.matrix_df['id_funcao'] == target_function_id) &
                        (self.matrix_df['norma_obrigatoria'] == norma_obrigatoria)
                    ]
                    if not existing.empty:
                        logger.debug(f"Treinamento '{norma_obrigatoria}' já existe para esta função")
                        continue

                # Adicionar treinamento
                mapping_data = {
                    'id_funcao': target_function_id,
                    'norma_obrigatoria': norma_obrigatoria
                }

                mapping_id = self.supabase_ops.insert_row("matriz_treinamentos", mapping_data)
                if mapping_id:
                    imported_count += 1
                    logger.debug(f"Treinamento '{norma_obrigatoria}' importado")
                else:
                    logger.warning(f"Falha ao importar treinamento '{norma_obrigatoria}'")

            if imported_count > 0:
                self._matrix_df = None  # Forçar recarregamento
                return True, f"{imported_count} treinamentos importados com sucesso"
            else:
                return False, "Nenhum treinamento novo foi importado (já existem)"

        except Exception as e:
            logger.error(f"Erro ao importar treinamentos: {e}")
            return False, f"Erro ao importar treinamentos: {str(e)}"

    def find_global_function_matches(self, employee_cargo: str, score_cutoff: int = 80) -> List[Tuple[dict, int]]:
        """
        Encontra funções similares na matriz global usando fuzzy matching.

        Args:
            employee_cargo: Nome do cargo/função do funcionário
            score_cutoff: Score mínimo para considerar match

        Returns:
            Lista de tuplas (função_global, score) ordenadas por score
        """
        if not employee_cargo or not isinstance(employee_cargo, str):
            return []

        employee_cargo = employee_cargo.strip()
        if not employee_cargo:
            return []

        try:
            global_functions = self.get_all_functions_global()
            if not global_functions:
                return []

            function_names = [f['nome_funcao'] for f in global_functions]
            best_matches = process.extractBests(employee_cargo, function_names, score_cutoff=score_cutoff)

            results = []
            for match_name, score in best_matches:
                # Encontrar o objeto completo da função
                matching_function = next((f for f in global_functions if f['nome_funcao'] == match_name), None)
                if matching_function:
                    results.append((matching_function, score))

            return sorted(results, key=lambda x: x[1], reverse=True)

        except Exception as e:
            logger.error(f"Erro no fuzzy matching global: {e}")
            return []

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
