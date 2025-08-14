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

def find_relevant_chunks(query_text: str, chat_id: str, n_results: int = 3) -> list[str]:
    """
    Busca en la colección de ChromaDB los fragmentos de texto más relevantes para una consulta.

    Args:
        query_text (str): La pregunta o texto de búsqueda del usuario.
        chat_id (str): El ID del chat para saber en qué colección buscar.
        n_results (int): El número de fragmentos relevantes a devolver.

    Returns:
        list[str]: Una lista con los textos de los fragmentos más relevantes.
    """
    try:
        # 1. Obtener la colección existente. Si no existe, no hay nada que buscar.
        collection = client.get_collection(name=chat_id)
        
        # 2. Realizar la consulta (query).
        # ChromaDB se encarga de:
        #   a) Convertir el 'query_text' a un embedding.
        #   b) Buscar los 'n_results' embeddings más cercanos en la colección.
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        # 3. Extraer el texto de los documentos encontrados.
        relevant_chunks = results['documents'][0]
        logger.info(f"Se encontraron {len(relevant_chunks)} chunks relevantes para la consulta en la colección '{chat_id}'.")
        print(relevant_chunks)
        return relevant_chunks

    except Exception as e:
        # Esto puede pasar si la colección no existe (ej. chatId incorrecto)
        logger.error(f"Error al consultar la colección '{chat_id}' en ChromaDB: {e}")
        return []
