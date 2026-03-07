# Use Python 3.11 slim as base
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY cash-track/ ./cash-track/
COPY Procfile .
COPY runtime.txt .

# Download Ollama model (mistral:7b)
RUN ollama serve & \
    sleep 10 && \
    ollama pull mistral:7b && \
    pkill ollama

# Expose port
EXPOSE 8000

# Start Ollama in background and run the app
CMD ollama serve & sleep 5 && cd cash-track && gunicorn --bind 0.0.0.0:$PORT wsgi:app
