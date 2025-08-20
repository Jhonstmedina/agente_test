import logging
import chromadb

logger = logging.getLogger(__name__)
client = None

try:
    # [CAMBIO] Conexión directa con la URL "quemada" (hardcoded)
    # Usamos la sintaxis que te funcionó en tu script de prueba.
    CHROMA_URL = "https://playground.androide.tech/chromadb_server"
    
    client = chromadb.HttpClient(
        host=CHROMA_URL,
        port=443,
        ssl=True
    )
    
    client.heartbeat() # Verifica la conexión al iniciar
    logger.info(f"Conectado exitosamente al servidor de ChromaDB en {CHROMA_URL}.")

except Exception as e:
    logger.error(f"Error CRÍTICO al inicializar el cliente de ChromaDB: {e}", exc_info=True)


def create_and_store_embeddings(chunks: list[str], chat_id: str):
    """Almacena embeddings en una colección del servidor ChromaDB."""
    if not client: 
        logger.error("El cliente de ChromaDB no está inicializado.")
        return False
    try:
        collection = client.get_or_create_collection(name=chat_id)
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        collection.add(documents=chunks, ids=ids)
        logger.info(f"Vectores almacenados en la colección '{chat_id}' de ChromaDB.")
        return True
    except Exception as e:
        logger.error(f"Error al almacenar embeddings en ChromaDB: {e}", exc_info=True)
        return False

def find_relevant_chunks(query_text: str, chat_id: str, n_results: int = 3) -> list[str]:
    """Busca en una colección del servidor ChromaDB."""
    if not client: 
        logger.error("El cliente de ChromaDB no está inicializado.")
        return []
    try:
        collection = client.get_collection(name=chat_id)
        results = collection.query(query_texts=[query_text], n_results=n_results)
        return results['documents'][0]
    except Exception as e:
        logger.error(f"Error al consultar ChromaDB: {e}", exc_info=True)
        return []