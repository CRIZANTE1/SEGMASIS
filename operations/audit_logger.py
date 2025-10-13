import streamlit as st
from datetime import datetime
import json
import logging
from operations.supabase_operations import SupabaseOperations

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_action(action: str, details: dict):
    """
    Registra uma ação do usuário na tabela de log do Supabase.
    """
    try:
        user_email = st.session_state.get('user_info', {}).get('email', 'system')
        user_role = st.session_state.get('role', 'N/A')
        target_unit = st.session_state.get('unit_name', 'N/A')
        timestamp = datetime.now().isoformat()

        # ✅ Usa Supabase Operations com unit_id None (tabela global)
        supabase_ops = SupabaseOperations(unit_id=None)
        
        log_data = {
            'timestamp': timestamp,
            'user_email': user_email,
            'user_role': user_role,
            'action': action,
            'details': json.dumps(details, ensure_ascii=False),
            'target_uo': target_unit
        }
        
        result = supabase_ops.insert_row("log_auditoria", log_data)
        
        if result:
            logger.info(f"LOG SUCCESS: Action '{action}' by '{user_email}' logged.")
        else:
            logger.warning(f"LOG FAILED: Could not log action '{action}'.")

    except Exception as e:
        logger.error(f"LOG FAILED: Could not log action '{action}'. Reason: {e}")