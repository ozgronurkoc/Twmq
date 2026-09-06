#!/usr/bin/env bash
#
# Deponun TEK kalite kapısı — iki tarafı da koşturur.
#
#   bash scripts/check.sh            # her şey
#   bash scripts/check.sh --hizli    # yavaş ölçüm testlerini atla
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

# `.claude/` KAPSAM DISINDAYDI. Yukaridaki cagri `backend/`ten kosuyor ve
# deponun kendi ajan betikleri (`graf_uret`, `graf_sorgu`, `graf_baglam`,
# hook'lar — ~700 satir) ne lint ne tip denetimi goruyordu. Ayni kural
# kumesiyle kosuluyor; yapilandirma `backend/pyproject.toml`da oldugu icin
# bayraklar acikca veriliyor.
#
# Vendor edilmis skill (`.claude/skills/`) BILEREK disarida: bizim kodumuz
# degil, upstream'den geldigi gibi duruyor ve tek basina 1.596 bulgu
# uretiyor — yani gercek bulgularin uzerini orterdi.
# Kural kumesi `backend/pyproject.toml` ile AYNI — `S` (guvenlik) dahil.
# Onceden `S` burada yoktu, yani depo kendi ajan betiklerini backend'e
# uyguladigi kuralla olcmuyordu; iki `subprocess` cagrisi denetimsizdi.
"$PY" -m ruff check "$KOK/.claude"/*.py "$KOK/.claude/hooks" \
  --line-length 100 --target-version py310 \
  --select E,W,F,I,UP,B,C4,RUF,S \
  --ignore E501,B905,RUF001,RUF002,RUF003,S101,S311,S607

baslik "mypy (kademeli tip denetimi)"
"$PY" -m mypy

# `.claude/` TIP denetimi de burada. Yukaridaki ruff blogunun yorumu
# "ne lint ne tip denetimi goruyordu" diye basliyor ama YALNIZCA lint
# ekliyordu; cumlenin isaret ettigi boslugun yarisi acik kalmisti. O yarim
# bu oturumda bir hata ortaya cikardi: `graf_uret.sayilar_denetle` uc
# elemanli demet listesi donduruyor ama `list[str]` ilan ediyordu ve
# cagirma yerinde "Unpacking a string is disallowed" veriyordu.
#
# Ayarlar acikca veriliyor: yapilandirma `backend/pyproject.toml`da ve o
# dosya `files` ile kendi agacini sayiyor.
"$PY" -m mypy "$KOK/.claude"/*.py \
  --python-version 3.10 --ignore-missing-imports --no-error-summary \
  && echo "  .claude: temiz"

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
  spor_toto/ortak.py spor_toto/getiri.py spor_toto/takim.py spor_toto/deger.py \
  spor_toto/odds.py spor_toto/egitim.py spor_toto/hafta_hakki.py

baslik "pytest (hızlı)"
# `-rs`: ATLANAN her test sebebiyle birlikte yazilir. `-q` onlari
# gizliyordu ve sessiz atlama bu depoda gercek bir zarar verdi — `mcp` ve
# `ocr` ekstralari hicbir CI isinde kurulmadigi icin iki test bir kez bile
# kosmamisti ve kapi her seferinde yesil dedi. Gorunur bir atlama karar
# konusudur; gorunmez olan bir yalandir.
"$PY" -m pytest -m "not slow" -q -rs

if [[ $HIZLI -eq 0 ]]; then
  baslik "pytest (yavaş ölçüm)"
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
#
# HAFTA SABIT YAZILMIYOR. Once "--hafta 2" yaziyordu ve bu, yukaridaki
# "Haftalar SABIT YAZILMAZ" kuralini kendi dosyasinda cigniyordu: ucuncu bir
# `_tahmin2` kaydi girildigi gun kapi ona hic bakmayacakti — kapinin sessizce
# kuculmesi, tam olarak yakalamasi gereken sey. Liste artik diskten cikiyor.
TAHMIN2=$("$PY" -c "
import re
from pathlib import Path
d = Path('data/super_toto/2026_27')
print(' '.join(sorted(str(int(re.findall(r'hafta_(\\d+)_tahmin2\\.json', f.name)[0]))
                      for f in d.glob('hafta_[0-9][0-9]_tahmin2.json'))))")
echo "   2. tahmin kayitli haftalar: $TAHMIN2"
for h in $TAHMIN2; do
  "$PY" scripts/super_toto_tahmin2.py --hafta "$h" --tarih 2026-01-01 --json \
    | "$PY" -c "import json,sys; d=json.load(sys.stdin); k=d['kupon']; \
        assert len(k['ayarli']['picks'])==15; \
        assert k['taban']['columns']==k['ayarli']['columns']"

  # "Sonuclar gorulmeden uretildi" DISKTEKI kayittan denetlenir. Once taze
  # govdeden okunuyordu; hafta kapanip sonuc girilince taze govde dogru
  # sekilde `true` demeye baslar ve kapi kendi dogru davranisina takilirdi.
  "$PY" -c "import json,sys; \
      d=json.load(open('data/super_toto/2026_27/hafta_%02d_tahmin2.json' % int(sys.argv[1]))); \
      assert d['meta']['results_known'] is False" "$h"

  # Sonuc girilmis haftanin degerlendirmesi: iki kayit da puanlanmali.
  # Sonucu GIRILMEMIS hafta bu adimi atlar — `_tahmin2` kaydinin olmasi
  # sonucun da girildigi anlamina gelmez.
  if echo " $SONUCLU " | grep -q " $h "; then
    "$PY" scripts/super_toto_degerlendir.py --hafta "$h" --json \
      | "$PY" -c "import json,sys; d=json.load(sys.stdin); \
          assert len(d['results'])==15; assert d['tahmin2']; \
          assert d['kiyas']['union_best'] >= max(x['best'] for x in d['coupons'])"
  fi
done

# Hafta raporu sayfasi: kapida hic kosmuyordu ve tam bu yuzden sessizce
# kirildi (sonucu girilmis ama ikramiyesi girilmemis haftada KeyError).
for h in $HAFTALAR; do
  "$PY" scripts/super_toto_sayfa.py --hafta "$h" --cikti "$(mktemp -u).html" >/dev/null
done

# Üretilmiş iki dosya: bayatlarsa arayüz SESSIZCE yanlış olur.
baslik "üretilmiş üç dosya güncel mi"
"$PY" scripts/super_toto_frontend.py --kontrol
"$PY" scripts/api_sozlesme.py --kontrol
# Ucuncu uretilmis dosya. `data/odds/fiyat_kaynaklari.json` surumleniyor ve
# `odds.py` ile `fiyatlar.py` docstring'lerinden aniliyordu, ama hicbir sey
# onu diskteki gercekle karsilastirmiyordu — arsiv buyudugunde sessizce
# bayatlardi. Ustteki iki bekcinin ayni deseni.
"$PY" scripts/fiyat_kaynaklari.py --kontrol

# ─── Frontend ────────────────────────────────────────────────────────────
cd "$KOK/frontend"

if [[ ! -d node_modules ]]; then
  echo "! node_modules yok — 'bash scripts/setup.sh' çalıştırın" >&2
  exit 1
fi

# `npm run check` = lint + typecheck + check.mjs (sozlesme denetimi dahil).
baslik "eslint + tsc + arayüz denetimleri (sözleşme dahil)"
npm run check

# Portlar derlemeden ONCE secilir ve `API_PORT` disari verilir: rewrite'lar
# `next.config.mjs`te DERLEME ZAMANINDA gomuluyor (dosyanin kendi basligi
# bunu yaziyor). Varsayilan olmayan bir port secmek ayrica o dosyanin
# duzeltmesini de sinar — "backend'in portu degisince proxy onu izleyemiyordu"
# cumlesi artik bir iddia degil, kapinin kostugu bir sey.
API_PORT="$("$PY" -c "
import socket
s = socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()")"
UI_PORT="$("$PY" -c "
import socket
s = socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()")"
export API_PORT

baslik "üretim derlemesi"
npm run build >/dev/null

# ─── Üretim topolojisi dumanı ────────────────────────────────────────────
#
# **Niçin var.** Ürünün gerçekten koştuğu yol `scripts/run_prod.sh`tir:
# gunicorn `127.0.0.1`de (dışarıya kapalı) + `next start` dışarıya açık tek
# portta + `/api/*` rewrite ile arkaya proxy. Bu zincirin TAMAMI hiçbir
# testte, hiçbir kapıda ve hiçbir CI işinde ayağa kalkmıyordu. Uçların
# kendisi `test_api_*` ile Flask'ın `test_client`ından geçiyor — yani WSGI
# çağrısı deneniyor, ama gunicorn, port bağlama, Next'in ayakta olması ve
# rewrite'ın hedefi tutması denenmiyordu.
#
# Elle sürüldüğünde (2026-09-03) tertemiz çıktı; bu adım o ölçümü kalıcı
# kılıyor. `curl` KULLANILMIYOR: kapı yeni bir araca bağlanmasın diye
# istekler Python'un stdlib'iyle atılıyor.
baslik "üretim topolojisi dumanı (gunicorn + next start + proxy)"
echo "   API 127.0.0.1:$API_PORT · UI 127.0.0.1:$UI_PORT"

API_PID=""; UI_PID=""
temizle() {
  [[ -n "$UI_PID"  ]] && kill "$UI_PID"  2>/dev/null || true
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
}
trap temizle EXIT

( cd "$KOK/backend" && exec "$PY" -m gunicorn \
    --bind="127.0.0.1:$API_PORT" --workers 1 --timeout 120 web_app:app \
    >/tmp/twmq_gunicorn.log 2>&1 ) &
API_PID=$!
npx next start -H 127.0.0.1 -p "$UI_PORT" >/tmp/twmq_next.log 2>&1 &
UI_PID=$!

# Ikisi de ayaga kalkana kadar bekle; kalkmazsa gunlugu ADIYLA goster.
"$PY" - "$API_PORT" "$UI_PORT" <<'PYEOF'
import sys, time, urllib.error, urllib.request

def bekle(ad, url, saniye=90.0):
    son = None
    bitis = time.monotonic() + saniye
    while time.monotonic() < bitis:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            son = e
        time.sleep(0.5)
    sys.exit(f"! {ad} {saniye:.0f} sn icinde ayaga kalkmadi ({son}) "
             f"— gunluk: /tmp/twmq_gunicorn.log, /tmp/twmq_next.log")

api, ui = sys.argv[1], sys.argv[2]
bekle("API", f"http://127.0.0.1:{api}/health")
bekle("UI", f"http://127.0.0.1:{ui}/")
PYEOF

# Zincirin TAMAMI UI portundan surulur — yani rewrite gercekten hedefi
# tutuyor mu, tek dis port yeterli mi, govdeler bozulmadan geciyor mu.
"$PY" - "$UI_PORT" <<'PYEOF'
import json
import sys
import urllib.request

ui = sys.argv[1]
kok = f"http://127.0.0.1:{ui}"


def al(yol):
    with urllib.request.urlopen(kok + yol, timeout=180) as r:
        return r.status, r.read()


# 1) Arayuzun butun sayfalari uretim sunucusundan 200 donmeli.
sayfalar = ["/", "/saglik", "/super-toto", "/istatistik", "/istatistik/geri-test",
            "/istatistik/oranlar", "/takimlar", "/pazarlar", "/tahmin"]
for yol in sayfalar:
    kod, govde = al(yol)
    assert kod == 200, f"{yol} -> {kod}"
    # Next hata sayfasini da 200 ile dondurebilir; govdeye bakilir.
    assert b"__next_error__" not in govde, f"{yol}: sayfa hata durumunda render edildi"

# 2) `/health` (liveness) ve `/api/*` PROXY uzerinden — asil sinanan bu.
kod, govde = al("/health")
assert kod == 200 and json.loads(govde)["service"] == "spor-toto-api", "liveness proxy'si kirik"

kod, govde = al("/api/meta")
meta = json.loads(govde)
assert meta["match_count"] == 15, f"/api/meta proxy uzerinden bozuk: {meta.get('match_count')}"

kod, govde = al("/api/health")
rapor = json.loads(govde)
assert rapor["summary"]["kayitli_kontrol"] >= 1, "/api/health proxy uzerinden bozuk"

print(f"   {len(sayfalar)} sayfa + 3 uc proxy uzerinden dogrulandi")
PYEOF

temizle
trap - EXIT

printf '\n\033[1;32m✓ check.sh geçti\033[0m (%s sn)\n' "$(( $(date +%s) - BASLANGIC ))"
