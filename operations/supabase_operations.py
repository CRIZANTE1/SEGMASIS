import logging
import pandas as pd
from operations.supabase_config import get_cached_supabase_client

logger = logging.getLogger(__name__)

class SupabaseOperations:
    def __init__(self, unit_id: str):
        self.unit_id = unit_id
        self.client = get_cached_supabase_client()

    def get_table_data(self, table_name: str) -> pd.DataFrame:
        """
        Retrieves all data from a table for the given unit_id and returns it as a pandas DataFrame.
        """
        try:
            response = self.client.table(table_name).select("*").eq("unit_id", self.unit_id).execute()
            df = pd.DataFrame(response.data)
            return df
        except Exception as e:
            logger.error(f"Error getting table data for {table_name}: {e}")
            return pd.DataFrame()

    def insert_row(self, table_name: str, data: dict) -> dict:
        """
        Inserts a new row into a table and returns the inserted row.
        """
        try:
            data['unit_id'] = self.unit_id
            response = self.client.table(table_name).insert(data).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error inserting row into {table_name}: {e}")
            return None

    def insert_batch(self, table_name: str, data: list[dict]):
        """
        Inserts a batch of new rows into a table.
        """
        try:
            for row in data:
                row['unit_id'] = self.unit_id
            response = self.client.table(table_name).insert(data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error inserting batch into {table_name}: {e}")
            return None

    def update_row(self, table_name: str, row_id: str, data: dict) -> bool:
        """
        Updates a row in a table by its id.
        """
        try:
            self.client.table(table_name).update(data).eq("id", row_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating row in {table_name}: {e}")
            return False

    def delete_row(self, table_name: str, row_id: str) -> bool:
        """
        Deletes a row from a table by its id.
        """
        try:
            self.client.table(table_name).delete().eq("id", row_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting row from {table_name}: {e}")
            return False
