--- START OF FILE Segsisone.py ---

import streamlit as st
import sys
import os
import logging
from streamlit_option_menu import option_menu

# Configuração do Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('segsisone_app')

# Configuração do Caminho
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importações
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import authenticate_user, is_user_logged_in, get_user_role, get_user_unit_id
from managers.matrix_manager import MatrixManager
from operations.training_matrix_manager import MatrixManager as TrainingMatrixManager
from front.dashboard import show_dashboard_page
from front.administracao import show_admin_page
from front.plano_de_acao import show_plano_acao_page
from operations.employee import EmployeeManager
from operations.company_docs import CompanyDocsManager
from operations.epi import EPIManager
from operations.action_plan import ActionPlanManager
from analysis.nr_analyzer import NRAnalyzer 

def configurar_pagina():
    st.set_page_config(
        page_title="SEGMA-SIS | Gestão Inteligente",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def initialize_managers():
    # ✅ CORREÇÃO: Converte unit_id para string logo no início para garantir consistência.
    unit_id_obj = st.session_state.get('unit_id')
    unit_id = str(unit_id_obj) if unit_id_obj else None

    folder_id = st.session_state.get('folder_id')
    unit_name = st.session_state.get('unit_name')
    user_role = st.session_state.get('role')
    
    # ✅ MODO GLOBAL para admins
    if user_role == 'admin' and unit_name == 'Global':
        logger.info("Inicializando modo de visão global (admin)")
        
        # Limpa managers de unidade específica
        keys_to_delete = [
            'employee_manager', 'docs_manager', 'epi_manager', 
            'action_plan_manager', 'nr_analyzer', 'matrix_manager_unidade'
        ]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.managers_initialized = False
        st.session_state.managers_unit_id = None
        st.session_state.is_global_view = True  # ✅ Flag para indicar visão global
        
        # MatrixManager global (sempre disponível)
        if 'matrix_manager' not in st.session_state:
            logger.info("Inicializando MatrixManager global...")
            st.session_state.matrix_manager = MatrixManager()
            logger.info("MatrixManager global inicializado.")
        
        return
    
    # ✅ Reseta flag de visão global
    st.session_state.is_global_view = False
    
    # ✅ VALIDAÇÃO: Não inicializa se unit_id for None (usuários não-admin)
    if not unit_id or unit_id == 'None' or str(unit_id).strip() == '':
        logger.info("Nenhuma unidade selecionada. Managers de unidade não serão inicializados.")
        if st.session_state.get('managers_initialized', False):
            # Limpa managers antigos
            keys_to_delete = [
                'employee_manager', 'docs_manager', 'epi_manager', 
                'action_plan_manager', 'nr_analyzer', 'managers_unit_id', 
                'matrix_manager_unidade'
            ]
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
        st.session_state.managers_initialized = False
        
        # MatrixManager global (sempre disponível)
        if 'matrix_manager' not in st.session_state:
            logger.info("Inicializando MatrixManager global...")
            st.session_state.matrix_manager = MatrixManager()
            logger.info("MatrixManager global inicializado.")
        
        return
    
    # ✅ CORREÇÃO: A validação de tipo agora não é mais necessária, pois já convertemos para string.
    # if not isinstance(unit_id, str):
    #     logger.error(f"unit_id tem tipo inválido: {type(unit_id)}")
    #     st.error("❌ Erro: ID da unidade inválido")
    #     return
    
    # Verifica se precisa reinicializar os managers
    if st.session_state.get('managers_unit_id') != unit_id:
        logger.info(f"Trocando de unidade. Inicializando managers para: ...{unit_id[-6:]}")
        
        try:
            with st.spinner("Configurando ambiente da unidade..."):
                managers_ok = True

                # ✅ EmployeeManager
                try:
                    employee_manager = EmployeeManager(unit_id, folder_id)
                    if not employee_manager.data_loaded_successfully:
                        raise Exception("Falha ao carregar dados de funcionários")
                    st.session_state.employee_manager = employee_manager
                    logger.info("✅ EmployeeManager inicializado")
                except Exception as e:
                    logger.error(f"Erro ao inicializar EmployeeManager: {e}")
                    st.error("❌ Erro ao carregar dados de funcionários")
                    managers_ok = False

                # ✅ CompanyDocsManager
                try:
                    docs_manager = CompanyDocsManager(unit_id)
                    if not docs_manager.data_loaded_successfully:
                        raise Exception("Falha ao carregar documentos")
                    st.session_state.docs_manager = docs_manager
                    logger.info("✅ CompanyDocsManager inicializado")
                except Exception as e:
                    logger.error(f"Erro ao inicializar CompanyDocsManager: {e}")
                    st.error("❌ Erro ao carregar documentos da empresa")
                    managers_ok = False

                # ✅ EPIManager
                try:
                    epi_manager = EPIManager(unit_id)
                    if not epi_manager.data_loaded_successfully:
                        logger.warning("Dados de EPI não carregados (pode ser vazio)")
                    st.session_state.epi_manager = epi_manager
                    logger.info("✅ EPIManager inicializado")
                except Exception as e:
                    logger.error(f"Erro ao inicializar EPIManager: {e}")
                    st.error("❌ Erro ao carregar dados de EPIs")
                    managers_ok = False

                # ✅ ActionPlanManager
                try:
                    action_plan_manager = ActionPlanManager(unit_id)
                    if not action_plan_manager.data_loaded_successfully:
                        logger.warning("Dados do plano de ação não carregados (pode ser vazio)")
                    st.session_state.action_plan_manager = action_plan_manager
                    logger.info("✅ ActionPlanManager inicializado")
                except Exception as e:
                    logger.error(f"Erro ao inicializar ActionPlanManager: {e}")
                    st.error("❌ Erro ao carregar plano de ação")
                    managers_ok = False

                # ✅ NRAnalyzer
                try:
                    nr_analyzer = NRAnalyzer(unit_id)
                    st.session_state.nr_analyzer = nr_analyzer
                    logger.info("✅ NRAnalyzer inicializado")
                except Exception as e:
                    logger.error(f"Erro ao inicializar NRAnalyzer: {e}")
                    st.error("❌ Erro ao carregar analisador NR")
                    managers_ok = False

                # ✅ TrainingMatrixManager
                try:
                    matrix_manager = TrainingMatrixManager(unit_id)
                    st.session_state.matrix_manager_unidade = matrix_manager
                    logger.info("✅ TrainingMatrixManager inicializado")
                except Exception as e:
                    logger.error(f"Erro ao inicializar TrainingMatrixManager: {e}")
                    st.error("❌ Erro ao carregar matriz de treinamentos")
                    managers_ok = False

                # ✅ CRÍTICO: Só marca como sucesso se TODOS funcionaram
                if not managers_ok:
                    st.session_state.managers_initialized = False
                    st.error("⚠️ Alguns componentes falharam ao inicializar. Funcionalidade limitada.")
                    return
            
            st.session_state.managers_unit_id = unit_id
            st.session_state.managers_initialized = True
            st.toast("✅ Ambiente configurado com sucesso!", icon="✅")
            logger.info("✅ Managers da unidade inicializados com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro crítico ao inicializar managers: {e}", exc_info=True)
            st.error("❌ Falha ao configurar ambiente. Tente novamente.")
            st.session_state.managers_initialized = False

def main():
    configurar_pagina()

    # Verifica login
    if not is_user_logged_in():
        show_login_page()
        st.stop()
    
    # Autentica e carrega contexto do usuário
    if not authenticate_user():
        st.stop()

    # Inicializa os managers
    initialize_managers()

    with st.sidebar:
        show_user_header()
        user_role = get_user_role()
        unit_name = st.session_state.get('unit_name', 'Nenhuma')

        # ✅ MUDANÇA: Admin pode trocar de unidade, usuários comuns veem apenas a sua
        if user_role == 'admin':
            matrix_manager = st.session_state.matrix_manager
            
            all_units = matrix_manager.get_all_units()
            unit_options = [unit['nome_unidade'] for unit in all_units]
            unit_options.insert(0, 'Global')
            current_unit_name = st.session_state.get('unit_name', 'Global')
            
            try:
                default_index = unit_options.index(current_unit_name)
            except ValueError:
                default_index = 0

            selected_admin_unit = st.selectbox(
                "Operar como Unidade:", 
                options=unit_options,
                index=default_index, 
                key="admin_unit_selector"
            )

            if selected_admin_unit != current_unit_name:
                logger.info(f"Admin trocando de unidade: de '{current_unit_name}' para '{selected_admin_unit}'.")
                
                if selected_admin_unit == 'Global':
                    st.session_state.unit_name = 'Global'
                    st.session_state.unit_id = None
                    st.session_state.folder_id = None
                else:
                    unit_info = matrix_manager.get_unit_info_by_name(selected_admin_unit)
                    if unit_info:
                        st.session_state.unit_name = unit_info['nome_unidade']
                        st.session_state.unit_id = unit_info['id']
                        st.session_state.folder_id = unit_info['folder_id']
                
                st.session_state.managers_unit_id = None 
                st.rerun()
        else:
            # ✅ Usuários não-admin veem apenas sua unidade
            st.info(f"📍 **Unidade:** {unit_name}")

        # Menu de navegação
        menu_items = {
            "Dashboard": {"icon": "clipboard2-data-fill", "function": show_dashboard_page},
            "Plano de Ação": {"icon": "clipboard2-check-fill", "function": show_plano_acao_page},
        }
        
        if user_role == 'admin':
            menu_items["Administração"] = {"icon": "gear-fill", "function": show_admin_page}

        selected_page = option_menu(
            menu_title="Menu Principal",
            options=list(menu_items.keys()),
            icons=[item["icon"] for item in menu_items.values()],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0 !important", "background-color": "transparent"},
                "icon": {"color": "inherit", "font-size": "15px"},
                "nav-link": {
                    "font-size": "12px", 
                    "text-align": "left", 
                    "margin": "0px", 
                    "--hover-color": "rgba(255, 255, 255, 0.1)" if st.get_option("theme.base") == "dark" else "#f0f2f6"
                },
                "nav-link-selected": {"background-color": st.get_option("theme.primaryColor")},
            }
        )
        show_logout_button()
    
    # Executa a página selecionada
    page_to_run = menu_items.get(selected_page)
    if page_to_run:
        logger.info(f"Navegando para a página: {selected_page}")
        page_to_run["function"]()

if __name__ == "__main__":
    main()
