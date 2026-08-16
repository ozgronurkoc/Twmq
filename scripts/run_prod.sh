#!/usr/bin/env bash
# Replit Deploy (autoscale) calistirma adimi:
#   gunicorn -> Flask API  127.0.0.1:8080  (disariya kapali)
#   next start -> UI       0.0.0.0:3000    (disariya acilan port)
#
# API'ye disaridan erisim UI ustunden olur: next.config.mjs icindeki rewrite
# /api/* isteklerini 127.0.0.1:8080'e proxy'ler. Boylece tek dis port yeter.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "→ Flask API (gunicorn) 127.0.0.1:8080"
# `python -m gunicorn`: PATH'te gunicorn olmasa da ayni yorumlayiciyi kullanir
(cd backend && exec "${PYTHON:-python3}" -m gunicorn \
  --bind=127.0.0.1:8080 --reuse-port --workers 2 --timeout 120 web_app:app) &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

for i in $(seq 1 20); do
  # /api/meta hazir olma sinyali: /api/health degismez dusunce 503 dondurur
  if curl -sf http://127.0.0.1:8080/api/meta >/dev/null 2>&1; then
    echo "✓ API hazir"
    break
  fi
  sleep 0.5
done

echo "→ Next.js UI 0.0.0.0:3000"
cd frontend
exec npx next start -H 0.0.0.0 -p 3000
