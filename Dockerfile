FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copia el archivo de dependencias.
COPY requirements.txt .

# Instala explícitamente nltk, descarga sus datos y luego el resto de dependencias.
RUN pip install --no-cache-dir nltk && \
    python -m nltk.downloader punkt && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación al contenedor.
COPY . .


CMD exec python -m gunicorn --worker-class gthread --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 app:app