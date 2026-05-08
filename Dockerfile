FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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

# Copy project files
COPY . .

# Build FAISS index if not exists
RUN if [ ! -f catalog.index ]; then python build_index.py; fi

# Expose port 10000 (Render expects this by default)
EXPOSE 10000

# Run the service - Render will set PORT env var
CMD ["python", "main.py"]