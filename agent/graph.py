import os
import logging
from typing import TypedDict, List, Literal
import google.generativeai as genai
from langgraph.graph import StateGraph, END
from processing.vector_store import find_relevant_chunks
from dotenv import load_dotenv
from google.cloud import secretmanager

load_dotenv()
logger = logging.getLogger(__name__)

try:
    PROJECT_ID = 'adi-cla'
    SECRET_NAME = 'firebase-credentials'

    #if PROJECT_ID and SECRET_NAME:
    logger.info("Cargando credenciales de Firebase desde Secret Manager...")
    client = secretmanager.SecretManagerServiceClient()
    secret_version_name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/1"
    
    response = client.access_secret_version(name=secret_version_name)
    
    # El secreto se decodifica de bytes a string y luego se carga como un diccionario JSON
    GOOGLE_API_KEY = response.payload.data.decode("UTF-8")

except Exception as e:
    logger.error(f"Error CRÍTICO al inicializar Firebase: {e}")
    client = secretmanager.SecretManagerServiceClient()
    secret_version_name = "projects/564961795889/secrets/firebase-credentials/versions/1"
    
    response = client.access_secret_version(name=secret_version_name)
    
    # El secreto se decodifica de bytes a string y luego se carga como un diccionario JSON
    GOOGLE_API_KEY = response.payload.data.decode("UTF-8")

class AgentState(TypedDict):
    question: str
    chat_id: str
    context: List[str]
    chat_session: any
    answer: str
    intent: Literal["rag_query", "code_query", "greeting", "clarification", "memory_query"]

class Agent:
    def __init__(self):
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        except TypeError:
            logger.error("No se encontró la GOOGLE_API_KEY.")
            self.model = None
        self.chat_sessions = {}
        self.graph = self._build_graph()

    def _get_or_create_chat_session(self, chat_id: str):
        if chat_id not in self.chat_sessions:
            self.chat_sessions[chat_id] = self.model.start_chat(history=[])
        return self.chat_sessions[chat_id]

    def _get_initial_state(self, question: str, chat_id: str):
        chat_session = self._get_or_create_chat_session(chat_id)
        return {"question": question, "chat_id": chat_id, "chat_session": chat_session}

    def _analyze_intent(self, state: AgentState):
        logger.info("Nodo: Analizando intención con memoria...")
        question = state["question"]
        chat_session = state["chat_session"]
        
        history_str = "\n".join([f"{msg.role}: {msg.parts[0].text}" for msg in chat_session.history])

        prompt = f"""
        Tu tarea es clasificar la pregunta actual de un usuario basándote en el historial de la conversación.
        Categorías:
        - "rag_query": Si la pregunta busca información que probablemente se encuentre en un documento.
        - "code_query": Si la pregunta contiene código o pide analizar/explicar código.
        - "greeting": Si es un saludo, despedida o conversación trivial (ej. "hola", "gracias").
        - "memory_query": Si la pregunta pide recordar información mencionada previamente en el historial (ej. "¿cuál es mi nombre?", "¿qué te dije antes?").
        - "clarification": Si la pregunta es demasiado ambigua.

        Responde únicamente con la etiqueta de la categoría.

        HISTORIAL DEL CHAT:
        {history_str}

        PREGUNTA ACTUAL: "{question}"
        Categoría:
        """
        
        response = self.model.generate_content(prompt)
        intent = response.text.strip().lower().replace('"', '')
        if intent not in ["rag_query", "code_query", "greeting", "clarification", "memory_query"]:
            intent = "clarification"
        return {"intent": intent}

    def _retrieve_context(self, state: AgentState):
        logger.info("Nodo: Recuperando contexto RAG...")
        question, chat_id = state["question"], state["chat_id"]
        context = find_relevant_chunks(query_text=question, chat_id=chat_id, n_results=2)
        return {"context": context}

    def _generate_rag_answer(self, state: AgentState):
        logger.info("Nodo: Generando respuesta RAG...")
        question, context, chat_session = state["question"], state["context"], state["chat_session"]
        context_str = "\n\n---\n\n".join(context)
        prompt = f"Usa el contexto para responder la pregunta.\nCONTEXTO: {context_str}\nPREGUNTA: {question}\nRESPUESTA:"
        response = chat_session.send_message(prompt)
        return {"answer": response.text}

    def _code_analysis_node(self, state: AgentState):
        logger.info("Nodo: Analizando código...")
        question, chat_session = state["question"], state["chat_session"]
        prompt = f"Actúa como un programador experto. Analiza el siguiente código según la pregunta.\nPREGUNTA Y CÓDIGO:\n{question}\nANÁLISIS:"
        response = chat_session.send_message(prompt)
        return {"answer": response.text}

    def _conversational_response_node(self, state: AgentState):
        logger.info("Nodo: Generando respuesta conversacional desde memoria...")
        question = state["question"]
        chat_session = state["chat_session"]
        # Para saludos y memoria, a menudo un prompt simple que incluya tu identidad es mejor.
        prompt = f"""
        Eres un asistente de IA amigable y servicial. Te creo el Ingeniero Jhon Medina.
        El usuario ha dicho: "{question}".
        Usa el contexto de la conversación para responder de manera breve, amigable y siempre en español.
        """
        response = chat_session.send_message(prompt)
        return {"answer": response.text}

    def _ask_for_clarification_node(self, state: AgentState):
        logger.info("Nodo: Pidiendo clarificación...")
        return {"answer": "No he entendido bien tu pregunta. ¿Podrías reformularla de una manera más específica?"}

    def _code_formatter_node(self, state: AgentState):
        logger.info("Nodo: Formateando código en la respuesta...")
        answer = state["answer"]
        prompt = f"Revisa el texto. Si contiene código, reescríbelo en un bloque Markdown (```python\\n# tu código\\n```). Si no, devuelve el texto original.\nTEXTO: {answer}\nRESULTADO:"
        response = self.model.generate_content(prompt)
        return {"answer": response.text.strip()}

    def _router(self, state: AgentState):
        logger.info(f"Router: Intención detectada -> {state['intent']}")
        return state['intent']

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("intent_analyzer", self._analyze_intent)
        workflow.add_node("retriever", self._retrieve_context)
        workflow.add_node("rag_generator", self._generate_rag_answer)
        workflow.add_node("code_analyzer", self._code_analysis_node)
        workflow.add_node("conversational_responder", self._conversational_response_node)
        workflow.add_node("clarification_node", self._ask_for_clarification_node)
        workflow.add_node("code_formatter", self._code_formatter_node)

        workflow.set_entry_point("intent_analyzer")
        workflow.add_conditional_edges(
            "intent_analyzer", self._router,
            {
                "rag_query": "retriever",
                "code_query": "code_analyzer",
                "greeting": "conversational_responder",
                "memory_query": "conversational_responder",
                "clarification": "clarification_node"
            }
        )
        
        workflow.add_edge("retriever", "rag_generator")
        workflow.add_edge("rag_generator", "code_formatter")
        workflow.add_edge("code_analyzer", "code_formatter")
        workflow.add_edge("code_formatter", END)
        workflow.add_edge("conversational_responder", END)
        workflow.add_edge("clarification_node", END)

        return workflow.compile()

    def invoke(self, question: str, chat_id: str):
        if not self.model: 
            return {"answer": "Modelo de IA no configurado."}
        return self.graph.invoke(self._get_initial_state(question, chat_id))
    