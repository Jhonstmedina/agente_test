import logging
import os
import pprint
import uuid
import firebase_admin
from flask import Flask, request, jsonify
from datetime import datetime
from firebase_admin import credentials, firestore
from processing.scraper import scrape_and_clean_url
from processing.chunking import chunk_text_intelligently, semantic_chunker
from processing.vector_store import create_and_store_embeddings, find_relevant_chunks
from agent.generation import generate_response
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/app_{datetime.now().strftime('%Y%m%d')}.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Inicialización de Firebase ---
try:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Conexión con Firebase Firestore establecida.")
except Exception as e:
    logger.error(f"Error al inicializar Firebase: {e}")
    db = None

# --- Inicialización de la Aplicación Flask ---
app = Flask(__name__)
logger.info("Aplicación Flask inicializada.")

# --- Endpoints de la API v1 ---

@app.route('/api/v1/process-documentation', methods=['POST'])
def process_documentation():
    if not db:
        return jsonify({"error": "Servicio de base de datos no disponible."}), 503

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Se requiere la 'url' en el cuerpo del request."}), 400

    chat_id = data.get('chatId', str(uuid.uuid4()))
    url = data['url']
    
    logger.info(f"Solicitud de procesamiento para URL: {url} con chatId: {chat_id}")

    # NOTA: Esta es una llamada SÍNCRONA. La API esperará a que termine.
    # Esto se modificará más adelante para ser un proceso asíncrono.
    cleaned_text = scrape_and_clean_url(url)
    if not cleaned_text:
        # Si el scraping falla, lo registramos en la DB y devolvemos un error.
        db.collection('chats').document(chat_id).set({
            "status": "Error en el procesamiento",
            "history": [],
            "source_url": url,
            "error_message": "No se pudo extraer contenido de la URL.",
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return jsonify({"error": f"No se pudo procesar la URL: {url}"}), 500

    text_chunks = semantic_chunker(cleaned_text)

    vector_collection = create_and_store_embeddings(text_chunks, chat_id)
    if not vector_collection:
        return jsonify({"error": "Ocurrió un error al almacenar los datos vectoriales."}), 500


    doc_ref = db.collection('chats').document(chat_id)
    doc_ref.set({
        "status": "Completado", 
        "history": [],
        "source_url": url,
        "created_at": firestore.SERVER_TIMESTAMP,
        "processed_text_char_count": len(cleaned_text),
        "chunk_count": len(text_chunks) # Guardamos el número de chunks generados
    })
    
    logger.info(f"Documento {url} procesado y guardado en Firestore para chatId {chat_id}.")
    
    # --- FIN DE LA MODIFICACIÓN ---
    
    response = {
        "message": "El procesamiento de la documentación ha sido completado.",
        "chatId": chat_id,
        "status": "Completado",
         "chunks_created": len(text_chunks)
    }
    return jsonify(response), 200 # Devolvemos 200 OK porque el proceso ya terminó

@app.route('/api/v1/processing-status/<string:chatId>', methods=['GET'])
def get_processing_status(chatId):
    if not db:
        return jsonify({"error": "Servicio de base de datos no disponible."}), 503

    # [MODIFICADO] Obtiene la referencia del documento y lo consulta
    doc_ref = db.collection('chats').document(chatId)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({"error": "Chat ID no encontrado."}), 404
    
    logger.info(f"Consultando estado para el chatId: {chatId}")
    
    chat_data = doc.to_dict()
    status = chat_data.get('status', 'desconocido')
    
    # Simulación para pruebas: Cambia el estado para permitir el chat
    if status == "En progreso":
        doc_ref.update({"status": "Completado"})
        status = "Completado"
        logger.info(f"Simulación: El estado para {chatId} ha cambiado a 'Completado'.")

    return jsonify({"chatId": chatId, "status": status})

@app.route('/api/v1/chat/<string:chatId>', methods=['POST'])
def chat(chatId):
    if not db:
        return jsonify({"error": "Servicio de base de datos no disponible."}), 503
    
    doc_ref = db.collection('chats').document(chatId)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({"error": "Chat ID no encontrado."}), 404

    chat_data = doc.to_dict()
    if chat_data.get('status') != 'Completado':
        return jsonify({"error": "La documentación aún está siendo procesada."}), 425

    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "Se requiere 'question' en el cuerpo del request."}), 400

    user_question = data['question']
    logger.info(f"Recibida pregunta para el chat {chatId}: '{user_question}'")

    relevant_chunks = find_relevant_chunks(query_text=user_question, chat_id=chatId, n_results=2)
    if not relevant_chunks:
        # Si no se encuentra contexto, se puede dar una respuesta genérica.
        ai_response_content = "Lo siento, no he encontrado información relevante en la documentación para responder a tu pregunta."
    else:
        ai_response_content = generate_response(
            question=user_question, 
            context_chunks=relevant_chunks
        )

    # 1. Crear el objeto del mensaje del usuario con timestamp
    user_message = {
        "role": "user",
        "content": user_question,
        "timestamp": datetime.utcnow().isoformat() + "Z" # Añade timestamp en formato UTC
    }
    
    # Añadir el mensaje del usuario al historial en Firestore
    doc_ref.update({
        "history": firestore.ArrayUnion([user_message])
    })
    
    # Lógica de IA (a implementar)
    #ai_response_content = f"Respuesta simulada a tu pregunta: '{user_question}'."
    
    # 2. Crear el objeto del mensaje de la IA con el nuevo rol y timestamp
    ai_message = {
        "role": "IA",  # <-- ROL CAMBIADO de "assistant" a "IA"
        "content": ai_response_content,
        "timestamp": datetime.utcnow().isoformat() + "Z" # Añade timestamp en formato UTC
    }
    
    # Añadir el mensaje de la IA al historial en Firestore
    doc_ref.update({
        "history": firestore.ArrayUnion([ai_message])
    })
    
    # --- FIN DE LA MODIFICACIÓN ---
    
    return jsonify({"answer": ai_response_content})

@app.route('/api/v1/chat-history/<string:chatId>', methods=['GET'])
def get_chat_history(chatId):
    if not db:
        return jsonify({"error": "Servicio de base de datos no disponible."}), 503

    # [MODIFICADO] Obtiene el documento y devuelve el campo 'history'
    doc_ref = db.collection('chats').document(chatId)
    doc = doc_ref.get()
    
    if not doc.exists:
        return jsonify({"error": "Chat ID no encontrado."}), 404
        
    logger.info(f"Solicitando historial para el chat {chatId}")
    
    chat_data = doc.to_dict()
    history = chat_data.get('history', [])
    return jsonify({"chatId": chatId, "history": history})

# --- Manejo de Errores y Ejecución ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint no encontrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    
    logger.info(f"Iniciando API en http://0.0.0.0:{port} con modo debug: {debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)