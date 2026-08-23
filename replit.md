# Spor Toto Lab

Tarihsel veriyi ve piyasa oranlarını analiz edip **maç sonucu tahmini** üreten,
bu tahmini 14-garanti **kaplama kodu (covering code)** ile en az kupona indiren
motor; üstüne bu motoru sonuna kadar açan bir web arayüzü.

> **Amaç: kazanma oranını artırmak.** Hedefe bugünkü mesafe ölçülmüştür ve
> `README.md` §1.1'de yazar (hold-out isabeti 0 hafta, piyasa Brier 0,579, iddaa
> marjı %17,2). Ölçülmemiş hiçbir iyileşme iddia edilmez, ölçülmemiş hiçbir
> tahminci arayüze çıkmaz.

> Bu dosya Replit çalışma alanının hafızasıdır. Depo iki parçalıdır ve
> **Python HTML servis etmez**; arayüzün tamamı Next.js'tir. Mimari kararın
> gerekçesi: `docs/ARCHITECTURE_NEXT.md`.

## Yapı

```
backend/     Python — motor + JSON API (Flask). Hiç HTML yok.
frontend/    Next.js 14 App Router + TypeScript + Tailwind. Tek arayüz.
scripts/     setup.sh (bağımlılıklar), run_next_dev.sh (Run), build.sh, run_prod.sh
docs/        mimari, veri, istatistik yol haritası, sağlık vizyonu
```

## Çalıştırma

**Run düğmesi** `scripts/run_next_dev.sh` çalıştırır: Flask API arka planda
`:8080`, Next.js UI önde `:3000`. Replit önizlemesi `:3000`'i açar.

Hazır iş akışları (Workflows):

| İş akışı | Ne yapar |
|----------|----------|
| **Project / Start Lab** | UI + API birlikte (varsayılan, preview) |
| **Kurulum** | `scripts/setup.sh` — pip + npm bağımlılıkları (git pull sonrası) |
| **API only** | Yalnızca Flask `:8080` |
| **Testler** | `pytest -m "not slow"` |
| **Saglik** | `python -m spor_toto.health` — değişmez kontrolleri |
| **spor-toto** | CLI örneği, arayüzsüz formül üretimi |

### Git pull sonrası

```bash
bash scripts/setup.sh    # yeni bağımlılık geldiyse kurar, kuruluysa atlar
```

`setup.sh` `backend/`'i **editable** kurar; `import spor_toto` ve `spor-toto`
komutu her dizinden çalışır. `scripts/run_next_dev.sh` bunu kendisi çağırır,
yani Run düğmesi tek başına da yeterlidir.

### Önemli: `NEXT_PUBLIC_API_URL` boş kalmalı

`frontend/.env.local` içindeki değer **boş** olur. İstekler aynı origin'e gider,
`next.config.mjs` rewrite'ı `/api/*`'ı Flask `:8080`'e proxy'ler. Replit
önizlemesinde tarayıcı `127.0.0.1`'e ulaşamadığı için bu şarttır; run script'i
`127.0.0.1:8080` yazan bir `.env.local` bulursa proxy moduna geri alır.

## Sayfalar

| Yol | İçerik |
|-----|--------|
| `/` | **Formül** — maç ızgarası, olasılık girişi, motorun tüm modları |
| `/tahmin` | Yaklaşan maçlara 1/0/2 + **ölçülmüş isabet** (ayrılmaz) |
| `/super-toto` | Canlı sezon defteri (statik besleme) |
| `/istatistik` | Sezon dağılımı, oran/favori kırılımları, veri kalitesi |
| `/istatistik/[week]` | Hafta detayı (olasılıkları formül sayfasına devredebilir) |
| `/istatistik/geri-test` | Oranlardan strateji üretip 41 haftayı motorla koşturur |
| `/saglik` | Kategorili değişmez (invariant) kontrolleri, kısmi çalıştırma |

## API (Flask, `backend/web_app.py`)

