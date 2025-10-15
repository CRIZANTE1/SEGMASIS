import streamlit as st
import pandas as pd
from operations.supabase_operations import SupabaseOperations
import logging

logger = logging.getLogger(__name__)

@st.cache_data(ttl=600, show_spinner="Carregando dados da unidade...")
def load_all_unit_data(unit_id: str) -> dict:
    """
    Carrega TODOS os dados de uma unidade específica.
    Cache de 10 minutos (600 segundos).
    """
    if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
        logger.warning("load_all_unit_data chamado sem unit_id válido")
        return {
            'companies': pd.DataFrame(), 'employees': pd.DataFrame(), 'asos': pd.DataFrame(),
            'trainings': pd.DataFrame(), 'epis': pd.DataFrame(), 'company_docs': pd.DataFrame(),
            'action_plan': pd.DataFrame()
        }
    
    logger.info(f"Carregando dados para unit_id: ...{str(unit_id)[-6:]}")
    
    try:
        supabase_ops = SupabaseOperations(unit_id)
        if not supabase_ops.engine:
            raise RuntimeError("Engine do banco de dados não disponível")

        data = {
            'companies': supabase_ops.get_table_data("empresas"),
            'employees': supabase_ops.get_table_data("funcionarios"),
            'asos': supabase_ops.get_table_data("asos"),
            'trainings': supabase_ops.get_table_data("treinamentos"),
            'epis': supabase_ops.get_table_data("fichas_epi"),
            'company_docs': supabase_ops.get_table_data("documentos_empresa"),
            'action_plan': supabase_ops.get_table_data("plano_acao")
        }
        
        for key in data.keys():
            if data[key] is None:
                logger.warning(f"Tabela '{key}' retornou None para unit_id {unit_id}, usando DataFrame vazio")
                data[key] = pd.DataFrame()
        
        # Processa datas
        date_columns_map = {
            'asos': ['data_aso', 'vencimento'],
            'trainings': ['data', 'vencimento'],
            'company_docs': ['data_emissao', 'vencimento'],
            'employees': ['data_admissao'],
            'epis': ['data_entrega'],
            'action_plan': ['data_criacao', 'data_conclusao', 'prazo']
        }
        
        for df_name, date_cols in date_columns_map.items():
            if data[df_name] is not None and not data[df_name].empty:
                for col in date_cols:
                    if col in data[df_name].columns:
                        try:
                            data[df_name][col] = pd.to_datetime(data[df_name][col], errors='coerce')
                        except Exception as e:
                            logger.error(f"Erro ao processar datas em '{df_name}.{col}': {e}")
        
        logger.info(f"✅ Dados carregados com sucesso para unit_id: ...{str(unit_id)[-6:]}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Erro crítico ao carregar dados da unidade {unit_id}: {e}", exc_info=True)
        return {
            'companies': pd.DataFrame(), 'employees': pd.DataFrame(), 'asos': pd.DataFrame(),
            'trainings': pd.DataFrame(), 'epis': pd.DataFrame(), 'company_docs': pd.DataFrame(),
            'action_plan': pd.DataFrame()
        }

def _get_empty_consolidated_data() -> dict:
    """Retorna estrutura vazia de dados consolidados"""
    return {
        'companies': pd.DataFrame(), 'employees': pd.DataFrame(), 'asos': pd.DataFrame(),
        'trainings': pd.DataFrame(), 'epis': pd.DataFrame(), 'company_docs': pd.DataFrame(),
        'action_plan': pd.DataFrame()
    }

@st.cache_data(ttl=600, show_spinner="Carregando dados consolidados...")
def load_all_units_consolidated_data() -> dict:
    """
    Carrega dados de TODAS as unidades para a visão global do admin de forma eficiente.
    """
    logger.info("Iniciando carregamento de dados consolidados de todas as unidades...")
    
    try:
        # Usa SupabaseOperations SEM unit_id para ter acesso global
        supabase_ops = SupabaseOperations(unit_id=None)
        if not supabase_ops.engine:
            raise RuntimeError("Engine do banco de dados não disponível para acesso global.")

        # 1. Carrega a tabela de unidades para mapeamento
        units_df = supabase_ops.get_table_data("unidades")
        if units_df.empty:
            logger.warning("Nenhuma unidade encontrada na tabela 'unidades'.")
            return _get_empty_consolidated_data()

        # Garante que o ID da unidade seja string para o merge
        units_df['id'] = units_df['id'].astype(str)
        unit_map = units_df[['id', 'nome_unidade']].rename(columns={'id': 'unit_id', 'nome_unidade': 'unidade'})

        # 2. Carrega todas as tabelas de dados de uma vez, sem filtro de unidade
        all_data_tables = [
            "empresas", "funcionarios", "asos", "treinamentos", 
            "fichas_epi", "documentos_empresa", "plano_acao"
        ]
        data_map_keys = {
            "empresas": "companies", "funcionarios": "employees", "asos": "asos",
            "treinamentos": "trainings", "fichas_epi": "epis", 
            "documentos_empresa": "company_docs", "plano_acao": "action_plan"
        }

        all_data = {data_map_keys[table]: supabase_ops.get_table_data(table) for table in all_data_tables}

        consolidated_data = {}
        # 3. Para cada tabela, faz o merge (join) com os nomes das unidades
        for key, df in all_data.items():
            if df is not None and not df.empty and 'unit_id' in df.columns:
                df['unit_id'] = df['unit_id'].astype(str)
                merged_df = pd.merge(df, unit_map, on='unit_id', how='left')
                consolidated_data[key] = merged_df
            else:
                consolidated_data[key] = df if df is not None else pd.DataFrame()
        
        # 4. Processa datas em todos os DataFrames consolidados
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

        logger.info("✅ Dados consolidados carregados e mesclados com sucesso.")
        return consolidated_data
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados consolidados: {e}", exc_info=True)
        return _get_empty_consolidated_data()

# Funções individuais mantidas para compatibilidade
def load_epis_df(unit_id: str) -> pd.DataFrame:
    if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
        return pd.DataFrame()
    return load_all_unit_data(unit_id)['epis']

def load_action_plan_df(unit_id: str) -> pd.DataFrame:
    if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
        return pd.DataFrame()
    return load_all_unit_data(unit_id)['action_plan']
