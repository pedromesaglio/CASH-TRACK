# Use Python 3.11 slim as base
FROM python:3.11-slim

# Install system dependencies including zstd
RUN apt-get update && apt-get install -y \
    curl \
    zstd \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama manually (bypass the install script issues)
RUN curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/local/bin/ollama && \
    chmod +x /usr/local/bin/ollama

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY cash-track/ ./cash-track/
COPY Procfile .
COPY runtime.txt .

# Create Ollama data directory
RUN mkdir -p /root/.ollama

# Expose port
EXPOSE 8000

# Start Ollama in background, pull model, and run the app
CMD ollama serve & \
    sleep 5 && \
    ollama pull mistral:7b && \
    cd cash-track && \
    gunicorn --bind 0.0.0.0:$PORT wsgi:app
