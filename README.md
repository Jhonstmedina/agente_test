# Agente RAG Contextual con scraping

Sistema de IA para procesar documentación técnica desde una URL y responder preguntas complejas de forma conversacional. El agente está orquestado con LangGraph y se expone a través de una API RESTful con una interfaz de usuario web.

## 📋 Descripción

Este proyecto implementa un agente de IA avanzado capaz de ingestar, comprender y razonar sobre documentación técnica en línea. La solución completa permite:

- **Endpoint público** para iniciar el procesamiento asíncrono de una URL.
- **Lógica de agente no lineal** con análisis de intención y enrutamiento condicional.
- **Sistema de RAG (Retrieval-Augmented Generation)** para basar las respuestas en el contenido del documento.
- **Memoria conversacional** para entender preguntas de seguimiento.
- **Panel de usuario interactivo** para gestionar sesiones y chatear con el agente.

## 🚀 Características Principales

### ✅ Funcionalidades Implementadas

#### 1. **Procesamiento de Documentación**
- `POST /api/v1/process-documentation/`
- Proceso **asíncrono** que se ejecuta en segundo plano.
- Opción de elegir entre un **scraper estándar** y un método avanzado con IA (**Jina Reader**).
- El texto extraído pasa por una **segmentación semántica inteligente** para preservar el contexto.
- Los fragmentos (chunks) se vectorizan y almacenan en una base de datos vectorial.

#### 2. **Lógica del Agente con LangGraph**
- **Análisis de Intención**: El agente clasifica cada pregunta del usuario para entender su propósito (`rag_query`, `code_query`, `memory_query`, etc.).
- **Enrutamiento Condicional**: Basado en la intención, el grafo dirige la solicitud a la ruta más adecuada (RAG, análisis de código, respuesta conversacional).
- **Memoria Conversacional**: La memoria nativa del modelo (gestionada a través de un objeto de sesión) se mantiene en el estado del grafo, permitiendo al agente recordar interacciones previas.
- **Formateo de Código**: Un nodo final revisa las respuestas y se asegura de que cualquier fragmento de código esté correctamente formateado en Markdown.

#### 3. **Interfaz de Usuario y API**
- **Interfaz Web**: Un frontend completo para iniciar el procesamiento, ver sesiones anteriores y chatear de forma interactiva.
- **API RESTful**: Endpoints bien definidos para todas las funcionalidades, permitiendo la integración con otros sistemas.
- **Persistencia de Datos**: El estado del procesamiento y el historial de cada chat se almacenan de forma persistente en Firebase Firestore.
***
## 🏛️ Arquitectura de la Solución

La aplicación se divide en tres capas principales: Frontend, Backend (API) y el Agente de IA.

1.  **Frontend**: Una aplicación de una sola página (SPA) construida con HTML, CSS y JavaScript vainilla.
2.  **Backend (API Flask)**: Una API RESTful que expone los endpoints y orquesta las llamadas al agente.
3.  **Agente de IA (LangGraph)**: El cerebro del sistema. Un grafo de estados que gestiona la lógica de la conversación.
4.  **Bases de Datos**:
    * **Firebase Firestore**: Almacena el historial de conversaciones y el estado del procesamiento.
    * **ChromaDB**: Base de datos vectorial para almacenar los embeddings y realizar búsquedas de similitud.

## Diagrama del Grafo del Agente (LangGraph)
```
graph TD
    A[Input: Pregunta] --> B{1. Analizar Intención};
    B --> C{2. Router Condicional};
    C -- "rag_query" --> D[3a. Recuperar Contexto];
    D --> E[4a. Generar Respuesta RAG];
    E --> F[5. Formatear Código];
    C -- "code_query" --> G[3b. Analizar Código];
    G --> F;
    C -- "greeting / memory_query" --> H[3c. Respuesta Conversacional];
    C -- "clarification" --> I[3d. Pedir Clarificación];
    F --> Z[Output: Respuesta Final];
```
## Modelo de Datos en Firestore
La base de datos se estructura en una colección chats, donde cada documento representa una sesión de conversación.
```
chats (Colección)
└── 9a8b7c6d-e5f4-3g2h-1i0j (Documento - ID de Chat Único)
    ├── source_url: "https://requests.readthedocs.io/..." (String)
    ├── status: "Completado" (String)
    ├── created_at: Timestamp
    ├── chunk_count: 5 (Number)
    └── history: (Array)
        └── [0] (Objeto/Mapa)
            ├── role: "user" (String)
            ├── content: "Que hace Indra?" (String)
            └── timestamp: "2025-08-15T22:15:30.123Z" (String)
```

