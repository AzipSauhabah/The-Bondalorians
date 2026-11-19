# Image unique pour les services (GUI, worker, serveur MCP).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY src ./src
COPY data ./data
COPY scripts ./scripts
COPY tests ./tests

ENV PYTHONPATH=/app/src

# GUI par defaut ; les autres services surchargent la commande.
CMD ["streamlit", "run", "app/Home.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
