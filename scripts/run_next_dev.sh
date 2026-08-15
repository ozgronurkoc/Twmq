#!/usr/bin/env bash
# Replit / yerel: Flask API + Next.js UI birlikte
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Spor Toto Lab — Next.js + Flask ==="

# .env.local
if [[ ! -f frontend/.env.local ]]; then
  if [[ -f frontend/.env.example ]]; then
    cp frontend/.env.example frontend/.env.local
    echo "✓ .env.local oluşturuldu"
  else
    echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8080" > frontend/.env.local
    echo "✓ .env.local varsayılan ile yazıldı"
  fi
fi

# npm deps
if [[ ! -d frontend/node_modules ]]; then
  echo "→ npm install..."
  (cd frontend && npm install)
fi

# Flask API arka planda
echo "→ Flask API :8080"
python web_app.py &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

sleep 1
echo "→ Next.js UI :3000"
(cd frontend && npm run dev)
