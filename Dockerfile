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

# Run
CMD ["python", "-m", "uvicorn", "agno_agent:app", "--host", "0.0.0.0", "--port", "8000"]
