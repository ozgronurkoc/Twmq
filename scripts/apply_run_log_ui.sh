#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only || true
git checkout HEAD -- templates/index.html 2>/dev/null || true
git apply patches/run_log_ui.patch
echo "Uygulandı. runLogCard:"
grep -c runLogCard templates/index.html || true
grep -c resetSubmitUI templates/index.html || true
echo "python web_app.py ile yeniden başlat."
