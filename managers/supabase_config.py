import os
import streamlit as st
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('segsisone_app.supabase_config')

def get_database_connection_string() -> str:
    """Retorna a connection string do PostgreSQL"""
    db_connection_string = None
    
    try:
        if hasattr(st, 'secrets') and 'database' in st.secrets:
            logger.info("Lendo connection string de st.secrets")
            db_connection_string = st.secrets.database.get("connection_string")
    except Exception as e:
        logger.warning(f"Não foi possível ler de st.secrets: {e}")
    
    if not db_connection_string:
        logger.info("Lendo connection string de variáveis de ambiente")
        db_connection_string = os.getenv("DATABASE_CONNECTION_STRING")
    
    if not db_connection_string:
        error_msg = """
❌ Connection string não encontrada!

Configure no arquivo .streamlit/secrets.toml:

[database]
connection_string = "postgresql://postgres.xxxxx:senha@host:6543/postgres"

Ou configure a variável de ambiente:
- DATABASE_CONNECTION_STRING
        """
        logger.critical(error_msg)
        raise ValueError(error_msg)
    
    return db_connection_string

def get_supabase_credentials() -> tuple[str, str]:
    """Retorna as credenciais do Supabase (para Storage)"""
    supabase_url = None
    supabase_key = None
    
    try:
        if hasattr(st, 'secrets') and 'supabase' in st.secrets:
            logger.info("Lendo configurações do Supabase de st.secrets")
            supabase_url = st.secrets.supabase.get("url")
            supabase_key = st.secrets.supabase.get("key")
    except Exception as e:
        logger.warning(f"Não foi possível ler de st.secrets: {e}")
    
    if not supabase_url or not supabase_key:
        logger.info("Lendo configurações do Supabase de variáveis de ambiente")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.warning("Credenciais do Supabase não encontradas (Storage desabilitado)")
        return None, None
    
    return supabase_url, supabase_key

def get_database_engine(user_email: str = None):
    """
    Retorna um SQLAlchemy engine configurado.
    Se user_email for fornecido, configura o contexto RLS.
    """
    connection_string = get_database_connection_string()
    
    try:
        connect_args = {
            "connect_timeout": 10,
            "options": "-c timezone=America/Sao_Paulo"
        }
        
        # Adiciona configuração de contexto de usuário para RLS
        if user_email:
            safe_email = user_email.replace("'", "''")
            connect_args["options"] += f" -c app.current_user_email='{safe_email}'"
        
        engine = create_engine(
            connection_string,
            poolclass=NullPool,
            echo=False,
            connect_args=connect_args
        )
        logger.info(f"Database engine criado{' com contexto RLS' if user_email else ''}")
        return engine
    except Exception as e:
        logger.critical(f"Erro ao criar database engine: {e}")
        raise

def get_supabase_client() -> Client:
    """Retorna um cliente Supabase configurado (apenas para Storage)"""
    supabase_url, supabase_key = get_supabase_credentials()
    
    if not supabase_url or not supabase_key:
        logger.warning("Cliente Supabase não disponível")
        return None
    
    try:
        client = create_client(supabase_url, supabase_key)
        logger.info("Cliente Supabase criado com sucesso (Storage)")
        return client
    except Exception as e:
        logger.error(f"Erro ao criar cliente Supabase: {e}")
        return None

def get_cached_supabase_client() -> Client:
    """Retorna instância singleton do cliente"""
    return get_supabase_client()

# Nomes dos buckets no Supabase Storage
STORAGE_BUCKETS = {
    'documentos': 'segma-sis-documentos',
    'fichas_epi': 'segma-sis-epi',
    'docs_empresa': 'segma-sis-docs-empresa',
}

def get_bucket_name(doc_type: str) -> str:
    """Retorna o nome do bucket correto para cada tipo de documento"""
    bucket_map = {
        'aso': STORAGE_BUCKETS['documentos'],
        'treinamento': STORAGE_BUCKETS['documentos'],
        'epi': STORAGE_BUCKETS['fichas_epi'],
        'doc_empresa': STORAGE_BUCKETS['docs_empresa'],
    }
    return bucket_map.get(doc_type.lower(), STORAGE_BUCKETS['documentos'])