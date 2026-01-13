#!/bin/bash
echo "Starting CapaRox Bot Services..."

# 1. Start Web Server (Background)
echo "Starting Gunicorn..."
gunicorn --bind 0.0.0.0:${PORT:-5000} --timeout 120 --workers 1 --threads 8 api.index:app &
GUNICORN_PID=$!

# 2. Start Bot Worker (Foreground)
# This ensures if the worker dies, the container restarts (good for reliability)
echo "Starting Bot Worker..."
python worker.py

# Note: If worker.py is designed to exit, we might want to wait for gunicorn instead.
# But typically a bot worker runs forever.
