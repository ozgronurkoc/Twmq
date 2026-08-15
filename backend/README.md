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
  report.py    Konsol / dosya çıktısı
  cli.py       spor-toto komut satırı
web_app.py     Flask — /api/solve, /api/stats, /api/health
data/          Tarihsel 1/0/2 verisi (spor_toto/history.py buradan okur)
tests/
```

`data/` yolu `spor_toto/history.py` içinde `__file__` üzerinden çözülür
(`backend/spor_toto/` → `backend/data/`), yani çalışma dizininden bağımsızdır.

## API

Uç noktalar ve `POST /api/solve` gövdesi için: `../docs/ARCHITECTURE_NEXT.md`.
