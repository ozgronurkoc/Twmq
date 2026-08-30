# Dış geliştirme planları — depoyla madde madde eşleme

**Kapsam:** Depo dışından gelen iki geliştirme/refactor planının madde madde
karşılığı: **hangisi zaten var, hangisi kısmen var, hangisi gerçekten eksikti,
hangisi bilerek reddedildi.**
**İncelenen belgeler:** `SPOR_TOTO_BACKTEST_CLAUDE_CODE_GELISTIRME_PLANI.md`
(25 faz) · `SPOR_TOTO_ANALIZ_MOTORU_GELISTIRME_PLANI.md` (40 faz)
**Bu belgenin tarihi:** 2026-08-29 · taban `d607360` (PR #23 birleştikten sonra)
**İlgili belgeler:** [`DIS_INCELEME_AZ_RAPORU.md`](DIS_INCELEME_AZ_RAPORU.md) ·
[`DIS_INCELEME.md`](DIS_INCELEME.md) ·
[`DIS_INCELEME_ALPHAPY.md`](DIS_INCELEME_ALPHAPY.md) (aynı türün önceki
örnekleri) · [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §6
(projenin kendi sonlanan planı ve durma kuralları)

> **Künye — bu planlar depo okunmadan yazıldı.** İkisi de projeyi bulunduğu
> yerden farklı tarif ediyor: `backtest.py` tek dosyalık bir script,
> `analysis.py` tek dev modül, proje testsiz. Gerçekte 46 modül, 55 test
> dosyası (1.867 test), ruff + kademeli mypy, on adımlı tek kalite kapısı ve
> ayrı bir sağlık katmanı var. Bu, planları değersiz yapmaz — **üç yerde
> gerçek kusura parmak bastılar** ve üçü de bugün koddaydı. Ama statüleri
> **dış görüştür**, teyit değil.

---

## 1. Kısa cevap

| Kova | Sayı | Örnek |
|---|---:|---|
| **Zaten var** | çoğunluk | bootstrap CI, hold-out, sezon dışarıda bırakmalı ölçüm, kalibrasyon kademesi, üç arındırma yöntemi, üç kademeli kaplama çözücüsü, baseline kaydı, eşik taraması |
| **PR #23'te kapandı** (main'de, `d607360`) | 3 | walk-forward (ileri yürüyüş) · model arenası · sızıntı sözleşmesi |
| **Gerçekten eksikti → uygulandı** | 4 | atıl `max_d` · `d2` paydası · bütün uzayı RAM'e alan üretim · `holdout` kolon paydası |
| **Reddedildi, gerekçesi ölçülmüş** | 3 | ROI/drawdown/Sharpe tabloları · `0/0/0`'ın hataya çevrilmesi · `analysis/` paket bölünmesi |

Uygulanan dördün ürettiği sonuç, iki planın ana tezini **değiştirmedi**: ikisi
de "sistem ölçülmemiş" diyordu; bulunan şey ölçümün yokluğu değil, dört
ölçüm aracının kendi içindeki kusurlarıydı. İkisi bugün yanlış sayı üretiyordu
(`d2` yüzdeleri, `ci95`'in adı), ikisi gizliydi (`max_d`, `holdout` paydası).

---

## 2. Gerçekten eksik olan dört şey

### 2.1 `max_d` atıldı — `analysis.py`

Parametre imzada vardı, gövde katmanları `((1, err_d1), (2, err_d2))` diye
**sabit** yazıyordu. Üç çağırandan ikisi `max_d=2` geçtiği, biri varsayılanı
kullandığı için atıllık hiçbir yerde görünmüyordu — ve `ruff` yapılandırması
`F` (pyflakes) seçiyor ama kullanılmayan **argüman** kuralı (ARG) seçili
değil, yani linter de göremiyordu.

Atıl bir parametre, olmayan bir yeteneği ilan eder. Artık katman sayısını
gerçekten belirliyor; maç sayısına tavanlanıyor; negatif ve sayı olmayan
reddediliyor. `d1`/`d2`/`n1`/`n2` her zaman üretiliyor (arayüz sözleşmesi),
`d3` ancak istenirse — yani canlı sözleşme değişmedi.

Planın istediğinden bir yerde ayrıldı: `max_d = 0` **"yalnızca tam eşleşme"
değil**, "hiçbir katman". Bu fonksiyon hata **pozisyonu** sayar ve `d = 0`
noktasının hata pozisyonu yoktur; `d0` katmanı tanım gereği boştur.

### 2.2 `d2` yüzdeleri %200'e topluyordu — `analysis.py`

Payda nokta sayısıydı (`n2`) ama pay hata **pozisyonu** sayıyor: `d = 2`
noktası iki hata katar. Aynı tabloda aynı biçimde sunulan iki sütun farklı
ölçekte normalize ediliyordu.

Payda artık hata yuvası (`n_d × d`). Ölçüldü (örnek kupon, kaplama kasten
eksik bırakılmış):

| | eski | yeni |
|---|---:|---:|
| `d1` yüzde toplamı | 100,03 | 100,03 |
| `d2` yüzde toplamı | **200,01** | **100,00** |
| `d2`, 2. maç satırı | %31,15 | %15,57 |

Arayüz sayıyı olduğu gibi basıyor (`panels-analiz.tsx`), yani düzelen şey
doğrudan ekrandaki sayıdır.

### 2.3 Bütün sonuç uzayı RAM'e alınıyordu — `analysis.py`

Yalnızca mesafe hesabı parçalıydı, **üretim değil**: `meshgrid` + `stack`
uzayın tamamını tek seferde kuruyordu. Üretim artık karışık tabanda
(mixed-radix) parça parça yapılıyor.

Sıra korundu ve korunması zorunluydu: `argmin` eşit mesafede **ilk** kolonu
seçer, sıra kayarsa eşitliklerde başka kolon kazanır ve `d1`/`d2` dağılımı
sessizce değişir. Test bunu `itertools.product`'a karşı hem parçalı hem
parçasız doğruluyor.

Ölçüldü (bu makine, tek çekirdek):

| kesit | uzay × kolon | süre | tepe bellek |
|---|---:|---:|---:|
| 4 çifte / 6 üçlü | 11.664 × 1.296 | 0,43 sn | 10,5 MB |
| 9 üçlü | 19.683 × 1.296 | 0,72 sn | 11,2 MB |
| **15 üçlü** (3^15) | 14.348.907 × 16 | 10,1 sn | **8,9 MB** |

Tepe bellek uzayla **büyümüyor** — parça boyuna bağlı. Eski yolda son
satırdaki `uzay` dizisi tek başına 215 MB olurdu, üstelik `stack` öncesi aynı
boyda 15 ara dizi daha ayakta.

Ayrıca modülün kendi iş tavanı kondu (`ISLEM_SINIRI`). Koruma tek bir
çağıranda duruyordu (`web_app.py`, uzay ≤ 20.000); `health.py`'nin iki
çağrısında hiç yoktu ve orada sabit kupon kullanıldığı için güvenlik yapıdan
değil **tesadüften** geliyordu. Tavan uzaya değil **işe** bakıyor (uzay ×
kolon), çünkü maliyet öyle büyüyor. Değeri tek bir kural belirledi: motorun
üretebileceği en büyük kupon, kanıtlanmış optimal kaplamasıyla hâlâ
koşabilmeli. `web_app.py`'nin kendi sınırı kaldırılmadı — o bir **ürün**
kararı (kullanıcı beklerken ne kadar), bu bir **motor** korkuluğu.

### 2.4 `holdout` kolon ortalaması yanlış paydaya bölünüyordu — `backtest.py`

Backtest planının §24'ü (`n = len(kullanilir)`) haklıydı. `n` döngünün
önünde sabitleniyor ama döngü iki yerde `continue` ediyor (eşik seçilemedi;
dışarıda bırakılan hafta `UZAY_SINIRI`ne takıldı). `kolon` yalnızca ölçülen
katlarda birikirken `columns_avg = kolon / n` bütün kesiti sayıyordu.

**Bugünkü sayı değişmedi** (2.228,4 aynen duruyor): 36 haftalık kesitte
kazanan eşik çifti (0,68/0,38) hiçbir haftayı atlamıyor. Kusur gizliydi — ve
ne kadar gizli olduğu ölçüldü:

> 28 eşik çiftinden **dördü** hafta atlıyor (0,65/0,42 · 0,68/0,42 ·
> 0,72/0,42 · 0,78/0,42) ve bunlardan **0,68/0,42 bugün kazananla aynı
> hit14'ü (3) veriyor** — eşitliği ucuz kolon lehine bozulduğu için
> kaybediyor. Veri bir tık kaysa atlayan çift kazanır ve ortalama sessizce
> düşerdi.

`hit14` paydası **bilerek** kesit olarak kaldı: ölçülemeyen hafta ıska
sayılır. Paydadan düşmek, stratejinin çözemediği haftaları yok sayarak isabet
oranını yukarı çekerdi. Değişen şey karar değil, **görünürlüğü**: çıktı artık
`olculen`, `atlanan` ve hangi metriğin hangi paydaya dayandığını (`payda`)
yazıyor; arayüz de atlanan kat varken bunu kartta söylüyor.

---

## 3. Reddedilenler — ve gerekçelerinin nerede ölçüldüğü

### 3.1 ROI / bankroll / max drawdown / Sharpe tabloları (backtest planı FAZ 12–14)

**Hesap zaten var, ölçüm kasten yok.** `getiri.py` müşterek beklenen değeri
kapalı formda veriyor (`getiri_orani` dahil, §3.34). Eksik olan tahminci
değil, **veri**: ikramiye kaydı 3 hafta.

Gereken örneklem tahmin edilmedi, **ölçüldü**: `scripts/faz_b.py --guc`, orta
büyüklükte bir etkiyi (log ölçekte 0,5) %80 güçle ayırt etmek için **≈71
ikramiyeli hafta ≈ 3,5 sezon** istiyor (§6.3b). Kişi başı ikramiye haftalar
arası çok oynak, çünkü kazanan sayısına bölünüyor ve kazanan sayısı 0 ile
binler arasında geziyor.

Toplam ROI ve max drawdown tablosu üretmek, ölçülmemiş bir sayıya tabloda yer
ayırmak olurdu — deponun kendi kuralı, ve `arena.py` aynı gerekçeyle ROI
sütunu koymadı (`DIS_INCELEME_AZ_RAPORU.md` §6).

**Hangi koşulda açılır:** ikramiye kaydı ≈71 haftaya ulaştığında, ya da
`faz_b.py --guc` gerçek (varsayılan 1,5 yerine ölçülen) standart sapmayla
daha küçük bir sayı verdiğinde. Durma kuralının üç şıkkı §6.3b'de yazılı.

### 3.2 `0/0/0 → hata` (analiz planı FAZ 2)

Plan geçersiz olasılık dağılımı için açık hata istiyor. **Sıfır toplam için
uygulanmadı**, gerekçesi: `total <= 0 → düzgün dağılım` keyfi değil, "bilgi
yok"un tarafsız karşılığıdır; kural tek yerde yazılı
(`ortak.normalize_olasilik`) ve `frontend/lib/utils.ts`'te **birebir
aynadadır**. Yığının bir ucunda hataya çevirmek ikisini ayrıştırırdı.

**Planın asıl haklı olduğu yer uygulandı:** `NaN`, `inf` ve sayı olmayan
girdi artık adıyla reddediliyor. Üçü de sessizce yutuluyordu ve yutulma
biçimleri birbirinden kötüydü — `max(0.0, nan)` Python'da `0.0` döner (eksik
veri **sıfır olasılık** oluyordu), `inf` ise normalize sonucu bütün
sembolleri `nan` yapıyor ve `nan` karşılaştırmaları hep yanlış olduğu için
hiçbir eşik yakalanmıyordu. Ayrıca `analysis.py`'deki yerel kopya silinip
paylaşılan kural çağrıldı.

### 3.3 `analysis/` paket bölünmesi (analiz planı FAZ 31)

Aynı gerekçe `DIS_INCELEME_AZ_RAPORU.md` §6'da §38 için yazılmıştı: bugünkü
modül sınırları ölçüm koşumlarına göre kurulu ve `test_egitim.py`'nin katman
bekçisi onları koruyor. `analysis.py` 231 satır; on iki dosyaya bölmenin
bedeli faydasından büyük.

---

## 4. Backtest planı — faz faz

| Faz | Durum | Karşılığı |
|---|---|---|
| 1 — repository audit | KISMİ | Mimari `README.md` §7 ve `docs/`te; ayrı bir `AUDIT_REPORT.md` yok, yerini bu belge alıyor |
| 2 — test / regresyon | VAR | 62 dosya, 1.867 test; `scripts/check.sh` on adım (ruff · mypy · pytest · yavaş ILP · sağlık · CLI · boru hattı · üretilmiş dosya tazeliği · arayüz · üretim derlemesi) |
| 3 — veri kalitesi, skip nedeni | VAR | **İki ayrı mekanizma**: eksik oran → `usable=False`, `meta.weeks_dropped` (hafta ve kaç maçın eksik olduğu); arama uzayı → `_ozet.skipped`. Değişmez `test_backtest.py`'de |
| 4 — probability engine, overround | VAR | `odds.implied_probs`; üç arındırma (`orantili`/`guc`/`shin`), varsayılan `shin`; ham marj ayrı (`odds.margin`) |
| 5 — kalibrasyon | VAR | `kalibrasyon.py`, `kalibre.py` (Venn-Abers), `recalibrate.py` (19 basamaklı kademe); Brier ve log kaybı `ortak.py`, Murphy ayrışımı `ortak.brier_ayrisimi` |
| 6 — strateji modülü | VAR | `backtest.secim_uret` (eşik kuralı) ve `secim.en_iyi_secim` (hedef tabanlı ardıl, Pareto DP) |
| 7 — eşik optimizasyonu, train/val/test | KISMİ → **düzeltildi** | `holdout()` leave-one-week-out var; paydası kırıktı → §2.4 |
| 8 — walk-forward | VAR (PR #23) | `evaluate.ileri_yuruyus` — k. grup yalnızca `0..k-1`de eğitilir |
| 9 — baseline'lar | VAR | `predict.referans_fabrikalar()`: `duzgun` (mutlak zemin), `sezon_sabiti` (naif), `piyasa` (aşılması gereken çizgi) + `arena.py` (PR #23) |
| 10 — covering seviyeleri, solver_mode | VAR | `_kaplama` üç kademeyi **adıyla** raporluyor: `sabit 16 satır (Hamming 7,4)` → `blok ayrıştırma` → `sezgisel`; her sonuç `dogrula_kaplama` ile bağımsız doğrulanıyor ve `guaranteed` bayrağı taşıyor |
| 11 — arama uzayı sınırı raporlaması | VAR | `UZAY_SINIRI = 200.000`; atlanan hafta sayısı **ve gerekçesi** payload'da |
| 12–14 — ekonomi / bankroll / risk | REDDEDİLDİ | §3.1 |
| 15 — bootstrap | VAR | `evaluate.bootstrap_farki` — eşleştirilmiş, hafta üzerinden, 2.000 tekrar, sabit tohum |
| 16–17 — anlamlılık / çoklu test | VAR | `gecti` **yalnızca** güven aralığının tamamı sıfırın altındaysa; tarama ile hold-out ayrı; `UYARI` metni her payload'da |
| 18 — dayanıklılık | VAR | 7 × 4 = 28 eşik çiftlik ızgara taraması (`esik_taramasi`), her satırda hafta/atlanan/hit/kolon |
| 19 — alt grup analizi | KISMİ | `odds._favori_bantlari`, `_lig_kirilimi`, `_kume_kapsama`; `AZ_ORNEK = 30` altında `low_sample` bayrağı — planın `INSUFFICIENT_SAMPLE` maddesinin karşılığı |
| 20 — metrik tanımları | VAR | `README.md` §12 sözlük; her metrik kendi fonksiyonunun docstring'inde tanımlı |
| **21 — payda** | **YOKTU → düzeltildi** | §2.4 |
| 22–24 — raporlama / grafikler | VAR | Yapılandırılmış payload (`payloads.py`), JSON API, grafikler arayüzde (`frontend/components/istatistik/charts.tsx`) |
| 25 — verdict engine | KISMİ | Otomatik "STRONG/WEAK EVIDENCE" sınıflandırması **yok** ve bilerek: projenin ölçütü not değil **durma kuralıdır** (§6.5). Dört sorunun her biri için "evet/hayır + ölçülen sayı + onu tekrar açacak koşul" yazılı |

---

## 5. Analiz planı — faz faz

| Faz | Durum | Karşılığı |
|---|---|---|
| 1 — envanter + test altyapısı | VAR | `tests/test_analysis.py` (28 test), `test_edge_cases.py` |
| 2 — probability validation | KISMİ → **düzeltildi** | §3.2 |
| **3 — `max_d` bug'ı** | **YOKTU → düzeltildi** | §2.1 |
| 4 — mesafe motoru | KISMİ | Vektörleştirilmiş Hamming `match_error_frequency` içinde gömülü, ayrı bir `hamming_distance()` yok. `core.hamming` (skaler) ve `fire_scenarios._min_mesafeler` (aynı desen) var |
| 5 — exact engine | VAR | `core.olasilik_raporu` — kapalı form, `p_kume_ici`/`p_15`/`p_14`/`p_tek_kolon_15` |
| **6 — chunked enumeration** | **YOKTU → düzeltildi** | §2.3 |
| 7 — Monte Carlo temizliği | KISMİ | Deterministik (`random.Random(seed)`, testli), doğrulanmış; ama hâlâ saf Python döngüsü — bkz. §6 |
| 8 — exact vs MC doğrulaması | VAR | `report.py` sapma tablosu basıyor; `health._check_monte_carlo` 0,05 toleransla denetliyor; `test_analysis.py` yakınsamayı ölçüyor |
| 9 — Wilson CI | KISMİ → **düzeltildi** | `ci95` bir **aralık değil**, normal yaklaşımın yarı genişliğiydi ve `1.96` gömülüydü — üstelik normal yaklaşım tam da bu fonksiyonun "n düşük" uyarısı verdiği bölgede kenarlara yapışır. Ad **sözleşme** olduğu için kaldı; yanına gerçek aralık kondu (`ci_alt`/`ci_ust`, `ortak.wilson`) ve gömülü sabit `ortak.GUVEN_Z` oldu. Planın "`ci95` gibi belirsiz bir ad kullanma" maddesi kırmadan karşılandı |
| 10 — expected hits | YOK | Uygulanmadı ve reddedilmedi — bkz. §6 |
| 11 — tam mesafe dağılımı | KISMİ | `max_d` artık bağlı olduğu için `d1..dN` istenebiliyor; ayrı bir "d0..d15 dağılımı" raporu yok |
| 12 — maç bazlı hata analizi | VAR | `match_error_frequency`in kendisi; `fire_scenarios.py` "ya yanılırsam" katmanı |
| 13 — kritik maç skoru | YOK | Uygulanmadı. Planın kendi uyarısı geçerli: "keyfi bir skor oluşturma" — matematiksel tanımı olmayan bir skor üretmemek deponun da kuralı |
| 14 — duyarlılık analizi | KISMİ | `getiri.duyarlilik` (havuz ekseninde) var; olasılık perturbasyonu üzerinden P15/P14 duyarlılığı yok |
| 15 — kalibrasyon | VAR | Planın kendi koşulu ("yalnızca gerçek historical prediction data varsa") sağlanıyor: 31.103 maçlık korpus |
| 16 — EV | VAR | `getiri.py`. Planın kendi uyarısı — "havuz bazlı mı netleştirilmeden EV iddiası yapılmamalı" — deponun ölçtüğü şeyle birebir örtüşüyor (§3.1) |
| 17–18 — ağırlıklı / ağırlıksız kapsama | VAR | `kume_ici` (olasılık ağırlıklı) ve `space_size`/`ball_size`/`lower_bound` (ağırlıksız) ayrı ayrı raporlanıyor; ikisi hiçbir yerde karıştırılmıyor |
| 19–20 — kolon verimliliği / fazlalık | KISMİ | `core.butce_danismani` marjinal katkıyı bütçe ekseninde veriyor; kolonlar arası Hamming dağılımı yok |
| 21 — optimizasyon motoru | VAR | Planın "ilk sürümde yapılmamalı" dediği şey zaten yapılmış: `core` ILP + blok + sezgisel; kaplama ekseni **kapandı** (kanıtlanmış optimal, §6.1) |
| 22 — raporlama şeması | VAR | `payloads.py` + `frontend/lib/api-sozlesme.json` (üretilen ve tazeliği denetlenen sözleşme) |
| 23 — CLI | VAR | `python -m spor_toto.cli` (`--mc-samples`, `--seed`, …) |
| 24 — logging | KISMİ | `web_app` `logger` kullanıyor; `analysis.py` sessiz (231 satır, log gerektiren uzun bir koşumu yok) |
| 25 — benchmark | VAR | Ölçümler docstring'lerde ve bu belgede sayıyla; `health.py` her kontrole süre bütçesi koyuyor |
| **26 — memory safety** | **YOKTU → düzeltildi** | §2.3 |
| 27 — determinizm | VAR | `test_analysis.test_monte_carlo_deterministik` |
| 28 — edge case'ler | VAR | `test_edge_cases.py` + eklenenler (14 maçlık kupon, `max_d` sınırları, geçersiz olasılık) |
| 29 — duplicate kolon | YOK | Uygulanmadı; `merge_rows` satır sıkıştırması var ama duplicate kolon raporu yok |
| 30 — input şeması | VAR | `Encoder` + `parse_picks` + API sözleşmesi |
| 31 — paket bölünmesi | REDDEDİLDİ | §3.3 |
| 32–33 — type hints / dataclass | KISMİ | Kademeli mypy; `analysis.py` hâlâ `ignore_errors` bloğunda (`pyproject.toml` "Araştırma ve ölçüm katmanı") |
| 34 — dokümantasyon | VAR | Docstring'ler matematiksel tanımı ve **niçin öyle** olduğunu taşıyor |
| 35–36 — matematiksel / istatistiksel doğrulama | VAR | Exact–MC karşılaştırması toleranslı; testler beklenen değere karşı yazılı |
| 37 — API uyumluluğu | VAR | Bu turda hiçbir çıktı anahtarı kaldırılmadı; eklenenler additif ve sözleşme yenilendi |
| 38 — final test matrisi | VAR | `pytest`, `ruff`, `mypy` — üçü de `check.sh`te ve CI onu **çağırıyor** |
| 39 — performans kabul ölçütleri | VAR | §2.3 ölçümleri |
| 40 — final report | VAR | `report.py` insan-okunur çıktı basıyor |

---

## 6. Alınmayan ama kaydedilen

Bunlar reddedilmedi; sıraya girmesi için ölçülmüş bir gerekçe bekliyorlar.

**Monte Carlo'nun vektörleştirilmesi** (analiz planı FAZ 7). Örnekleme hâlâ
saf Python: web varsayılanında 80.000 örnek × 15 maç ≈ 1,2 milyon `random()`
çağrısı, senkron istek yolunda. Gerçek bir hızlanma fırsatı ama **bugün
ölçülmüş bir darboğaz değil** (`health` 5.000 örneği 140 ms'de koşuyor) ve
determinizm sözleşmesini —aynı girdi + aynı tohum = aynı çıktı— riske atar.
Yapılacaksa exact motora karşı doğrulanarak yapılmalı.

**Expected Hits** (FAZ 10) ve **kolon fazlalığı analizi** (FAZ 19–20). İkisi
de tanımlanabilir ve hesaplanabilir; ikisi de bugün bir karara bağlanmıyor.
Planın kendi kuralı geçerli: "bir metrik matematiksel olarak tanımlanmamışsa
üretme" — ve buna "bir karara girmiyorsa üretme" eklenmeli, çünkü ölçülen ama
kullanılmayan sayı bakım borcudur.

**`drift.py`** — `DIS_INCELEME_AZ_RAPORU.md` §7'de zaten kayıtlı ve gerekçesi
oradaki ileri yürüyüş bulgusuyla güçlendi.

---

## 7. Bu turda değişen sayılar

Refactor, öncesi/sonrası karşılaştırılmadan tamamlanmış sayılmaz (backtest
planı Kural 3). Değişen üç sayı:

| Sayı | Önce | Sonra | Niçin |
|---|---:|---:|---|
| `error_freq.d2` yüzde toplamı | 200,01 | 100,00 | Payda hata yuvası oldu (§2.2) |
| `error_freq.d2` satır yüzdesi (örnek) | %31,15 | %15,57 | aynı |
| `monte_carlo.*.ci95` | `1.96 × se` | `1.959964 × se` | Gömülü sabit `ortak.GUVEN_Z` oldu; fark ~0,002 % |

**Değişmeyen** ve değişmemesi gereken sayılar: `holdout.columns_avg` 2.228,4
(§2.4), `season.hit14` 3/36, `holdout.hit14` 1/36, exact/MC olasılıkları,
kaplama bedelleri. `check.sh` on adımın hepsinde yeşil.
