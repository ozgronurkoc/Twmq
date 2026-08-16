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

# Health (13 invariant)
python -m spor_toto.health
```

## Testler

```bash
cd backend
pytest -m "not slow"        # hızlı süit
pytest                      # tamamı (ILP testleri dahil, ~60 sn)
bash scripts/check.sh       # CI ile aynı çekirdek adımlar
```

## Yapı

```
spor_toto/
  core.py      Encoder, Fix-16, ILP, heuristic, exact olasılık
  analysis.py  Monte Carlo, maç bazlı hata frekansı
  bayes.py     Dirichlet prior → posterior, KL, preset'ler
  markov.py    Seçim hayatta kalma + hata bütçesi zinciri
  health.py    13 invariant health check
  history.py   Tarihsel 1/0/2 + analiz blokları
  odds.py      Oran arşivi okuyucu — YALNIZCA analiz için, API'ye bağlı değil
  report.py    Konsol / dosya çıktısı
  cli.py       spor-toto komut satırı
web_app.py     Flask — /api/solve, /api/stats, /api/health
scripts/
  build_history.py  Tarihsel veri setini kaynağından üretir
  build_odds.py     Kupon maçlarına piyasa oranlarını eşleştirir
data/
  st_history_2025_26.json   Tarihsel 1/0/2 (history.py buradan okur)
  odds/                     Oran arşivi (aşağıda)
tests/
```

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

**Arayüze bağlı değildir** — ileride yapılacak analiz için durur. Hiçbir API
ucu, sayfa ya da motor akışı buradan okumaz.

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
