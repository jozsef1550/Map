#!/usr/bin/env bash
# Unified startup script — runs both backend and frontend dev server.
# Usage: bash run.sh
# On Replit: backend is available on port 8000 (mapped to :80)
#            frontend dev server on port 5173 (mapped to :3000)

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing Python dependencies ==="
cd "$ROOT/backend"
pip install -r requirements.txt -q

echo "=== Installing Node dependencies ==="
cd "$ROOT/frontend"
npm install --silent

echo "=== Starting backend (port ${PORT:-8000}) ==="
cd "$ROOT/backend"
PORT="${PORT:-8000}"
python -m uvicorn main:app --host 0.0.0.0 --port "$PORT" &
BACKEND_PID=$!

echo "=== Starting frontend dev server (port 5173) ==="
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Fantasy Map Engine is running!"
echo "   Backend  → http://0.0.0.0:${PORT}      (API docs: http://0.0.0.0:${PORT}/docs)"
echo "   Frontend → http://0.0.0.0:5173"
echo ""
echo "Press Ctrl+C to stop."

wait $BACKEND_PID $FRONTEND_PID
