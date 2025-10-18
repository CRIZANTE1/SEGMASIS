import streamlit as st
import os
import tempfile
import yaml
import logging 
from managers.supabase_storage import SupabaseStorageManager

logger = logging.getLogger('segsisone_app.api_manager')

class GoogleApiManager:
    """
    DEPRECATED: Esta classe está sendo gradualmente removida.
    Use SupabaseStorageManager para operações de storage.
    Mantida apenas para compatibilidade temporária.
    """
    
    @staticmethod
    def _infer_doc_type(filename: str) -> str:
        """
        Infere o tipo de documento pelo nome do arquivo.
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            Tipo do documento ('aso', 'treinamento', 'epi', 'doc_empresa')
        """
        if not filename or not isinstance(filename, str):
            return 'aso'  # Default
        
        filename_lower = filename.lower()
        
        # Prioridade de verificação
        if 'aso' in filename_lower:
            return 'aso'
        elif 'training' in filename_lower or 'treinamento' in filename_lower:
            return 'treinamento'
        elif 'epi' in filename_lower:
            return 'epi'
        elif any(doc in filename_lower for doc in ['pgr', 'pcmso', 'ppr', 'pca', 'doc_empresa']):
            return 'doc_empresa'
        
        # Default: ASO
        return 'aso'

    def __init__(self):
        """Inicializa o gerenciador usando Supabase Storage."""
        self.storage_manager = SupabaseStorageManager()
        logger.info("GoogleApiManager inicializado (usando Supabase Storage)")
    
    def upload_file(self, unit_id: str, arquivo, novo_nome: str = None) -> str | None:
        """
        Faz upload de um arquivo para o Supabase Storage.
        
        Args:
            unit_id: ID da unidade (anteriormente folder_id)
            arquivo: Objeto de arquivo do Streamlit
            novo_nome: Nome customizado para o arquivo
            
        Returns:
            URL do arquivo ou None em caso de erro
        """
        if not unit_id:
            st.error("Erro: ID da unidade não foi fornecido para o upload.")
            return None
        
        try:
            # Atualiza o unit_id do storage manager
            self.storage_manager.unit_id = unit_id
            
            # Determina o nome do arquivo
            filename = novo_nome if novo_nome else arquivo.name
            
            # Infere o tipo de documento
            doc_type = GoogleApiManager._infer_doc_type(filename)
            
            # Faz o upload
            result = self.storage_manager.upload_file(
                file_content=arquivo.getvalue(),
                filename=filename,
                doc_type=doc_type,
                content_type=arquivo.type
            )
            
            if result:
                return result['url']
            
            return None
            
        except Exception as e:
            st.error(f"Erro ao fazer upload do arquivo: {str(e)}")
            logger.error(f"Erro no upload: {e}", exc_info=True)
            return None
    
    def delete_file_by_url(self, file_url: str) -> bool:
        """
        Deleta um arquivo do Supabase Storage usando sua URL.
        
        Args:
            file_url: URL do arquivo
            
        Returns:
            True se deletado com sucesso, False caso contrário
        """
        if not file_url or not isinstance(file_url, str):
            logger.warning("URL inválida fornecida para exclusão")
            return False
        
        return self.storage_manager.delete_file_by_url(file_url)
    

    
    # Métodos legados do Google Drive que não são mais necessários
    # mas mantidos para compatibilidade
    
    def create_folder(self, name: str, parent_folder_id: str = None):
        """
        [DEPRECATED] Folders não são mais usados com Supabase Storage.
        """
        logger.error(f"create_folder() foi chamado para '{name}'. Este método está DEPRECATED.")
        raise DeprecationWarning("Método create_folder() foi removido. Use Supabase Storage.")

    def move_file_to_folder(self, file_id: str, folder_id: str):
        """
        [DEPRECATED] Não implementado no Supabase Storage.
        """
        logger.error(f"move_file_to_folder() foi chamado. Este método está DEPRECATED.")
        raise DeprecationWarning("Método move_file_to_folder() foi removido. Use Supabase Storage.")