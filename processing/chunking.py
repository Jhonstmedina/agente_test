from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import nltk
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

#nltk.download('punkt')

logger = logging.getLogger(__name__)

try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"No se pudo cargar el modelo de SentenceTransformer: {e}")
    embedding_model = None

def semantic_chunker(text: str, similarity_threshold: float = 0.85) -> list[str]:
    """
    Segmenta un texto en chunks basándose en la similitud semántica de las oraciones.

    Args:
        text (str): El texto completo a segmentar.
        similarity_threshold (float): El umbral de similitud de coseno para decidir
                                      dónde cortar. Un valor más alto crea chunks
                                      más pequeños y cohesivos.

    Returns:
        list[str]: Una lista de los fragmentos de texto semánticamente coherentes.
    """
    if not embedding_model:
        logger.error("El modelo de embeddings no está disponible. No se puede realizar la segmentación semántica.")
        return []

    # 1. Dividir el texto en oraciones
    sentences = nltk.sent_tokenize(text)
    if len(sentences) < 2:
        return sentences

    logger.info(f"Texto dividido en {len(sentences)} oraciones.")

    # 2. Generar embeddings para cada oración
    embeddings = embedding_model.encode(sentences)

    # 3. Calcular la similitud de coseno entre oraciones adyacentes
    similarities = []
    for i in range(len(sentences) - 1):
        # Reshape para que scikit-learn pueda trabajar con ellos (1D -> 2D)
        embedding1 = embeddings[i].reshape(1, -1)
        embedding2 = embeddings[i+1].reshape(1, -1)
        sim = cosine_similarity(embedding1, embedding2)[0][0]
        similarities.append(sim)

    # 4. Crear chunks basados en el umbral de similitud
    chunks = []
    current_chunk_sentences = [sentences[0]]

    for i in range(len(similarities)):
        # Si la similitud con la siguiente oración es menor que el umbral,
        # significa un cambio de tema, por lo que cerramos el chunk actual.
        if similarities[i] < similarity_threshold:
            chunks.append(" ".join(current_chunk_sentences))
            current_chunk_sentences = [] # Empezamos un nuevo chunk

        current_chunk_sentences.append(sentences[i+1])

    # Añadir el último chunk que quedó en el buffer
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    logger.info(f"Texto segmentado semánticamente en {len(chunks)} chunks.")
    return chunks

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