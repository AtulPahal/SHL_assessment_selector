FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Build FAISS index at build time (not run time)
RUN python build_index.py

# Expose port
EXPOSE 10000

# Run
CMD ["python", "main.py"]