# backend/

Spor Toto kaplama kodu motoru + JSON API. **HTML servis etmez** — arayüz
`../frontend/` altındaki Next.js uygulamasıdır.

## Kurulum

```bash
cd backend
pip install -e ".[test]"
```

`scipy` yoksa araç çalışır, yalnızca kesin çözücü (ILP) devre dışı kalır.

## Çalıştırma

```bash
# API (kök dizinden de çalışır: python backend/web_app.py)
python web_app.py                 # http://localhost:8080

# CLI
python -m spor_toto.cli --picks "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"

# Health (değişmezler)
python -m spor_toto.health
python -m spor_toto.health --list           # kontrol envanteri
python -m spor_toto.health --only olasilik  # tek kategori
```

Ortam değişkenleri (hepsi isteğe bağlı):

| Değişken | Varsayılan | Ne yapar |
|---|---|---|
| `PORT` | `8080` | Flask'ın dinlediği port (`web_app.py` doğrudan koşarken) |
| `API_PORT` | `8080` | `run_next_dev.sh` / `run_prod.sh` API'yi buraya bağlar ve `PORT` olarak geçirir |
| `UI_PORT` | `3000` | Aynı betiklerde Next.js portu |
| `CORS_ALANLARI` | `replit.dev,replit.app,repl.co` | İzinli origin **alan adları**, virgülle. Verilirse varsayılanın yerini alır |
| `SESSION_SECRET` | `spor-toto-api` | Flask oturum anahtarı |
| `HEALTH_TTL_S` | `5` | `/api/health` önbellek ömrü (sn); `?fresh=1` atlar |
| `HEALTH_HISTORY_LIMIT` | `200` | Sunucudaki koşu geçmişi tamponu |
| `HEALTH_ALARM_URL` | — | Tanımlıysa durum DEĞİŞİMİNDE buraya POST atılır |
| `HEALTH_ALARM_TIMEOUT_S` | `5` | Alarm isteğinin zaman aşımı |
| `INSTANCE_ID` | — | Rapordaki örnek etiketi (çok örnekli dağıtım); yoksa `REPL_ID` |

> `CORS_ALANLARI` **hostname** üzerinden eşleşir, substring olarak değil:
> `https://x.replit.app.saldirgan.com` reddedilir. Önceki sürüm substring
> bakıyordu ve tam bu origin geçiyordu.

## Testler

```bash
cd backend
pytest -m "not slow"        # hızlı süit (~77 sn, 4 çekirdek)
pytest                      # tamamı (ILP testleri dahil)
# Kalite kapisi repo KOKUNDEDIR ve iki tarafi da kosturur; CI de onu cagirir.
# (Buradaki `backend/scripts/check.sh` silindi: "CI ile ayni cekirdek adimlar"
#  diyordu ama alti adimdan ucunu kosuyordu.)
cd .. && bash scripts/check.sh
```

Süit varsayılan olarak **paralel** koşar (`-n auto`, pytest-xdist): ağırlığı
korpus üzerinde dönen birbirinden bağımsız modüllerde ve tek süreçte
çekirdeklerin çoğu boş duruyordu. Hata ayıklarken `-n0` ile kapatılır —
çıktı sırası da o zaman düzelir:

```bash
pytest -n0 tests/test_egitim.py -x
```

## Yapı

> **Aşağıdaki modül listesi bir SEÇKİdir, envanter değil.** 51 modülün tam
> listesi tek yerdedir — kök `README.md` §7 — ve orayı bir bekçi dosya
> sistemine karşı tutar (`tests/test_belgeler.py::test_readme_modul_listesi_eksiksiz`).
> Buraya ikinci bir tam liste yazmak, eskiyecek ikinci bir liste yaratmak
> olurdu; bu dosyanın sayıları tam olarak öyle bayatladı.

