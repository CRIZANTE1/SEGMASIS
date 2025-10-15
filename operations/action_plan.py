import streamlit as st
import pandas as pd
from datetime import date
from operations.supabase_operations import SupabaseOperations
from operations.audit_logger import log_action, logger
from operations.cached_loaders import load_all_unit_data

class ActionPlanManager:
    def __init__(self, unit_id: str):
        if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
            logger.error("ActionPlanManager inicializado sem unit_id válido")
            raise ValueError("unit_id não pode ser vazio")
        
        self.supabase_ops = SupabaseOperations(unit_id)
        self.unit_id = unit_id
        
        self.columns = [
            'id', 'audit_run_id', 'id_empresa', 'id_documento_original', 
            'id_funcionario', 'item_nao_conforme', 'referencia_normativa', 
            'plano_de_acao', 'responsavel', 'prazo', 'status', 
            'data_criacao', 'data_conclusao'
        ]
        
        self.action_plan_df = pd.DataFrame()
        self.data_loaded_successfully = False
        self.load_data()

    def load_data(self):
        """Carrega os dados do plano de ação e padroniza os IDs para string."""
        try:
            all_unit_data = load_all_unit_data(self.unit_id)
            self.action_plan_df = all_unit_data.get("action_plan", pd.DataFrame(columns=self.columns))
            
            if self.action_plan_df is None:
                logger.warning("load_action_plan_df retornou None")
                self.action_plan_df = pd.DataFrame(columns=self.columns)
                self.data_loaded_successfully = False
            elif self.action_plan_df.empty:
                logger.info("Tabela 'plano_acao' está vazia para esta unidade")
                self.data_loaded_successfully = True
            else:
                # ✅ CORREÇÃO PREVENTIVA: Converte todas as colunas de ID para string.
                id_cols = ['id', 'id_empresa', 'id_funcionario']
                for col in id_cols:
                    if col in self.action_plan_df.columns:
                        # Usa .astype(str) para converter a coluna inteira de uma vez.
                        self.action_plan_df[col] = self.action_plan_df[col].astype(str)

                logger.info(f"✅ {len(self.action_plan_df)} item(ns) do plano de ação carregado(s)")
                self.data_loaded_successfully = True
        
        except Exception as e:
            logger.error(f"Erro ao carregar plano de ação: {e}", exc_info=True)
            self.action_plan_df = pd.DataFrame(columns=self.columns)
            self.data_loaded_successfully = False

    def add_action_item(self, audit_run_id, company_id, doc_id, item_details, employee_id=None):
        """Adiciona um novo item ao plano de ação usando Supabase."""
        if not self.data_loaded_successfully:
            st.error("Não é possível adicionar item de ação.")
            return None
    
        item_title = item_details.get('item_verificacao', 'Não conformidade não especificada')
        item_observation = item_details.get('observacao', 'Sem detalhes fornecidos.')
        full_description = f"{item_title.strip()}: {item_observation.strip()}"
        
        new_data = {
            'audit_run_id': str(audit_run_id),
            'id_empresa': str(company_id),
            'id_documento_original': str(doc_id),
            'id_funcionario': str(employee_id) if employee_id else None,
            'item_nao_conforme': full_description,
            'referencia_normativa': item_details.get('referencia_normativa', ''),
            'plano_de_acao': '',
            'responsavel': '',
            'prazo': None,
            'status': 'Aberto',
            'data_criacao': date.today().strftime("%Y-%m-%d"),
            'data_conclusao': None
        }
        
        new_item_id = self.supabase_ops.insert_row("plano_acao", new_data)
        
        if new_item_id:
            st.toast(f"Item de ação '{item_title}' criado com sucesso!", icon="✅")
            log_action("CREATE_ACTION_ITEM", {
                "item_id": new_item_id, 
                "company_id": company_id,
                "original_doc_id": doc_id,
                "employee_id": employee_id if employee_id else "N/A",
                "description": full_description
            })
            self.load_data()
            return new_item_id
        else:
            st.error("Falha crítica: Não foi possível salvar o item no Plano de Ação.")
            return None
    
    def get_action_items_by_employee(self, employee_id: str):
        """Retorna itens do plano de ação para um funcionário específico."""
        if self.action_plan_df.empty:
            return pd.DataFrame()
        
        return self.action_plan_df[
            self.action_plan_df['id_funcionario'] == str(employee_id)
        ]

    def get_action_items_by_company(self, company_id: str):
        """Retorna todos os itens do plano de ação para uma empresa."""
        if self.action_plan_df.empty:
            return pd.DataFrame()
        
        return self.action_plan_df[
            self.action_plan_df['id_empresa'] == str(company_id)
        ].copy()

    def update_action_item(self, item_id: str, updates: dict):
        """Atualiza um item do plano de ação."""
        if not self.data_loaded_successfully:
            st.error("Plano de ação não foi carregado corretamente.")
            return False
        
        success = self.supabase_ops.update_row("plano_acao", item_id, updates)
        
        if success:
            log_action("UPDATE_ACTION_ITEM", {
                "item_id": item_id,
                "updated_fields": list(updates.keys())
            })
            self.load_data()
            return True
        
        return False
