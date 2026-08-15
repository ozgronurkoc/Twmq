#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only || true
git checkout HEAD -- templates/index.html 2>/dev/null || true
git apply patches/run_log_ui.patch 2>/dev/null || true
if ! grep -q runLogCard templates/index.html 2>/dev/null; then
  echo "UYARI: runLogCard yok"
fi
python3 scripts/fix_form_js.py
echo "--- dogrulama ---"
echo "runLogCard=$(grep -c runLogCard templates/index.html || echo 0)"
echo "fetch=$(grep -c 'fetch(' templates/index.html || echo 0)"
echo "function(ev)=$(grep -c 'function(ev)' templates/index.html || echo 0)"
echo "python web_app.py + HARD REFRESH"
