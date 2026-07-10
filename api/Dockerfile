# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies. ffmpeg is required for faster-whisper to
# decode the webm/opus audio chunks the browser sends.
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the Whisper model so the first API request doesn't pay
# Hugging Face download latency. Cached into /home/appuser via the user
# created below (we chown after).
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8', download_root='/opt/whisper-models')"

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /opt/whisper-models
USER appuser

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/healthz', timeout=5).raise_for_status()" || exit 1

# Run the application
CMD ["python", "main.py"]