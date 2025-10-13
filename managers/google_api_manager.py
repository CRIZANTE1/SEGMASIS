import streamlit as st
import os
import tempfile
import yaml
import logging 
from operations.supabase_storage import SupabaseStorageManager

logger = logging.getLogger('segsisone_app.api_manager')

class GoogleApiManager:
    """
    Classe refatorada para usar Supabase Storage ao invés do Google Drive.
    Mantém a mesma interface para compatibilidade com código legado.
    """
    
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
            doc_type = self._infer_doc_type(filename)
            
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
    
    def _infer_doc_type(self, filename: str) -> str:
        """Infere o tipo de documento pelo nome do arquivo."""
        filename_lower = filename.lower()
        
        if 'aso' in filename_lower:
            return 'aso'
        elif 'training' in filename_lower or 'treinamento' in filename_lower:
            return 'treinamento'
        elif 'epi' in filename_lower:
            return 'epi'
        elif any(doc in filename_lower for doc in ['pgr', 'pcmso', 'ppr', 'pca']):
            return 'doc_empresa'
        
        return 'aso'  # Default
    
    # Métodos legados do Google Drive que não são mais necessários
    # mas mantidos para compatibilidade
    
    def create_folder(self, name: str, parent_folder_id: str = None):
        """
        [LEGACY] Folders não são necessários no Supabase Storage.
        Retorna um ID dummy para compatibilidade.
        """
        logger.warning("create_folder() chamado, mas folders não são usados no Supabase Storage")
        return f"supabase_virtual_folder_{name}"
    
    def move_file_to_folder(self, file_id: str, folder_id: str):
        """[LEGACY] Não implementado no Supabase Storage."""
        logger.warning("move_file_to_folder() não implementado no Supabase Storage")
        pass