FROM python:3.11-slim

WORKDIR /app

# Install Node.js (needed for MCP tools)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8000

# Use shell form to allow env var expansion
CMD python -m uvicorn agno_agent:app --host 0.0.0.0 --port ${PORT:-8000}
