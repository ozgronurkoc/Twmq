# Spor Toto 14-Garanti Formül Üreticisi

Spor Toto kuponu için **kaplama kodu** (covering code) üreten araç.

Seçtiğin ihtimal kümeleri içinde doğru sonuç varsa, oynanan kolonlardan en az biri **en fazla 1 maç hatalı** olur — yani **14-garanti**.

Bu araç maç sonucu **tahmin etmez**. Tahminin doğruysa onu kaçırmamanı, hem de mümkün olan **en az kuponla** sağlamanı hedefler. Bir maliyet düşürme aracıdır; kazanma olasılığını büyütmez.

---

## Ne yapar / ne yapmaz

| Yapar | Yapmaz |
|-------|--------|
| Hamming yarıçap-1 kaplama kodu üretir | Maç sonucu tahmin etmez |
| En kötü durumda 14 doğru **garantiler** (küme içinde) | İkramiye / beklenen değer hesabı yapmaz |
| Exact + Monte Carlo olasılık raporu verir | Bülten verisi çekmez (henüz) |
| Bayes (Dirichlet) ile tahminlerini yumuşatır | 14-garantiyi olasılıkla “güçlendirmez” — garanti kombinatoryaldir |
| Markov ile sıralı risk profili çıkarır | Mobil uygulama değildir |

**Kritik ayrım:** Garanti, *seçim kümesi içinde* geçerlidir. Küme dışı bir sonuç gelirse sistem zaten o senaryoyu kapsamaz — bu bir hata değil, tasarımın sınırıdır.

---

## Kurulum

Python tarafının tamamı `backend/` altındadır:

```bash
cd backend
pip install -e .
# veya geliştirme + test:
pip install -e ".[test]"
# uv kullanıyorsan:
uv sync --extra test
```

Bağımlılıklar: `numpy`, `scipy` (kesin ILP için), `flask` (web).
`scipy` yoksa araç çalışır; yalnızca kesin çözücü (ILP) devre dışı kalır.

---

## CLI kullanım

```bash
spor-toto --picks "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
```

### `--picks` biçimi

- 15 maç virgülle ayrılır
- Her maçın seçenekleri bitişik yazılır
- `1` = banko ev, `10` = çifte, `102` / `012` = üçlü (kapama)
- Baş/son fazla ayırıcı (`",1,10,"`) yok sayılır; **ortadaki boş slot** (`"1,,10"`) `ValueError` fırlatır
- `"1, 10"` gibi boşluklu yazım geçerlidir

### Modlar

| Mod | Ne yapar |
|-----|----------|
| `fix16` (varsayılan) | Her zaman 16 kupon satırı. En az 7 çifte zorunlu. Hamming(7,4) tabanlı. |
| `auto` | En ucuz çözümü arar; satır sayısı değişken. |
| `exact` | ILP ile kanıtlanmış optimal (küçük uzaylar). |
| `block` | Yalnızca blok ayrıştırma motoru. |
| `heuristic` | Açgözlü + local search (büyük uzaylar). |
| `butce` | “Elimde N kolon var, hangi maçı kısmalıyım?” |
| `maxcov` | Sabit bütçeyle maksimum kapsama. **Garanti vermez.** |

```bash
spor-toto --picks "..." --variant 3
spor-toto --picks "..." --mode auto
spor-toto --picks "..." --mode butce --budget 32
spor-toto --picks "..." --mode maxcov --budget 16
spor-toto --picks "..." --probs "1:0.5,0:0.3,2:0.2;..." --mc-samples 20000
```

### Olasılık, Monte Carlo, Bayes

`--probs`: maçlar `;` ile ayrılır, her maç `1:0.5,0:0.3,2:0.2`.

```bash
# Exact + Monte Carlo
spor-toto --picks "..." --probs "..." --mc-samples 20000

# Dirichlet Bayes (preset kısayolu)
spor-toto --picks "..." --probs "..." --bayes-preset dengeli --mc-samples 10000

# Manuel α / n
spor-toto --picks "..." --probs "..." --bayes --prior-strength 2 --evidence-strength 20
```

#### `--bayes-preset` seçenekleri

