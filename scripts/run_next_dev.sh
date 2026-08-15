#!/usr/bin/env bash
# Replit / yerel: Flask API (arka plan) + Next.js UI (ön plan, preview :3000)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Spor Toto Lab — Next.js :3000 + Flask :8080 ==="

# .env.local — boş API_URL = aynı origin (next.config rewrites → Flask)
if [[ ! -f frontend/.env.local ]]; then
  echo "NEXT_PUBLIC_API_URL=" > frontend/.env.local
  echo "✓ .env.local oluşturuldu (proxy modu)"
elif grep -q '127.0.0.1:8080' frontend/.env.local 2>/dev/null; then
  # Replit preview'da 127.0.0.1 tarayıcıdan çalışmaz; proxy kullan
  echo "NEXT_PUBLIC_API_URL=" > frontend/.env.local
  echo "✓ .env.local proxy moduna alındı"
fi

# npm deps (sadece yoksa)
if [[ ! -d frontend/node_modules ]]; then
  echo "→ npm install (ilk kurulum)..."
  (cd frontend && npm install)
fi

# Flask API arka planda
echo "→ Flask API  http://0.0.0.0:8080"
PORT=8080 python web_app.py &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

# API ayağa kalksın
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
    echo "✓ API hazır"
    break
  fi
  sleep 0.5
done

echo "→ Next.js UI  http://0.0.0.0:3000  (Replit preview burayı açar)"
cd frontend
exec npx next dev -H 0.0.0.0 -p 3000
