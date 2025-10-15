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
    # ✅ VALIDAÇÃO CRÍTICA: Retorna dados vazios se não houver unit_id
    if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
        logger.warning("load_all_unit_data chamado sem unit_id válido")
        return {
            'companies': pd.DataFrame(),
            'employees': pd.DataFrame(),
            'asos': pd.DataFrame(),
            'trainings': pd.DataFrame(),
            'epis': pd.DataFrame(),
            'company_docs': pd.DataFrame(),
            'action_plan': pd.DataFrame()
        }
    
    logger.info(f"Carregando dados para unit_id: ...{unit_id[-6:]}")
    
    try:
        supabase_ops = SupabaseOperations(unit_id)
        
        # ✅ VALIDAÇÃO: Verifica se o engine foi inicializado
        if not supabase_ops.engine:
            logger.error("Engine do banco de dados não disponível")
            return {
                'companies': pd.DataFrame(),
                'employees': pd.DataFrame(),
                'asos': pd.DataFrame(),
                'trainings': pd.DataFrame(),
                'epis': pd.DataFrame(),
                'company_docs': pd.DataFrame(),
                'action_plan': pd.DataFrame()
            }
        
        data = {
            'companies': supabase_ops.get_table_data("empresas"),
            'employees': supabase_ops.get_table_data("funcionarios"),
            'asos': supabase_ops.get_table_data("asos"),
            'trainings': supabase_ops.get_table_data("treinamentos"),
            'epis': supabase_ops.get_table_data("fichas_epi"),
            'company_docs': supabase_ops.get_table_data("documentos_empresa"),
            'action_plan': supabase_ops.get_table_data("plano_acao")
        }
        
        # ✅ VALIDAÇÃO: Garante que todos os DataFrames existam
        for key in data.keys():
            if data[key] is None:
                logger.warning(f"Tabela '{key}' retornou None, usando DataFrame vazio")
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
        
        logger.info(f"✅ Dados carregados com sucesso para unit_id: ...{unit_id[-6:]}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Erro crítico ao carregar dados: {e}", exc_info=True)
        return {
            'companies': pd.DataFrame(),
            'employees': pd.DataFrame(),
            'asos': pd.DataFrame(),
            'trainings': pd.DataFrame(),
            'epis': pd.DataFrame(),
            'company_docs': pd.DataFrame(),
            'action_plan': pd.DataFrame()
        }

# ✅ Funções individuais mantidas para compatibilidade
def load_epis_df(unit_id: str) -> pd.DataFrame:
    """Carrega apenas EPIs de uma unidade"""
    if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
        logger.warning("load_epis_df chamado sem unit_id válido")
        return pd.DataFrame()
    
    data = load_all_unit_data(unit_id)
    return data['epis']

def load_action_plan_df(unit_id: str) -> pd.DataFrame:
    """Carrega apenas o plano de ação de uma unidade"""
    if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
        logger.warning("load_action_plan_df chamado sem unit_id válido")
        return pd.DataFrame()
    
    data = load_all_unit_data(unit_id)
    return data['action_plan']