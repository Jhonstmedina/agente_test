import os
import logging
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

def generate_response(question: str, context_chunks: list[str]) -> str:
    """
    Genera una respuesta utilizando un LLM a partir de una pregunta y un contexto.

    Args:
        question (str): La pregunta del usuario.
        context_chunks (list[str]): La lista de chunks de contexto recuperados.

    Returns:
        str: La respuesta generada por el LLM.
    """
    if not context_chunks:
        return "Lo siento, no he encontrado información relevante en la documentación para responder a tu pregunta."

    try:
        # 1. Inicializar el modelo de lenguaje de Google (Gemini)
        # La API key se carga automáticamente desde la variable de entorno GOOGLE_API_KEY
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        # 2. Formatear el contexto para incluirlo en el prompt
        context_str = "\n\n---\n\n".join(context_chunks)

        prompt = f"""
        Eres un asistente experto en responder preguntas sobre documentación técnica.
        Usa los siguientes fragmentos de contexto recuperado para responder la pregunta.
        Si no sabes la respuesta basándote en el contexto, simplemente di que no lo sabes.
        Sé conciso y responde en un máximo de tres oraciones.

        CONTEXTO:
        {context_str}

        PREGUNTA:
        {question}

        RESPUESTA:
        """
        # template = """
        # Eres un asistente experto creado por Jhon Medina Desarrollador backend y de IA Generativa y estas en capacidad de responder preguntas sobre documentación técnica.
        # Usa los siguientes fragmentos de contexto recuperado para responder la pregunta.
        # Si no sabes la respuesta basándote en el contexto, simplemente di que no lo sabes.
        # Sé conciso y responde en un máximo de tres oraciones.

        # CONTEXTO:
        # {context}

        # PREGUNTA:
        # {question}

        # RESPUESTA:
        # """
        # prompt = PromptTemplate.from_template(template)
        
        # # 4. Construir la cadena de ejecución (LCEL - LangChain Expression Language)
        # # Esta es la forma moderna de encadenar componentes en LangChain.
        # rag_chain = prompt | llm | StrOutputParser()

        # # 5. Invocar la cadena con la pregunta y el contexto
        # logger.info("Invocando la cadena RAG con el LLM...")
        # answer = rag_chain.invoke({"context": context_str, "question": question})

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        logger.error(f"Error al generar la respuesta con el LLM: {e}")
        return "Lo siento, ha ocurrido un error al intentar generar la respuesta."