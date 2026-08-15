#!/usr/bin/env bash
# Replit: uncommitted changes engelini kaldır — stage, commit, pull, push
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

echo "== git status (önce) =="
git status -sb || true

# Nav/stats ile ilgili dosyalar
FILES=(
  "data/st_history_2025_26.json"
  "spor_toto/history.py"
  "scripts/patch_nav_routes.py"
  "scripts/commit_and_sync.sh"
  "templates/base.html"
  "templates/stats.html"
  "templates/stats_week.html"
  "templates/health.html"
  "docs/VERI_TOPLAMA_VE_ISLEME.md"
  "web_app.py"
)

for f in "${FILES[@]}"; do
  if [[ -f "$f" ]]; then
    git add -- "$f"
    echo "staged: $f"
  else
    echo "yok (atlandı): $f"
  fi
done

# Route patch (idempotent)
if [[ -f scripts/patch_nav_routes.py ]]; then
  python3 scripts/patch_nav_routes.py || true
  git add -- web_app.py 2>/dev/null || true
fi

if git diff --cached --quiet; then
  echo "Commitlenecek staged değişiklik yok."
else
  git commit -m "feat: tarihsel 1/0/2 istatistik, /stats sayfalari, nav route" || {
    echo "Commit atlandı (belki zaten commitli)."
  }
fi

echo "== pull --rebase =="
git pull --rebase origin main || git pull --no-rebase origin main || true

echo "== push =="
git push origin HEAD:main || git push -u origin HEAD || true

echo "== git status (sonra) =="
git status -sb || true
echo "DONE"
