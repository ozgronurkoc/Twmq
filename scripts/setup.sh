#!/usr/bin/env bash
# Replit / yerel: bagimliliklari kur. Idempotent — kurulu olani tekrar kurmaz,
# bu yuzden her calistirmadan once cagrilabilir.
#
#   bash scripts/setup.sh
#
# Yaptigi iki is:
#   1. backend/ paketini duzenlenebilir (editable) kurar -> `import spor_toto`
#      ve `spor-toto` komutu her dizinden calisir.
#   2. frontend/node_modules yoksa npm bagimliliklarini kurar.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"

# ─── Python ───────────────────────────────────────────────────────────────────
# `xdist` de kontrol ediliyor, cunku bu koruma AKSI HALDE ZARARLI: pytest
# yapilandirmasi `-n auto` tasiyor ve xdist yoksa pytest hic acilmadan
# "unrecognized arguments" verir. Kurulu bir makinede kosul yalnizca
# spor_toto'ya baksaydi yeniden kurulum atlanir, xdist hic gelmez ve
# "Testler" dugmesi calismaz olurdu.
if "$PY" -c "import flask, numpy, spor_toto, xdist" >/dev/null 2>&1; then
  echo "✓ Python bagimliliklari kurulu"
else
  echo "→ Python bagimliliklari kuruluyor (backend/)..."
  "$PY" -m pip install -q -e "./backend[test]" \
    || "$PY" -m pip install -q -r backend/requirements.txt \
    || true
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
if [[ -d frontend/node_modules ]]; then
  echo "✓ npm bagimliliklari kurulu"
else
  echo "→ npm bagimliliklari kuruluyor (frontend/)..."
  (cd frontend && { npm ci --no-audit --no-fund || npm install --no-audit --no-fund; })
fi

echo "✓ kurulum tamam"
