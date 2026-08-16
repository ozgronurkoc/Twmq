#!/usr/bin/env bash
# Replit Deploy (autoscale) build adimi: bagimliliklar + Next.js uretim derlemesi.
# Dev'de gerekmez; `scripts/run_next_dev.sh` derlemesiz calisir.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/setup.sh

echo "→ Next.js uretim derlemesi (frontend/)..."
(cd frontend && npm run build)

echo "✓ build tamam"
