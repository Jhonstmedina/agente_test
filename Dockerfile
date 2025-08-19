# Dockerfile

# Usa una imagen base de Python oficial y ligera.
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copia el archivo de dependencias.
COPY requirements.txt .

# [CORRECCIÓN DEFINITIVA]
# 1. Instala explícitamente nltk.
# 2. Inmediatamente después, descarga los datos de 'punkt'.
# 3. Finalmente, instala el resto de las dependencias.
# Esto asegura que nltk esté presente y configurado antes que nada.
RUN pip install --no-cache-dir nltk && \
    python -m nltk.downloader punkt && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación al contenedor.
COPY . .

# Cloud Run establece la variable de entorno PORT. Gunicorn la usará.
ENV PORT 8080

# Comando para ejecutar la aplicación con Gunicorn.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]