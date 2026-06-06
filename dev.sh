#!/usr/bin/env bash
# Launch the Wiki LM web app: FastAPI backend (:8000) + Next.js frontend (:3100).
# The frontend proxies /api/* to the backend, so just open http://localhost:3100.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "→ Starting FastAPI backend on :8000"
.venv/bin/uvicorn api:app --port 8000 --reload &
BACKEND_PID=$!

cleanup() { echo; echo "→ Stopping…"; kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "→ Starting Next.js frontend on :3100"
cd web
[ -d node_modules ] || npm install
npm run dev
