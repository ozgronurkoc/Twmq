# Spor Toto 14-Garanti Formül Üreticisi

Spor Toto kuponu için **kaplama kodu** (covering code) üreten araç. Seçtiğin ihtimal kümeleri içinde doğru sonuç varsa, oynanan kolonlardan en az biri **en fazla 1 maç hatalı** olur — yani 14-garanti.

Bu araç maç sonucu tahmin etmez. Tahminin doğruysa onu kaçırmamanı, hem de mümkün olan **en az kuponla** sağlamanı hedefler. Bir maliyet düşürme aracıdır.

## Kurulum

```bash
pip install -e .
# veya
uv sync --extra test
```

Bağımlılıklar: `numpy`, `scipy` (kesin ILP çözücü için), `flask` (web). scipy yoksa araç çalışır ama kesin çözücü devre dışı kalır.

## CLI kullanım

```bash
spor-toto --picks "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
```

`--picks` biçimi: 15 maç virgülle ayrılır, her maçın seçenekleri bitişik yazılır.
`1` = banko ev sahibi, `10` = çifte, `102` = kapama (üçlü).

### Modlar

| Mod | Ne yapar |
|---|---|
| `fix16` (varsayılan) | Her zaman 16 kupon satırı. En az 7 çifte zorunlu. |
| `auto` | En ucuz çözümü arar; satır sayısı değişken. |
| `exact` | ILP ile kanıtlanmış optimal (küçük uzaylar). |
| `block` | Yalnızca blok ayrıştırma motoru. |
| `heuristic` | Açgözlü + local search (büyük uzaylar). |
| `butce` | "Elimde N kolon var, hangi maçı kısmalıyım?" |
| `maxcov` | Sabit bütçeyle maksimum kapsama. **Garanti vermez.** |

```bash
spor-toto --picks "..." --variant 3
spor-toto --picks "..." --mode butce --budget 32
spor-toto --picks "..." --mode maxcov --budget 16
spor-toto --picks "..." --probs "1:0.5,0:0.3,2:0.2;..."
spor-toto --picks "..." --probs "..." --mc-samples 20000   # Monte Carlo
```

## Web arayüzü

```bash
python web_app.py
# http://localhost:5000
```

Özellikler:

- Maç seçimi tablosu, canlı bedel, Fix-16 / auto / bütçe / maxcov / heuristic
- Gelişmiş olasılık girişi (maç bazlı 1/0/2)
- Uniform dağılım + hata seviyesi seçici (0/1/2)
- Exact olasılık + **Monte Carlo** (%95 CI)
- Maç bazlı hata frekansı
- Kopyala / görsel indir / localStorage kupon kaydı
- **Sistem Health** paneli (UI’den test çalıştırma)

### Health

```bash
python -m spor_toto.health              # bir kez
python -m spor_toto.health --interval 60
curl http://localhost:5000/health       # JSON (200 / 503)
```

## Satır ≠ kolon

Bir maça çifte işaretlersen o satır **2 kolon** üretir ve 2 kolon bedeli ödersin.
16 satır + 1 ekstra çifte faktörü = daha yüksek bedel.

## Bilinen sınırlar

Küre-kaplama sınırı: `kolon ≥ |uzay| / top_boyutu`.

| Durum | Optimal kolon |
|---|---|
| 5 çifte | 7 |
| 6 çifte | 12 |
| 7 çifte | **16** (Hamming(7,4)) |
| 8 çifte | **32** |
| 4 üçlü | **9** |

**8 çifteyi 16 kolona sığdırmak imkânsızdır.** `maxcov` 16 kolonla en fazla ~%56 kapsama verir — garanti değil.

## Testler

```bash
pytest
pytest -m "not slow"
pytest tests/test_analysis.py tests/test_health.py -v
```

Kapsam: girdi doğrulama, geometri, motorlar, fuzz invariant’lar, CLI, analysis (MC), health.

## Uyarı

Bu araç kazanma olasılığını artırmaz. Yalnızca belirli bir garantiyi daha az kuponla elde etmeni sağlar. Olasılık / Monte Carlo raporu beklenen-değer/kâr hesabı değildir.
