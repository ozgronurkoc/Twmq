# Spor Toto Lab

Tarihsel veriyi ve piyasa oranlarını analiz edip **maç sonucu tahmini** üreten,
bu tahmini 14-garanti **kaplama kodu (covering code)** ile en az kupona indiren
motor; üstüne bu motoru sonuna kadar açan bir web arayüzü.

> **Amaç: kazanma oranını artırmak.** Hedefe bugünkü mesafe ölçülmüştür ve
> `README.md` §1.1'de yazar (hold-out isabeti **1 hafta**, piyasa Brier 0,579,
> iddaa marjı %17,2). Ölçülmemiş hiçbir iyileşme iddia edilmez, ölçülmemiş
> hiçbir tahminci arayüze çıkmaz.
>
> Hold-out burada uzun süre **0** yazıyordu: marj arındırma varsayılanı
> `orantili`dan `shin`e çevrilince (A5) o sayı 1'e çıkmıştı, bu satır ise
> güncellenmemişti. Tek bir olaydır ve güven aralıkları fazlasıyla örtüşür —
> okunacak sağlam sayı isabet değil maliyettir (kolon/hafta 6.897 → 2.228).

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
| `/super-toto` | Canlı sezon defteri (statik besleme); kaydı olan haftada `1. Tahmin` / `2. Tahmin` sekmeleri |
| `/istatistik` | **Sezon** — dağılım, seyir, bantlar, ısı haritası, haftalar (§6.8 G1'de bölündü) |
| `/istatistik/oranlar` | **Piyasa** — favori kırılımı, banko bantları, kalibrasyon; sekme şeridi `?last`i taşır |
| `/istatistik/[week]` | Hafta detayı (olasılıkları formül sayfasına devredebilir) |
| `/pazarlar` | **Alt/üst 2,5 ve Asya handikabı** — fiyat + ölçülmüş kalibrasyon |
| `/takimlar` | **Küçültülmüş takım gücü** — her satırda maç sayısı, küçültme oranı, %95 aralık |
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
GET  /api/pazar              1X2 disi pazarlar (alt/ust 2,5 · Asya handikabi)
GET  /api/takimlar           kucultulmus takim gucu (?lig=, ?sezon=)
GET  /api/benzer             "bu oranda geçmişte ne oldu" (31 bin maç)
GET  /                       servis bilgisi + uç envanteri
POST /api/solve              motorun tamamı
```

Sözleşmenin tamamı: `docs/ARCHITECTURE_NEXT.md` ve `frontend/lib/types.ts`.

## Motor (`backend/spor_toto/`)

26 modül var; tam liste ve tek satırlık açıklamaları `README.md` §7'dedir.
Katman katman:

- **Çekirdek** — `core.py` (Encoder, Fix-16, ILP, heuristic) · `engines.py`
  (mod çalıştırıcıları — API, CLI ve sağlık **aynı** yolu kullanır) ·
  `meta.py` (yetenek envanteri, `/api/meta` tek kaynağı) · `cli.py`
- **Analiz** — `analysis.py` (Monte Carlo, hata frekansı) · `bayes.py`
  (Dirichlet prior → posterior) · `markov.py` (hata bütçesi) ·
  `fire_scenarios.py`
- **Veri** — `history.py` (tarihsel 1/0/2) · `odds.py` (oran arşivi) ·
  `backtest.py` (eşikli strateji + hold-out) · `egitim.py` (31.103 maçlık
  korpus)
- **Tahmin** — `predict.py` (tahminci sözleşmesi) · `evaluate.py` (dışarıda
  bırakmalı ölçüm + bootstrap) · `recalibrate.py` · `tahmin.py`
  (`/api/tahmin`) · `benzer.py` (`/api/benzer`)
- **Ölçüm araçları** (yalnızca `python -m spor_toto.<x>`, arayüze çıkmaz) —
  `cizgi.py` (A1) · `bahisci.py` (A2) · `disari.py` (A3) · `kalibrasyon.py` ·
  `getiri.py` (müşterek beklenen değer — hesap var, **ölçüm yok**; §3.34)
- **Veri (Faz 3.4)** — `avrupa.py` (UEFA fiksturu takvime ENJEKTE edilir;
  `dinlenme`/`sikisiklik` artik o gunleri de gorur) · `sehir.py`
  (kulup-sehir tablosu, `openfootball/clubs` CC0; derbi bir SICAKLIK
  degiskeni). Uretim: `scripts/build_avrupa.py`, `scripts/build_sehir.py`
- **Veri (Faz 3.5)** — `xg.py`: korpusun kendi `sut`/`isabet` sayimindan
  KALIBRE EDILMIS beklenen gol. Katsayi `hudl/open-data`in (StatsBomb) 2015/16
  dort lig kesitinde (1.517 mac) gercek xG'ye karsi olculur; StatsBomb bir
  GIRDI degil REFERANStir — depo Super Lig'i ve alt Ingiliz liglerini
  kapsamiyor, korpusla kesisimi 92 mac ve canli akisi yok. Uretim:
  `scripts/build_xg.py`. **Lisans: ham veri commit EDILEMEZ** (StatsBomb
  Public Data User Agreement md. 1.2.1); depoya yalnizca katsayi + rapor
  girer, yayimlanan analiz StatsBomb logosuyla kunyelenir (md. 1.4)
- **Takım** — `takim_gucu.py` (`/api/takimlar`): ampirik Bayes kucultmesi,
  lig icinde; her satirda `n`, `kucultme` ve %95 aralik. §7'nin "takim bazli
  istatistik yok" yasagi buradan kalkti (§3.35)
- **Altyapı** — `kosum.py` (olcum kosum defteri: yedi CLI'da `--kaydet`,
  korpus sha256 + commit + tohum yazilir; defter SURUMLENMEZ) ·
  `artefakt.py` (egitilmis modelin JSON zarfi: korpus sha256 +
  egitim tarihi + surum; bayatlik `health`te KIRMIZI — `--yaz` ile uretilir,
  surumlenmez)
- **Ortak / gövde** — `ortak.py` (normalizasyon, Wilson, Brier, bantlama) ·
  `payloads.py` (uç gövdeleri, tek kaynak) · `health.py` (27 değişmez) ·
  `health_history.py` · `report.py`

> `odds.py` burada uzun süre "yalnızca analiz" diye yazılıydı; **artık değil**.
> `/api/stats` bir `odds` bloğu döndürüyor ve `backtest` `match_1x2`yi
> çağırıyor. **Arşivdeki diğer pazarlar da artık çıkıyor** (§3.31):
> alt/üst 2,5 ve Asya handikabı `pazar.py` → `/api/pazar` → `/pazarlar`
> yolunu izliyor, ölçülmüş kalibrasyonlarıyla birlikte. Maç istatistikleri
> (şut, korner) hâlâ API'ye girmiyor — onlar `egitim.py`nin form
> tablosunun girdisi.

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
python -m pytest                    # tamamı (1.701 test, ILP dahil)
python -m pytest -n0 tests/test_egitim.py   # tek çekirdek (hata ayıklarken)
cd .. && bash scripts/check.sh      # TEK kapı; CI de bunu çağırır
```

Süit **paralel** koşar (`-n auto`, pytest-xdist — `pyproject.toml` `addopts`).
`setup.sh` xdist'i de doğrular: o olmadan pytest hiç açılmaz.

`check.sh` ruff ve mypy de koşturduğu için `kalite` ekstrasını ister:
`pip install -e "./backend[test,kalite]"`.

GitHub Actions: `tests.yml` (her push) ve `snapshot-iddaa.yml` (haftalık bülten
arşivi). `tests.yml` iki iştir — `matris` hızlı süiti ve değişmezleri Python
3.10–3.13'te koşar (`.replit` python-3.10 kullanıyor, yani ürünün koştuğu sürüm
de matriste), `kapi` ise `scripts/check.sh`i çağırır.

