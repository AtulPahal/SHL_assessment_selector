FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and activate venv
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (excluding .venv, __pycache__, .git)
COPY . .

# Build FAISS index if not exists
RUN if [ ! -f catalog.index ]; then python build_index.py; fi

# Expose port from environment
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run the service using PORT from environment
CMD ["python", "-c", "import os; import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))"]