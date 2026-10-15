# ==============================================================================
# Dockerfile para la Automatización RPA Mercado Pago con Servidor Web
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la app, módulo RPA y assets del frontend
COPY conciliar.py app.py ./
COPY static/ ./static/

# Puerto del servidor web
EXPOSE 8000

# Comando de inicio del servidor
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
