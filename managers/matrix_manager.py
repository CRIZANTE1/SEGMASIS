import streamlit as st
import pandas as pd
import logging
from typing import Tuple
from operations.supabase_operations import SupabaseOperations
from fuzzywuzzy import process
from operations.audit_logger import log_action

logger = logging.getLogger('segsisone_app.matrix_manager')

@st.cache_data(ttl=300)
def load_matrix_data():
    """Carrega dados globais da matriz (usuários, unidades, logs e solicitações)."""
    logger.info("Carregando dados da matriz global...")
    try:
        supabase_ops = SupabaseOperations(unit_id=None)
        
        users_data = supabase_ops.get_table_data("usuarios")
        units_data = supabase_ops.get_table_data("unidades")
        log_data = supabase_ops.get_table_data("log_auditoria")
        # ✅ NOVO: Carrega as solicitações de acesso
        requests_data = supabase_ops.get_table_data("solicitacoes_acesso")
        
        logger.info("Dados da matriz carregados com sucesso.")
        return users_data, units_data, log_data, requests_data
        
    except Exception as e:
        logger.critical(f"Falha ao carregar dados da matriz: {e}", exc_info=True)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

class MatrixManager:
    def __init__(self):
        self.supabase_ops = SupabaseOperations(unit_id=None)
        self.users_df = pd.DataFrame()
        self.units_df = pd.DataFrame()
        self.log_df = pd.DataFrame()
        self.requests_df = pd.DataFrame() # ✅ NOVO
        self.data_loaded_successfully = False
        self._load_data_from_cache()

    def _load_data_from_cache(self):
        """Carrega os dados da função em cache e padroniza os IDs."""
        users_data, units_data, log_data, requests_data = load_matrix_data()

        if not users_data.empty:
            self.users_df = users_data.astype({'id': 'str', 'unidade_associada': 'str'})
        else:
            self.users_df = pd.DataFrame(columns=['id', 'email', 'nome', 'role', 'unidade_associada'])

        if not units_data.empty:
            self.units_df = units_data.astype({'id': 'str'})
        else:
            self.units_df = pd.DataFrame(columns=['id', 'nome_unidade', 'folder_id'])

        if not log_data.empty:
            self.log_df = log_data
        else:
            self.log_df = pd.DataFrame()
        
        # ✅ NOVO: Carrega e padroniza solicitações
        if not requests_data.empty:
            self.requests_df = requests_data
        else:
            self.requests_df = pd.DataFrame(columns=['id', 'email_usuario', 'nome_usuario', 'status'])

        self.data_loaded_successfully = True

    def get_user_info(self, email: str) -> dict | None:
        if self.users_df.empty:
            return None
        user_data = self.users_df[self.users_df['email'].str.lower() == email.lower()]
        return user_data.to_dict('records')[0] if not user_data.empty else None

    def get_unit_info(self, unit_id: str) -> dict | None:
        if self.units_df.empty:
            return None
        unit_data = self.units_df[self.units_df['id'] == unit_id]
        return unit_data.to_dict('records')[0] if not unit_data.empty else None

    def get_unit_info_by_name(self, unit_name: str) -> dict | None:
        if self.units_df.empty:
            return None
        unit_data = self.units_df[self.units_df['nome_unidade'] == unit_name]
        return unit_data.to_dict('records')[0] if not unit_data.empty else None

    def get_all_units(self) -> list:
        if self.units_df.empty:
            return []
        return self.units_df.to_dict('records')
        
    def get_all_users(self) -> list:
        if self.users_df.empty:
            return []
        return self.users_df.to_dict('records')

    def get_audit_logs(self) -> pd.DataFrame:
        return self.log_df

    # ✅ NOVO: Método para buscar solicitações pendentes
    def get_pending_access_requests(self) -> pd.DataFrame:
        """Retorna um DataFrame com as solicitações de acesso pendentes.""" 
        if self.requests_df.empty:
            return pd.DataFrame()
        return self.requests_df[self.requests_df['status'].str.lower() == 'pendente'].copy()

    # ✅ NOVO: Método para atualizar o status de uma solicitação
    def update_access_request_status(self, request_id: int, new_status: str) -> bool:
        """Atualiza o status de uma solicitação de acesso pelo seu ID."""
        success = self.supabase_ops.update_row(
            "solicitacoes_acesso", 
            str(request_id), 
            {'status': new_status}
        )
        if success:
            load_matrix_data.clear() # Limpa o cache para recarregar
            self._load_data_from_cache()
        return success is not None
        
    def add_unit(self, unit_data: dict) -> bool:
        # ✅ CORREÇÃO: insert_row retorna apenas string do ID
        unit_id = self.supabase_ops.insert_row("unidades", unit_data)
        if unit_id:
            load_matrix_data.clear()
            self._load_data_from_cache()
            return True
        return False

    def add_user(self, user_data: dict) -> bool:
        # ✅ CORREÇÃO: insert_row retorna apenas string do ID
        user_id = self.supabase_ops.insert_row("usuarios", user_data)
        if user_id:
            load_matrix_data.clear()
            self._load_data_from_cache()
            return True
        return False

    def update_user(self, user_id: str, updates: dict) -> bool:
        result = self.supabase_ops.update_row("usuarios", user_id, updates)
        if result:
            load_matrix_data.clear()
            self._load_data_from_cache()
        return result is not None
            
    def remove_user(self, user_id: str) -> bool:
        result = self.supabase_ops.delete_row("usuarios", user_id)
        if result:
            load_matrix_data.clear()
            self._load_data_from_cache()
        return result is not None

    # ==================== GLOBAL MATRIX MANAGEMENT ====================

    def bulk_apply_global_matrix_to_unit(self, unit_id: str) -> Tuple[bool, str]:
        """
        Aplica a matriz global completa a uma unidade específica.

        Args:
            unit_id: ID da unidade alvo

        Returns:
            tuple: (sucesso, mensagem)
        """
        if not unit_id:
            return False, "ID da unidade não informado"

        try:
            from operations.training_matrix_manager import MatrixManager as TrainingMatrixManager
            global_matrix_manager = TrainingMatrixManager("global")

            # Buscar todas as funções globais
            global_functions = global_matrix_manager.get_all_functions_global()

            if not global_functions:
                return False, "Nenhuma função encontrada na matriz global"

            success_count = 0
            error_messages = []

            # Para cada função global, importar para a unidade
            for global_function in global_functions:
                try:
                    # Importar função
                    success, message = global_matrix_manager.import_function_from_global(
                        global_function['id'], unit_id
                    )

                    if success:
                        # Importar treinamentos da função
                        # Primeiro encontrar o ID da função recém-importada na unidade
                        unit_matrix_manager = TrainingMatrixManager(unit_id)
                        unit_functions = unit_matrix_manager.functions_df

                        if not unit_functions.empty:
                            matching_function = unit_functions[
                                unit_functions['nome_funcao'].str.lower() == global_function['nome_funcao'].lower()
                            ]
                            if not matching_function.empty:
                                target_function_id = matching_function.iloc[0]['id']

                                # Importar treinamentos
                                train_success, train_message = global_matrix_manager.import_function_matrix_from_global(
                                    global_function['id'], target_function_id
                                )

                                if train_success:
                                    success_count += 1
                                else:
                                    error_messages.append(f"Função '{global_function['nome_funcao']}': {train_message}")
                                    success_count += 1  # Função importada mesmo sem treinamentos
                            else:
                                error_messages.append(f"Função '{global_function['nome_funcao']}' importada mas não encontrada na unidade")
                        else:
                            error_messages.append(f"Função '{global_function['nome_funcao']}' importada mas lista vazia na unidade")
                    else:
                        error_messages.append(f"Falha ao importar função '{global_function['nome_funcao']}': {message}")

                except Exception as e:
                    error_messages.append(f"Erro ao processar função '{global_function['nome_funcao']}': {str(e)}")

            # Resultado final
            if success_count > 0:
                message = f"Matriz aplicada com sucesso para {success_count} funções"
                if error_messages:
                    message += f". Avisos: {'; '.join(error_messages[:3])}"  # Limitar mensagens de erro
                return True, message
            else:
                return False, f"Falha ao aplicar matriz. Erros: {'; '.join(error_messages)}"

        except Exception as e:
            return False, f"Erro crítico ao aplicar matriz global: {str(e)}"

    def bulk_apply_global_matrix_to_all_units(self) -> Tuple[bool, str]:
        """
        Aplica a matriz global a todas as unidades existentes.

        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            all_units = self.get_all_units()
            if not all_units:
                return False, "Nenhuma unidade encontrada"

            success_count = 0
            error_messages = []

            for unit in all_units:
                try:
                    success, message = self.bulk_apply_global_matrix_to_unit(unit['id'])
                    if success:
                        success_count += 1
                    else:
                        error_messages.append(f"Unidade '{unit['nome_unidade']}': {message}")
                except Exception as e:
                    error_messages.append(f"Erro na unidade '{unit['nome_unidade']}': {str(e)}")

            if success_count > 0:
                message = f"Matriz aplicada com sucesso para {success_count}/{len(all_units)} unidades"
                if error_messages:
                    message += f". Erros em algumas unidades: {'; '.join(error_messages[:2])}"
                return True, message
            else:
                return False, f"Falha em todas as unidades. Erros: {'; '.join(error_messages)}"

        except Exception as e:
            return False, f"Erro crítico ao aplicar matriz para todas as unidades: {str(e)}"

    def auto_apply_global_matrix_on_unit_creation(self, unit_id: str) -> Tuple[bool, str]:
        """
        Aplica automaticamente a matriz global durante a criação de uma nova unidade.

        Args:
            unit_id: ID da nova unidade

        Returns:
            tuple: (sucesso, mensagem)
        """
        if not unit_id:
            return False, "ID da unidade não informado"

        # Verificar se a unidade existe
        unit_info = self.get_unit_info(unit_id)
        if not unit_info:
            return False, "Unidade não encontrada"

        logger.info(f"Aplicando matriz global automaticamente para nova unidade: {unit_info['nome_unidade']}")

        return self.bulk_apply_global_matrix_to_unit(unit_id)
