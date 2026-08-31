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

# Kalite araclari `[kalite]` ekstrasinda ve `setup.sh`in VARSAYILANI onlari
# kurmuyor (gerekce orada: bu betik uretim derlemesinde de kosuyor). Onceden
# kapi bunu soylemeden `python -m ruff` satirinda `No module named ruff` ile
# duserdi — hangi komutun eksik oldugu ancak izi okuyarak anlasilirdi.
# Asagidaki `node_modules` bekcisinin simetrigi: eksigi ADIYLA ve caresiyle
# soyler, ilk adima hic girmeden.
EKSIK_KALITE=()
for _m in ruff mypy interrogate pip_audit; do
  "$PY" -c "import $_m" >/dev/null 2>&1 || EKSIK_KALITE+=("$_m")
done
if (( ${#EKSIK_KALITE[@]} )); then
  echo "! kalite araci yok (${EKSIK_KALITE[*]}) —" \
       "'bash scripts/setup.sh --kalite' calistirin" >&2
  exit 1
fi

baslik "ruff (lint)"
"$PY" -m ruff check .

baslik "mypy (kademeli tip denetimi)"
"$PY" -m mypy

baslik "docstring kapsaması (interrogate)"
# Bu depoda docstring bir gelenek; kapı onu kural yapar. Eşiğin gerekçesi
# ve ölçülen değer `pyproject.toml` `[tool.interrogate]` içinde.
"$PY" -m interrogate -c pyproject.toml spor_toto/

baslik "bağımlılık açıkları (pip-audit)"
# BEYAN EDİLEN bağımlılıklar denetlenir, bütün ortam değil — gerekçe
# `backend/scripts/bagimliliklar.py` başlığında (taban imajın paketleri
# bizim seçimimiz değil ve kapıyı kalıcı kırmızıya boyardı).
"$PY" scripts/bagimliliklar.py | "$PY" -m pip_audit -r /dev/stdin --progress-spinner off

baslik "doctest (belgelerdeki sayılar hâlâ doğru mu)"
# `sports-betting` incelemesinden geldi: docstring'lerimiz bu deponun en
# değerli parçalarından biri ama HİÇBİRİ yürütülmüyordu — sayı içeren bir
# docstring sessizce eskiyebilirdi. Tamamına değil, SAYI ÜRETEN
# fonksiyonlara örnek konuldu. `no:randomly`: doctest'ler tanım gereği
# sırasızdır, sabit sıra kapı çıktısını okunur tutar.
"$PY" -m pytest --doctest-modules -p no:randomly -q \
  spor_toto/ortak.py spor_toto/getiri.py spor_toto/takim.py spor_toto/deger.py

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
# Haftalar SABIT YAZILMAZ. Once "for h in 1 2" yaziyordu ve 3. hafta
# girildiginde kapi ona hic bakmadi — kapinin sessizce kuculmesi, tam olarak
# yakalamasi gereken sey. Liste artik diskteki hafta dosyalarindan cikiyor.
HAFTALAR=$("$PY" -c "
from pathlib import Path
import re
d = Path('data/super_toto/2026_27')
print(' '.join(sorted(str(int(re.findall(r'hafta_(\\d+)\\.json', f.name)[0]))
                      for f in d.glob('hafta_[0-9][0-9].json'))))")
echo "   haftalar: $HAFTALAR"
for h in $HAFTALAR; do
  "$PY" scripts/super_toto_hafta.py --hafta "$h" --json \
    | "$PY" -c "import json,sys; d=json.load(sys.stdin); \
        assert len(d['profile']['rows'])==15; assert d['coupons'][0]['picks']"
done
# Sonucu girilmis HER hafta degerlendirilir; liste yine diskten gelir.
SONUCLU=$("$PY" -c "
import json
from pathlib import Path
out = []
for f in sorted(Path('data/super_toto/2026_27').glob('hafta_[0-9][0-9].json')):
    if json.loads(f.read_text(encoding='utf-8'))['meta'].get('results'):
        out.append(str(int(f.stem.split('_')[1])))
print(' '.join(out))")
echo "   sonuclu haftalar: $SONUCLU"
for h in $SONUCLU; do
  "$PY" scripts/super_toto_degerlendir.py --hafta "$h" --json \
    | "$PY" -c "import json,sys; d=json.load(sys.stdin); \
        assert len(d['results'])==15; assert abs(sum(d['coupons'][0]['dist'])-1) < 1e-9"
done

# 2. Tahmin: ikinci kayit da ayni boru hattinin parcasi. Ayarli plan tabanla
# AYNI bedelde olmali — degilse "ayar bedava" cumlesi yalan olur.
"$PY" scripts/super_toto_tahmin2.py --hafta 2 --tarih 2026-01-01 --json \
  | "$PY" -c "import json,sys; d=json.load(sys.stdin); k=d['kupon']; \
      assert len(k['ayarli']['picks'])==15; \
      assert k['taban']['columns']==k['ayarli']['columns']"

# "Sonuclar gorulmeden uretildi" DISKTEKI kayittan denetlenir. Once taze
# govdeden okunuyordu; hafta kapanip sonuc girilince taze govde dogru
# sekilde `true` demeye baslar ve kapi kendi dogru davranisina takilirdi.
"$PY" -c "import json; \
    d=json.load(open('data/super_toto/2026_27/hafta_02_tahmin2.json')); \
    assert d['meta']['results_known'] is False"

# Sonuc girilmis haftanin degerlendirmesi: iki kayit da puanlanmali.
"$PY" scripts/super_toto_degerlendir.py --hafta 2 --json \
  | "$PY" -c "import json,sys; d=json.load(sys.stdin); \
      assert len(d['results'])==15; assert d['tahmin2']; \
      assert d['kiyas']['union_best'] >= max(x['best'] for x in d['coupons'])"

# Hafta raporu sayfasi: kapida hic kosmuyordu ve tam bu yuzden sessizce
# kirildi (sonucu girilmis ama ikramiyesi girilmemis haftada KeyError).
for h in $HAFTALAR; do
  "$PY" scripts/super_toto_sayfa.py --hafta "$h" --cikti "$(mktemp -u).html" >/dev/null
done

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
