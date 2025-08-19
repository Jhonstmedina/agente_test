# Dockerfile

# Usa una imagen base de Python oficial y ligera.
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copia el archivo de dependencias primero para aprovechar el cache de Docker.
COPY requirements.txt .

# Instala las dependencias.
RUN pip install --no-cache-dir -r requirements.txt

# Descarga el paquete 'punkt' de NLTK durante la construcción de la imagen.
RUN python -m nltk.downloader punkt

# Copia el resto del código de la aplicación al contenedor.
COPY . .

# Cloud Run establece la variable de entorno PORT. Gunicorn la usará.
# El valor por defecto en Cloud Run es 8080.
ENV PORT 8080

# Comando para ejecutar la aplicación con Gunicorn.
# app:app se refiere al objeto 'app' dentro del archivo 'app.py'.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]