| Preset | Prior α | Evidence n | Ne zaman |
|--------|---------|------------|----------|
| `zayif_prior` | 0.5 | 15 | Evidence’e güven yüksek |
| `dengeli` | 1.0 | 10 | Varsayılan denge |
| `guclu_prior` | 5.0 | 8 | Seçim kümesine güçlü güven |
| `evidence_agir` | 1.0 | 40 | Evidence neredeyse doğrudan alınır |
| `sadece_prior` | 3.0 | 0 | Evidence yok sayılır (posterior = prior) |

Bayes **14-garantiyi değiştirmez**; yalnızca exact/MC motoruna giden olasılık ağırlıklarını günceller.

CLI çıktısında:
- `Kaynak: bayes_posterior`
- Ortalama KL + etiket (`ihmal edilebilir` … `güçlü kayma`)
- En büyük KL kaymaları (maç bazlı, web “Yorum” sütunu ile aynı bilgi)

Web’de Bayes paneli: preset dropdown (CLI ile **aynı α/n**), posterior tablosu, maç bazlı KL **Yorum**.

---

## Web arayüzü

Backend yalnızca JSON API'dir; arayüz Next.js tarafındadır (`frontend/`).

```bash
# API tek başına
python backend/web_app.py       # http://localhost:8080

# API + Next.js arayüz birlikte
bash scripts/run_next_dev.sh    # UI :3000, API :8080
```

### Sayfalar

| Rota | İçerik |
|------|--------|
| `/` | **Formül** — motorun tamamı |
| `/istatistik` | Sezon dağılımı, bantlar, 41 hafta |
| `/istatistik/<hafta>` | Tek hafta detayı |
| `/saglik` | 13 invariant, süreleriyle |

### Formül sayfası

Girdi tarafı:

- 15 × 3 maç ızgarası (klavye: ok tuşları + `1` / `0` / `2`)
- Canlı sayaç: banko / çifte / üçlü / uzay / tahmini kolon bedeli
- **7 modun tamamı**: fix16, auto, exact, block, heuristic, butce, maxcov
- Varyant, bütçe, bütçe planı seçimi, katı doğrulama
- **Maç bazlı olasılık girişi** (1/0/2) — ham ağırlık da kabul edilir, normalize edilir
- **Bayes**: 5 hazır preset (CLI ile aynı α/n) veya elle α / n
- Monte Carlo örnek sayısı (1.000–200.000)
- Motor ayarları: `trials`, `ls_iters`, `seed`, `time_limit`, `block_limit`, `exact_limit`

Sonuç sekmeleri — hepsi backend alanlarıyla birebir:

| Sekme | Gösterdiği |
|-------|------------|
| Özet | Garanti durumu, satır/kolon/alt sınır, bütçe planları, uyarılar |
| Kupon | Kupon tablosu, satır başına kolon bedeli, kopyala |
| Dağılım | Kapsama katmanları + uniform varsayım |
| Olasılık | Exact vs Monte Carlo (%95 CI) |
| Bayes | Maç bazlı prior → posterior, KL + yorum, en çok kayan maçlar |
| Markov | Küme-içi hayatta kalma + hata bütçesi (0 / 1 / 2+) |
| Hata frekansı | d=1 ve d=2 katmanlarında hangi maç hata üretiyor |
| Log | Motorun adım adım çalışma logu |

Arayüz mod listesini, preset'leri ve sınırları `GET /api/meta` üzerinden okur —
hiçbiri arayüzde sabit kodlanmaz, motorla tek kaynaktan senkron kalır.

