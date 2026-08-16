#!/usr/bin/env bash
# Replit / yerel: bagimliliklari kur. Idempotent — guncel olani tekrar kurmaz,
# bu yuzden her calistirmadan once cagrilabilir.
#
#   bash scripts/setup.sh
#
# Yaptigi iki is:
#   1. backend/ paketini duzenlenebilir (editable) kurar -> `import spor_toto`
#      ve `spor-toto` komutu her dizinden calisir.
#   2. frontend/ npm bagimliliklarini kurar.
#
# "Kurulu mu?" sorusu klasor VARLIGINA bakilarak yanitlanamaz: git pull yeni bir
# bagimlilik getirdiginde eski node_modules yerinde durur ve derleme
# "Module not found" ile patlar. Asagidaki iki kontrol bayatligi arar.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"

# ─── Python ───────────────────────────────────────────────────────────────────
# Bayat sayilir: import edilemiyorsa ya da pyproject.toml editable kurulumun
# biraktigi egg-info'dan yeniyse (= bagimlilik listesi degismis).
py_bayat() {
  "$PY" -c "import flask, numpy, spor_toto" >/dev/null 2>&1 || return 0
  local damga
  damga="$(ls -d backend/*.egg-info/PKG-INFO 2>/dev/null | head -1)"
  [[ -n "$damga" ]] || return 0
  [[ backend/pyproject.toml -nt "$damga" ]] && return 0
  return 1
}

if py_bayat; then
  echo "→ Python bagimliliklari kuruluyor (backend/)..."
  "$PY" -m pip install -q -e "./backend[test]" \
    || "$PY" -m pip install -q -r backend/requirements.txt \
    || true
else
  echo "✓ Python bagimliliklari guncel"
fi

# Flask + numpy zorunlu: bunlar olmadan API acilmaz.
if ! "$PY" -c "import flask, numpy" >/dev/null 2>&1; then
  echo "✗ flask/numpy kurulamadi. Elle deneyin: $PY -m pip install -e './backend[test]'" >&2
  exit 1
fi

# scipy istege bagli: yoksa yalnizca kesin cozucu (ILP) devre disi kalir.
"$PY" -c "import scipy" >/dev/null 2>&1 \
  || echo "! scipy yok — arac calisir, yalnizca 'exact' (ILP) modu kapali"

# ─── Node ─────────────────────────────────────────────────────────────────────
# Bayat sayilir: node_modules yoksa, manifest npm'in son kurulumundan yeniyse ya
# da `npm ls` bir bagimliligi eksik/uyumsuz buluyorsa (lucide-react vakasi).
npm_bayat() {
  local damga=frontend/node_modules/.package-lock.json
  [[ -d frontend/node_modules ]] || return 0
  [[ -f "$damga" ]] || return 0
  [[ frontend/package.json      -nt "$damga" ]] && return 0
  [[ frontend/package-lock.json -nt "$damga" ]] && return 0
  (cd frontend && npm ls --depth=0 >/dev/null 2>&1) || return 0
  return 1
}

if npm_bayat; then
  echo "→ npm bagimliliklari kuruluyor (frontend/)..."
  (cd frontend && { npm ci --no-audit --no-fund || npm install --no-audit --no-fund; })
  (cd frontend && npm ls --depth=0 >/dev/null 2>&1) \
    || echo "! npm ls hala eksik bagimlilik goruyor — 'cd frontend && npm install' ciktisina bakin"
else
  echo "✓ npm bagimliliklari guncel"
fi

echo "✓ kurulum tamam"
