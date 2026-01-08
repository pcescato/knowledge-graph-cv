FROM python:3.11-slim
WORKDIR /app

# uv pour installation rapide
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copie des métadonnées & code
COPY pyproject.toml .
COPY . .

# Installation
RUN uv pip install --system -e .

# Port Cloud Run
EXPOSE 8080

# Commande Streamlit (OPTIONS VALIDES UNIQUEMENT)
CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.runOnSave=false \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
