#!/bin/bash
# start.sh

# Start Streamlit in background
streamlit run app.py \
    --server.port=8501 \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --server.runOnSave=false &

# Wait for Streamlit
sleep 5

# Start Caddy in foreground
caddy run --config /app/Caddyfile
