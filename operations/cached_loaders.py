import streamlit as st
import pandas as pd
from operations.supabase_operations import SupabaseOperations
import logging
from auth.auth_utils import get_user_email # <-- Importação necessária

logger = logging.getLogger(__name__)

@st.cache_data(ttl=300, show_spinner="Carregando dados da unidade...")
def load_all_unit_data(unit_id: str) -> dict:
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
        
        all_data = {key: supabase_ops.get_table_data(table_name) for key, table_name in data_tables.items()}
        logger.info(f"Dados carregados com sucesso para a unidade: {unit_id}")
        return all_data
    except Exception as e:
        logger.error(f"Erro ao carregar dados da unidade {unit_id}: {e}", exc_info=True)
        st.error(f"Ocorreu um erro ao buscar os dados da unidade: {e}")
        return {}

def _get_empty_consolidated_data() -> dict:
    return {
        "companies": pd.DataFrame(), "employees": pd.DataFrame(), "asos": pd.DataFrame(),
        "trainings": pd.DataFrame(), "epis": pd.DataFrame(), "company_docs": pd.DataFrame(),
        "action_plan": pd.DataFrame()
    }

@st.cache_data(ttl=600, show_spinner="Carregando dados consolidados...")
def load_all_units_consolidated_data() -> dict:
    """
    Carrega dados de TODAS as unidades para a visão global do admin,
    usando o contexto RLS do usuário logado para garantir permissão.
    """
    logger.info("Iniciando carregamento de dados consolidados de todas as unidades...")
    
    try:
        # ✅ CORREÇÃO: Usa uma instância de SupabaseOperations, mas vamos usar um engine com RLS.
        supabase_ops = SupabaseOperations(unit_id=None)
        
        admin_email = get_user_email()
        if not admin_email:
            logger.error("E-mail do admin não fornecido para carregar dados globais.")
            return _get_empty_consolidated_data()

        # Cria um engine específico com as permissões do admin.
        engine_with_rls = supabase_ops.get_engine_with_rls()
        if not engine_with_rls:
            logger.error("Falha ao obter o engine com RLS para o admin.")
            return _get_empty_consolidated_data()

        # 1. Carrega a tabela de unidades
        units_df = pd.read_sql('SELECT * FROM public.unidades', engine_with_rls)
        if units_df.empty:
            logger.warning("Nenhuma unidade encontrada na tabela 'unidades'.")
            return _get_empty_consolidated_data()

        units_df['id'] = units_df['id'].astype(str)
        unit_map = units_df[['id', 'nome_unidade']].rename(columns={'id': 'unit_id', 'nome_unidade': 'unidade'})

        # 2. Carrega todas as tabelas de dados usando a conexão com RLS.
        all_data_tables = {
            "companies": "empresas", "employees": "funcionarios", "asos": "asos",
            "trainings": "treinamentos", "epis": "fichas_epi", 
            "company_docs": "documentos_empresa", "action_plan": "plano_acao"
        }
        all_data = {key: pd.read_sql(f'SELECT * FROM public.{table_name}', engine_with_rls) for key, table_name in all_data_tables.items()}

        consolidated_data = {}
        # 3. Junta os nomes das unidades
        for key, df in all_data.items():
            if df is not None and not df.empty and 'unit_id' in df.columns:
                df['unit_id'] = df['unit_id'].astype(str)
                merged_df = pd.merge(df, unit_map, on='unit_id', how='left')
                consolidated_data[key] = merged_df
            else:
                consolidated_data[key] = df if df is not None else pd.DataFrame()
        
        # 4. Processa datas
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
                        consolidated_data[df_key][col] = pd.to_datetime(consolidated_data[df_key][col], errors='coerce')

        logger.info("✅ Dados consolidados carregados com sucesso usando RLS.")
        return consolidated_data
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados consolidados: {e}", exc_info=True)
        st.error(f"Ocorreu um erro ao buscar os dados globais: {e}")
        return _get_empty_consolidated_data()