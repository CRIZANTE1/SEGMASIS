from typing import Optional, Union
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

def format_date_safe(dt: Optional[Union[date, datetime]], fmt: str = "%Y-%m-%d") -> Optional[str]:
    """
    Formata uma data de forma segura, retornando None se a data for inválida.

    Args:
        dt: Data a ser formatada (pode ser date ou datetime)
        fmt: Formato desejado para a string de data

    Returns:
        String formatada com a data ou None se a data for inválida
    """
    if not dt or not isinstance(dt, (date, datetime)):
        return None
    try:
        return dt.strftime(fmt)
    except Exception as e:
        logger.error(f"Erro ao formatar data {dt}: {e}")
        return None
