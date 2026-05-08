FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Build index if not exists
RUN if [ ! -f catalog.index ]; then python build_index.py; fi

# Expose port
EXPOSE 8080

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
