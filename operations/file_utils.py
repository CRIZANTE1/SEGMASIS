"""
Utilitários para manipulação de arquivos.
"""
import logging

logger = logging.getLogger(__name__)


def infer_doc_type(filename: str) -> str:
    """
    Infere o tipo de documento pelo nome do arquivo.
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        Tipo do documento ('aso', 'treinamento', 'epi', 'doc_empresa')
    """
    if not filename or not isinstance(filename, str):
        logger.warning(f"Nome de arquivo inválido: {filename}")
        return 'aso'  # Default
    
    filename_lower = filename.lower()
    
    # Prioridade de verificação
    if 'aso' in filename_lower:
        return 'aso'
    elif 'training' in filename_lower or 'treinamento' in filename_lower:
        return 'treinamento'
    elif 'epi' in filename_lower:
        return 'epi'
    elif any(doc in filename_lower for doc in ['pgr', 'pcmso', 'ppr', 'pca', 'doc_empresa']):
        return 'doc_empresa'
    
    # Default: ASO
    logger.debug(f"Tipo não identificado para '{filename}', usando 'aso' como padrão")
    return 'aso'


def get_file_extension(filename: str) -> str:
    """
    Retorna a extensão do arquivo.
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        Extensão do arquivo (ex: 'pdf', 'jpg')
    """
    if not filename or '.' not in filename:
        return ''
    
    return filename.rsplit('.', 1)[-1].lower()


def is_valid_pdf(filename: str) -> bool:
    """
    Verifica se o arquivo é um PDF válido pelo nome.
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        True se for PDF, False caso contrário
    """
    return get_file_extension(filename) == 'pdf'