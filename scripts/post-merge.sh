#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! grep -q 'runLogCard' templates/index.html 2>/dev/null || ! grep -q 'resetSubmitUI' templates/index.html 2>/dev/null; then
  echo "[post-merge] UI eksik — ensure_ui çalışıyor..."
  bash scripts/ensure_ui.sh
fi
echo "[post-merge] runLogCard=$(grep -c runLogCard templates/index.html 2>/dev/null || echo 0) resetSubmitUI=$(grep -c resetSubmitUI templates/index.html 2>/dev/null || echo 0)"
