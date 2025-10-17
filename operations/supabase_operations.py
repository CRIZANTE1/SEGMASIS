import streamlit as st
import pandas as pd
import logging
from datetime import datetime
from sqlalchemy import text
from managers.supabase_config import get_database_engine

logger = logging.getLogger('segsisone_app.supabase_operations')

class SupabaseOperations:
    _instance = None

    def __new__(cls, unit_id: str = None):
        cache_key = f"_instance_{unit_id}"
        if not hasattr(cls, cache_key) or getattr(cls, cache_key) is None:
            logger.info(f"Criando instância de SupabaseOperations para unit_id: {unit_id}")
            instance = super().__new__(cls)
            setattr(cls, cache_key, instance)
            instance._initialized = False
        return getattr(cls, cache_key)

    def __init__(self, unit_id: str = None):
        if self._initialized:
            return

        self.unit_id = unit_id
        self.global_tables = ['usuarios', 'unidades', 'log_auditoria']

        # ✅ ADICIONAR: Whitelist de tabelas permitidas
        self.allowed_tables = {
            'usuarios', 'unidades', 'log_auditoria', 'empresas',
            'funcionarios', 'asos', 'treinamentos', 'fichas_epi',
            'documentos_empresa', 'plano_acao', 'funcoes',
            'matriz_treinamentos', 'regras_normas', 'regras_treinamentos',
            'solicitacoes_acesso', 'solicitacoes_suporte'
        }
        
        try:
            self.engine = get_database_engine()
            logger.info(f"SupabaseOperations inicializado (unit_id: {unit_id})")
        except Exception as e:
            logger.critical(f"Falha ao inicializar SupabaseOperations: {e}")
            self.engine = None
        
        self._initialized = True

    def get_engine_with_rls(self):
        """
        Retorna um engine com contexto RLS do usuário logado.
        """
        user_email = None
        
        if hasattr(st, 'session_state'):
            user_email = st.session_state.get('user_info', {}).get('email')
            if not user_email:
                user_email = st.session_state.get('authenticated_user_email')
        
        if not user_email:
            logger.error("Tentativa de obter engine RLS sem e-mail de usuário")
            return None
        
        try:
            from managers.supabase_config import get_database_engine
            return get_database_engine(user_email)
        except Exception as e:
            logger.error(f"Erro ao criar engine com RLS: {e}")
            return None

    def get_table_data(self, table_name: str) -> pd.DataFrame:
        # ✅ ADICIONAR: Validação de tabela
        if table_name not in self.allowed_tables:
            logger.error(f"Tentativa de acesso a tabela não autorizada: {table_name}")
            return pd.DataFrame()

        if not self.engine:
            logger.error("Database engine não está disponível")
            return pd.DataFrame()
        
        try:
            if table_name in self.global_tables or self.unit_id is None:
                query = text(f'SELECT * FROM "{table_name}"')
                params = {}
            else:
                query = text(f'SELECT * FROM "{table_name}" WHERE unit_id = :unit_id')
                params = {"unit_id": self.unit_id}
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=params)
            
            return df
                
        except Exception as e:
            logger.error(f"Erro ao carregar '{table_name}': {e}")
            return pd.DataFrame()

    def insert_row(self, table_name: str, data: dict) -> str | None:
        """Insere uma linha e retorna APENAS O ID do registro inserido como string."""
        if not self.engine:
            return None
        
        try:
            if table_name not in self.global_tables and self.unit_id is not None:
                data['unit_id'] = self.unit_id
            
            columns = ', '.join([f'"{k}"' for k in data.keys()])
            placeholders = ', '.join([f':{k}' for k in data.keys()])
            query = text(f'''
                INSERT INTO "{table_name}" ({columns})
                VALUES ({placeholders})
                RETURNING id
            ''')
            
            with self.engine.connect() as conn:
                result = conn.execute(query, data)
                conn.commit()
                
                row = result.fetchone()
                if row and row[0]:
                    # Retorna o ID como string
                    return str(row[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao inserir em '{table_name}': {e}")
            return None

    def insert_batch(self, table_name: str, data_list: list[dict]) -> list[dict] | None:
        successful_inserts = []
        
        for row_data in data_list:
            result = self.insert_row(table_name, row_data)
            if result:
                successful_inserts.append(result)
        
        return successful_inserts if successful_inserts else None

    def update_row(self, table_name: str, row_id: str, data: dict) -> dict | None:
        if not self.engine or not data:
            return None
        
        try:
            set_clause = ', '.join([f'"{k}" = :{k}' for k in data.keys()])
            query = text(f'''
                UPDATE "{table_name}"
                SET {set_clause}
                WHERE id = :id
                RETURNING *
            ''')
            
            params = {**data, 'id': row_id}
            
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                conn.commit()
                
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao atualizar '{table_name}': {e}")
            return None

    def delete_row(self, table_name: str, row_id: str) -> bool:
        if not self.engine:
            return False
        
        try:
            query = text(f'DELETE FROM "{table_name}" WHERE id = :id')
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {'id': row_id})
                conn.commit()
                
                return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Erro ao deletar de '{table_name}': {e}")
            return False

    def get_by_field(self, table_name: str, field: str, value) -> pd.DataFrame:
        if not self.engine:
            return pd.DataFrame()

        try:
            query = text(f'SELECT * FROM "{table_name}" WHERE "{field}" = :value')

            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={'value': value})

            return df
        except Exception as e:
            logger.error(f"Erro ao buscar em '{table_name}': {e}")
            return pd.DataFrame()

    def get_by_id(self, table_name: str, row_id: str) -> pd.DataFrame:
        """
        Busca um registro por ID.

        Args:
            table_name: Nome da tabela
            row_id: ID do registro

        Returns:
            DataFrame com o registro encontrado ou DataFrame vazio
        """
        return self.get_by_field(table_name, 'id', row_id)

    def get_by_field_no_rls(self, table_name: str, field: str, value) -> pd.DataFrame:
        return self.get_by_field(table_name, field, value)
