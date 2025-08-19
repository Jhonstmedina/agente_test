import logging
import os
import requests
import pprint
import uuid
import threading
import firebase_admin
import json
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from firebase_admin import credentials, firestore
from google.cloud import secretmanager
from processing.scraper import scrape_and_clean_url
from processing.chunking import chunk_text_intelligently, semantic_chunker
from processing.vector_store import create_and_store_embeddings, find_relevant_chunks
from agent.generation import generate_response
from agent.graph import Agent
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
# agent = Agent()

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
# try:
#     cred = credentials.Certificate("firebase-credentials.json")
#     firebase_admin.initialize_app(cred)
#     db = firestore.client()
#     logger.info("Conexión con Firebase Firestore establecida.")
# except Exception as e:
#     logger.error(f"Error al inicializar Firebase: {e}")
#     db = None

db = None
try:
    PROJECT_ID = os.getenv('adi-cla')
    SECRET_NAME = os.getenv('firebase-credentials')

    #if PROJECT_ID and SECRET_NAME:
    logger.info("Cargando credenciales de Firebase desde Secret Manager...")
    client = secretmanager.SecretManagerServiceClient()
    secret_version_name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = client.access_secret_version(name=secret_version_name)
    
    # El secreto se decodifica de bytes a string y luego se carga como un diccionario JSON
    secret_payload_str = response.payload.data.decode("UTF-8")
    credentials_dict = json.loads(secret_payload_str)

    cred = credentials.Certificate(credentials_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Conexión con Firebase Firestore establecida desde Secret Manager.")
    # else:
    #     # Fallback para desarrollo local usando el archivo
    #     logger.info("Usando archivo local firebase-credentials.json para desarrollo.")
    #     base_dir = os.path.abspath(os.path.dirname(__file__))
    #     credentials_path = os.path.join(base_dir, "firebase-credentials.json")
    #     cred = credentials.Certificate(credentials_path)
    #     firebase_admin.initialize_app(cred)
    #     db = firestore.client()
    #     logger.info("Conexión con Firebase Firestore establecida desde archivo local.")
        
except Exception as e:
    logger.error(f"Error CRÍTICO al inicializar Firebase: {e}")

# --- Inicialización de la Aplicación Flask ---
app = Flask(__name__)
logger.info("Aplicación Flask inicializada.")

agent = None 
_agent_initialized = False
_lock = threading.Lock()

@app.before_request
def initialize_agent():
    """
    Inicializa el agente de IA pesado solo una vez, de forma segura para hilos.
    Se ejecuta antes de cada petición, pero el código de inicialización solo corre en la primera.
    """
    global agent, _agent_initialized
    with _lock:
        if not _agent_initialized:
            logger.info("Inicializando el agente de IA por primera vez...")
            agent = Agent()
            _agent_initialized = True
            logger.info("Agente de IA inicializado y listo.")

@app.route('/')
def chat_ui():
    """
    Renderiza la plantilla HTML de la interfaz de chat.
    """
    return render_template('index.html')

def process_documentation_task(chat_id, url, method):
    """
    Esta función se ejecuta en un hilo separado para no bloquear la API.
    Realiza el scraping, chunking, embedding y actualiza el estado final en Firestore.
    """
    logger.info(f"[Thread-{chat_id}] Iniciando tarea de procesamiento.")
    
    # El mismo código de procesamiento que teníamos antes
    cleaned_text = None
    if method == 'jina':
        try:
            response = requests.get(f"https://r.jina.ai/{url}", timeout=60)
            response.raise_for_status()
            cleaned_text = response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"[Thread-{chat_id}] Error con Jina Reader: {e}")
    else:
        cleaned_text = scrape_and_clean_url(url)

    doc_ref = db.collection('chats').document(chat_id)

    if not cleaned_text:
        logger.error(f"[Thread-{chat_id}] No se pudo extraer texto. Terminando tarea.")
        doc_ref.update({"status": "Error en el procesamiento", "error_message": "No se pudo extraer contenido."})
        return

    logger.info(f"[Thread-{chat_id}] Texto extraído. Segmentando...")
    text_chunks = semantic_chunker(cleaned_text)
    
    logger.info(f"[Thread-{chat_id}] Segmentación completa. Almacenando embeddings...")
    if not create_and_store_embeddings(text_chunks, chat_id):
        logger.error(f"[Thread-{chat_id}] Error al almacenar embeddings. Terminando tarea.")
        doc_ref.update({"status": "Error en el procesamiento", "error_message": "Fallo al crear vectores."})
        return
        
    logger.info(f"[Thread-{chat_id}] Tarea completada. Actualizando estado a 'Completado'.")
    doc_ref.update({"status": "Completado", "chunk_count": len(text_chunks)})

