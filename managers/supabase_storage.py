import streamlit as st
import logging
import os
import tempfile
from datetime import datetime, timedelta
from managers.supabase_config import get_cached_supabase_client, get_bucket_name
from supabase import StorageException

logger = logging.getLogger('segsisone_app.supabase_storage')

class SupabaseStorageManager:
    """Gerencia uploads e downloads de arquivos no Supabase Storage."""
    
    def __init__(self, unit_id: str = None):
        """
        Inicializa o gerenciador de storage.

        Args:
            unit_id: ID da unidade operacional (usado para organizar arquivos)
        """
        try:
            self.supabase = get_cached_supabase_client()
            if not self.supabase:
                raise ValueError("Cliente Supabase não inicializado")
        except Exception as e:
            logger.error(f"Falha ao inicializar SupabaseStorageManager: {e}")
            raise RuntimeError(f"Supabase não disponível: {e}")

        self.unit_id = unit_id
        logger.info(f"SupabaseStorageManager inicializado para unit_id: {unit_id}")
    
    def _get_file_path(self, doc_type: str, filename: str) -> str:
        """
        Gera o caminho do arquivo no bucket.
        Estrutura: unit_id/doc_type/YYYY-MM/filename
        """
        now = datetime.now()
        year_month = now.strftime("%Y-%m")
        
        if self.unit_id:
            return f"{self.unit_id}/{doc_type}/{year_month}/{filename}"
        else:
            return f"global/{doc_type}/{year_month}/{filename}"
    
    def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        doc_type: str,
        content_type: str = "application/pdf"
    ) -> dict | None:
        """
        Faz upload de um arquivo para o Supabase Storage.
        
        Args:
            file_content: Conteúdo do arquivo em bytes
            filename: Nome do arquivo
            doc_type: Tipo do documento (aso, treinamento, epi, doc_empresa)
            content_type: MIME type do arquivo
            
        Returns:
            dict com 'path' e 'url' do arquivo, ou None em caso de erro
        """
        try:
            bucket_name = get_bucket_name(doc_type)
            file_path = self._get_file_path(doc_type, filename)
            
            logger.info(f"📤 Iniciando upload: {filename} para {bucket_name}/{file_path}")
            
            # Upload do arquivo
            response = self.supabase.storage.from_(bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": "false"  # Não sobrescreve se já existir
                }
            )
            
            if response:
                # Gera URL pública ou assinada
                public_url = self._get_file_url(bucket_name, file_path)
                
                logger.info(f"✅ Upload bem-sucedido: {file_path}")
                
                return {
                    'path': file_path,
                    'url': public_url,
                    'bucket': bucket_name
                }
            
            return None
            
        except StorageException as e:
            logger.error(f"❌ Erro de Storage ao fazer upload: {e}")
            st.error(f"Erro ao fazer upload do arquivo: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado no upload: {e}", exc_info=True)
            st.error(f"Erro inesperado ao fazer upload: {e}")
            return None
    
    def _get_file_url(self, bucket_name: str, file_path: str, expires_in: int = 3600) -> str:
        """
        Gera URL assinada para acesso ao arquivo.
        
        Args:
            bucket_name: Nome do bucket
            file_path: Caminho do arquivo no bucket
            expires_in: Tempo de expiração em segundos (padrão: 1 hora)
            
        Returns:
            URL assinada do arquivo
        """
        try:
            public_url = self.supabase.storage.from_(bucket_name).get_public_url(file_path)
            if public_url and isinstance(public_url, str):
                return public_url
        except Exception as e:
            logger.warning(f"Bucket não é público, gerando URL assinada: {e}")

        # Sempre gera URL assinada como fallback
        try:
            signed_url = self.supabase.storage.from_(bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            return signed_url.get('signedURL', '')
        except Exception as e:
            logger.error(f"❌ Erro ao gerar URL do arquivo: {e}")
            return ""
    
    def delete_file(self, file_path: str, bucket_name: str = None) -> bool:
        """
        Deleta um arquivo do Supabase Storage.
        
        Args:
            file_path: Caminho completo do arquivo no bucket
            bucket_name: Nome do bucket (opcional, será inferido se não fornecido)
            
        Returns:
            True se deletado com sucesso, False caso contrário
        """
        try:
            if not bucket_name:
                # Tenta inferir o bucket pelo caminho
                if 'epi' in file_path.lower():
                    bucket_name = get_bucket_name('epi')
                elif 'doc_empresa' in file_path.lower():
                    bucket_name = get_bucket_name('doc_empresa')
                else:
                    bucket_name = get_bucket_name('aso')
            
            logger.info(f"🗑️ Deletando arquivo: {bucket_name}/{file_path}")
            
            response = self.supabase.storage.from_(bucket_name).remove([file_path])
            
            if response:
                logger.info(f"✅ Arquivo deletado com sucesso: {file_path}")
                return True
            
            return False
            
        except StorageException as e:
            logger.error(f"❌ Erro ao deletar arquivo: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao deletar: {e}")
            return False
    
    def delete_file_by_url(self, file_url: str) -> bool:
        """
        Deleta um arquivo usando sua URL.
        Extrai o caminho da URL e deleta o arquivo.
        
        Args:
            file_url: URL completa do arquivo no Supabase Storage
            
        Returns:
            True se deletado com sucesso, False caso contrário
        """
        try:
            # Extrai o caminho do arquivo da URL
            # Formato: https://[project].supabase.co/storage/v1/object/public/[bucket]/[path]
            if not file_url or not isinstance(file_url, str):
                logger.warning("URL inválida fornecida para exclusão")
                return False
            
            # Parse da URL
            parts = file_url.split('/storage/v1/object/')
            if len(parts) < 2:
                logger.error(f"URL em formato inválido: {file_url}")
                return False
            
            # Remove 'public/' ou 'sign/' do início
            path_with_bucket = parts[1].replace('public/', '').replace('sign/', '')
            
            # Separa bucket e path
            path_parts = path_with_bucket.split('/', 1)
            if len(path_parts) < 2:
                logger.error(f"Não foi possível extrair bucket e path da URL: {file_url}")
                return False
            
            bucket_name = path_parts[0]
            file_path = path_parts[1]
            
            return self.delete_file(file_path, bucket_name)
            
        except Exception as e:
            logger.error(f"❌ Erro ao deletar arquivo por URL: {e}")
            return False
    
    def download_file(self, file_path: str, bucket_name: str = None) -> bytes | None:
        """
        Baixa um arquivo do Supabase Storage.
        
        Args:
            file_path: Caminho do arquivo no bucket
            bucket_name: Nome do bucket (opcional)
            
        Returns:
            Conteúdo do arquivo em bytes, ou None em caso de erro
        """
        try:
            if not bucket_name:
                bucket_name = get_bucket_name('aso')  # Default
            
            logger.info(f"📥 Baixando arquivo: {bucket_name}/{file_path}")
            
            response = self.supabase.storage.from_(bucket_name).download(file_path)
            
            if response:
                logger.info(f"✅ Download bem-sucedido: {file_path}")
                return response
            
            return None
            
        except StorageException as e:
            logger.error(f"❌ Erro ao baixar arquivo: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado no download: {e}")
            return None
    
    def list_files(self, folder_path: str, bucket_name: str = None) -> list:
        """
        Lista arquivos em uma pasta do bucket.
        
        Args:
            folder_path: Caminho da pasta
            bucket_name: Nome do bucket (opcional)
            
        Returns:
            Lista de dicionários com informações dos arquivos
        """
        try:
            if not bucket_name:
                bucket_name = get_bucket_name('aso')
            
            logger.info(f"📋 Listando arquivos em: {bucket_name}/{folder_path}")
            
            response = self.supabase.storage.from_(bucket_name).list(folder_path)
            
            if response:
                logger.info(f"✅ {len(response)} arquivo(s) encontrado(s)")
                return response
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar arquivos: {e}")
            return []
    
    def get_file_metadata(self, file_path: str, bucket_name: str = None) -> dict | None:
        """
        Obtém metadados de um arquivo.
        
        Args:
            file_path: Caminho do arquivo
            bucket_name: Nome do bucket (opcional)
            
        Returns:
            Dicionário com metadados ou None
        """
        try:
            if not bucket_name:
                bucket_name = get_bucket_name('aso')
            
            # Lista o arquivo específico para obter metadados
            folder = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            files = self.list_files(folder, bucket_name)
            
            for file in files:
                if file.get('name') == filename:
                    return file
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadados: {e}")
            return None


class SupabaseUploader:
    """Classe de compatibilidade com o código legado (GoogleDriveUploader)."""
    
    def __init__(self, unit_id: str):
        """
        Inicializa o uploader para uma unidade específica.
        
        Args:
            unit_id: O ID da unidade (equivalente ao folder_id do Google Drive)
        """
        self.unit_id = unit_id
        self.storage_manager = SupabaseStorageManager(unit_id)
        logger.info(f"SupabaseUploader inicializado para unidade: {unit_id}")
    
    def upload_file(self, arquivo, novo_nome: str = None) -> str | None:
        """
        Faz upload do arquivo para o Supabase Storage.
        Interface compatível com GoogleDriveUploader.
        
        Args:
            arquivo: Objeto de arquivo do Streamlit (UploadedFile)
            novo_nome: Nome customizado para o arquivo
            
        Returns:
            URL do arquivo ou None em caso de erro
        """
        progress_bar = st.progress(0, text="Preparando upload...")
        
        try:
            progress_bar.progress(10, text="Lendo arquivo...")
            
            # Lê o conteúdo do arquivo
            file_content = arquivo.getvalue()
            filename = novo_nome if novo_nome else arquivo.name
            
            progress_bar.progress(30, text="Determinando tipo de documento...")
            
            # Determina o tipo de documento pelo nome
            doc_type = self._infer_doc_type(filename)
            
            progress_bar.progress(50, text="Enviando para o servidor...")
            
            # Faz o upload
            result = self.storage_manager.upload_file(
                file_content=file_content,
                filename=filename,
                doc_type=doc_type,
                content_type=arquivo.type
            )
            
            progress_bar.progress(100, text="Upload concluído!")
            
            if result:
                st.success("✅ Upload concluído com sucesso!")
                return result['url']
            
            return None
            
        except Exception as e:
            st.error(f"❌ Erro ao fazer upload: {str(e)}")
            logger.error(f"Erro no upload: {e}", exc_info=True)
            return None
        finally:
            progress_bar.empty()
    
    def delete_file_by_url(self, file_url: str) -> bool:
        """
        Deleta um arquivo usando sua URL.
        Interface compatível com GoogleDriveUploader.
        
        Args:
            file_url: URL do arquivo
            
        Returns:
            True se deletado com sucesso, False caso contrário
        """
        if not file_url:
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