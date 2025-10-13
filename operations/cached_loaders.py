import streamlit as st
import pandas as pd
from operations.supabase_operations import SupabaseOperations
import logging

logger = logging.getLogger(__name__)

@st.cache_data(ttl=600, show_spinner="Carregando dados...")
def load_all_unit_data(unit_id: str) -> dict:
    """
    Carrega TODOS os dados de uma unidade de uma vez.
    Cache de 10 minutos (600 segundos)
    """
    if not unit_id:
        return {
            'companies': pd.DataFrame(),
            'employees': pd.DataFrame(),
            'asos': pd.DataFrame(),
            'trainings': pd.DataFrame(),
            'epis': pd.DataFrame(),
            'company_docs': pd.DataFrame(),
            'action_plan': pd.DataFrame()
        }
    
    supabase_ops = SupabaseOperations(unit_id)
    
    data = {
        'companies': supabase_ops.get_table_data("empresas"),
        'employees': supabase_ops.get_table_data("funcionarios"),
        'asos': supabase_ops.get_table_data("asos"),
        'trainings': supabase_ops.get_table_data("treinamentos"),
        'epis': supabase_ops.get_table_data("fichas_epi"),
        'company_docs': supabase_ops.get_table_data("documentos_empresa"),
        'action_plan': supabase_ops.get_table_data("plano_acao")
    }
    
    # Processa datas
    for df_name, date_cols in [
        ('asos', ['data_aso', 'vencimento']),
        ('trainings', ['data', 'vencimento']),
        ('company_docs', ['data_emissao', 'vencimento']),
        ('employees', ['data_admissao'])
    ]:
        df = data[df_name]
        if not df.empty:
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return data

# ✅ Funções individuais mantidas para compatibilidade
def load_epis_df(unit_id: str) -> pd.DataFrame:
    data = load_all_unit_data(unit_id)
    return data['epis']

def load_action_plan_df(unit_id: str) -> pd.DataFrame:
    data = load_all_unit_data(unit_id)
    return data['action_plan']