```
spor_toto/                        (51 modül — aşağısı yönlendirici seçki)
  core.py      Encoder, Fix-16, ILP, heuristic, exact olasılık
  engines.py   Mod çalıştırıcıları — /api/solve, health ve CLI AYNI yolu kullanır
  meta.py      Yetenek envanteri (modlar, preset'ler, sınırlar) = /api/meta
  cli.py       spor-toto komut satırı
  report.py    Konsol / dosya çıktısı
  analysis.py  Monte Carlo, maç bazlı hata frekansı
  bayes.py     Dirichlet prior → posterior, KL, preset'ler
  markov.py    Seçim hayatta kalma + hata bütçesi zinciri
  fire_scenarios.py  Seçim DIŞI fire analizi (1-fire / 2-fire)
  history.py   Tarihsel 1/0/2 + analiz blokları
  odds.py      Oran arşivi okuyucu; arayüze yalnızca 1X2 çıkar (aşağıda)
  backtest.py  Eşikli strateji → kaplama → skor; eşik taraması + hold-out
  egitim.py    Eğitim korpusu okuyucu (31.103 maç) — /istatistik'e GİRMEZ
  predict.py   TAHMİN: tahminci sözleşmesi + 3 referans
  evaluate.py  TAHMİN: dışarıda bırakmalı ölçüm + eşleştirilmiş bootstrap
  recalibrate.py  TAHMİN: piyasanın yeniden kalibrasyonu (kademe, Newton)
  tahmin.py    TAHMİN: yaklaşan maçlar + ölçülmüş isabet = /api/tahmin
  benzer.py    "Bu oranda geçmişte ne oldu" = /api/benzer
  cizgi.py     ÖLÇÜM: açılış→kapanış çizgi hareketi (A1)
  bahisci.py   ÖLÇÜM: bahisçiler arası ayrışma (A2)
  disari.py    ÖLÇÜM: piyasanın fiyatlamadığı bir şey kalıyor mu (A3)
  kalibrasyon.py  ÖLÇÜM: izotonik düzeltme piyasayı geçiyor mu
  ortak.py     Paylaşılan hesaplar: normalizasyon, Wilson, Brier, bantlama
  payloads.py  Uç gövdeleri — tek kaynak (health bunları denetler)
  health.py    Kategorili değişmez (invariant) kontrolleri — 27 kontrol
  health_history.py  Sunucu tarafı koşu geçmişi + durum değişimi bildirimi
web_app.py     Flask — 15 uç, yalnızca JSON (tam liste: ARCHITECTURE_NEXT.md)
scripts/                          (28 betik + __init__.py — normal paket)
  build_history.py  Tarihsel veri setini kaynağından üretir
  build_odds.py     Kupon maçlarına piyasa oranlarını eşleştirir
  build_egitim.py   Eğitim korpusu (football-data, 22 lig × 4 geçmiş sezon)
  build_hakem.py    Hakem sütunu — korpusa DEĞİL ayrı tabloya (E4, `--kontrol`)
  build_fixtures.py Yaklaşan maç fikstürü (tahmin katmanının kaynağı)
  snapshot_iddaa.py İddaa açık bültenini tarih damgalı arşivler
  super_toto_*.py   Canlı sezon boru hattı (hafta, değerlendir, sezon, sayfa,
                    frontend beslemesi — sonuncusu `--kontrol` ile CI kapısı)
  api_sozlesme.py   API sözleşmesini üretir/denetler (`--kontrol`: CI kapısı)
  faz_b.py          Havuz ekseni güç analizi
  hafta_kos.py      Haftalık döngü: `--oncesi` kupon, `--sonrasi` karne
  acilis_kapanis.py Açılış–kapanış oranı karşılaştırması
  devir_tavani.py   ÖLÇÜM: devir çarpanı `1+d` ve pozitif BD koşulu
                    (`DIS_TARAMA_PIYASAYI_YENME.md` §4–§5)
data/
  st_history_2025_26.json   Tarihsel 1/0/2 (history.py buradan okur)
  odds/                     Oran arşivi (aşağıda)
  iddaa/ egitim/ fixtures/ super_toto/ hakem/
tests/                            (71 dosya → 2.049 test)
```

> **ÖLÇÜM modülleri arayüze çıkmaz** ve yalnızca `python -m spor_toto.<ad>`
> ile koşulur. Ölü kod değildirler; A1–A3 ölçümlerinin koşum yüzeyidirler.

`data/` yolu `spor_toto/history.py` içinde `__file__` üzerinden çözülür
(`backend/spor_toto/` → `backend/data/`), yani çalışma dizininden bağımsızdır.

## Veri üretimi

```bash
python scripts/build_history.py     # tarihsel 1/0/2 setini yeniden üret
python scripts/build_odds.py        # oranları çek ve kupon maçlarına eşleştir
```

İkisi de doğrulama yapmadan dosya yazmaz; `tests/test_history.py` ve
`tests/test_odds.py` sonucu bağımsız olarak bir kez daha denetler.

## Oran arşivi (`data/odds/`)

**Arayüze yalnızca MAÇ SONUCU (1X2) çıkar.** Burada bir zamanlar "hiçbir API
ucu, sayfa ya da motor akışı buradan okumaz" yazıyordu; artık doğru değil:
`/api/stats` bir `odds` bloğu döndürüyor, `/api/benzer` bu korpusa dayanıyor
ve `backtest` `match_1x2`yi çağırıyor.

Arşivdeki **diğer pazarlar** (2,5 alt/üst, Asya handikap) ve maç istatistikleri
API'ye hiç girmez — onlar analiz için durur ve bu ayrım kasıtlıdır.

| Dosya | Durum | İçerik |
|-------|-------|--------|
| `odds_2025_26.csv` | sürümlenir | Maç başına bir satır, 108 oran sütunu + 14 maç istatistiği |
| `odds_rapor.json` | sürümlenir | Kapsama raporu, sütun sözlüğü, eşleşmeyen maçlar |
| `odds.sqlite3` | git dışı | Sorgulanabilir kopya (`mac`, `oran`, `istatistik` tabloları) |
| `_kaynak/*.csv` | git dışı | İndirilen ham football-data.co.uk dosyaları |

Pazarlar: 1X2 (11 bahisçi × açılış/kapanış), 2.5 alt/üst, Asya handikap.
Bunlardan **yalnızca 1X2** arayüze çıkar (`/api/stats`, `/api/stats/<week>`);
gerisi burada analiz için durur.
Kaynak **piyasa oranlarıdır, iddaa değildir** — gerekçe:
`../docs/VERI_TOPLAMA_VE_ISLEME.md` §3.2. Katmanın tamamı ve yol haritası:
`../docs/ISTATISTIK_YOL_HARITASI.md`.

```python
from spor_toto.odds import load_odds, market_odds, implied_probs
r = load_odds()[0]
implied_probs(market_odds(r, "1X2", "Avg"))   # {"1": .., "0": .., "2": ..}
```

```sql
-- SQLite: bir pazarın tamamı
SELECT m.week, m.no, m.home, m.away, o.secim, o.deger
FROM oran o JOIN mac m USING (week, no)
WHERE o.pazar = '1X2' AND o.donem = 'kapanis' AND o.kaynak = 'Avg';
```

## API

Uç noktalar ve `POST /api/solve` gövdesi için: `../docs/ARCHITECTURE_NEXT.md`.
