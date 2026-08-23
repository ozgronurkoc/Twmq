#!/usr/bin/env bash
# Replit / yerel: Flask API (arka plan) + Next.js UI (ön plan, preview :3000)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Portlar TEK yerde. Once 8080 bu dosyada uc, run_prod.sh'te uc,
# next.config.mjs'te iki kez sabitti; biri degisince otekiler sessizce
# eski porta konusuyordu.
API_PORT="${API_PORT:-8080}"
UI_PORT="${UI_PORT:-3000}"
export API_PORT UI_PORT

echo "=== Spor Toto Lab — Next.js :$UI_PORT + Flask :$API_PORT ==="

# Bagimliliklar (idempotent: kurulular atlanir)
bash scripts/setup.sh

# .env.local — boş API_URL = aynı origin (next.config rewrites → Flask)
if [[ ! -f frontend/.env.local ]]; then
  echo "NEXT_PUBLIC_API_URL=" > frontend/.env.local
  echo "✓ .env.local oluşturuldu (proxy modu)"
elif grep -q '127.0.0.1:' frontend/.env.local 2>/dev/null; then
  # Replit preview'da 127.0.0.1 tarayıcıdan çalışmaz; proxy kullan
  echo "NEXT_PUBLIC_API_URL=" > frontend/.env.local
  echo "✓ .env.local proxy moduna alındı"
fi

# Flask API arka planda.
# `python backend/web_app.py` yeterli: Python script'in bulundugu dizini
# (backend/) sys.path'e ekler, yani `import spor_toto` calisir.
echo "→ Flask API  http://0.0.0.0:$API_PORT"
PORT="$API_PORT" "${PYTHON:-python3}" backend/web_app.py &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

# API ayağa kalksın
for i in 1 2 3 4 5 6 7 8 9 10; do
  # Ayaga kalkma sinyali /health (liveness): hicbir degismez kosmaz, bu
  # yuzden bir kontrol dustugunde de "surec ayakta" cevabini verir.
  # /api/health readiness'tir ve degismez dusunce bilerek 503 doner.
  if curl -sf "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
    echo "✓ API hazır"
    break
  fi
  sleep 0.5
done

echo "→ Next.js UI  http://0.0.0.0:$UI_PORT  (Replit preview burayı açar)"
cd frontend
exec npx next dev -H 0.0.0.0 -p "$UI_PORT"
