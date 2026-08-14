#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only || true
git checkout HEAD -- templates/index.html 2>/dev/null || true
git apply patches/run_log_ui.patch
if ! grep -q resetSubmitUI templates/index.html 2>/dev/null; then
  bash scripts/fix_submit_btn.sh || true
fi
echo "Uygulandı."
echo "runLogCard=$(grep -c runLogCard templates/index.html || echo 0)"
echo "resetSubmitUI=$(grep -c resetSubmitUI templates/index.html || echo 0)"
echo "copyRunLog=$(grep -c 'function copyRunLog' templates/index.html || echo 0)"
echo "python web_app.py ile yeniden başlat."
