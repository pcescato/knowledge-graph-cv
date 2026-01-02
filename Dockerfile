FROM python:3.11-slim

WORKDIR /app

# Installation de uv pour la rapidité
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copie des fichiers de config
COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

# Cloud Run injecte la variable PORT
CMD ["sh", "-c", "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"]