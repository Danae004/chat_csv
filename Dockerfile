# Imagen base con Python 3.10 slim
FROM python:3.10-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar todo el código al contenedor (incluye .streamlit/secrets.toml si está)
COPY . .

# Instalar dependencias desde requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 8501 que usa Streamlit
EXPOSE 8501

# Comando para ejecutar la app con Streamlit escuchando en todas las interfaces
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
