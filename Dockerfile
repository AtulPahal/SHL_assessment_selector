FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency files first (better caching)
COPY requirements.txt pyproject.toml* ./

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    uv pip install --no-cache -r requirements.txt

# Copy all project files
COPY . .

# Build index at build time (not run time)
RUN . .venv/bin/activate && python build_index.py

# Expose port
EXPOSE 10000

# Run with virtual environment activated
CMD [".venv/bin/python", "main.py"]
