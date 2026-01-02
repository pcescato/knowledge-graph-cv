FROM python:3.11-slim

WORKDIR /app

# uv (rapide et moderne)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copie des métadonnées et du code
COPY pyproject.toml .
COPY . .

# Installation des dépendances
RUN uv pip install --system -e .

# Port Cloud Run
EXPOSE 8080

# Cloud Run fournit $PORT
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0"]