## Dağıtım (Deploy)

Autoscale. `scripts/build.sh` bağımlılıkları kurup Next.js üretim derlemesini
alır; `scripts/run_prod.sh` gunicorn'u `127.0.0.1:8080`'de arka planda, Next.js'i
`0.0.0.0:3000`'de önde çalıştırır. **Dağıtımda** dışarıya tek port açılır
(`3000 → 80`); API'ye erişim UI'nin `/api/*` proxy'si üzerindendir ve gunicorn
loopback'e bağlandığı için dışarıdan doğrudan erişilemez.

> **Çalışma alanı bundan farklıdır ve bilerek öyledir.** `.replit` geliştirme
> tarafında `8080 → 8080`'i de yayımlar, çünkü **API only** iş akışı
> (`waitForPort = 8080`, webview) UI olmadan uçlara bakabilmek için buna
> dayanır. "Tek port" cümlesi dağıtım hakkındadır, çalışma alanı hakkında
> değil.

## Değişmeyen ürün kuralları

1. **Semboller daima kupon düzeninde: 1, 0, 2.** Alfabetik sıralama `0,1,2`
   üretir ve kuponu elle doldururken hata yaptırır.
2. **Satır ≠ kolon.** Ödenecek tutar kolon sayısıdır; kolon bedeli hiçbir yerde
   satır sayısından ayrı gösterilmez.
3. **Frontend'de HTML yok.** Jinja şablonu, `.html` dosyası ve
   `dangerouslySetInnerHTML` kullanılmaz (tek istisna `app/layout.tsx`'in
   döndürdüğü kök JSX).

## User preferences
