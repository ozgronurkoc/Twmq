#!/usr/bin/env bash
# UI log panelini index.html'e uygular
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only || true
if grep -q 'runLogCard' templates/index.html; then
  echo "UI log zaten uygulanmış."
else
  git apply patches/run_log_ui.patch
  echo "Patch uygulandı."
fi
grep -c 'runLogCard\|copyRunLog' templates/index.html || true
echo "Şimdi sunucuyu RESTART et (Stop → Run)."
