FROM python:3.11-slim

WORKDIR /app

# Install Node.js (needed for MCP tools)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Install Vercel SDK for deployment tool
RUN cd tests/vercel_mcp && npm install

# Expose port (Railway uses dynamic PORT)
EXPOSE ${PORT:-8000}

# Use shell form to expand $PORT environment variable
CMD python -m uvicorn agno_agent:app --host 0.0.0.0 --port ${PORT:-8000}