## 🛠️ Tecnologías Utilizadas

- **Lenguaje**: Python 3.11
- **Framework Backend**: Flask
- **Framework del Agente**: LangGraph
- **Modelo de Lenguaje (LLM)**: Google Gemini 1.5 Flash
- **Base de Datos (Estado/Historial)**: Firebase Firestore
- **Base de Datos Vectorial**: ChromaDB
- **Procesamiento NLP**: NLTK, Sentence-Transformers

## 📦 Instalación

### Prerrequisitos
- Python 3.11+
- Git
- Un entorno virtual (recomendado)

### Configuración Local

1.  **Clonar el repositorio**
    ```bash
    git clone <url-del-repositorio>
    cd <nombre-del-repositorio>
    ```

2.  **Crear y activar el entorno virtual**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    
    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar dependencias**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar credenciales y variables de entorno**
    * **Google AI (Gemini)**:
        1.  Obtén tu clave de API desde [Google AI Studio](https://aistudio.google.com/).
        2.  Crea un archivo `.env` en la raíz del proyecto.
        3.  Añade la clave al archivo: `GOOGLE_API_KEY="TU_CLAVE_DE_API"`

    * **Firebase**:
        1.  Crea un proyecto en la [Consola de Firebase](https://console.firebase.google.com/) y activa **Firestore Database**.
        2.  En `Project settings > Service accounts`, genera una nueva clave privada.
        3.  Renombra el archivo JSON descargado a `firebase-credentials.json` y colócalo en la raíz del proyecto.

5.  **Descargar paquete de NLTK**
    Abre una consola de Python (`python`) y ejecuta:
    ```python
    import nltk
    nltk.download('punkt')
    ```

6.  **Ejecutar el servidor de desarrollo**
    ```bash
    python app.py
    ```
    La aplicación estará disponible en `http://127.0.0.1:5000`.

## 📡 API Endpoints

| Método | Endpoint | Descripción | Autenticación |
|---|---|---|---|
| `POST` | `/api/v1/process-documentation/` | Inicia el procesamiento asíncrono de una URL | No requerida |
| `GET` | `/api/v1/processing-status/{id}/` | Consulta el estado de un procesamiento | No requerida |
| `POST` | `/api/v1/chat/{id}/` | Envía un mensaje al chat (síncrono) | No requerida |
| `GET` | `/api/v1/chat-history/{id}/` | Obtiene el historial de un chat | No requerida |
| `GET` | `/api/v1/chats/` | Lista todas las sesiones de chat creadas | No requerida |

## 🧪 Ejemplos de Uso (Postman)

Aunque la aplicación está diseñada para ser usada a través de su interfaz web, la API es completamente funcional con herramientas como Postman.

### Crear Solicitud de Procesamiento

* **Método**: `POST`
* **URL**: `http://127.0.0.1:5000/api/v1/process-documentation`
* **Body**: `raw`, `JSON`
    ```json
    {
        "url": "[https://langchain-ai.github.io/langgraph/concepts/](https://langchain-ai.github.io/langgraph/concepts/)",
        "method": "jina"
    }
    ```
* **Respuesta**: Confirmación inmediata con `chatId` y estado `"En progreso"`.


### Chatear con el Agente

* **Método**: `POST`
* **URL**: `http://127.0.0.1:5000/api/v1/chat/<tu-chat-id>`
* **Body**: `raw`, `JSON`
    ```json
    {
        "question": "¿Qué es el estado en LangGraph?"
    }
    ```
* **Respuesta**: Un objeto JSON con la respuesta final del agente.

## 💻 Uso de la Interfaz Web

La forma más sencilla de interactuar con el agente es a través de la interfaz web integrada. Una vez que la aplicación esté corriendo, abre tu navegador y ve a la siguiente URL:

**URL LOCAL**: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
**URL DESPLEGADO EN GCP**: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### Flujo de Uso

1.  **Procesar un Documento Nuevo**:
    * En la pantalla principal, verás una sección para introducir una URL.
    * Pega la URL de la documentación técnica que quieres analizar y haz clic en **"Procesar Documentación"**.
    * Aparecerá un diálogo preguntando el método de extracción:
        * **Estándar**: Usa el scraper básico.
        * **Con IA (Jina)**: Usa el servicio avanzado de Jina Reader para una extracción más limpia (recomendado).
    * La interfaz te mostrará el estado "Procesando...". Una vez que termine, el chat se activará.

2.  **Continuar una Sesión Anterior**:
    * La página principal lista todas las documentaciones que han sido procesadas previamente.
    * Para cada una, tienes dos opciones:
        * **Ver Historial**: Carga la conversación anterior en la ventana de chat para revisarla.
        * **Iniciar Chat**: Te lleva a la ventana de chat para continuar la conversación donde la dejaste.

3.  **Chatear con el Agente**:
    * Una vez en la ventana de chat, escribe tus preguntas en el campo de texto y presiona "Enviar" o la tecla Enter.
    * La respuesta del agente aparecerá en la ventana. Puedes tener una conversación fluida, haciendo preguntas de seguimiento o cambiando de tema.


## 🧠 Lógica del Agente Inteligente (LangGraph)

El núcleo del proyecto es un grafo de estados que permite al agente tomar decisiones complejas.

### Flujo de Razonamiento del Agente

1.  **Análisis de Intención**: Al recibir una pregunta, el primer nodo utiliza el LLM y el historial de la conversación para clasificar la intención del usuario (ej. `rag_query`, `code_query`, `memory_query`).
2.  **Enrutamiento Condicional**: Un enrutador dirige el flujo al camino más apropiado según la intención detectada. Esto evita procesos innecesarios, como hacer una búsqueda vectorial para un simple "hola".
3.  **Ejecución de la Ruta**:
    * **Ruta RAG**: Recupera fragmentos de texto relevantes de ChromaDB y los usa para generar una respuesta basada en la fuente.
    * **Ruta de Código**: Utiliza un prompt especializado para analizar o explicar fragmentos de código.
    * **Ruta Conversacional**: Responde directamente usando la memoria de la conversación para preguntas de seguimiento o saludos.
4.  **Formateo de Código**: Antes de finalizar, un nodo especializado se asegura de que cualquier código en la respuesta esté correctamente formateado en Markdown, mejorando la legibilidad.
5.  **Respuesta Final**: El estado final del grafo contiene la respuesta pulida que se envía al usuario.

## 🏗️ Estructura del Proyecto
```
agente-documentacion/
├── agent/
│   └── graph.py           # Lógica del agente con LangGraph
├── processing/
│   ├── chunking.py        # Segmentación semántica
│   ├── scraper.py         # Scraper estándar
│   └── vector_store.py    # Interacción con ChromaDB
├── templates/
│   └── index.html         # Frontend todo-en-uno
├── .env                   # Variables de entorno (local)
├── app.py                 # Servidor Flask y API Endpoints
├── firebase-credentials.json # Clave de servicio de Firebase
└── requirements.txt
```

## ⚠️ Problemas Comunes

1.  **Error `onnxruntime` al iniciar**:
    * **Causa**: Discrepancia entre el entorno virtual de la terminal y el intérprete de Python del editor (ej. VS Code).
    * **Solución**: Asegúrate de que tu editor esté configurado para usar el intérprete de `.\venv\Scripts\python.exe`. Ejecuta `python -m pip install --upgrade --force-reinstall chromadb` para asegurar las dependencias.

2.  **Error `LookupError: Resource punkt not found`**:
    * **Causa**: Faltan los datos del tokenizador de NLTK.
    * **Solución**: Ejecuta el paso 5 de la instalación para descargar los datos necesarios.

3.  **Error `403 Insufficient authentication scopes`**:
    * **Causa**: La API de Google (Vertex AI) no está habilitada en el proyecto de Google Cloud asociado a tu clave.
    * **Solución**: Ve a la consola de Google Cloud, selecciona el proyecto correcto, busca "Vertex AI API" y haz clic en "Habilitar".

## 📄 Licencia

Este proyecto es propiedad de Jhon Medina. Todos los derechos reservados.

## 📞 Soporte

- **Desarrollador**: [Jhon Medina]
- **Email**: [jhonstmedinav@gmail.com]