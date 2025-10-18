import streamlit as st
import pandas as pd
from operations.supabase_operations import SupabaseOperations
import logging
from auth.auth_utils import get_user_email
from typing import Dict, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# ✅ MUDANÇA: TTL reduzido e estratificado
@st.cache_data(
    ttl=180,  # 3 minutos (era 5 min)
    show_spinner="Carregando dados da unidade...",
    max_entries=50  # Limita memória
)
def load_all_unit_data(unit_id: str) -> Dict[str, Any]:
    logger.info(f"Carregando todos os dados para a unidade: {unit_id}")
    try:
        supabase_ops = SupabaseOperations(unit_id=unit_id)
        data_tables = {
            "companies": "empresas",
            "employees": "funcionarios",
            "asos": "asos",
            "trainings": "treinamentos",
            "epis": "fichas_epi",
            "company_docs": "documentos_empresa",
            "action_plan": "plano_acao"
        }
        
        all_data = {
            key: supabase_ops.get_table_data(table_name) 
            for key, table_name in data_tables.items()
        }
        
        logger.info(f"Dados carregados com sucesso para a unidade: {unit_id}")
        return all_data
    except Exception as e:
        logger.error(f"Erro ao carregar dados da unidade {unit_id}: {e}", exc_info=True)
        st.error(f"Ocorreu um erro ao buscar os dados da unidade: {e}")
        return {}

# ✅ MUDANÇA: TTL reduzido para dados globais
@st.cache_data(
    ttl=300,  # 5 minutos (era 10 min)
    show_spinner="Carregando dados globais...",
    max_entries=10
)
def load_matrix_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega dados globais da matriz (usuários, unidades, logs e solicitações)."""
    logger.info("Carregando dados da matriz global...")
    try:
        supabase_ops = SupabaseOperations(unit_id=None)
        
        users_data = supabase_ops.get_table_data("usuarios")
        units_data = supabase_ops.get_table_data("unidades")
        log_data = supabase_ops.get_table_data("log_auditoria")
        requests_data = supabase_ops.get_table_data("solicitacoes_acesso")
        
        logger.info("Dados da matriz carregados com sucesso.")
        return users_data, units_data, log_data, requests_data
        
    except Exception as e:
        logger.critical(f"Falha ao carregar dados da matriz: {e}", exc_info=True)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ✅ MUDANÇA: TTL maior para regras (mudam raramente)
@st.cache_data(
    ttl=1800,  # 30 minutos (era 1 hora)
    show_spinner="Carregando regras de conformidade...",
    max_entries=20
)
def load_nr_rules_data() -> pd.DataFrame:
    """Carrega regras de NRs - dados que mudam raramente."""
    logger.info("Carregando todas as regras de NRs do banco de dados...")
    try:
        supabase_ops = SupabaseOperations(unit_id=None)
        
        query = """
        SELECT
            n.id AS norma_id,
            n.norma,
            CAST(n.unit_id AS TEXT) AS unit_id,
            n.is_active AS norma_is_active,
            t.id AS treinamento_id,
            t.titulo,
            t.carga_horaria_minima_horas,
            t.reciclagem_anos,
            t.reciclagem_carga_horaria_horas,
            t.cargas_por_risco,
            t.is_active AS treinamento_is_active
        FROM public.regras_normas AS n
        JOIN public.regras_treinamentos AS t ON n.id = t.id_norma;
        """
        
        df = pd.read_sql(query, supabase_ops.engine)
        logger.info(f"{len(df)} regras de treinamento carregadas com sucesso.")
        return df
    except Exception as e:
        logger.error(f"Erro ao carregar regras de NRs: {e}", exc_info=True)
        st.error("Falha crítica ao carregar as regras de conformidade do sistema.")
        return pd.DataFrame()

# ✅ NOVO: Cache seletivo para dados pesados
@st.cache_data(
    ttl=600,  # 10 minutos
    show_spinner="Carregando dados consolidados...",
    max_entries=5  # Poucos admins
)
def load_all_units_consolidated_data(admin_email: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """Cache mais longo para visão global (acesso menos frequente)."""
    logger.info("Iniciando carregamento de dados consolidados de todas as unidades...")
    
    # ... código existente mantido
    try:
        supabase_ops = SupabaseOperations(unit_id=None)
        
        if not admin_email:
            from auth.auth_utils import get_user_email
            admin_email = get_user_email()
            
        if not admin_email:
            logger.error("E-mail do admin não fornecido para carregar dados globais.")
            return _get_empty_consolidated_data()

        engine_with_rls = supabase_ops.get_engine_with_rls()
        if not engine_with_rls:
            logger.error("Falha ao obter o engine com RLS para o admin.")
            return _get_empty_consolidated_data()

        try:
            units_df = pd.read_sql('SELECT * FROM public.unidades', engine_with_rls)
        except Exception as e:
            logger.error(f"Erro ao ler tabela unidades: {e}")
            return _get_empty_consolidated_data()

        if units_df.empty:
            logger.warning("Nenhuma unidade encontrada na tabela 'unidades'.")
            return _get_empty_consolidated_data()

        units_df['id'] = units_df['id'].astype(str)
        unit_map = units_df[['id', 'nome_unidade']].rename(
            columns={'id': 'unit_id', 'nome_unidade': 'unidade'}
        )

        all_data_tables = {
            "companies": "empresas",
            "employees": "funcionarios",
            "asos": "asos",
            "trainings": "treinamentos",
            "epis": "fichas_epi",
            "company_docs": "documentos_empresa",
            "action_plan": "plano_acao"
        }

        all_data = {}
        for key, table_name in all_data_tables.items():
            try:
                all_data[key] = pd.read_sql(
                    f'SELECT * FROM public.{table_name}',
                    engine_with_rls
                )
            except Exception as e:
                logger.error(f"Erro ao ler tabela {table_name}: {e}")
                all_data[key] = pd.DataFrame()

        consolidated_data = {}
        for key, df in all_data.items():
            if df is not None and not df.empty and 'unit_id' in df.columns:
                df['unit_id'] = df['unit_id'].astype(str)
                merged_df = pd.merge(df, unit_map, on='unit_id', how='left')
                consolidated_data[key] = merged_df
            else:
                consolidated_data[key] = df if df is not None else pd.DataFrame()
        
        date_columns_map = {
            'asos': ['data_aso', 'vencimento'],
            'trainings': ['data', 'vencimento'],
            'company_docs': ['data_emissao', 'vencimento'],
            'employees': ['data_admissao'],
        }
        
        for df_key, date_cols in date_columns_map.items():
            if df_key in consolidated_data and not consolidated_data[df_key].empty:
                for col in date_cols:
                    if col in consolidated_data[df_key].columns:
                        consolidated_data[df_key][col] = pd.to_datetime(
                            consolidated_data[df_key][col],
                            errors='coerce'
                        )

        logger.info("✅ Dados consolidados carregados com sucesso usando RLS.")
        return consolidated_data

    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados consolidados: {e}", exc_info=True)
        st.error(f"Ocorreu um erro ao buscar os dados globais: {e}")
        return _get_empty_consolidated_data()

def _get_empty_consolidated_data() -> Dict[str, pd.DataFrame]:
    return {
        "companies": pd.DataFrame(),
        "employees": pd.DataFrame(),
        "asos": pd.DataFrame(),
        "trainings": pd.DataFrame(),
        "epis": pd.DataFrame(),
        "company_docs": pd.DataFrame(),
        "action_plan": pd.DataFrame()
    }
