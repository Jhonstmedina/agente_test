import chromadb
import logging

logger = logging.getLogger(__name__)

# Inicializa el cliente de ChromaDB para que guarde los datos en el disco
# en una carpeta llamada 'db' en la raíz del proyecto.
client = chromadb.PersistentClient(path="./db")

def create_and_store_embeddings(chunks: list[str], chat_id: str):
    """
    Crea o accede a una colección en ChromaDB y almacena los embeddings de los chunks.

    Args:
        chunks (list[str]): La lista de fragmentos de texto.
        chat_id (str): El ID único del chat, que se usará como nombre de la colección.
    
    Returns:
        chromadb.Collection: El objeto de la colección con los datos almacenados.
    """
    if not chunks:
        logger.warning("No se proporcionaron chunks para almacenar.")
        return None

    try:
        # 1. Crear o obtener una colección. Cada chat tendrá su propia colección de vectores.
        # Esto aísla los datos de cada documentación procesada.
        logger.info(f"Accediendo a la colección: {chat_id}")
        collection = client.get_or_create_collection(name=chat_id)

        # 2. Preparar los IDs para cada chunk. Deben ser únicos.
        ids = [f"chunk_{i}" for i in range(len(chunks))]

        # 3. Añadir los documentos a la colección.
        # ChromaDB se encargará de generar los embeddings automáticamente
        # usando su modelo por defecto.
        collection.add(
            documents=chunks,
            ids=ids
        )
        
        logger.info(f"Se han almacenado {len(chunks)} chunks en la colección '{chat_id}' de ChromaDB.")
        return collection

    except Exception as e:
        logger.error(f"Error al interactuar con ChromaDB: {e}")
        return None
    