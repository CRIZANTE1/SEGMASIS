import streamlit as st
import os
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """
    Retorna um cliente Supabase configurado.
    Busca credenciais de st.secrets (Streamlit Cloud) ou variáveis de ambiente.
    """
    try:
        # Tenta carregar do Streamlit Secrets
        if hasattr(st, 'secrets') and 'supabase' in st.secrets:
            url = st.secrets.supabase.url
            key = st.secrets.supabase.key
            logger.info("✅ Credenciais carregadas do Streamlit Secrets")
        # Fallback para variáveis de ambiente
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            logger.info("✅ Credenciais carregadas das variáveis de ambiente")
        
        if not url or not key:
            # ✅ Mensagem de erro mais detalhada
            error_msg = """
❌ Credenciais do Supabase não encontradas!

Configure no arquivo .streamlit/secrets.toml:

[supabase]
url = "https://seu-projeto.supabase.co"
key = "sua-chave-publica-anon"

Ou configure variáveis de ambiente:
- SUPABASE_URL
- SUPABASE_KEY

Obtenha as credenciais em: https://supabase.com/dashboard > Settings > API
            """
            raise ValueError(error_msg)
        
        logger.info("✅ Cliente Supabase inicializado com sucesso")
        return create_client(url, key)
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar Supabase: {e}")
        raise

# Singleton para reutilizar conexão
_supabase_client = None

def get_cached_supabase_client() -> Client:
    """Retorna uma instância singleton do cliente Supabase."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = get_supabase_client()
    return _supabase_client

# Configurações de Storage
STORAGE_BUCKETS = {
    'documentos': 'segma-sis-documentos',  # ASOs, Treinamentos, etc.
    'fichas_epi': 'segma-sis-epi',
    'docs_empresa': 'segma-sis-docs-empresa',
}

def get_bucket_name(doc_type: str) -> str:
    """Retorna o nome do bucket correto para cada tipo de documento."""
    bucket_map = {
        'aso': STORAGE_BUCKETS['documentos'],
        'treinamento': STORAGE_BUCKETS['documentos'],
        'epi': STORAGE_BUCKETS['fichas_epi'],
        'doc_empresa': STORAGE_BUCKETS['docs_empresa'],
    }
    return bucket_map.get(doc_type.lower(), STORAGE_BUCKETS['documentos'])