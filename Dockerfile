FROM python:3.11-slim

WORKDIR /app

# Install Caddy (single binary, super lightweight)
RUN apt-get update && \
    apt-get install -y curl && \
    curl -o /usr/bin/caddy -L "https://caddyserver.com/api/download?os=linux&arch=amd64" && \
    chmod +x /usr/bin/caddy && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml .
COPY . .

# Install Python dependencies
RUN uv pip install --system -e .

# Copy Caddy config and start script
COPY Caddyfile /app/Caddyfile
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8080

CMD ["/app/start.sh"]
