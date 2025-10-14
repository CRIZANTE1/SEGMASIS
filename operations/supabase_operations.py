import logging
from typing import Any, Dict, List, Optional, TypeVar, Union
import pandas as pd
from supabase import Client, create_client
from managers.supabase_config import get_cached_supabase_client

logger = logging.getLogger(__name__)

# Tipo para dicionários de dados genéricos
DataDict = Dict[str, Any]
SupabaseResponse = Any  # Tipo para respostas do Supabase

def safe_get_data(response: SupabaseResponse) -> List[Dict[str, Any]]:
    """Extrai dados de uma resposta do Supabase de forma segura."""
    if hasattr(response, 'data') and isinstance(response.data, list):
        return response.data
    return []

class SupabaseOperations:
    def __init__(self, unit_id: str | None = None):
        """
        Inicializa as operações do Supabase.
        
        Args:
            unit_id: ID da unidade ou None para operações globais
        """
        self.unit_id = unit_id
        self.client = get_cached_supabase_client()
        
        # Lista de tabelas que não precisam de unit_id
        self.global_tables = ['usuarios', 'unidades', 'log_auditoria']

    def get_table_data(self, table_name: str) -> pd.DataFrame:
        """
        Retrieves all data from a table for the given unit_id and returns it as a pandas DataFrame.
        Se unit_id for None, retorna dados globais (para tabelas como 'usuarios' e 'unidades').
        
        Args:
            table_name: Nome da tabela para buscar os dados
            
        Returns:
            DataFrame com os dados da tabela
        """
        try:
            # Valida o nome da tabela
            if not table_name or not isinstance(table_name, str):
                logger.error(f"Nome da tabela inválido: {table_name}")
                return pd.DataFrame()
            
            # Decide se usa filtro de unit_id
            if table_name in self.global_tables or self.unit_id is None:
                query = self.client.table(table_name).select("*")
            else:
                query = self.client.table(table_name).select("*").eq("unit_id", self.unit_id)
            
            # Executa a query
            try:
                response = query.execute()
            except Exception as e:
                logger.error(f"Erro na query Supabase para {table_name}: {e}")
                return pd.DataFrame()
            
            # Converte para DataFrame usando o safe_get_data
            return pd.DataFrame(safe_get_data(response))
                
        except Exception as e:
            logger.error(f"Erro ao obter dados da tabela {table_name}: {e}")
            return pd.DataFrame()

    def insert_row(self, table_name: str, data: DataDict) -> Optional[DataDict]:
        """
        Inserts a new row into a table and returns the inserted row.
        Adiciona unit_id automaticamente para tabelas que não são globais.
        
        Args:
            table_name: Nome da tabela para inserção
            data: Dicionário com os dados a serem inseridos
            
        Returns:
            Dicionário com os dados inseridos ou None em caso de erro
        """
        try:
            # Só adiciona unit_id se não for tabela global
            if table_name not in self.global_tables and self.unit_id is not None:
                data['unit_id'] = self.unit_id
            
            response = self.client.table(table_name).insert(data).execute()
            inserted_data = safe_get_data(response)
            return inserted_data[0] if inserted_data else None
            
        except Exception as e:
            logger.error(f"Error inserting row into {table_name}: {e}")
            return None

    def insert_batch(self, table_name: str, data: List[DataDict]) -> Optional[List[DataDict]]:
        """
        Inserts a batch of new rows into a table.
        Insere linha por linha para evitar falhas totais em caso de erro parcial.
        
        Args:
            table_name: Nome da tabela para inserção
            data: Lista de dicionários com os dados a serem inseridos
            
        Returns:
            Lista com os dados inseridos com sucesso ou None em caso de erro total
        """
        try:
            successful_inserts: List[DataDict] = []
            failed_inserts: List[DataDict] = []
            
            for row in data:
                try:
                    # Só adiciona unit_id se não for tabela global
                    if table_name not in self.global_tables and self.unit_id is not None:
                        row['unit_id'] = self.unit_id
                    
                    response = self.client.table(table_name).insert(row).execute()
                    inserted_data = safe_get_data(response)
                    if inserted_data:
                        successful_inserts.append(inserted_data[0])
                except Exception as row_error:
                    logger.error(f"Error inserting single row into {table_name}: {row_error}")
                    failed_inserts.append(row)
            
            if failed_inserts:
                logger.warning(
                    f"Batch insert into {table_name}: "
                    f"{len(successful_inserts)} succeeded, {len(failed_inserts)} failed"
                )
            
            return successful_inserts if successful_inserts else None
            
        except Exception as e:
            logger.error(f"Critical error in batch insert for {table_name}: {e}")
            return None

    def update_row(self, table_name: str, row_id: str, data: DataDict) -> Optional[DataDict]:
        """
        Updates a row in a table by its id.
        
        Args:
            table_name: Nome da tabela para atualização
            row_id: ID da linha a ser atualizada
            data: Dicionário com os dados para atualização
            
        Returns:
            Dicionário com os dados atualizados ou None em caso de erro
        """
        try:
            response = self.client.table(table_name).update(data).eq("id", row_id).execute()
            updated_data = safe_get_data(response)
            return updated_data[0] if updated_data else None
        except Exception as e:
            logger.error(f"Error updating row in {table_name}: {e}")
            return None

    def delete_row(self, table_name: str, row_id: str) -> bool:
        """
        Deletes a row from a table by its id.
        
        Args:
            table_name: Nome da tabela
            row_id: ID da linha a ser excluída
            
        Returns:
            True se a exclusão foi bem sucedida, False caso contrário
        """
        try:
            response = self.client.table(table_name).delete().eq("id", row_id).execute()
            return bool(safe_get_data(response))
        except Exception as e:
            logger.error(f"Error deleting row from {table_name}: {e}")
            return False
