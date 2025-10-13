import streamlit as st
import pandas as pd
import logging
from operations.supabase_operations import SupabaseOperations
from fuzzywuzzy import process
from operations.audit_logger import log_action

logger = logging.getLogger('segsisone_app.matrix_manager')

@st.cache_data(ttl=300)
def load_matrix_data():
    """Carrega dados globais da matriz (usuários e unidades)."""
    logger.info("Carregando dados da matriz global...")
    try:
        # Usa None como unit_id para acessar tabelas globais
        supabase_ops = SupabaseOperations(unit_id=None)
        
        users_data = supabase_ops.get_table_data("usuarios")
        units_data = supabase_ops.get_table_data("unidades")
        log_data = supabase_ops.get_table_data("log_auditoria")
        
        logger.info("Dados da matriz carregados com sucesso.")
        return users_data, units_data, log_data
        
    except Exception as e:
        logger.critical(f"Falha ao carregar dados da matriz: {e}", exc_info=True)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

class MatrixManager:
    def __init__(self):
        """Gerencia dados globais: Usuários e Unidades."""
        self.supabase_ops = SupabaseOperations(unit_id=None)
        self.users_df = pd.DataFrame()
        self.units_df = pd.DataFrame()
        self.log_df = pd.DataFrame()
        self.data_loaded_successfully = False
        self._load_data_from_cache()

    def _load_data_from_cache(self):
        """Carrega os dados da função em cache."""
        users_data, units_data, log_data = load_matrix_data()

        # Define colunas esperadas
        user_cols = ['id', 'email', 'nome', 'role', 'unidade_associada']
        unit_cols = ['id', 'nome_unidade', 'folder_id', 'email_contato']
        log_cols = ['id', 'timestamp', 'user_email', 'user_role', 'action', 'details', 'target_uo']

        # Carrega Usuários
        if not users_data.empty:
            self.users_df = users_data
            for col in user_cols:
                if col not in self.users_df.columns:
                    self.users_df[col] = None
            if 'email' in self.users_df.columns:
                self.users_df['email'] = self.users_df['email'].str.lower().str.strip()
        else:
            self.users_df = pd.DataFrame(columns=user_cols)
            logger.warning("Tabela 'usuarios' está vazia.")

        # Carrega Unidades
        if not units_data.empty:
            self.units_df = units_data
            for col in unit_cols:
                if col not in self.units_df.columns:
                    self.units_df[col] = None
        else:
            self.units_df = pd.DataFrame(columns=unit_cols)
            logger.warning("Tabela 'unidades' está vazia.")

        # Carrega Logs
        if not log_data.empty:
            self.log_df = log_data
            for col in log_cols:
                if col not in self.log_df.columns:
                    self.log_df[col] = None
        else:
            self.log_df = pd.DataFrame(columns=log_cols)
            logger.info("Tabela 'log_auditoria' está vazia.")
        
        self.data_loaded_successfully = True
        
    def get_user_info(self, email: str) -> dict | None:
        """Retorna informações de um usuário pelo email."""
        if self.users_df.empty: 
            return None
        user_info = self.users_df[self.users_df['email'] == email.lower().strip()]
        return user_info.iloc[0].to_dict() if not user_info.empty else None

    def get_unit_info(self, unit_id: str) -> dict | None:
        """Retorna informações de uma unidade pelo ID."""
        if self.units_df.empty: 
            return None
        unit_info = self.units_df[self.units_df['id'] == unit_id]
        return unit_info.iloc[0].to_dict() if not unit_info.empty else None
    
    def get_unit_info_by_name(self, unit_name: str) -> dict | None:
        """Retorna informações de uma unidade pelo nome."""
        if self.units_df.empty: 
            return None
        unit_info = self.units_df[self.units_df['nome_unidade'] == unit_name]
        return unit_info.iloc[0].to_dict() if not unit_info.empty else None

    def get_all_units(self) -> list:
        """Retorna todas as unidades."""
        return self.units_df.to_dict(orient='records') if not self.units_df.empty else []

    def get_audit_logs(self) -> pd.DataFrame:
        """Retorna o DataFrame de logs de auditoria."""
        return self.log_df

    def get_all_users(self) -> list:
        """Retorna todos os usuários."""
        return self.users_df.to_dict(orient='records') if not self.users_df.empty else []

    def add_unit(self, unit_data: dict) -> bool:
        """Adiciona uma nova unidade usando Supabase."""
        try:
            result = self.supabase_ops.insert_row("unidades", unit_data)
            
            if result:
                log_action(
                    action="ADD_UNIT",
                    details={
                        "message": f"Nova unidade '{unit_data['nome_unidade']}' adicionada.",
                        "unit_id": result['id'],
                        "unit_name": unit_data['nome_unidade']
                    }
                )
                
                load_matrix_data.clear()
                logger.info(f"Nova unidade '{unit_data['nome_unidade']}' adicionada. Cache invalidado.")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Falha ao adicionar nova unidade: {e}")
            return False

    def add_user(self, user_data: dict) -> bool:
        """Adiciona um novo usuário usando Supabase."""
        try:
            result = self.supabase_ops.insert_row("usuarios", user_data)
            
            if result:
                log_action(
                    action="ADD_USER",
                    details={
                        "message": f"Novo usuário '{user_data['nome']}' ({user_data['email']}) adicionado.",
                        "email": user_data['email'],
                        "name": user_data['nome'],
                        "role": user_data['role'],
                        "assigned_unit": user_data.get('unidade_associada')
                    }
                )
                
                load_matrix_data.clear()
                logger.info(f"Novo usuário '{user_data['email']}' adicionado. Cache invalidado.")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Falha ao adicionar novo usuário: {e}")
            return False

    def update_user(self, user_id: str, updates: dict) -> bool:
        """Atualiza os dados de um usuário pelo ID."""
        if self.users_df.empty or not user_id:
            return False
        
        try:
            success = self.supabase_ops.update_row("usuarios", user_id, updates)
            
            if success:
                log_action("UPDATE_USER", {"user_id": user_id, "updates": updates})
                load_matrix_data.clear()
                return True
            return False
        except Exception as e:
            logger.error(f"Falha ao atualizar usuário '{user_id}': {e}")
            return False
            
    def remove_user(self, user_id: str) -> bool:
        """Remove um usuário pelo ID."""
        if self.users_df.empty or not user_id: 
            return False
        
        try:
            success = self.supabase_ops.delete_row("usuarios", user_id)
            if success:
                log_action("REMOVE_USER", {"removed_user_id": user_id})
                load_matrix_data.clear()
                return True
            return False
        except Exception as e:
            logger.error(f"Falha ao remover usuário '{user_id}': {e}")
            return False