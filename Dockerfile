# Usar la imagen oficial ligera de Python 3.11
FROM python:3.11-slim

# Evitar que Python escriba archivos compilados .pyc y habilitar salida de consola en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configurar el directorio de trabajo
WORKDIR /workspace

# Instalar herramientas básicas del sistema que puedan ser necesarias para psycopg2 u otras dependencias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos
COPY requirements.txt /workspace/

# Instalar las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido de la WebApp al contenedor
COPY . /workspace/

# Exponer el puerto 80 (puerto interno en el que escuchará Gunicorn)
EXPOSE 80

# Comando para ejecutar la aplicación usando Gunicorn
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:80", "app.main:app"]
