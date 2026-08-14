#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only || true
# Eski yama kalıntısını temizle, taze uygula
git checkout HEAD -- templates/index.html 2>/dev/null || true
git apply patches/run_log_ui.patch
echo "Uygulandı. runLogCard sayısı:"
grep -c runLogCard templates/index.html || true
echo "Sunucuyu RESTART et (Stop → Run)."
