#!/usr/bin/env bash
# Replit / yerel: bagimliliklari kur. Idempotent — kurulu olani tekrar kurmaz,
# bu yuzden her calistirmadan once cagrilabilir.
#
#   bash scripts/setup.sh             # calistirmak + test etmek icin yeter
#   bash scripts/setup.sh --kalite    # ayrica `scripts/check.sh` kosulabilir
#
# Yaptigi iki is:
#   1. backend/ paketini duzenlenebilir (editable) kurar -> `import spor_toto`
#      ve `spor-toto` komutu her dizinden calisir.
#   2. frontend/node_modules yoksa npm bagimliliklarini kurar.
#
# **`--kalite` neden var ve neden VARSAYILAN DEGIL.** Kapinin ilk adimi
# `ruff` ve o `[kalite]` ekstrasinda; varsayilan kurulum onu getirmiyordu,
# yani "kurulumu yaptim" diyen biri `scripts/check.sh`i kosturamiyordu —
# kapi ilk satirda `No module named ruff` ile duserdi. Varsayilana eklemek
# de dogru degil: `.replit` `[deployment] build` -> `scripts/build.sh` ->
# BU BETIK, yani varsayilan uretim derlemesinde de kosuyor ve ruff/mypy/
# pip-audit'in uretim imajinda isi yok. Bu yuzden acik istege bagli.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"

KALITE=0
[[ "${1:-}" == "--kalite" ]] && KALITE=1

# Tek kaynak: hem kurulan ekstralar hem de asagidaki dogrulama listesi
# buradan turer. Ikisi ayrisirsa guard bos kalir — `xdist` dersi (asagida).
EKSTRALAR="test,model"
DOGRULANACAK=(flask numpy pytest xdist)
if [[ $KALITE -eq 1 ]]; then
  # CI'nin kalite kapisi isiyle AYNI kume. Ayrisirsa yerelde gecen kapi
  # CI'da baska bir sey kosar — bu betigin var olma sebebinin tersi.
  # `mcp` ve `ocr` de burada: yoklugunda testleri ATLANIR ve kapi yesil
  # kalir, yani sessizce daralir.
  EKSTRALAR="test,kalite,model,mcp,ocr"
  DOGRULANACAK+=(ruff mypy interrogate pip_audit mcp PIL)
fi

# ─── Python ───────────────────────────────────────────────────────────────────
# `xdist` de kontrol ediliyor, cunku bu koruma AKSI HALDE ZARARLI: pytest
# yapilandirmasi `-n auto` tasiyor ve xdist yoksa pytest hic acilmadan
# "unrecognized arguments" verir. Kurulu bir makinede kosul yalnizca
# spor_toto'ya baksaydi yeniden kurulum atlanir, xdist hic gelmez ve
# "Testler" dugmesi calismaz olurdu.
#
# `--kalite` verildiginde bu kosul kalite araclarini DA sormak zorunda: aksi
# halde test bagimliliklari kurulu bir makinede kurulum atlanir, `ruff` hic
# gelmez ve bayrak sessizce hicbir sey yapmaz — xdist'in dersinin aynisi.
if "$PY" -c "import spor_toto, $(IFS=,; echo "${DOGRULANACAK[*]}")" >/dev/null 2>&1; then
  echo "✓ Python bagimliliklari kurulu"
else
  echo "→ Python bagimliliklari kuruluyor (backend/)..."
  # `|| true` YOK. Once vardi ve gercek kurulum hatasini yutuyordu; asagidaki
  # guard yalnizca flask/numpy'ye baktigi icin eksik bir `pytest` ya da
  # `gunicorn` sessizce geciyor, sorun ancak testi/dagitimi kosarken
  # ortaya cikiyordu.
  if ! "$PY" -m pip install -q -e "./backend[$EKSTRALAR]"; then
    echo "! duzenlenebilir kurulum basarisiz; requirements.txt deneniyor" >&2
    "$PY" -m pip install -q -r backend/requirements.txt
  fi
fi

# Calisma ve test icin GEREKEN her sey burada dogrulanir — biri eksikse
# kurulum basarisiz sayilir. `xdist` de listede: pytest yapilandirmasi
# `-n auto` tasidigi icin o olmadan suit hic acilmiyor (yukaridaki atlama
# kosulu da tam bu yuzden onu soruyor; iki liste ayrisirsa guard bos kalir).
for _m in "${DOGRULANACAK[@]}"; do
  if ! "$PY" -c "import $_m" >/dev/null 2>&1; then
    echo "✗ '$_m' kurulamadi. Elle deneyin:" \
         "$PY -m pip install -e './backend[$EKSTRALAR]'" >&2
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

if [[ $KALITE -eq 1 ]]; then
  echo "✓ kurulum tamam (kalite araclari dahil — 'bash scripts/check.sh' kosabilir)"
else
  echo "✓ kurulum tamam"
  echo "  not: kapiyi kosturmak icin 'bash scripts/setup.sh --kalite' gerekir"
fi
