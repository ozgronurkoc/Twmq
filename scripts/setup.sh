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
  # `|| true` YOK. Once vardi ve gercek kurulum hatasini yutuyordu; asagidaki
  # guard yalnizca flask/numpy'ye baktigi icin eksik bir `pytest` ya da
  # `gunicorn` sessizce geciyor, sorun ancak testi/dagitimi kosarken
  # ortaya cikiyordu.
  if ! "$PY" -m pip install -q -e "./backend[test,model]"; then
    echo "! duzenlenebilir kurulum basarisiz; requirements.txt deneniyor" >&2
    "$PY" -m pip install -q -r backend/requirements.txt
  fi
fi

# Calisma ve test icin GEREKEN her sey burada dogrulanir — biri eksikse
# kurulum basarisiz sayilir. `xdist` de listede: pytest yapilandirmasi
# `-n auto` tasidigi icin o olmadan suit hic acilmiyor (yukaridaki atlama
# kosulu da tam bu yuzden onu soruyor; iki liste ayrisirsa guard bos kalir).
for _m in flask numpy pytest xdist; do
  if ! "$PY" -c "import $_m" >/dev/null 2>&1; then
    echo "✗ '$_m' kurulamadi. Elle deneyin: $PY -m pip install -e './backend[test]'" >&2
    exit 1
  fi
done

# scipy istege bagli: yoksa yalnizca kesin cozucu (ILP) devre disi kalir.
"$PY" -c "import scipy" >/dev/null 2>&1 \
  || echo "! scipy yok — arac calisir, yalnizca 'exact' (ILP) modu kapali"

# lightgbm de istege bagli ve UYARI ILE gecer: agac tahmincisi (Faz 2.2)
# yalnizca olcum katmanindadir, urune cikmaz. Yoksa `spor_toto.agac`
# kurulamaz ve testleri atlanir; geri kalan her sey calisir.
"$PY" -c "import lightgbm" >/dev/null 2>&1 \
  || echo "! lightgbm yok — agac olcumu (python -m spor_toto.agac) kapali"

# ─── Node ─────────────────────────────────────────────────────────────────────
if [[ -d frontend/node_modules ]]; then
  echo "✓ npm bagimliliklari kurulu"
else
  echo "→ npm bagimliliklari kuruluyor (frontend/)..."
  (cd frontend && { npm ci --no-audit --no-fund || npm install --no-audit --no-fund; })
fi

echo "✓ kurulum tamam"