```
GET  /api/meta               yetenek envanteri (modlar, preset'ler, ızgaralar)
GET  /health                 liveness — süreç ayakta mı (değişmez koşmaz)
GET  /api/health             readiness — değişmezler (?only=, ?fresh=1)
GET  /api/health/checks      kontrol envanteri (çalıştırmadan)
GET  /api/health/history     son koşular ("ne zamandan beri kırmızı?")
POST /api/health/kupon       kullanıcının kendi kuponunu doğrular
GET  /api/stats              sezon istatistikleri (?last=N)
GET  /api/stats/<week>       hafta detayı
GET  /api/backtest           geri test (eşik taraması + hold-out)
GET  /api/tahmin             yaklaşan maçlar + ölçülmüş isabet
GET  /api/benzer             "bu oranda geçmişte ne oldu" (31 bin maç)
GET  /                       servis bilgisi + uç envanteri
POST /api/solve              motorun tamamı
```

Sözleşmenin tamamı: `docs/ARCHITECTURE_NEXT.md` ve `frontend/lib/types.ts`.

## Motor (`backend/spor_toto/`)

`core.py` (Encoder, Fix-16, ILP, heuristic) · `engines.py` (mod çalıştırıcıları
— API ve sağlık aynı yolu kullanır) · `meta.py` (yetenek envanteri, `/api/meta`
tek kaynağı) · `analysis.py` (Monte Carlo, hata frekansı) · `bayes.py` (Dirichlet
prior → posterior) · `markov.py` (hata bütçesi) · `health.py` (değişmezler) ·
`history.py` (tarihsel 1/0/2) · `odds.py` (oran arşivi, yalnızca analiz) ·
`cli.py`.

### CLI

```bash
cd backend
python -m spor_toto.cli --picks "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
```

15 maç, virgülle ayrılır; bir maçın seçimleri bitişik yazılır:
`1` ev, `0` beraberlik, `2` deplasman, `10`/`02`/`12` çift, `102` üçlü.

Modlar: `--mode auto|exact|heuristic|butce|maxcov` (`--budget` ile),
`--variant 3` (alternatif 16 satır).

## Veri

- `backend/data/st_history_2025_26.json` — tarihsel 1/0/2 (sürümlenir)
- `backend/data/odds/` — piyasa oranları arşivi; CSV + rapor sürümlenir,
  SQLite kopyası ve ham kaynaklar git dışıdır
- `backend/data/iddaa/` — ileriye dönük iddaa bülteni snapshot'ları; tarih
  damgalı CSV'ler **sürümlenir** (arşivin kendisi odur)

Yeniden üretim: `python scripts/build_history.py`, `build_odds.py`,
`snapshot_iddaa.py` (hepsi `backend/scripts/` altında; doğrulamadan dosya
yazmazlar). Ayrıntı: `docs/VERI_TOPLAMA_VE_ISLEME.md`.

## Testler

```bash
cd backend
python -m pytest -m "not slow" -q   # hızlı süit
python -m pytest                    # tamamı (1.022 test, ILP dahil)
bash scripts/check.sh               # TEK kapı (repo kökünden); CI de bunu çağırır
```

GitHub Actions: `tests.yml` (her push) ve `snapshot-iddaa.yml` (haftalık bülten
arşivi).

## Dağıtım (Deploy)

Autoscale. `scripts/build.sh` bağımlılıkları kurup Next.js üretim derlemesini
alır; `scripts/run_prod.sh` gunicorn'u `127.0.0.1:8080`'de arka planda, Next.js'i
`0.0.0.0:3000`'de önde çalıştırır. Dışarıya tek port açılır (`3000 → 80`); API'ye
erişim UI'nin `/api/*` proxy'si üzerindendir.

## Değişmeyen ürün kuralları

1. **Semboller daima kupon düzeninde: 1, 0, 2.** Alfabetik sıralama `0,1,2`
   üretir ve kuponu elle doldururken hata yaptırır.
2. **Satır ≠ kolon.** Ödenecek tutar kolon sayısıdır; kolon bedeli hiçbir yerde
   satır sayısından ayrı gösterilmez.
3. **Frontend'de HTML yok.** Jinja şablonu, `.html` dosyası ve
   `dangerouslySetInnerHTML` kullanılmaz (tek istisna `app/layout.tsx`'in
   döndürdüğü kök JSX).

## User preferences
