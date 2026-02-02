#!/bin/bash

# Load environment variables from .env file
set -a
source .env
set +a

# Run the server
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
