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
        ('employees', ['data_admissao']),
        ('epis', ['data_entrega', 'vencimento']),  # ✅ FALTAVA EPI
        ('action_plan', ['data_criacao', 'data_conclusao', 'prazo'])  # ✅ FALTAVA PLANO DE AÇÃO
    ]:
        if not data[df_name].empty:
            for col in date_cols:
                if col in data[df_name].columns:
                    try:
                        before_count = data[df_name][col].notna().sum()
                        data[df_name][col] = pd.to_datetime(data[df_name][col], errors='coerce')
                        after_count = data[df_name][col].notna().sum()
                        
                        if before_count != after_count:
                            invalid_count = before_count - after_count
                            logger.warning(
                                f"Tabela '{df_name}', coluna '{col}': "
                                f"{invalid_count} data(s) inválida(s) convertida(s) para NaT"
                            )
                    except KeyError:
                        logger.warning(f"Coluna '{col}' não encontrada em '{df_name}'")
                    except Exception as e:
                        logger.error(f"Erro ao processar datas em '{df_name}.{col}': {e}")
    
    return data

# ✅ Funções individuais mantidas para compatibilidade
def load_epis_df(unit_id: str) -> pd.DataFrame:
    data = load_all_unit_data(unit_id)
    return data['epis']

def load_action_plan_df(unit_id: str) -> pd.DataFrame:
    data = load_all_unit_data(unit_id)
    return data['action_plan']