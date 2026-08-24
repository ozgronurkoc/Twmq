#!/usr/bin/env bash
#
# Deponun TEK kalite kapısı — iki tarafı da koşturur.
#
#   bash scripts/check.sh            # her şey
#   bash scripts/check.sh --hizli    # yavaş ILP testlerini atla
#
# **Neden var.** Önceden `backend/scripts/check.sh` vardı ve "CI ile aynı
# çekirdek adımlar" diyordu, ama CI'nın altı adımından üçünü koşuyordu:
# `pytest -m slow`, Süper Toto boru hattı dumanı ve besleme tazeliği
# denetimi eksikti. Yani o betiğin "OK" demesi artık "CI geçer" demek
# değildi. Üstelik arayüz tarafına hiç bakmıyordu ve dosya `644` idi —
# dizindeki tek çalıştırılamayan betik.
#
# CI artık bu betiği ÇAĞIRIR (adımları yeniden yazmaz), dolayısıyla ikisi
# tanım gereği ayrışamaz.
set -euo pipefail
KOK="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KOK"

HIZLI=0
[[ "${1:-}" == "--hizli" ]] && HIZLI=1

PY="${PYTHON:-python3}"
BASLANGIC=$(date +%s)

baslik() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# ─── Backend ─────────────────────────────────────────────────────────────
cd "$KOK/backend"

baslik "ruff (lint)"
"$PY" -m ruff check .

baslik "mypy (kademeli tip denetimi)"
"$PY" -m mypy

baslik "pytest (hızlı)"
"$PY" -m pytest -m "not slow" -q

if [[ $HIZLI -eq 0 ]]; then
  baslik "pytest (yavaş ILP)"
  "$PY" -m pytest -m slow -q
fi

baslik "system health (değişmezler)"
"$PY" -m spor_toto.health

baslik "CLI duman"
ORNEK="1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
PROBS="1:0.5,0:0.3,2:0.2;1:0.4,0:0.4,2:0.2;1:0.6,0:0.2,2:0.2;1:0.5,0:0.25,2:0.25;1:0.3,0:0.4,2:0.3;1:0.45,0:0.35,2:0.2;1:0.5,0:0.3,2:0.2;1:0.4,0:0.3,2:0.3;1:0.55,0:0.25,2:0.2;1:0.5,0:0.3,2:0.2;1:0.4,0:0.3,2:0.3;1:0.5,0:0.3,2:0.2;1:0.45,0:0.35,2:0.2;1:0.5,0:0.25,2:0.25;1:0.4,0:0.4,2:0.2"
"$PY" -m spor_toto.cli --picks "$ORNEK" --kisa >/dev/null
"$PY" -m spor_toto.cli --picks "$ORNEK" --probs "$PROBS" \
  --bayes-preset dengeli --kisa >/dev/null

# Boru hattı: canlı sezonun tek yolu. Veri repoda olduğu için ağ gerekmez.
# JSON çıktısı ayrıca ayrıştırılır — sıfır çıkış kodu tek başına yeterli
# değil, bozuk JSON da sıfırla dönebilir.
baslik "Süper Toto boru hattı dumanı"
for h in 1 2; do
  "$PY" scripts/super_toto_hafta.py --hafta "$h" --json \
    | "$PY" -c "import json,sys; d=json.load(sys.stdin); \
        assert len(d['profile']['rows'])==15; assert d['coupons'][0]['picks']"
done
"$PY" scripts/super_toto_degerlendir.py --hafta 1 --json \
  | "$PY" -c "import json,sys; d=json.load(sys.stdin); \
      assert len(d['results'])==15; assert abs(sum(d['coupons'][0]['dist'])-1) < 1e-9"

# 2. Tahmin: ikinci kayit da ayni boru hattinin parcasi. Ayarli plan tabanla
# AYNI bedelde olmali — degilse "ayar bedava" cumlesi yalan olur.
"$PY" scripts/super_toto_tahmin2.py --hafta 2 --tarih 2026-01-01 --json \
  | "$PY" -c "import json,sys; d=json.load(sys.stdin); k=d['kupon']; \
      assert len(k['ayarli']['picks'])==15; \
      assert k['taban']['columns']==k['ayarli']['columns']; \
      assert d['meta']['results_known'] is False"

# Üretilmiş iki dosya: bayatlarsa arayüz SESSIZCE yanlış olur.
baslik "üretilmiş dosyalar güncel mi"
"$PY" scripts/super_toto_frontend.py --kontrol
"$PY" scripts/api_sozlesme.py --kontrol

# ─── Frontend ────────────────────────────────────────────────────────────
cd "$KOK/frontend"

if [[ ! -d node_modules ]]; then
  echo "! node_modules yok — 'bash scripts/setup.sh' çalıştırın" >&2
  exit 1
fi

# `npm run check` = lint + typecheck + check.mjs (sozlesme denetimi dahil).
baslik "eslint + tsc + arayüz denetimleri (sözleşme dahil)"
npm run check

baslik "üretim derlemesi"
npm run build >/dev/null

printf '\n\033[1;32m✓ check.sh geçti\033[0m (%s sn)\n' "$(( $(date +%s) - BASLANGIC ))"
