# Spor Toto 14-Garanti Formül Üreticisi

Spor Toto kuponu için **kaplama kodu** (covering code) üreten araç. Seçtiğin ihtimal kümeleri içinde doğru sonuç varsa, oynanan kolonlardan en az biri **en fazla 1 maç hatalı** olur — yani 14-garanti.

Bu araç maç sonucu tahmin etmez. Tahminin doğruysa onu kaçırmamanı, hem de mümkün olan **en az kuponla** sağlamanı hedefler. Bir maliyet düşürme aracıdır.

## Kurulum

```bash
pip install -e .
```

Bağımlılıklar: `numpy`, `scipy` (kesin ILP çözücü için). scipy yoksa araç çalışır ama kesin çözücü devre dışı kalır.

## Kullanım

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
spor-toto --picks "..." --variant 3                  # aynı garanti, farklı 16 satır
spor-toto --picks "..." --mode butce --budget 32     # bütçe danışmanı
spor-toto --picks "..." --mode maxcov --budget 16    # garanti yok, olasılık
spor-toto --picks "..." --probs "1:0.5,0:0.3,2:0.2;..."   # olasılık raporu
```

## Satır ≠ kolon

Bir maça çifte işaretlersen o satır **2 kolon** üretir ve 2 kolon bedeli ödersin.
16 satır + 1 çifte = **32 kolon bedeli**.

Çoklu işaret hiçbir zaman bedeli düşürmez. Maçlara `a_i` işaret konursa maliyet `∏a_i`, kapsanan nokta `∏a_i · (1 + Σ(k_i−a_i)/a_i)`. Birim bedel başına verim `1 + Σ(k_i−a_i)/a_i ≤ 1 + Σ(k_i−1)` olup eşitlik ancak tüm `a_i = 1` iken sağlanır.

## Bilinen sınırlar

Küre-kaplama sınırı: `kolon ≥ |uzay| / top_boyutu`. Kesin çözücü literatürdeki değerleri yeniden üretir:

| Durum | Optimal kolon |
|---|---|
| 5 çifte | 7 |
| 6 çifte | 12 |
| 7 çifte | **16** (Hamming(7,4), mükemmel kod) |
| 8 çifte | **32** |
| 3 üçlü | 5 |
| 4 üçlü | **9** (üçlü Hamming, mükemmel kod) |

**8 çifteyi 16 kolona sığdırmak imkânsızdır.** 16 × 9 = 144 < 256. `maxcov` modu 16 kolonla en fazla %56.2 kapsama verir — bu bir garanti değil, olasılıktır.

## Testler

```bash
pytest              # tümü (~70 sn)
pytest -m "not slow"
```

434 test: girdi doğrulama, geometri değişmezleri, bilinen optimal değerler, sıkıştırmanın kayıpsızlığı, rastgele kuponlar üzerinde fuzz testleri, CLI çıkış kodları.

## Uyarı

Bu araç kazanma olasılığını artırmaz. Yalnızca belirli bir garantiyi daha az kuponla elde etmeni sağlar. `--probs` ile üretilen olasılık raporu bir beklenen-değer/kâr hesabı değildir; ikramiye havuzu ve kolon bedeli hesaba katılmaz.
