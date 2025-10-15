import streamlit as st
import pandas as pd
import logging
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
        result = self.supabase_ops.insert_row("unidades", unit_data)
        if result:
            load_matrix_data.clear()
            self._load_data_from_cache()
        return result is not None

    def add_user(self, user_data: dict) -> bool:
        result = self.supabase_ops.insert_row("usuarios", user_data)
        if result:
            load_matrix_data.clear()
            self._load_data_from_cache()
        return result is not None

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