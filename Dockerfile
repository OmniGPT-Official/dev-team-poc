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

# Install Playwright + Chromium for Indeed browser automation
RUN pip install playwright && playwright install --with-deps chromium

# Copy app
COPY . .

# Default port (Railway overrides via $PORT)
ENV PORT=8000
EXPOSE 8000

# Use shell to expand $PORT at runtime
CMD ["/bin/sh", "-c", "python -m uvicorn agno_agent:app --host 0.0.0.0 --port $PORT"]
