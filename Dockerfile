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

# Install Chromium system dependencies (pre-install so Playwright doesn't need --with-deps)
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libcairo2 \
    libatspi2.0-0 libgtk-3-0 fonts-liberation \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Download Playwright Chromium binary (no --with-deps since deps installed above)
RUN playwright install chromium

# Copy app
COPY . .

# Default port (Railway overrides via $PORT)
ENV PORT=8000
EXPOSE 8000

# Use shell to expand $PORT at runtime
CMD ["/bin/sh", "-c", "python -m uvicorn agno_agent:app --host 0.0.0.0 --port $PORT"]