### API uçları

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/api/meta` | Modlar, preset'ler, varsayılanlar, sınırlar |
| GET | `/api/health` | 13 invariant (200 = HEALTHY, 503 = UNHEALTHY) |
| GET | `/api/stats` | Tarihsel 1/0/2 |
| GET | `/api/stats/<week>` | Tek hafta |
| POST | `/api/solve` | Motorun tamamı |

### Health

```bash
cd backend
python -m spor_toto.health              # bir kez
python -m spor_toto.health --interval 60
curl http://localhost:8080/api/health   # JSON (200 = HEALTHY, 503 = UNHEALTHY)
```

13 invariant: encoder, fix16 garanti, distance layers, blok/heuristic, exact olasılık, Monte Carlo, Bayes, Markov, error_freq, pipeline şekli, scipy bayrağı.

---

## Satır ≠ kolon

Bir maça çifte işaretlersen o satır **2 kolon** üretir ve 2 kolon bedeli ödersin.
16 satır + ekstra çifte faktörü = daha yüksek bedel. UI ve CLI toplam **kolon bedelini** gösterir.

---

## Bilinen sınırlar (matematik)

Küre-kaplama alt sınırı: `kolon ≥ |uzay| / top_boyutu`.

| Durum | Optimal kolon (alt sınır civarı) |
|-------|----------------------------------|
| 5 çifte | 7 |
| 6 çifte | 12 |
| 7 çifte | **16** (Hamming(7,4)) |
| 8 çifte | **32** |
| 4 üçlü | **9** |

**8 çifteyi 16 kolona sığdırmak imkânsızdır.**
`maxcov` 16 kolonla kısmi kapsama verir — **garanti değildir**.

---

## Mimari (kısa)

Repo iki tarafa ayrılmıştır: `backend/` (Python) ve `frontend/` (Next.js).

```
backend/
  spor_toto/
    core.py      Encoder, Fix-16, ILP, heuristic, exact olasılık
    analysis.py  Monte Carlo, maç bazlı hata frekansı
    bayes.py     Dirichlet prior → posterior, KL, preset'ler
    markov.py    Seçim hayatta kalma + hata bütçesi zinciri
    health.py    13 invariant health check
    report.py    Konsol / dosya çıktısı
    cli.py       spor-toto komut satırı
  web_app.py     Flask — yalnızca JSON API, HTML servis etmez
  tests/         pytest (core, engines, analysis, bayes, markov, health, cli)
  data/          Tarihsel 1/0/2 verisi
  scripts/       check.sh (yerel CI eşdeğeri)
  pyproject.toml

frontend/        Next.js App Router — yalnızca TSX, hiç HTML dosyası yok
  app/           sayfalar (/, /istatistik, /saglik)
  components/
    shell/       kalıcı kenar çubuğu + sayfa geçişleri
    formul/      maç ızgarası, olasılık girişi, sonuç panelleri
    ui/          temel bileşenler (elle yazıldı, Radix yok)
  lib/types.ts   API sözleşmesinin tamamı tipli
  lib/api.ts     tipli, iptal edilebilir API istemcisi

scripts/         run_next_dev.sh (API + UI birlikte ayağa kaldırır)
docs/            Mimari ve veri notları
archive/         Kullanımdan kalkmış Jinja2 arayüzü ve tek-seferlik yamalar
```

Detay için `docs/ARCHITECTURE_NEXT.md` ve `archive/README.md`.

Katmanlar bağımsızdır:

1. **Kombinatoryal** — kolon üretimi, Hamming mesafesi, 14-garanti
2. **Olasılıksal** — exact, MC, Bayes, Markov (garantiyi bozmaz)
3. **Gözlem** — health, UI, CLI

---

## Testler

```bash
cd backend
pytest
pytest -m "not slow"
pytest tests/test_bayes.py tests/test_markov.py tests/test_health.py tests/test_cli.py -v
```

Kapsam: girdi doğrulama, geometri, motorlar, fuzz invariant’lar, CLI (Bayes preset dahil), analysis, health.

### Yerel tek komut (health + CLI smoke)

```bash
bash backend/scripts/check.sh
```

`backend/scripts/check.sh`: hızlı pytest → 13 invariant health → CLI fix16 + `--bayes-preset dengeli` dumanı.
Exit code ≠ 0 ise bir adım kırık demektir (CI ile aynı mantık).

---

## CI (GitHub Actions)

Her `main` push ve PR’da:

| Adım | Python | Açıklama |
|------|--------|----------|
| `pytest -m "not slow"` | 3.10–3.13 | Hızlı süit |
| `pytest -m slow` | 3.12 | ILP / yavaş |
| `python -m spor_toto.health` | 3.12 | 13/13 HEALTHY zorunlu |
| CLI smoke | 3.12 | fix16 + Bayes preset |

Workflow: `.github/workflows/tests.yml`  
Actions: repository **Actions** sekmesi.

CD (otomatik deploy) yok: Replit Publish manuel / yarı-otomatik kalır — health kırmızıysa yayınlama.

---

## Uyarı

Bu araç **kazanma olasılığını artırmaz**.
Yalnızca belirli bir garantiyi daha az kuponla elde etmeni sağlar.

Olasılık / Monte Carlo / Bayes / Markov çıktıları **beklenen-değer veya kâr hesabı değildir**; ikramiye havuzu ve kolon bedeli hesaba katılmaz.

Sorumlu oynayın.