# --- Endpoints de la API v1 ---
@app.route('/api/v1/process-documentation', methods=['POST'])
def process_documentation():
    """
    Recibe una URL e inicia el procesamiento asíncrono en un hilo.
    Devuelve una confirmación inmediata.
    """
    if not db:
        return jsonify({"error": "Servicio de base de datos no disponible."}), 503

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Se requiere la 'url' en el cuerpo del request."}), 400

    chat_id = data.get('chatId', str(uuid.uuid4()))
    url = data['url']
    method = data.get('method', 'custom')

    # 1. Crear el documento en Firestore con estado "En progreso"
    db.collection('chats').document(chat_id).set({
        "status": "En progreso",
        "source_url": url,
        "history": [],
        "created_at": firestore.SERVER_TIMESTAMP
    })

    # 2. Crear y lanzar el hilo para la tarea en segundo plano
    thread = threading.Thread(
        target=process_documentation_task, 
        args=(chat_id, url, method)
    )
    thread.start()

    logger.info(f"Lanzado hilo en segundo plano para procesar la URL: {url} (chatId: {chat_id})")

    # 3. Devolver la respuesta inmediata
    return jsonify({
        "message": "El procesamiento de la documentación ha comenzado en segundo plano.",
        "chatId": chat_id,
        "status": "En progreso"
    }), 202 # 202 Accepted es el código HTTP correcto para estas operaciones


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

    if not doc.exists or doc.to_dict().get('status') != 'Completado':
        return jsonify({"error": "El chat no está listo o no existe."}), 425

    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "Se requiere 'question'."}), 400

    user_question = data['question']
    logger.info(f"Recibida pregunta para el chat {chatId}: '{user_question}'")
    
    final_state = agent.invoke(user_question, chatId)
    ai_response_content = final_state.get("answer", "No se pudo generar una respuesta.")
    
    user_message = {"role": "user", "content": user_question, "timestamp": datetime.utcnow().isoformat() + "Z"}
    ai_message = {"role": "IA", "content": ai_response_content, "timestamp": datetime.utcnow().isoformat() + "Z"}
    
    doc_ref.update({"history": firestore.ArrayUnion([user_message, ai_message])})
    
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

@app.route('/api/v1/chats', methods=['GET'])
def get_chats():
    """
    Devuelve una lista de todas las sesiones de chat procesadas.
    """
    if not db:
        return jsonify({"error": "Servicio de base de datos no disponible."}), 503
    
    try:
        chats_ref = db.collection('chats').stream()
        all_chats = []
        for chat in chats_ref:
            chat_data = chat.to_dict()
            all_chats.append({
                "chatId": chat.id,
                "source_url": chat_data.get("source_url", "URL no disponible"),
                "status": chat_data.get("status", "desconocido"),
                # Opcional: añadir fecha de creación si la guardas
                # "created_at": chat_data.get("created_at")
            })
        
        logger.info(f"Se recuperaron {len(all_chats)} chats existentes.")
        return jsonify(all_chats)
    except Exception as e:
        logger.error(f"Error al recuperar la lista de chats: {e}")
        return jsonify({"error": "No se pudieron recuperar las sesiones de chat."}), 500

# --- Manejo de Errores y Ejecución ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint no encontrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    
    logger.info(f"Iniciando API en http://0.0.0.0:{port} con modo debug: {debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)