from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

def chunk_text_intelligently(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """
    Segmenta un texto largo en fragmentos más pequeños utilizando una estrategia recursiva.

    Args:
        text (str): El texto completo a segmentar.
        chunk_size (int): El tamaño máximo de cada fragmento (en caracteres).
        chunk_overlap (int): El número de caracteres que se superponen entre fragmentos
                             consecutivos para mantener el contexto.

    Returns:
        list[str]: Una lista de los fragmentos de texto.
    """
    if not text:
        return []
        
    logger.info(f"Iniciando segmentación inteligente. Tamaño de chunk: {chunk_size}, Superposición: {chunk_overlap}")
    
    # Define la lista de separadores por los que se intentará dividir el texto, en orden de prioridad.
    separators = ["\n\n", "\n", " ", ""]
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=separators,
    )
    
    chunks = text_splitter.split_text(text)
    
    logger.info(f"El texto fue dividido en {len(chunks)} chunks.")
    return chunks