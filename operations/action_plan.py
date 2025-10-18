import streamlit as st
import pandas as pd
from datetime import date
from operations.supabase_operations import SupabaseOperations
from operations.audit_logger import log_action, logger
from operations.cached_loaders import load_all_unit_data

class ActionPlanManager:
    def __init__(self, unit_id: str):
        # Validação melhorada
        if not unit_id or not isinstance(unit_id, str) or unit_id.strip() in ['', 'None', 'none', 'null']:
            logger.error(f"ActionPlanManager inicializado com unit_id inválido: {unit_id}")
            raise ValueError("unit_id não pode ser vazio ou None")

        unit_id = unit_id.strip()

        self.supabase_ops = SupabaseOperations(unit_id)
        self.unit_id = unit_id

        # ✅ ADICIONAR: Storage manager para upload de evidências
        from managers.supabase_storage import SupabaseStorageManager
        self.storage_manager = SupabaseStorageManager(unit_id)

        self.columns = [
            'id', 'audit_run_id', 'id_empresa', 'id_documento_original',
            'id_funcionario', 'item_nao_conforme', 'referencia_normativa',
            'plano_de_acao', 'responsavel', 'prazo', 'status',
            'data_criacao', 'data_conclusao', 'evidencia_arquivo_id'  # ✅ ADICIONAR
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

        if 'prazo' in new_data and (new_data['prazo'] == '' or new_data['prazo'] is None):
            new_data['prazo'] = None

        new_item_id = self.supabase_ops.insert_row("plano_acao", new_data)

        if new_item_id:
            # Após operação bem-sucedida:
            from operations.cached_loaders import load_all_unit_data
            load_all_unit_data.clear()  # Limpa cache da função
            st.cache_data.clear()        # Limpa cache do Streamlit
            st.session_state.force_reload_managers = True  # Força reload managers
            st.toast(f"Item de ação '{item_title}' criado com sucesso!", icon="✅")
            logger.info("✅ Item de ação adicionado. Reinicialização agendada.")
            log_action("CREATE_ACTION_ITEM", {
                "item_id": new_item_id,
                "company_id": company_id,
                "original_doc_id": doc_id,
                "employee_id": employee_id if employee_id else "N/A",
                "description": full_description
            })
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

        # ✅ CORREÇÃO: Validação adicional
        if not item_id or not updates:
            logger.error("item_id ou updates não fornecidos")
            return False

        try:
            success = self.supabase_ops.update_row("plano_acao", str(item_id), updates)

            if success:
                log_action("UPDATE_ACTION_ITEM", {
                    "item_id": item_id,
                    "updated_fields": list(updates.keys())
                })

                # ✅ CORREÇÃO: Limpar cache e forçar reload
                from operations.cached_loaders import load_all_unit_data
                load_all_unit_data.clear()
                st.cache_data.clear()
                st.session_state.force_reload_managers = True

                logger.info(f"✅ Item de ação {item_id} atualizado. Reinicialização agendada.")

                return True
            else:
                logger.error(f"Falha ao atualizar item {item_id} no Supabase")
                return False

        except Exception as e:
            logger.error(f"Erro ao atualizar item de ação: {e}", exc_info=True)
            st.error(f"Erro ao atualizar: {str(e)}")
            return False

    def upload_evidencia(self, item_id: str, arquivo) -> tuple[bool, str]:
        """
        Faz upload de arquivo de evidência para um item do plano de ação.

        Args:
            item_id: ID do item do plano de ação
            arquivo: Arquivo enviado pelo Streamlit (UploadedFile)

        Returns:
            tuple: (sucesso, mensagem)
        """
        if not arquivo:
            return False, "Nenhum arquivo fornecido"

        try:
            # Valida se o item existe
            item = self.action_plan_df[self.action_plan_df['id'] == str(item_id)]
            if item.empty:
                return False, "Item não encontrado"

            # Gera nome do arquivo
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # ✅ CORREÇÃO: Sanitiza o nome do arquivo original
            import re
            safe_filename = re.sub(r'[^\w\s.-]', '', arquivo.name)
            safe_filename = safe_filename.replace(' ', '_')

            nome_arquivo = f"evidencia_{item_id}_{timestamp}_{safe_filename}"

            # ✅ CORREÇÃO: Usa upload específico para evidências
            logger.info(f"Fazendo upload de evidência para item {item_id} no bucket 'evidencias'")

            # Upload direto especificando o tipo de documento
            result = self.storage_manager.upload_file(
                file_content=arquivo.getvalue(),
                filename=nome_arquivo,
                doc_type='evidencia',  # ✅ Especifica que é evidência
                content_type=arquivo.type
            )

            if not result or 'url' not in result:
                return False, "Falha ao fazer upload do arquivo"

            arquivo_url = result['url']

            # Atualiza o registro no banco
            updates = {'evidencia_arquivo_id': arquivo_url}
            if self.update_action_item(item_id, updates):
                logger.info(f"✅ Evidência anexada ao item {item_id}: {arquivo_url}")
                return True, "Evidência anexada com sucesso!"
            else:
                # Se falhou, tenta deletar o arquivo do storage
                try:
                    self.storage_manager.delete_file_by_url(arquivo_url)
                except Exception as e:
                    logger.warning(f"Não foi possível deletar arquivo órfão: {e}")
                return False, "Falha ao atualizar o registro"

        except Exception as e:
            logger.error(f"Erro ao fazer upload de evidência: {e}", exc_info=True)
            return False, f"Erro: {str(e)}"

    def delete_evidencia(self, item_id: str) -> tuple[bool, str]:
        """
        Remove a evidência de um item do plano de ação.

        Args:
            item_id: ID do item do plano de ação

        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            # Busca o item
            item = self.action_plan_df[self.action_plan_df['id'] == str(item_id)]
            if item.empty:
                return False, "Item não encontrado"

            evidencia_url = item.iloc[0].get('evidencia_arquivo_id')
            if not evidencia_url or pd.isna(evidencia_url):
                return False, "Este item não possui evidência"

            # Deleta do storage
            if self.storage_manager.delete_file_by_url(evidencia_url):
                # Atualiza o registro
                updates = {'evidencia_arquivo_id': None}
                if self.update_action_item(item_id, updates):
                    logger.info(f"✅ Evidência removida do item {item_id}")
                    return True, "Evidência removida com sucesso!"

            return False, "Falha ao remover evidência"

        except Exception as e:
            logger.error(f"Erro ao remover evidência: {e}", exc_info=True)
            return False, f"Erro: {str(e)}"
