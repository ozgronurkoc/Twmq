# Spor Toto Lab — 14-Garanti Formül Üreticisi

Spor Toto kuponu için tarihsel veriyi ve piyasa oranlarını analiz edip **maç sonucu
tahmini** üreten, bu tahmini **kaplama kodu** (covering code) ile en az kupona
indiren ve her iki katmanın da isabetini/sınırını ölçen açık bir laboratuvar.

**Amaç kazanma oranını artırmaktır.** Hedefe bugünkü mesafe ölçülmüştür ve
belgede açıkça yazar (§1.1) — ölçülmemiş hiçbir iyileşme iddia edilmez.

Kaplama katmanının vaadi ayrıdır ve tahminden bağımsızdır: seçtiğin ihtimal
kümeleri içinde doğru sonuç varsa, oynanan kolonlardan en az biri **en fazla 1 maç
hatalı** olur — yani **14-garanti**. Bu garanti bir tahmin değil, kombinatoryal bir
teoremdir: doğruysa her zaman doğrudur, yanlışsa hiçbir zaman doğru olmaz.

---

## 1. Vizyon

Bahis araçlarının çoğu aynı şeyi yapar: bir sayı üretir, o sayının nereden geldiğini
anlatmaz ve kullanıcıya kazanma hissi satar. Bu proje bunun tam tersini denemektedir.

**Amaç: elimizdeki veriyi analiz ederek kazanma oranını artıracak sonuçlar
üretmek.** Proje maç sonucu tahmini yapar ve bu tahmini en az kupona indirir. İki
katman birlikte çalışır: **tahmin katmanı** hangi sonuçların işaretleneceğine
katkı verir, **kaplama katmanı** o seçimi mümkün olan en ucuz şekilde oynatır.

Bu bir vaat değil, bir hedeftir — ve hedefe bugünkü mesafe ölçülmüştür (§1.1).
Aşağıdaki beş taahhüt amacın kendisinden bağımsızdır: onlar *neyi hedeflediğimizi*
değil, *neyi saklamadığımızı* tanımlar. Amaç değişti, bu taahhütler değişmedi.

### 1.1 Tahmin hedeftir, garanti teoremdir — ikisi karıştırılmaz

Amaç tahmin olsa da 14-garanti tahminle değişmez. Garanti Hamming geometrisinden
gelir: seçim kümesi içinde doğru sonuç varsa en fazla 1 hata kalır. Bu
kombinatoryal bir teoremdir; olasılık, Bayes, Markov hiçbiri onu güçlendirmez
veya zayıflatmaz. Kodda ayrım korunur: `core.py` olasılık katmanını hiç bilmez.

Değişen şey, **kümeyi kim seçiyor** sorusunun cevabıdır. Önceden işaretleri
yalnızca kullanıcı koyardı, araç maliyeti düşürmekle yetinirdi. Artık tahmin
katmanı bu seçime katkı verir ve **isabeti ölçülür** (§1.6).

**Hedefe bugünkü mesafe ölçülmüştür ve küçüktür.** Piyasa oranlarından mekanik
olarak üretilen strateji 36 haftanın 3'ünde 14+ tutturdu; eşik o haftayı görmeden
seçildiğinde (hold-out) **1**. Piyasanın kendi Brier skoru 0,579 — eşit olasılık
dağıtmanın karşılığı 0,667, yani piyasa bilgi taşıyor ama az. İddaa marjı %17,2.
Bu üç sayı tahmin katmanının **başlangıç çizgisidir, varış noktası değil**:
ilerleme bunlara karşı ölçülür ve ölçülmeden ilerleme sayılmaz.

**İlk üç adım ölçüldü ve sonuç şudur.** Tahminci sözleşmesi, değerlendirme
koşumu, yeniden kalibrasyon kademesi ve 31.103 maçlık eğitim korpusu kuruldu
(T1–T3). Kupon üzerinde eğitilen modeller piyasadan **kötü** çıkıyordu; büyük
korpusta eğitilince hepsi **iyi** tarafa geçti — aşırı uyum modelin
kapasitesinden değil örneklem küçüklüğünden geliyormuş. Ama kalan etki
**0,0005–0,0015 Brier**: 31 binde istatistiksel olarak anlamlı, 540 kupon
maçında değil ve %17,2'lik iddaa marjının yanında pratik eşiğe yakın bile
değil. **Yön doğru, miktar yetersiz** — ayrıntı §10 ve
[`docs/ISTATISTIK_YOL_HARITASI.md`](docs/ISTATISTIK_YOL_HARITASI.md) §5.1.

### 1.2 Belirsizlik saklanmaz, ölçülür ve gösterilir

Garanti yalnızca **seçim kümesi içinde** geçerlidir. Küme dışına çıkan bir sonuç
gelirse sistem o senaryoyu kapsamaz. Bu bir hata değil, tasarımın sınırıdır — ve
bir aracın en kolay gizleyebileceği şey tam olarak budur.

Bu yüzden sınırın ötesi ayrı bir katman olarak ölçülür: **fire analizi** (CLI
`--fire`, arayüzde *Fire* sekmesi) bir veya iki maç işaretlerin dışına çıkarsa en
iyi kolonun kaç tutturduğunu, banko/çifte ayrımıyla birlikte gösterir. "Ya
yanılırsam?" sorusunun cevabı üründe görünür bir yerde durur.

### 1.3 Veri kendini denetler, çelişki raporlanır

Tarihsel veri ve oran arşivi bu projede birer süs değil, denetlenen varlıklardır.
Maç listesi, sonuç dizisi ve sayımlar birbirini tutmadan dosya yazılmaz; okuma
anında aynı denetim tekrarlanır ve sonucu `data_quality` bloğu olarak **arayüzde
görünür**. "Sessizce doğru olanı seç" yaklaşımı, hatanın bir sonraki sefere kadar
saklanması demektir (bkz. §5.6 vaka: v1 sıra hatası).

### 1.4 Kaynak dürüstlüğü

Verinin ne **olmadığı**, ne olduğu kadar önemlidir. Arşivdeki oranlar piyasa
oranıdır, **iddaa oranı değildir** — ve bu, kodda, belgede ve arayüzde her yerde
yazar. Otomatik erişime kapalı bir kaynaktan veri çekilmez.

### 1.5 Vaat bir kez değil, her çağrıda kanıtlanır

Yukarıdaki dört taahhüdün hepsi kodda doğru yazılmış olabilir ve yine de
**yayındaki sürümde** geçerli olmayabilir: bağımlılık kurulamaz, veri dosyası
dağıtıma girmez, yanlış commit yayınlanır. Testler bunu yakalamaz — testler CI
makinesinde, o günkü kilitli bağımlılıklarla, o commit üzerinde koşar.

Bu yüzden sağlık katmanı ayrı bir katmandır ve `/saglik` sayfası ürünün eşit
haklı bir parçasıdır: **ürünün vaadinin şu anda, bu makinede, bu sürümde hâlâ
geçerli olduğunu kanıtlar.** 24 değişmez, 6 kategori, her çağrıda yeniden
ölçülür — ve neyi kanıtlamadığını da açıkça yazar (§6.3).

### 1.6 Ne yapar / ne yapmaz

| Yapar | Yapmaz |
|-------|--------|
| 41 haftalık sezon verisini ve piyasa oranlarını analiz edip **maç sonucu tahmini** üretir | Kazanmayı **garanti etmez** |
| Tahmin isabetini ölçer ve hold-out ile aşırı uyumdan ayırır | Ölçülmemiş bir isabet iddiası sunmaz |
| Hamming yarıçap-1 kaplama kodu üretir | 14-garantiyi olasılıkla "güçlendirmez" |
| En kötü durumda 14 doğru **garantiler** (küme içinde) | İkramiye / beklenen değer hesabı yapmaz (veri ilk kez birikiyor, ölçüm yok — §10) |
| Küme dışı senaryoları **fire** olarak ölçer | Kâr vaadi vermez |
| Exact + Monte Carlo olasılık raporu verir | Canlı bülten çekmez |
| Bayes (Dirichlet) ile tahminlerini yumuşatır | İddaa geçmiş oranı sunmaz (yok — §5.3) |
| Markov ile sıralı risk profili çıkarır | Geri testi bir kâr vaadine çevirmez; aşırı uyumu ölçüp gösterir |
| Bir stratejiyi geçmiş sezonda çalıştırıp bedelini ve isabetini ölçer (**geri test**) | Mobil uygulama değildir |
| Vaadin canlıda geçerliliğini 24 değişmezle ölçer | |
| Her sayının kaynağını ve sınırını yazar | |

---

## 2. Hızlı başlangıç

Python tarafının tamamı `backend/`, arayüzün tamamı `frontend/` altındadır.

```bash
# 1) Motor + API
cd backend
pip install -e ".[test]"        # calistirma + test
pip install -e ".[test,model]" # + olcum katmani (sklearn, lightgbm)
pip install -e ".[test,kalite]" # + ruff/mypy (scripts/check.sh bunlari ister)

# 2) CLI
spor-toto --picks "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"

# 3) API + arayüz birlikte (repo kökünden)
bash scripts/run_next_dev.sh    # UI :3000, API :8080
```

Adım 1'i atlamak isterseniz `bash scripts/setup.sh` pip ve npm bağımlılıklarını
birlikte, kuruluları atlayarak kurar; `run_next_dev.sh` zaten kendisi çağırır.
Replit kurulumu (Run düğmesi, iş akışları, dağıtım): `replit.md`.

Bağımlılıklar: `numpy`, `scipy` (kesin ILP için), `flask`, `gunicorn`.
`scipy` yoksa araç çalışır; yalnızca kesin çözücü (ILP) devre dışı kalır.
Python ≥ 3.10. Arayüz: Next.js 14 App Router + TypeScript + Tailwind.

---

## 3. Katman 1 — Kombinatoryal çekirdek

Ürünün değişmeyen çekirdeği. Girdi 15 maçlık işaret kümesi, çıktı kupon
satırlarıdır; arada olasılık yoktur.

### 3.1 `--picks` biçimi

- 15 maç virgülle ayrılır
- Her maçın seçenekleri bitişik yazılır
- `1` = banko ev, `0` = beraberlik, `2` = deplasman
- `10` / `02` / `12` = çifte, `102` / `012` = üçlü (kapama)
- Baş/son fazla ayırıcı (`",1,10,"`) yok sayılır; **ortadaki boş slot** (`"1,,10"`)
  `ValueError` fırlatır
- `"1, 10"` gibi boşluklu yazım geçerlidir

### 3.2 Modlar

| Mod | Ne yapar |
|-----|----------|
| `fix16` (varsayılan) | Her zaman 16 kupon satırı. En az 7 çifte zorunlu. Hamming(7,4) tabanlı. |
| `auto` | En ucuz çözümü arar; satır sayısı değişken. Web'de ILP'ye kısa bir bütçe verilir (`auto_ilp_limit`, 3 sn) — kanıt isteyen `exact` kullanır. |
| `exact` | ILP ile kanıtlanmış optimal (küçük uzaylar). Uzay sınırını yok sayar, tam `--time-limit` bütçesini kullanır. |
| `block` | Yalnızca blok ayrıştırma motoru. |
| `heuristic` | Açgözlü + local search (büyük uzaylar). |
| `butce` | "Elimde N kolon var, hangi maçı kısmalıyım?" |
| `maxcov` | Sabit bütçeyle maksimum kapsama. **Garanti vermez.** |

```bash
spor-toto --picks "..." --variant 3
spor-toto --picks "..." --mode auto
spor-toto --picks "..." --mode butce --budget 32
spor-toto --picks "..." --mode maxcov --budget 16
spor-toto --picks "..." --kati            # katı doğrulama
spor-toto --picks "..." --kisa            # kısa çıktı
spor-toto --picks "..." --output rapor.txt
```

Motor ayarları: `--trials`, `--ls-iters`, `--seed`, `--time-limit`,
`--block-limit`, `--exact-limit`, `--plan`, `--plan-uygula`.

Mod dağıtımı tek yerdedir (`spor_toto/engines.py`): CLI, `/api/solve` ve sağlık
raporu aynı çalıştırıcıları kullanır. CLI'de `auto` tam zaman bütçesiyle koşar —
komutu bilerek çalıştırdın ve karşısında oturuyorsun; web'de aynı bekleme istek
yolunu tıkardı.

### 3.3 Satır ≠ kolon

Bir maça çifte işaretlersen o satır **2 kolon** üretir ve 2 kolon bedeli ödersin.
16 satır + ekstra çifte faktörü = daha yüksek bedel. UI ve CLI toplam **kolon
bedelini** gösterir; bu bir tasarım kuralıdır, kolon bedeli hiçbir yerde satır
sayısından ayrı gösterilmez.

### 3.4 Bilinen matematiksel sınırlar

Küre-kaplama alt sınırı: `kolon ≥ |uzay| / top_boyutu`.

| Durum | Optimal kolon (alt sınır civarı) |
|-------|----------------------------------|
| 5 çifte | 7 |
| 6 çifte | 12 |
| 7 çifte | **16** (Hamming(7,4)) |
| 8 çifte | **32** |
| 4 üçlü | **9** |

**8 çifteyi 16 kolona sığdırmak imkânsızdır.** `maxcov` 16 kolonla kısmi kapsama
verir — **garanti değildir** ve arayüz bunu her seferinde yazar.

---

## 4. Katman 2 — Olasılıksal analiz

Bu katmanın tamamı isteğe bağlıdır ve **garantiyi değiştirmez**. `probs`
verilmezse `advanced`, `bayes` ve `markov` blokları `null` döner.

`--probs`: maçlar `;` ile ayrılır, her maç `1:0.5,0:0.3,2:0.2`. Ham ağırlık da
kabul edilir, normalize edilir.

```bash
# Exact + Monte Carlo
spor-toto --picks "..." --probs "..." --mc-samples 20000

# Dirichlet Bayes (preset kısayolu)
spor-toto --picks "..." --probs "..." --bayes-preset dengeli --mc-samples 10000

# Manuel α / n
spor-toto --picks "..." --probs "..." --bayes --prior-strength 2 --evidence-strength 20

# Seçim DIŞI fire analizi
spor-toto --picks "..." --fire
spor-toto --picks "..." --fire --fire-max 1
```

### 4.1 Bayes presetleri

| Preset | Prior α | Evidence n | Ne zaman |
|--------|---------|------------|----------|
| `zayif_prior` | 0.5 | 15 | Evidence'e güven yüksek |
| `dengeli` | 1.0 | 10 | Varsayılan denge |
| `guclu_prior` | 5.0 | 8 | Seçim kümesine güçlü güven |
| `evidence_agir` | 1.0 | 40 | Evidence neredeyse doğrudan alınır |
| `sadece_prior` | 3.0 | 0 | Evidence yok sayılır (posterior = prior) |

Web'deki preset dropdown CLI ile **aynı α/n** değerlerini kullanır; arayüz bunları
`GET /api/meta` üzerinden okur, sabit kodlamaz. CLI çıktısında `Kaynak:
bayes_posterior`, ortalama KL + etiket (`ihmal edilebilir` … `güçlü kayma`) ve
maç bazlı en büyük KL kaymaları görünür — web'deki "Yorum" sütunuyla aynı bilgi.

### 4.2 Ne ölçülür

| Blok | Soru |
|------|------|
| Exact olasılık | Seçim kümesi içinde kalma olasılığı tam olarak nedir |
| Monte Carlo | Aynı sayı örneklemeyle ne çıkıyor (%95 güven aralığıyla) |
| Bayes | Girdiğim olasılıklar seçim kümemle ne kadar çelişiyor (KL) |
| Markov | Maç maç ilerlerken hata bütçesi (0 / 1 / 2+) nasıl tükeniyor |
| Hata frekansı | d=1 ve d=2 katmanlarında hangi maç hata üretiyor |
| **Fire** | **Küme dışına çıkarsam en iyi kolonum kaç tutturur** |

Fire bloğu olasılık girdisi gerektirmez, çünkü olasılıkla ilgili değildir — sınırın
ötesindeki kombinatoryal manzarayı çizer. Pahalı olduğu için maliyet sınırı vardır;
aşılırsa blok sessizce `null` olmaz, `{"skipped": true, "reason": …}` döner.

---

## 5. Katman 3 — Veri ve istatistik

Motor tek başına tarihsiz çalışır; istatistik katmanı ona bağlam verir. **Üç** veri
seti vardır; ilk ikisi tek komutla kaynağından yeniden üretilebilir, üçüncüsü
üretilemez — ileriye dönük birikir.

| | Tarihsel sonuçlar | Piyasa oranı arşivi | İddaa bülten arşivi |
|---|---|---|---|
| **Dosya** | `data/st_history_2025_26.json` | `data/odds/odds_2025_26.csv` | `data/iddaa/iddaa_<tarih>.csv` |
| **Üreten** | `scripts/build_history.py` | `scripts/build_odds.py` | `scripts/snapshot_iddaa.py` |
| **Okuyan** | `spor_toto/history.py` | `spor_toto/odds.py` | (henüz analize girmiyor) |
| **Bekçi** | `tests/test_history.py` | `tests/test_odds.py` | `tests/test_snapshot_iddaa.py` |
| **Yönü** | geriye dönük, tamam | geriye dönük, tamam | **ileriye dönük, birikiyor** |

(Yollar `backend/` altındadır.)

### 5.1 Veri akışı

```
sportototahmin hafta payload'ları
        │  scripts/build_history.py   (haftanın kendi matches dizisi, sırayla)
        ▼
data/st_history_2025_26.json          41 hafta · 615 maç · maç listesiyle
        │  spor_toto/history.py       (6 analiz bloğu, dilimleme, veri kalitesi)
        ▼
GET /api/stats[?last=N] ─────────────► /istatistik
GET /api/stats/<week>   ─────────────► /istatistik/<hafta> ──┐ 15 maçın olasılığı
        ▲                                                     ▼
        │  spor_toto/odds.py          (1X2 özeti, banko bantları,    /  formül sayfası
        │                              kalibrasyon, çift kapsama,
        │                              beraberlik, lig, Brier)
data/odds/odds_2025_26.csv            567 maç · 108 oran sütunu
        ▲       │  spor_toto/backtest.py   (eşikli seçim → kaplama → skor)
        │       ▼
        │  GET /api/backtest ─────────────► /istatistik/geri-test
        │
        │  scripts/build_odds.py      (tarih ±1 gün + birebir skor + bulanık ad)
football-data.co.uk arşivi (38 dosya)

iddaa açık bülteni ──► scripts/snapshot_iddaa.py ──► data/iddaa/iddaa_<tarih>.csv
                       (haftalık; analize henüz girmiyor, birikiyor)
```

### 5.2 Veri doktrini

Bu yedi ilke, veri tarafındaki her kararın gerekçesidir. Tam metin:
[`docs/VERI_TOPLAMA_VE_ISLEME.md`](docs/VERI_TOPLAMA_VE_ISLEME.md) §1.

1. **Tek doğruluk kaynağı vardır ve zinciri bellidir.** Maç listesi → sonuç dizisi
   → sayımlar. Hiçbiri bağımsız yazılmaz.
2. **Kesin olmayan veri elenir, tahmin edilmez.** 15 maçı tam kapanmamış hafta
   analize hiç girmez.
3. **Sıra kaynağın kendi sırasıdır.** Tarihe göre sıralanmaz, isimden çıkarılmaz.
4. **Çelişki gizlenmez, raporlanır.** `data_quality` bloğu arayüzde görünür.
5. **Doğrulanmadan yazılmaz.** Üretim scriptleri `assert` geçmeden dosya yazmaz.
6. **Türetilmiş veri sürümlenir, ham veri sürümlenmez.** Ham indirmeler
   `.gitignore`'da; tek komutla geri gelirler.
7. **Kaynak dürüstlüğü.** Verinin ne olmadığı her yerde yazar.

### 5.3 Elimizde ne var

**Tarihsel sonuçlar** — 2025/2026 sezonu, 2025-08-18 → 2026-07-27, **41 hafta ·
615 maç** (yalnızca 15/15 kapanmış haftalar). Dağılım: 1 → 270 (%43,90) · 0 → 149
(%24,23) · 2 → 196 (%31,87). Her maç için takım adları, başlama saati, skor ve kod
saklanır.

**Oran arşivi** — football-data.co.uk piyasa oranları, **567 / 615 maç (%92,2)**,
41 haftanın 36'sı tam. **108 oran sütunu, 51.683 değer** (1X2 · 2.5 alt/üst · Asya
handikap, her biri açılış + kapanış) ve 14 maç istatistiği. Eşleşmeyen 48 maçın
45'i milli maç haftalarıdır (5, 10, 15) — kaynak milli maç yayınlamaz; bu yüzden
kapsama hiçbir zaman %100 olmayacak.

Eşleştirme anahtarı: **tarih (±1 gün) + birebir skor + bulanık takım adı**. Skor
şartı yanlış eşleşmeye karşı en güçlü korumadır.

**Bunlar iddaa oranı değildir.** İddaa geçmiş bültenini yayınlamıyor (resmi API
yalnızca açık bülteni veriyor), Maçkolik ise `robots.txt` ile otomatik erişime
kapalı. Piyasa oranının **seviyesi** iddaa ile tutmaz (marj farkı), **favori
sıralaması ve marj arındırılmış olasılık yapısı** tutar — analizde kullanılan da
budur.

Bu fark artık ölçülmüş bir sayı: iddaa açık bülteninde ortalama marj **%17,2**,
piyasa oranlarında **%7,26** — iddaa payı iki katından fazla.

**İddaa bülten arşivi** — yukarıdaki boşluğu ileriye dönük kapatmak için haftalık
snapshot alınır: yalnızca futbol, yalnızca maç sonucu (1X2), kupon ve web fiyatı
ayrı ayrı. Ölçümde 226 futbol etkinliğinin 225'inde 1X2 pazarı var; 222'si
kaydedildi (1'inde pazar yok, 3'ünde bir ayak `1.00` — bu bir fiyat değil, askıya
alınmış ayağın yer tutucusu, elenir).

Bu arşiv **bugün analize girmiyor**: tek snapshot bir şey söylemez, değeri
birikimdedir. Diğer iki setten kritik bir farkı var — **yeniden üretilemez.**
Kapanmış bir bülten bir daha çekilemez, o yüzden orada sürümlenen şey türetilmiş
çıktı değil arşivin kendisidir.

### 5.4 Ölçülmüş bulgular

Bunlar tahmin değil, bu veri seti üzerinde hesaplanmış sayılardır.

**Banko güvenilirliği** (kapanış favorisinin oranına göre):

| Favori oranı | Maç | Tuttu | Tutmadı | ↳ beraberlik | ↳ karşı taraf |
|---|---:|---:|---:|---:|---:|
| 1.00–1.20 | 11 | %90,9 | %9,1 | %9,1 | %0,0 |
| 1.20–1.35 | 39 | %76,9 | %23,1 | %17,9 | %5,1 |
| 1.35–1.50 | 64 | %64,1 | %35,9 | %23,4 | %12,5 |
| 1.50–1.75 | 106 | %60,4 | %39,6 | %20,8 | %18,9 |
| 1.75–2.00 | 104 | %50,0 | %50,0 | %35,6 | %14,4 |
| 2.00+ | 243 | %46,9 | %53,1 | %25,5 | %27,6 |

Okuma: 1.35 pratik bir sınır. 1.75–2.00 bandı tuzaktır — isabet %50'ye düşerken
tutmama sebebinin çoğu beraberliktir; orada banko yapmak aslında beraberliğe karşı
bahis yapmaktır.

**Favori kırılımı** — 567 maçın 311'inde favori tuttu (1 → 205, 2 → 106; **0 asla
favori olmadı**). Gerçek sürpriz (karşı taraf kazandı): 112 maç (%19,8). Piyasa iki
yönde de aynı doğrulukta: favori "1" iken isabet %54,8, "2" iken %54,9.

**Kalibrasyon** — 8 kova; ör. %20–30 kovasında model %25,5 → gerçek %24,7.
Ortalama marj %7,26. Rastgele ya da kaymış bir eşleştirme bu tabloyu üretemez;
`test_odds.py` favori isabetini alt/üst sınırla bekçiye bağlar.

**Marj arındırma yanlılığı (A5)** — yukarıdaki kalibrasyon 567 kupon maçında ölçülür;
31.103 maçlık korpusta aynı tablo çıkarılınca sapma **düzenli ve tek yönlü** çıkıyor:
piyasanın %70–80 dediği maçlar gerçekte **%78,9** oluyor (n=1.702, +4,4 puan, %95
güven aralığının dışında) ve 15 banttan 10'u anlamlı sapıyor. Sebep piyasanın hatası
değil, **oranı olasılığa çevirme biçimimiz**: marj her sonuca eşit dağıtılıyordu, oysa
bahisçi onu sürprizlere ağır yükler. `odds.implied_probs` artık `shin` ve `guc`
yöntemlerini de taşıyor — Brier 0,5940 → **0,5936**, fark −0,00035 [−0,00049,
−0,00021], yani projenin geçme kuralını (aralığın tamamı sıfırın altında)
sağlıyor; anlamlı sapan bant 10 → **4**.

**Varsayılan 2026-08'de `shin`e çevrildi.** Bu sayfadaki oran tabloları o gün
yeniden koşuldu; çevrimden önceki sayılar orantısal ölçekte ölçülmüştü ve
yenileriyle doğrudan kıyaslanamaz. İki istisna bilerek `orantili`da bırakıldı:
açılış↔kapanış hareketi ve bahisçi anlaşmazlığı. İkisi de bir **fark** ölçer ve
orantısal yöntem oranın ölçeğinden bağımsız olan tek yöntemdir — Shin'de,
bahisçinin yalnızca marjını büyütmesi "hareket" ya da "anlaşmazlık" gibi
okunurdu (ayrıntı: `docs/ISTATISTIK_YOL_HARITASI.md` §3.18).

**İşlenen sezonun karnesi** — `python scripts/super_toto_sezon.py`. Girilmiş
bütün haftaları üst üste koyar: birikimli Brier, favori isabetinin gözlenen ↔
beklenen sapması, en iyi kolon dağılımı, canlı sezon kalibrasyon eğrisi. Her
koşumda **örneklem yeterliliği** satırını basar: aranan üstünlük 0,0005 Brier,
bu örneklemde %95 aralığın yarı genişliği onun yüzlerce katı, ayırt edebilmek
için ~2,5 milyon maç gerekir. Defter kural değiştirmek için değil, kuralın ne
yaptığını görmek içindir — 5-10 hafta sonra doğacak "eşiği oynatalım" baskısına
karşı tek savunma budur.

**Havuz ekseni (Faz B)** — `python scripts/faz_b.py`. Sorusu kuruldu: *aynı
tutturma olasılığında az oynanan sembolü işaretlemek kişi başı ikramiyeyi
büyütüyor mu?* Bu soru **piyasayı geçmeyi gerektirmiyor**, o yüzden A1–A3'ün
kapattığı arayış bu ekseni kapatmıyor. Bugünkü cevap **ölçülemez**: elde 1
haftalık ikramiye kaydı var, güç analizi ≈71 ikramiyeli hafta (≈3,5 sezon)
istiyor. Durma kuralı şimdiden yazılı (`docs/ISTATISTIK_YOL_HARITASI.md`
§6.3b).

**"Bu oranda geçmişte ne olmuş?"** — `python -m spor_toto.benzer --oran 1.82,3.04,2.44`
ya da `GET /api/benzer?oran=1.82,3.04,2.44`. Verilen orana benzeyen geçmiş maçları
31 binlik korpusta bulur ve nasıl bittiklerini sayar. Eşleme **olasılık uzayında**
yapılır, oran uzayında değil: örnek oran (marj %28,8) korpusta ±%10'luk oran
komşuluğunda **hiç** maç bulmuyor, olasılık uzayında ±2 puanda **710** maç buluyor.
Her yüzde yanında n ve Wilson %95 aralığı gelir; 30 maçın altındaki dilim sayı vermez.

**Çift kapsama** — ilk-iki olasılık toplamı 0,70–0,80 iken gerçek sonuç küme içinde
kalma oranı %77,2; 0,80–0,90 iken %85,3; 0,90+ iken %95,1. Aynı bantlarda **banko**
yapılsaydı: %47,8 / %65,4 / %80,5. Yani en üst bantta ikinci işaret kolonu ikiye
katlayıp isabete yalnızca 14,6 puan ekliyor — çifte kararı bu tablonun işidir.

**Beraberlik profili** — favori ile ikincinin olasılık farkı 0–0,05 iken beraberlik
%34,0; 0,50+ iken %15,5. Eğilim var ama **tam monoton değil**. Tahmin katmanının
girdilerinden biridir; tek başına bir tahminci olarak kullanılamayacak kadar
zayıftır ve isabeti ölçülmeden karara bağlanmaz (§10.2).

**Lig kırılımı** — kuponun yarısı Süper Lig'den geliyor (kupon başına 7,5 maç) ve
orada beraberlik %29,8; Premier Lig'de %19,7. Bu fark "0" bütçesinin nereye
harcanacağını değiştirir.

**Piyasa hangi hafta yanıldı** — haftalık Brier skoru: sezon ortalaması **0,579**
(oranı olan 567 maç, 38 hafta). Üç sembole eşit olasılık vermenin karşılığı
0,667, yani piyasa bilgi taşıyor ama az. Favori isabeti tek başına yanıltıcıdır: 1,05 oranlı favorinin tutmasıyla 2,40
oranlınınki aynı sayılmaz; Brier olasılığın tamamını cezalandırır.

**Geri test** — varsayılan eşiklerle 36 haftanın **3'ünde** 14+ tutuyor (%8,3; %95
aralık %2,9–%21,8), hafta başına ortalama **1.987 kolon**. 15 maçın tamamının
işaretler içinde kaldığı hafta **yok**. Aynı yöntem eşiği o haftayı görmeden
seçtiğinde (**hold-out**) **1 hafta** ve hafta başına 2.228 kolon.

Bu satırlar 2026-08'de marj arındırma varsayılanı `shin`e çevrilince yeniden
koşuldu (§5.4, A5). Orantısal ölçekte aynı tablo 2.686 kolon/hafta ve hold-out'ta
**0** haftaydı; hold-out ayrıca eşiği 36 haftanın 31'inde 0,68/**0,42**'ye
kaydırıyordu. Shin ölçeğinde eşik 34 haftada 0,68/**0,38**'de — yani projenin
varsayılanında — kalıyor. **Eşik baştan doğruydu; onu besleyen olasılık
eğriydi.** Hold-out'taki 0→1 farkı tek bir olaydır ve güven aralıkları
fazlasıyla örtüşür (%0,5–14,2 ↔ %0–9,6); okunacak sağlam sayı isabet değil
**maliyettir**: 3,1 kat düşüş.

### 5.5 Veri kalitesi denetimi

`history.py` her okumada seti denetler ve sonucu API'ye koyar:

| Alan | Ne yakalar |
|---|---|
| `count_conflicts` | Dosyadaki `n1/n0/n2` ile diziden türeyen sayım çelişiyor |
| `match_conflicts` | Maç listesinin kodları diziyle örtüşmüyor (sıra dahil) |
| `weeks_without_matches` | Hafta maç listesi taşımıyor |
| `incomplete_weeks` | 15 maçtan az |
| `duplicate_results` | İki hafta birebir aynı diziyi taşıyor |
| `ok` | Hepsi temizse `true` |

Bu blok **arayüzde gösterilir**. Temizse yeşil bir satır, değilse hangi haftada ne
olduğu.

### 5.6 Neden bu denetim var — v1 sıra hatası

İlk üretimde payload düz taranıyor, haftanın kendi `matches` dizisiyle komşu
haftaların `featuredMatches` blokları karışıyordu. Sonuç: 41 haftanın **15'inde
sonuç dizisi yanlış sıradaydı**, 6'sında sayım da tutmuyordu; iki hafta çifti
birebir aynı diziyi taşıyordu.

Sezon toplamları etkilenmemişti — bu yüzden hata aylarca görünmedi. Ama **sıraya
bağlı her analiz** (maç sırası dağılımı, geçiş matrisi, seriler) 15 haftada
kirliydi. Düzeltme sonrası 51. hafta bağımsız bir kaynakla çapraz doğrulandı ve
birebir tuttu (`000111122212011`).

**Ders:** doğru görünen bir toplam, altındaki verinin doğru olduğunu göstermez.
Bugün `match_conflicts` tam olarak bunu yakalar. Vaka analizi:
[`docs/VERI_TOPLAMA_VE_ISLEME.md`](docs/VERI_TOPLAMA_VE_ISLEME.md) §7.4.

---

## 6. Katman 4 — Gözlem: arayüz, API, sağlık

### 6.1 Sayfalar

| Rota | İçerik |
|------|--------|
| `/` | **Formül** — motorun tamamı |
| `/istatistik` | Sezon dağılımı, bantlar, oran kartı, karar destek tabloları, 41 hafta |
| `/istatistik/<hafta>` | Tek hafta detayı + "bu haftayı formüle gönder" |
| `/istatistik/geri-test` | **Geri test** — strateji, eşik taraması, hold-out |
| `/saglik` | Değişmezler — kategori kategori, süre ve açıklamalarıyla |

**Formül sayfası — girdi:** 15 × 3 maç ızgarası (klavye: ok tuşları + `1` / `0` /
`2`) · **maç adları** (toplu giriş; hafta detayından devirde kendiliğinden gelir)
· canlı sayaç (banko / çifte / üçlü / uzay) · **üretmeden önce görülen koşul**
(seçim kümesinin doğru sonucu içerme olasılığı + maç başına kütle + verime göre
ekleme önerileri) · **7 modun tamamı** · varyant, bütçe, bütçe planı, katı
doğrulama · maç bazlı olasılık girişi · Bayes preset veya elle α/n · Monte Carlo
örnek sayısı (1.000–200.000) · fire analizi (kapalı / 1-fire / 1 ve 2 fire) ·
motor ayarları.

Kurulum **kalıcıdır**: maç işaretleri, adlar, olasılıklar ve motor ayarları
tarayıcıya yazılır, yenileme kaybettirmez. *Bağlantıyı kopyala* aynı kurulumu
~110 karakterlik bir adrese kodlar (ayrıntı ve kayıplar: `frontend/README.md`).

**Formül sayfası — sonuç sekmeleri.** Sekmeler motor bloğuna göre değil
**soruya göre** bölünür:

| Sekme | Cevapladığı soru | İçindekiler |
|-------|------------------|-------------|
| Ne aldım | Kaça mal oldu, ne garanti ediyor? | garanti durumu, satır/kolon/alt sınır, bütçe planları, uyarılar, **çalıştırılan modların karşılaştırması**, kapsama dağılımı + uniform taban |
| Ne yazacağım | Kupona ne yazacağım? | kupon tablosu, satır başına kolon bedeli, kopyala (başlıkta maç adları) |
| Ne kadar riskli | Tahminlerime göre ne olur? | exact vs Monte Carlo (%95 CI), hata bütçesi (0 / 1 / 2+), küme-içi çözülme, Bayes (prior → posterior, KL) |
| Zayıf halkalar | Hangi maçı değiştirmeliyim? | hata frekansı (d=1, d=2), **fire** — seçim dışı senaryolar |
| Log | — | motorun adım adım çalışma logu |

Bu sayfanın çalışma raporu ve yol haritası ayrı belgelerdedir:
[`FORMUL_GELISTIRME_RAPORU.md`](docs/FORMUL_GELISTIRME_RAPORU.md) ·
[`FORMUL_YOL_HARITASI.md`](docs/FORMUL_YOL_HARITASI.md).

**İstatistik sayfası:** sezon dağılımı · 5 sayı kutusu · haftalık seyir çizgisi ·
haftalık bantlar (min–maks, ±1σ, ortanca, ortalama) · adet dağılımı · **oran kartı**
(favori isabeti + kırılım + çapraz tablo + banko bantları + **çift kapsaması** +
**beraberlik profili** + **lig kırılımı** + kalibrasyon) · **geri test özeti** · maç
sırasına göre ısı haritası · geçiş matrisi · uçlar ve seriler · hafta tablosu
(**Brier sütunu + CSV dışa aktarma**) · veri kalitesi paneli. Aralık filtresi
`?last=N` olarak adres çubuğunda durur — sayfa paylaşılabilir.

**Geri test sayfası:** aşırı uyum uyarısı · strateji seçici (banko/üçlü eşiği) +
sezon özeti + örnek kupon · **hold-out sağlaması** · 28 satırlık eşik taraması
(satıra tıklayınca uygulanır) · hafta hafta sonuç · yöntem notu. Sayfa "en iyi
eşiği bul ve oyna" diye kurulmamıştır: taramanın en iyisi ile hold-out yan yana
durur, çünkü karara esas olan ikincisidir.

**Sağlık sayfası** okuma sırasına göre kurulmuştur — her blok, bir öncekinin cevabı
yetmediğinde okunur:

| Sıra | Blok | Cevapladığı soru |
|---|---|---|
| 1 | Durum kartı | "İyi mi kötü mü?" |
| 2 | Düşenler özeti | "Ne bozuldu?" |
| 3 | Kategori kartları (+ *"yalnızca bunu çalıştır"*) | "Hangi katman, tam olarak ne?" |
| 4 | Çalışma geçmişi (oturum içi) | "Sürekli mi, arada bir mi?" |
| 5 | Çalışan ortam | "Hangi sürümlerde?" |

Süre çubuğu her satırda görünür, çünkü performans gerilemesi de bir gerilemedir:
bir kontrolün 8 ms'den 400 ms'ye çıkması hiçbir değişmezi kırmaz ama bir şeyin
değiştiğini kesin olarak söyler. Sayfa kategorileri, açıklamaları ve kritiklik
bayrağını rapordan okur — hiçbirini sabit kodlamaz.

### 6.2 API uçları

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/` | Servis bilgisi JSON |
| GET | `/api/meta` | Modlar, preset'ler, varsayılanlar, sınırlar |
| GET | `/health` | **Liveness** — süreç ayakta mı; hiçbir değişmez koşmaz (~2 ms) |
| GET | `/api/health` | **Readiness** — değişmezler (200 = HEALTHY/DEGRADED, 503 = UNHEALTHY); `?only=` kısmi, `?fresh=1` önbelleği atlar |
| GET | `/api/health/checks` | Kontrol envanteri — çalıştırmadan |
| GET | `/api/health/history` | Sunucudaki son koşular — "ne zamandan beri kırmızı?" |
| POST | `/api/health/kupon` | **Kullanıcının kendi kuponunu** aynı değişmezlerden geçirir |
| GET | `/api/stats?last=N` | Tarihsel 1/0/2 + analiz blokları + oran özeti |
| GET | `/api/stats/<week>` | Tek hafta detayı (komşular, sıra, sapma, maç listesi) |
| GET | `/api/backtest` | Geri test: sezon, hafta hafta, eşik taraması, hold-out |
| POST | `/api/solve` | Motorun tamamı |

`/api/backtest` parametreleri: `?banko=` / `?uclu=` (strateji eşikleri), `?last=N`
(dilim), `?sweep=0` (taramayı kapat). Sonuç sunucuda önbelleklenir — tek strateji
~1,2 sn, 28 eşikli tarama ilk çağrıda ~15 sn, sonrasında milisaniye.

Üç sözleşme kuralı:

1. **`/api/meta` frontend'in tek gerçek kaynağıdır.** Mod listesi, preset'ler ve
   sayısal sınırlar arayüzde sabit kodlanmaz — motorla tek kaynaktan senkron kalır.
2. **`?last=N` bütün blokları birlikte diler.** Özet, bantlar ve analiz bloklarının
   tamamı aynı dilim üzerinden hesaplanır; iki görsel asla farklı veriyi anlatmaz.
3. **Arayüze yalnızca maç sonucu (1X2) çıkar.** 2.5 alt/üst, Asya handikap ve maç
   istatistikleri arşivde analiz için kalır; `test_api_stats.py` bunu denetler —
   `test_api_backtest.py` aynı kuralı geri test için de bekçiye bağlar.
4. **Geçmişe uydurulan sayı tek başına dönmez.** `/api/backtest` eşik taramasını
   her zaman hold-out ve uyarı metniyle birlikte verir.

Gövde şeması ve alan alan sözleşme:
[`docs/ARCHITECTURE_NEXT.md`](docs/ARCHITECTURE_NEXT.md).

### 6.3 Sağlık — vaadin hâlâ geçerli olduğunun kanıtı

Sağlık katmanı "sistem ayakta mı?" sorusunu sormaz; onu 200 dönen herhangi bir uç
zaten cevaplar. Sorduğu soru şudur: **ayakta olan şey hâlâ vaat ettiğimiz şey mi?**

Test ile sağlık kontrolü aynı iddiayı farklı zaman ve zeminde sınar. `pytest`
"bu commit doğru mu?" der; `/api/health` "yayınlanmış olan, kurulu gerçek
sürümlerle, şu anda hâlâ doğru mu?" der. Aradaki boşluk teorik değildir: scipy'nin
dağıtımda kurulamaması, numpy'ın majör sürüm atlaması, veri dosyasının dağıtıma
girmemesi ya da yanlış commit'in yayınlanması — hiçbirini test yakalamaz.

Kontrol mantığının **ikinci bir kopyası yoktur**: tek `CHECKS` tanımı üç ayrı
soruya cevap verir. Sağlık, ölçtüğü şeyi de kendi kopyasıyla değil ürünün
kendi yollarıyla koşturur — modlar `spor_toto/engines.py` (aynı kodu
`/api/solve` ve CLI kullanır), ilan edilen envanter `spor_toto/meta.py`,
istatistik/geri test gövdeleri `spor_toto/payloads.py`.

```
CHECKS (tek tanım)
   ├── pytest            → "bu commit doğru mu?"
   ├── CI adımı          → "yayınlanmaya uygun mu?"
   └── GET /api/health   → "yayınlanmış olan hâlâ doğru mu?"
```

```bash
cd backend
python -m spor_toto.health                  # bir kez
python -m spor_toto.health --interval 60
python -m spor_toto.health --list           # kontrol envanteri
python -m spor_toto.health --only olasilik  # tek kategori (veya tek kontrol)
curl http://localhost:8080/health           # liveness: süreç ayakta mı
curl http://localhost:8080/api/health       # readiness: tam rapor (JSON)
curl "http://localhost:8080/api/health?only=cekirdek"
curl "http://localhost:8080/api/health?fresh=1"   # 5 sn'lik önbelleği atla
curl http://localhost:8080/api/health/checks      # envanter, çalıştırmadan
curl http://localhost:8080/api/health/history     # son koşular
curl -X POST http://localhost:8080/api/health/kupon \
     -H 'Content-Type: application/json' \
     -d '{"picks":"1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"}'   # kendi kuponun
```

**`/health` ile `/api/health` ayrı uçlardır.** İlki liveness'tır ve hiçbir
değişmez koşmaz (~2 ms); ikincisi readiness'tır, tam raporu koşar (ısınmış
~520 ms, ilk koşu ~2,1 sn) ve kritik bir değişmez düşerse 503 döner. Aynı
handler'a bağlı olsalardı `/health`e vuran her şey tam raporu ödetirdi ve
`/health`i canlılık sinyali sanan bir probe, zaman aşımına düşünce **sağlıklı**
bir konteyneri öldürebilirdi.

**24 kontrol, 6 kategori.** Kategoriler motorun katmanlarını izler ve yukarıdan
aşağıya doğru ciddiyet azalır — düşen kontrolün adı değil, **hangi katmanın
bozulduğu** okunur. Güncel liste için `--list`:

| Kategori | Kapsam | Düşerse |
|----------|--------|---------|
| `cekirdek` | encoder, fix16 garanti, yetersiz çifte reddi, distance layers, **varyantlar** | **Ana vaat geçersiz.** Yayın durdurulur |
| `motor` | blok motoru, heuristic, **mod envanteri (7 modun hepsi)** | Bir mod güvenilmez; fix16 ayakta olabilir |
| `olasilik` | exact, Monte Carlo, Bayes, **Bayes preset'leri**, Markov | Sayılar yanlış; garanti geçerli olabilir |
| `analiz` | error_freq, **fire senaryoları**, veri seti, oran arşivi, **geri test** | Yorum katmanı bozuk; motor sağlam |
| `ucuca` | **meta sözleşmesi**, **stats/backtest gövdeleri**, pipeline sonuç şekli | Arayüz yanlış okuyor olabilir |
| `ortam` | scipy bayrağı (bilgi amaçlı) | Bir yetenek eksik olabilir |

**Her düşüş 503 değildir.** HTTP durum kodu "beni trafikten çıkar" demektir, "bir
eksiğim var" demek değildir:

| Durum | Koşul | `ok` | HTTP | Anlamı |
|---|---|---|---|---|
| **HEALTHY** | Her şey geçti | `true` | 200 | Vaat geçerli |
| **DEGRADED** | Yalnızca `critical=False` düştü **ya da** bir kontrol süre bütçesini aştı | `true` | **200** | Vaat geçerli; bir yetenek eksik ya da bir şey yavaşladı |
| **UNHEALTHY** | En az bir kritik düştü | `false` | 503 | Vaat sorgulanır |

Bugün tek bir kontrol kritik değildir (`scipy_flag`): scipy yoksa ILP devre dışı
kalır, motorun geri kalanı doğru çalışmaya devam eder. `critical=False` bir
istisnadır ve gerekçe ister; ölçüt tektir — *bu kontrol düşerken kullanıcının
aldığı sonuç hâlâ doğru mu?*

**Kısmi çalıştırma dürüsttür.** `?only=` tek kontrolü veya kategoriyi koşturur;
rapor `summary.kismi` ile kendini işaretler ve sayfa bunu bant olarak gösterir —
kısmi bir yeşil, tam bir yeşil gibi görünemez. Otomatik yenileme her zaman tam
raporu koşar. Bilinmeyen kontrol adı sessizce boş küme değil, **400** döner.

**Yavaşlamak da bir gerilemedir — ama düşüş değildir.** Her kontrolün beklenen
bir süre bandı (`butce_ms`) vardır. Bandı aşan kontrol **düşmez**: değişmez hâlâ
geçerlidir, yalnızca beklenenden pahalıya koşmuştur. Rapor `degraded` işaretlenir,
süre çubuğu ambere döner ve detaya `süre 50 ms > bütçe 10 ms` yazılır. Sürecin
**ilk koşusunda bütçe uygulanmaz**: o rapor numpy/scipy import'unu ve veri
setinin ilk okunmasını da üstlenir (~2,1 sn ↔ ~520 ms), ısınmayı gerileme saymak
her soğuk başlangıçta yanlış alarm üretirdi.

**"Ne zamandan beri kırmızı?"** `GET /api/health/history` süreç ayakta olduğu
sürece son koşuların özetini tutar (varsayılan 200 kayıt): durum, o durumda
geçen koşu sayısı, değişim zamanı, son sağlıklı koşu. Kısmi koşular ve
önbellekten dönen cevaplar seriye girmez — "5/5 geçti" ile "22/22 geçti" aynı
seride yan yana dururken seri, olduğundan çok şey doğrulanmış gibi görünür.

**Alarm opsiyoneldir ve yalnızca DEĞİŞİMİ bildirir.** `HEALTH_ALARM_URL`
tanımlıysa durum değiştiğinde (HEALTHY↔DEGRADED↔UNHEALTHY) arka planda bir POST
gider; tanımlı değilse değişim yalnızca log'a yazılır. Her kırmızı koşuda
bildirim göndermek bildirimleri okunmaz hâle getirirdi — okunmayan alarm,
alarmsızlıktan kötüdür: korunduğunu sanırsın.

**Hangi süreç cevap verdi?** Rapor ve liveness gövdesi `ornek` bloğu taşır
(pid, host, `INSTANCE_ID`/`REPL_ID` etiketi, başlangıç, uptime). Çok örnekli bir
dağıtımda iki ardışık çağrı farklı süreçlere düşebilir; fark, kim olduğu
yazılmadan rastgele görünür. Zaman serisi ve önbellek de süreç başınadır.

**Neyi kanıtlamaz:** kontroller **sabit dört kupon sınıfı** üzerinde koşar
(8 çift/256 nokta, 7 çift + 8 banko/128, 9 çift/512, üçlü içeren/768). HEALTHY,
*senin az önce ürettiğin kuponun* doğrulandığı anlamına gelmez; motorun o kupon
sınıflarında doğru davrandığı anlamına gelir. Kendi kuponun için iki yol var:
her `/api/solve` cevabındaki `guaranteed` / `worst` / `acik` alanları ve
`POST /api/health/kupon` — ikincisi kuponu aynı kombinatoryal zorunluluklardan
geçirir (kaplama garantisi, mesafe muhasebesi, satır/kolon muhasebesi, alt
sınır, olasılık tutarlılığı). Sonucu kayıtlı raporun tablosuna karışmaz ve
düşmesi 503 üretmez: bir kuponun değişmezi servisin sağlık durumu değildir.

Sağlık katmanının ortam değişkenleri — hepsi isteğe bağlıdır ve varsayılanlar
tek başına çalışır:

| Değişken | Varsayılan | Ne yapar |
|---|---|---|
| `HEALTH_TTL_S` | `5` | `/api/health` önbellek ömrü (sn); `?fresh=1` atlar |
| `HEALTH_HISTORY_LIMIT` | `200` | Sunucudaki koşu geçmişi tamponu |
| `HEALTH_ALARM_URL` | — | Tanımlıysa durum **değişiminde** buraya POST atılır |
| `HEALTH_ALARM_TIMEOUT_S` | `5` | Alarm isteğinin zaman aşımı |
| `INSTANCE_ID` | — | Rapordaki örnek etiketi (çok örnekli dağıtım) |

Neden böyle: [`docs/SAGLIK_VIZYONU.md`](docs/SAGLIK_VIZYONU.md) — sayfanın
varlık sebebi, kontrol yazma sözleşmesi ve bilinçli sınırlar oradadır.

Sağlık kırmızıysa yayınlama yapılmaz. Bu, otomatik CD'nin yerini alan kuraldır.

Katmanın vizyonu, kontrol sözleşmesi ve yol haritası:
[`docs/SAGLIK_VIZYONU.md`](docs/SAGLIK_VIZYONU.md).

---

## 7. Mimari

**Python = sadece backend (JSON API). HTML yok. Frontend = sadece Next.js
(TS/TSX).** Bu kesin bir karardır; eski Jinja2 arayüzü depodan tamamen
silinmiştir — yalnızca git geçmişinde durur.

```
Tarayıcı
   │
   ▼
frontend/              ← Next.js :3000, tek UI (Formül / İstatistik / Sağlık)
   │  /api/* rewrite
   ▼
backend/web_app.py     ← Flask :8080, sadece JSON
   │
   ▼
backend/spor_toto/     ← Fix-16, ILP, Bayes, MC, Markov, history, odds, health
```

```
backend/
  spor_toto/
    core.py            Encoder, Fix-16, ILP, heuristic, exact olasılık
    analysis.py        Monte Carlo, maç bazlı hata frekansı
    bayes.py           Dirichlet prior → posterior, KL, preset'ler
    markov.py          Seçim hayatta kalma + hata bütçesi zinciri
    fire_scenarios.py  Seçim DIŞI fire analizi (1-fire / 2-fire)
    history.py         Tarihsel 1/0/2, 6 analiz bloğu, veri kalitesi
    odds.py            Oran arşivi okuyucu, 1X2 özeti, kalibrasyon, karar destek blokları
    backtest.py        Eşikli strateji → kaplama → skor; eşik taraması + hold-out
    predict.py         TAHMİN: tahminci sözleşmesi + 3 referans (duzgun/sezon/piyasa)
    evaluate.py        TAHMİN: dışarıda bırakmalı + çapraz ölçüm, eşleştirilmiş bootstrap
    recalibrate.py     TAHMİN: piyasanın yeniden kalibrasyonu (kademe, Newton)
    egitim.py          TAHMİN: eğitim korpusu okuyucu — /istatistik'e GİRMEZ
    health.py          Kategorili değişmez (invariant) kontrolleri — tek CHECKS tanımı
    meta.py            Yetenek envanteri (modlar, preset'ler, sınırlar) = /api/meta
    engines.py         Mod çalıştırıcıları — /api/solve, CLI ve health AYNI yolu kullanır
    ortak.py           Paylaşılan hesaplar: normalizasyon, Wilson, Brier, bantlama
    payloads.py        /api/stats ve /api/backtest gövdeleri — tek kaynak
    tahmin.py          TAHMİN: yaklaşan maçlar + ölçülmüş isabet = /api/tahmin
    pazar.py           1X2 DIŞI: alt/üst 2,5 + Asya handikabı = /api/pazar
    benzer.py          "Bu oranda geçmişte ne oldu" = /api/benzer
    kalibrasyon.py     ÖLÇÜM: izotonik düzeltme piyasayı geçiyor mu
    cizgi.py           ÖLÇÜM: açılış→kapanış çizgi hareketi (A1)
    bahisci.py         ÖLÇÜM: bahisçiler arası ayrışma (A2)
    disari.py          ÖLÇÜM: piyasanın fiyatlamadığı bir şey kalıyor mu (A3)
    health_history.py  Sunucu tarafı sağlık geçmişi + durum değişimi bildirimi
    report.py          Konsol / dosya çıktısı
    cli.py             spor-toto komut satırı
  web_app.py           Flask — yalnızca JSON API, HTML servis etmez
  scripts/             (paket: `scripts/__init__.py` — kardeş betikler normal
                        import ile çağrılır)
    build_history.py   Tarihsel veri setini kaynağından üretir
    build_odds.py      Kupon maçlarına piyasa oranlarını eşleştirir
    build_egitim.py    Eğitim korpusu (football-data, 22 lig × 4 geçmiş sezon)
    build_fixtures.py  Yaklaşan maç fikstürü (tahmin katmanının ölçülen kaynağı)
    snapshot_iddaa.py  İddaa açık bültenini tarih damgalı arşivler (haftalık)
    super_toto_hafta.py       Canlı sezon: hafta profili + kupon kurulumu
    super_toto_degerlendir.py Sonuç girildikten sonra değerlendirme
    super_toto_sezon.py       Kümülatif sezon defteri
    super_toto_sayfa.py       Haftayı tek dosyalık HTML'e basar
    super_toto_frontend.py    Arayüzün okuduğu sezon beslemesi (--kontrol: CI kapısı)
    faz_b.py                  Havuz ekseni güç analizi
    acilis_kapanis.py         Açılış–kapanış oranı karşılaştırması
    api_sozlesme.py           API sözleşmesini üretir/denetler (--kontrol: CI kapısı)
  data/                st_history_2025_26.json · odds/ · iddaa/ · egitim/ ·
                       fixtures/ · super_toto/
  tests/               pytest (43 dosya → 1.340 test; §9'da katman dökümü)
  pyproject.toml

frontend/              Next.js App Router — yalnızca TSX, hiç HTML dosyası yok
  app/                 7 sayfa (/, /tahmin, /super-toto, /istatistik,
                       /istatistik/[week], /istatistik/geri-test, /saglik)
  components/
    shell/             kalıcı kenar çubuğu + sayfa geçişleri + tema
    formul/            maç ızgarası, olasılık girişi, sonuç panelleri
    istatistik/        grafikler (bağımlılıksız inline SVG), hafta tablosu, filtre,
                       geri test bileşenleri
    saglik/            durum kartı, kategori kartları, çalışma geçmişi, kontrol envanteri
    tahmin/            olasılık çubuğu, ölçülmüş isabet kartı
    benzer/            "bu oranda geçmişte ne oldu" kartı + lig kırılımı
    super-toto/        canlı sezon hafta sekmeleri
    ui/                temel bileşenler (elle yazıldı, Radix yok)
  lib/types.ts         API sözleşmesinin tamamı tipli
  lib/api.ts           tipli, AbortController ile iptal edilebilir istemci
  lib/transfer.ts      hafta → formül devri (idempotent; bkz. §7.2 kural 6)
  lib/kurulum.ts       formül kurulumunun kalıcılığı + paylaşılabilir bağlantı
  lib/kume-ici.ts      üretmeden önce görülen koşul + küre-kaplama alt sınırı
  lib/senaryo.ts       çalıştırılan modların karşılaştırma listesi
  lib/istek.ts         tek veri çekme kancası (AbortController + hata + yükleniyor)
  lib/adres.ts         adres çubuğu sorgu parametreleri — tek mekanizma
  lib/super-toto.ts    canlı sezon beslemesi okuyucu
  lib/super-toto-veri.json  ÜRETİLMİŞ besleme (super_toto_frontend.py)
  lib/api-sozlesme.json     ÜRETİLMİŞ API sözleşmesi (api_sozlesme.py)
  scripts/             check.mjs (saf mantık + sözleşme denetimi, bağımlılıksız)

scripts/               setup.sh (bağımlılıklar) · run_next_dev.sh (API + UI birlikte)
                       build.sh + run_prod.sh (Replit dağıtımı)
                       check.sh (TEK kalite kapısı — CI de bunu çağırır)
docs/                  Mimari, veri ve yol haritası belgeleri
```

### 7.1 Katman bağımsızlığı

1. **Kombinatoryal** — kolon üretimi, Hamming mesafesi, 14-garanti
2. **Olasılıksal** — exact, MC, Bayes, Markov (garantiyi bozmaz)
3. **Veri** — tarihsel sonuçlar, oran arşivi, veri kalitesi
4. **Gözlem** — health, UI, CLI

Sağlık katmanı bu şemada bir istisnadır: **hepsini birden ölçer**, ama hiçbirine
bağımlı değildir — kontrol tanımları tek yerdedir (`CHECKS`) ve motorun kendi
fonksiyonlarını çağırır, ikinci bir doğruluk kopyası tutmaz.

Alt katman üsttekini bilmez. `core.py` olasılığı, olasılık katmanı veriyi, veri
katmanı arayüzü bilmez.

### 7.2 Arayüze gömülü ürün kuralları

1. **Semboller daima kupon düzeninde (1, 0, 2).** Alfabetik sıralama `01` üretir ve
   kuponu elle doldururken hata yaptırır.
2. **Satır ≠ kolon.** Kolon bedeli hiçbir yerde satır sayısından ayrı gösterilmez.
3. **Renk kimliği takip eder, sıralamayı değil.** Seriler `--sym-1/0/2`
   token'larından gelir; dosyalarda sabit hex yoktur, koyu tema bu yüzden bedava
   çalışır.
4. **Her görselin tablo karşılığı vardır.** Hiçbir değer yalnızca renge ya da fare
   ipucuna bırakılmaz.
5. **Tek filtre satırı.** Kart içine filtre konmaz; aralık seçimi `?last=N` ile
   API'ye gider ve adres çubuğuna yazılır. *Strateji* parametresi (geri testteki
   eşikler) bundan ayrıdır: veri aralığı değil, ölçülen şeyin tanımıdır.
6. **Sayfalar arası devir idempotenttir.** App Router istemci geçişinde hedef sayfa
   iki kez bağlanabilir; "oku ve sil" biçimindeki bir devir sessizce kaybolur.
   Devredilen paket tüketilmez, işaret URL'de durur ve her bağlanma aynı değerleri
   yazar (`lib/transfer.ts`).
7. **Geçmişe uydurulan sayı yalnız gösterilmez.** Eşik taraması hold-out ve uyarı
   metniyle birlikte durur; ikisi ayrılamaz.
8. **Geri yüklenen kurulumda bozuk alan sessizce yutulmaz.** Formül kurulumu yerel
   depoya kendiliğinden yazılır, bağlantıya ise yalnızca istenince (`lib/kurulum.ts`).
   Okunamayan her alan varsayılana düşer *ve* arayüzde adıyla söylenir. Okunamayan
   olasılık girişi **kapalı** açılır: açık bırakıp seçimlerden tekdüze değer üretmek,
   kullanıcının girmediği bir tahmini Bayes'e ve Monte Carlo'ya beslemek olurdu.
9. **Anlamı olmayan sayı basılmaz, sebebi yazılır.** Küme-içi koşulu varsayılan
   olasılık satırlarıyla tanım gereği %100 çıkar; kart o sayıyı göstermek yerine
   neden çıktığını söyler (`lib/kume-ici.ts`). Aynı kural bedelde de geçerlidir:
   motorun arama sonunda bileceği kolon sayısı tek sayı gibi sunulmaz, aralık
   verilir.
10. **Ekrandaki sonuç girdiyi anlatmıyorsa bunu söyler.** Girdi değişince sonuç
    silinmez — eski sonuç hâlâ okunabilir bilgidir — ama "eski hâline ait" diye
    işaretlenir.
11. **Kıyas ancak aynı şey üzerindeyse yapılır.** Çalıştırılan modlar yan yana
    listelenir, ama farklı maç seçimiyle koşulmuş satırlar soluklaştırılıp
    işaretlenir — aradaki bedel farkı moddan değil seçimden geliyor olabilir.
    Garanti vermeyen bir çalışma "en ucuz" sayılmaz: `maxcov` daha ucuz
    görünür ama farklı bir şey satın alır (`lib/senaryo.ts`).
12. **Sekmeler soruya göre bölünür, motor bloğuna göre değil.** Formül sonucu
    dört soruya ayrılır (ne aldım / ne yazacağım / ne kadar riskli / zayıf
    halkalar); backend modüllerinin birebir yansıması olan dokuz sekme, tek bir
    sorunun cevabını üçe dörde dağıtıyordu. Aynı büyüklük iki yerde
    gösterilmez: Markov'un maç bazlı `p_stay` tablosu, girdi tarafındaki
    küme-içi kütleleriyle birebir aynı olduğu için kaldırıldı.

---

## 8. Veri üretimi ve yeniden üretim

```bash
cd backend

python scripts/build_history.py              # tarihsel seti üret
python scripts/build_history.py --dry-run    # yazmadan farkı gör
python scripts/build_history.py --cache /tmp/p   # payload'ları sakla/oradan oku

python scripts/build_odds.py                 # oranları çek ve eşleştir
python scripts/build_odds.py --dry-run       # yalnızca kapsama raporu
python scripts/build_odds.py --no-sqlite     # yalnızca CSV + rapor

python scripts/snapshot_iddaa.py             # iddaa bülteninin anlık görüntüsü
python scripts/snapshot_iddaa.py --dry-run   # yazmadan özet
```

Üç script de doğrulamadan dosya yazmaz. Ham indirmeler ve SQLite kopyaları git
dışıdır, bu komutlarla yeniden oluşur.

**Tek istisna — ve önemli:** iddaa snapshot'ı yeniden üretilemez. Diğer ikisi
kaynağından her an tekrar çekilebilir; kapanmış bir bülten çekilemez. `data/iddaa/`
altındaki tarih damgalı CSV'ler bu yüzden **arşivin kendisidir**; silmek geri
alınamaz. Haftalık tetik: `.github/workflows/snapshot-iddaa.yml` (zamanlanmış işler
yalnızca varsayılan daldan çalışır).

**Okuma tarafı:**

```python
from spor_toto.history import history_summary, history_week_detail
from spor_toto.odds import load_odds, market_odds, implied_probs
from spor_toto.backtest import backtest

history_summary(last=12)                      # son 12 hafta dilimi
implied_probs(market_odds(load_odds()[0], "1X2", "Avg"))   # {"1": .., "0": .., "2": ..}
backtest(sweep=False)["season"]               # 41 haftalık geri test, ~1,2 sn
```

**Oran arşivini sorgulamak** (SQLite, uzun biçim):

```sql
SELECT m.week, m.no, m.home, m.away, o.secim, o.deger
FROM oran o JOIN mac m USING (week, no)
WHERE o.pazar = '1X2' AND o.donem = 'kapanis' AND o.kaynak = 'Avg';
```

İddaa arşivi de **aynı uzun biçimdedir**, böylece iki kaynak yan yana sorgulanır
(`data/iddaa/iddaa.sqlite3`); tek fark anahtarın `alinma` zaman damgasını
içermesidir — aynı maç farklı snapshot'larda ayrı satırdır:

```sql
SELECT m.alinma, m.home, m.away, o.secim, o.deger
FROM oran o JOIN mac m USING (alinma, event_id)
WHERE o.pazar = '1X2' AND o.donem = 'kupon';
```

---

## 9. Testler ve CI

```bash
bash scripts/check.sh        # TEK kapı: iki tarafı da koşturur (repo kökünden)
bash scripts/check.sh --hizli # yavaş ILP testlerini atlar

cd backend
pytest                       # tamamı (ILP dahil)
pytest -m "not slow"         # hızlı süit
pytest -q tests/test_backtest.py                     # strateji, skorlama, hold-out
pytest -n0 tests/test_backtest.py                    # tek çekirdek (hata ayıklarken)
```

Süit **paralel** koşar: `pyproject.toml` `addopts`'a `-n auto` koyar
(pytest-xdist) ve süitin ağırlığı korpus üzerinde dönen bağımsız modüllerde
olduğu için tek süreçte çekirdeklerin çoğu boş duruyordu. Tek bir dosyayı
koşarken sabit bir açılış maliyeti getirir; hata ayıklarken `-n0` onu kapatır
ve çıktı sırası da o zaman düzelir.

`scripts/check.sh` sırasıyla: ruff → mypy → pytest (hızlı + yavaş) → health →
CLI dumanı → Süper Toto boru hattı → üretilmiş iki dosyanın tazeliği →
eslint + tsc + arayüz denetimleri → üretim derlemesi.

**CI bu betiği ÇAĞIRIR, adımları yeniden yazmaz.** Önceden
`backend/scripts/check.sh` vardı ve "CI ile aynı çekirdek adımlar" diyordu ama
altı adımdan üçünü koşuyordu — yani "OK" demesi "CI geçer" demek değildi.
Şimdi ikisi tanım gereği ayrışamaz.

Kapsam: girdi doğrulama, geometri, motorlar, fuzz invariant'lar, CLI (Bayes preset
dahil), analysis, bayes, markov, fire, health, health API, history, odds, geri test,
iddaa snapshot'ı, API sözleşmesi, tahminci sözleşmesi, değerlendirme koşumu,
yeniden kalibrasyon ve eğitim korpusu. **43 test dosyası, parametrizasyonla
1.340 test.** Katman katman dökümü (dosyalar adıyla sayılıdır ki bu tablo
elle bakımı gerektirmesin — `tests/test_belgeler.py` onu gerçek koleksiyona
karşı denetler):

| Katman | Dosyalar | Test |
|---|---|---|
| Çekirdek + motorlar | `core` `engines` `invariants` `edge_cases` `cli` `analysis` `bayes` `markov` `fire_scenarios` | 511 |
| Tahmin katmanı | `predict` `evaluate` `recalibrate` `egitim` `cizgi` `bahisci` `disari` `kalibrasyon` `tahmin` `benzer` `elo` `dixon_coles` `takim` `arama` `agac` `yigin` | 462 |
| Sağlık | `health` `api_health` `meta` `health_history` | 85 |
| Veri / istatistik / geri test | `history` `odds` `backtest` `api_stats` `api_backtest` `snapshot_iddaa` `pazar` | 113 |
| Süper Toto | `super_toto` | 54 |
| Karar katmanı | `secim` | 21 |
| Skor türetme | `skor` | 21 |
| Beraberlik düzeltmesi | `beraberlik` | 19 |
| İddaa hazırlığı | `iddaa_hazirlik` | 24 |
| Ortak gövde | `ortak` | 25 |
| Belgeler | `belgeler` | 3 |

İki test bilerek **ağa çıkmaz**: `test_snapshot_iddaa.py` gerçek bültenden alınmış
küçük bir örnek payload üzerinde koşar — ağ çağrısını sınamak bu paketin işi değil,
ayrıştırmanın doğruluğu ise arşivin tamamının dayandığı şey.

**Arayüz kontrolleri:**

```bash
cd frontend
npm run check                # eslint + tsc + saf mantık ve sözleşme (49 vaka)
npm run lint                 # yalnızca eslint
npm run build                # üretim derlemesi
```

`frontend/scripts/check.mjs` tarayıcı gerektirmeyen her şeyi denetler: kurulum
kodlaması (kalıcılık + paylaşılabilir bağlantı), küme-içi hesabı ve senaryo
karşılaştırması. **Bağımlılık eklemez** — `tsc` zaten devDependency olduğu için
modülleri geçici bir dizine çevirir, dosya düz `node` ile koşar.

Bu denetimin sebebi ölçülmüş bir olaydır: kurulum kodlaması sabit genişliklidir
ve taşan tek bir alan, ondan sonraki *bütün* maçları kaydırıp hiçbir yerde
patlamadan **sessizce başka bir kupon** üretir. İlk sürüm tam bunu yaptı (binde
birlik olasılık `1000` olabilir, yani dört basamak; `padStart(3)` alanı
taşırıyordu). Aynı sınıfta olan iki hesap daha aynı dosyada bekçiye bağlıdır:
küme-içi koşulunun backend'in `exact` değeriyle, küre-kaplama alt sınırının
sunucunun `alt_sinir`'iyle birebir tutması.

Bu sayılar artık **elle yazılmıyor**: `backend/scripts/api_sozlesme.py` onları
üretip `frontend/lib/api-sozlesme.json`e koyuyor ve `check.mjs` oradan okuyor.
Aynı dosya on üç ucun gövde **şeklini** de taşır; `check.mjs` TypeScript
derleyici API'siyle `lib/types.ts` arayüzlerini okuyup karşılaştırır — sunucunun
gönderdiği her alan tipte olmalı, tipte zorunlu diyen her alan sunucudan
gelmeli. Bu boşluk gerçekti: bir alan adı değiştiğinde motor sapasağlam kalır,
bütün testler geçer ve sayfa sessizce boş döner.

**CI (GitHub Actions)** — her `main` push ve PR'da:

| İş | Adım | Sürüm | Açıklama |
|----|------|-------|----------|
| `matris` | `pytest -m "not slow"` | Python 3.10 · 3.11 · 3.12 · 3.13 | Hızlı süit, her sürümde |
| `matris` | `python -m spor_toto.health` | Python 3.10 · 3.11 · 3.12 · 3.13 | HEALTHY zorunlu, **her sürümde** |
| `kapi` | `bash scripts/check.sh` | Python 3.10 + Node 22 | Yerelde koşulan komutun aynısı |

İkisinin ayrımı bilinçli. **`matris` taşınabilirliği** ölçer: bir sürüme özgü
kırılma erken görünsün. Değişmezler de her sürümde koşar — önce yalnızca
3.12'deydi, oysa `.replit` çalışma ortamı python-3.10 kullanıyor, yani ürünün
gerçekten koştuğu sürüm değişmezlerin hiç denenmediği sürümdü.

**`kapi` ise adımları yeniden yazmaz, `scripts/check.sh`i çağırır** — bir satır.
Önce öyle değildi ve ikisi ayrışmıştı: yerel betik CI'nın altı adımından üçünü
koşuyordu, yani "OK" demesi "CI geçer" demek değildi. Tek satır olması tam bu
yüzden: ayrışabilecekleri bir yer kalmasın. `check.sh`in adımları bu bölümün
başında sayılıdır.

Workflow: `.github/workflows/tests.yml`. Arayüzün uzun süre **hiçbir** otomatik
kapısı yoktu; yukarıdaki kodlama hatası bu yüzden sessizce geçebilirdi.

**İkinci workflow — veri toplama.** `.github/workflows/snapshot-iddaa.yml` haftada
bir (pazartesi 06:00 UTC) iddaa bültenini arşivler ve yeni veri varsa depoya işler.
Botun yazma alanı dardır: yalnızca `backend/data/iddaa/`, değişiklik yoksa commit
yok, testler push'tan önce koşar, eşzamanlı çalışma engellenir. Durdurmak: Actions →
"Disable workflow".

CD (otomatik deploy) yoktur: yayın manuel kalır — **health kırmızıysa
yayınlanmaz.**

---

## 10. Yol haritası

İstatistik katmanının **F1–F5 fazlarının tamamı uygulandı** (geri test, karar destek
kartları, formüle devir, kullanım cilası, iddaa arşivi). Ne yapıldığı, neden öyle
yapıldığı ve ölçülen sayılar:
[`docs/ISTATISTIK_YOL_HARITASI.md`](docs/ISTATISTIK_YOL_HARITASI.md) §3.5–3.9.

Amaç tahmine döndükten sonra **tahmin katmanının T1–T3'ü uygulandı**: tahminci
sözleşmesi + değerlendirme koşumu, piyasanın yeniden kalibrasyonu ve eğitim
korpusu. Ölçülen sayılar ve gerekçeler:
[`docs/ISTATISTIK_YOL_HARITASI.md`](docs/ISTATISTIK_YOL_HARITASI.md) §3.10–3.12
ve §5.1. Kural değişmedi — **ölçülmemiş tahminci arayüze çıkmaz** — ama
"hiçbir şey çıkmadı" artık doğru değil: `/tahmin` sayfası ve `/api/tahmin`
yayında. Çıkabilmesinin sebebi kuralın gevşetilmesi değil, kuralın
karşılanması: gövde `tahminler` ve `olculmus_isabet` bloklarını **ayrılmaz**
biçimde taşır, yani ölçülmüş isabeti olmayan bir olasılık dışarı çıkamaz.

> **Projenin tamamını kapsayan ve sonlanan plan:**
> [`docs/ISTATISTIK_YOL_HARITASI.md`](docs/ISTATISTIK_YOL_HARITASI.md) §6. Hedefi üç
> çarpımsal eksene ayırır (tahmin · havuz · kaplama), her eksene bir **durma kuralı** koyar
> ve projenin ne zaman biteceğini tanımlar. Aşağıdaki tablo onun özetidir.

Sıradakiler, "en çok belirsizliği kaldıran" ölçütüne göre:

| # | Ne | Neden / veri durumu |
|---|-----|---|
| **T4 — Referans skorları sağlık değişmezine** | `duzgun` her zaman 0,6667 (sabit: `ortak.BRIER_ESIT`); `piyasa` kupon kesitinde bugün 0,5856 (41 hafta, 615 maç) | **Küçük ve sıranın başında.** Bu sayılar kayarsa bozulan model değil veri/boru hattıdır ve bugün hiçbir şey fark etmez. Ama ikisi aynı cinsten değil: `duzgun` bir sabittir, `piyasa` veri büyüdükçe kayar (0,5747 → 0,5740 arındırma çevriminde, → 0,5856 kupon seti 36→41 haftaya çıkınca). Yani T4 `piyasa`yı sabit bir sayıya değil, **`duzgun`un altında kalmasına** bağlamalıdır |
| **T5 — Piyasa dışı girdi: takım formu** | football-data'nın maç istatistiklerinden yuvarlanan pencereyle form özelliği | **Ölçüm bunu söylüyor.** Piyasayı yeniden kalibre etmek yön olarak doğru ama miktar yetersiz; sinyal ancak piyasada olmayan bir girdiden gelir. Ek kaynak gerekmez |
| **S1 — Örneklem büyütme** | Kupon setini ikinci sezona çıkarmak | **Yarısı yapıldı, yarısı kapalı.** Tahmin ölçümü için gereken örneklem korpusla geldi (31.103 maç). Kupon ayağı bloke: sonuç kaynağı sezon parametresi taşımıyor + `robots.txt` kısıtı ([`docs/VERI_TOPLAMA_VE_ISLEME.md`](docs/VERI_TOPLAMA_VE_ISLEME.md) §10.2) |
| **İkramiye / havuz verisi** | Hafta başına kazanan adedi ve ödenen tutar | **Fizibilite kapandı, ölçüm açık.** Kaynak bulundu (Spor Toto resmî ikramiye ekranı) ve ilk iki hafta elle girildi. Müşterek bahiste "kazanma oranı" ile "beklenen getiri" hâlâ farklı şeylerdir ve ikincisi **hâlâ ölçülmedi** — n = 2 hafta. Ayrıntı: [`docs/ISTATISTIK_YOL_HARITASI.md`](docs/ISTATISTIK_YOL_HARITASI.md) §6.3 |
| **S2 — Geri testi zenginleştirmek** | Sabit kolon bütçesi kipi, ikinci strateji ailesi ("en belirsiz k maçı çifte yap"), bütçe danışmanıyla bağ | **Hazır** — ek veri gerekmez |
| **S3 — İddaa arşivi olgunlaşınca** | Snapshot'ları kupon maçlarıyla eşleştir; iddaa ile piyasa oranını yan yana koy; geri testi vekil değil gerçek fiyatla tekrarla | **Birikmeyi bekliyor** — ~10 snapshot sonra anlamlı |
| **S4 — Küçük işler** | Geri testte eşik çiftini URL'e yazmak, tarama tablosunu CSV'ye çıkarmak, hafta detayında Brier | Veri tarafı yok |

### 10.1 Formül sayfası

Sayfanın kendisi uzun süre yol haritası dışındaydı; ölçülünce en somut borcun
orada olduğu çıktı. **F0–F6 uygulandı** — ne yapıldığı, neden öyle yapıldığı ve
ölçülen sayılar: [`docs/FORMUL_GELISTIRME_RAPORU.md`](docs/FORMUL_GELISTIRME_RAPORU.md).

Sıradakiler ve gerekçeleri:
[`docs/FORMUL_YOL_HARITASI.md`](docs/FORMUL_YOL_HARITASI.md).

| # | Ne | Neden |
|---|-----|---|
| **K1 — Kupon doldurma görünümü** | 16–32 satırı fiziksel kupona geçirirken okunacak, yazdırılabilir görünüm | Sayfanın asıl işi burada bitiyor ama son adım desteklenmiyor |
| **K2 — Fire'ı karara bağlamak** | "Bu maç dışarı çıkarsa ne kaybederim" sayısını maç ızgarasına taşımak | Fire ölçülüyor ama karardan uzakta duruyor |
| **K3 — Bütçe danışmanını girdi tarafına almak** | Plan listesi sonuçta; oysa kısılacak maç kararı girdide veriliyor | Karar ile bilginin yeri ayrı |
| **K4 — Varyant gezgini** | Aynı garantiyi veren farklı 16 satırı kıyaslamak | `variant` bugün kör bir sayı |

### 10.2 Sağlık katmanı

Sıra, "en çok belirsizliği kaldıran" ölçütüne göredir. Ayrıntı:
[`docs/SAGLIK_VIZYONU.md`](docs/SAGLIK_VIZYONU.md) §10.

| # | Adım | Çözdüğü sorun |
|---|---|---|
| 1 | **Süre eşikleri** — kontrol başına beklenen bant; aşınca `degraded` | Performans gerilemesi bugün yalnızca gözle görülüyor |
| 2 | **Zaman serisi** — son N koşunun sunucuda saklanması | Geçmiş oturumla sınırlı, sekme kapanınca kayboluyor |
| 3 | **Kullanıcı kuponuyla koşma** | Sabit örnek kupon sınırı |
| 4 | **Örnek çeşitliliği** — sabit tohumlu birkaç kupon sınıfı | Tek kupon sınıfı; determinizm korunarak |
| 5 | **Alarm bağlantısı** | "Birinin bakıyor olması" varsayımı |
| 6 | **Örnek kimliği** | Çok örnekli dağıtımda "hangi örnek?" |

### 10.3 Bilinçli olarak yapılmayacaklar

| Fikir | Neden hayır |
|---|---|
| Takım bazlı istatistik | 216 takım, Süper Lig takımları bile 32 maç. Çıkacak sayı güvenilir *görünür* ama gürültüdür |
| Ölçülmemiş bir tahmincinin arayüze çıkması | Amaç tahmin olsa da isabeti hold-out ile ölçülmemiş hiçbir tahminci sayfaya çıkmaz |
| Diğer pazarların arayüze çıkması | Ürün kararı: 1X2 dışındakiler analiz içindir, arşivde kalır |
| Maçkolik'ten veri çekme | `robots.txt` otomatik erişimi kapatıyor; politika sınırı ihlal edilmez |
| Kontrolleri arayüzden düzenlemek | Değişmezler koddadır, yapılandırmada değil |
| Sağlık geçmişini metrik panosuna çevirmek | Bu bir APM işidir; sayfa motorun sağlığını ölçer, sürecin değil |
| Tahmin isabetini **sağlık sayfasında** ölçmek | İsabet istatistik katmanının işidir (geri test, hold-out); sağlık katmanı vaadin canlıda geçerliliğini ölçer, modelin kalitesini değil |

---

## 11. Riskler ve sınırlar

**Matematik.** 8 çifte 16 kolona sığmaz. `maxcov` garanti vermez. Garanti yalnızca
seçim kümesi içinde geçerlidir.

**Küçük örneklem.** 41 hafta, tek sezon. Geri testte aşırı uyum ölçüldü ve
büyüklüğü belli: 28 eşikli taramanın en iyisi 4 hafta, aynı yöntemin hold-out'u
0 hafta. Sonuçlar güven aralığıyla verilir ve "bu geçmişin en iyisidir, geleceğin
garantisi değildir" uyarısı sayfada görünür durumdadır — **kaldırılmamalıdır.** Bu
riski gerçekten küçültecek tek şey daha çok hafta (§10, S1), daha iyi bir eşik
değil.

**Geri test bir davranışı değil, bir kuralın bedelini ölçer.** Strateji oranlardan
mekanik üretilir: sakatlık, motivasyon, kadro gibi hiçbir dış bilgi yoktur. Ayrıca
gerçek bir oyuncunun hafta başına 1.987 kolonluk kupon oynamayacağı açıktır.

**Piyasa oranı ≠ iddaa oranı.** Seviye tutmaz, yapı tutar. Bu not sayfada her yerde
görünür durumdadır ve kaldırılmamalıdır.

**Milli maç haftaları.** 5., 10. ve 15. haftalarda oran yok; oran blokları o
haftalarda boş gelir ve kapsama hiçbir zaman %100 olmaz.

**Üçüncü parti kaynak.** Üç kaynak da dıştır. İlk ikisi silinir ya da biçim
değiştirirse yeniden çekim gerekir; üretim scriptleri tam olarak bunun için var.
Üçüncüsünde (iddaa bülteni) bu kurtarma yolu **yoktur**: kaçırılan hafta
kaçmıştır.

**Resmi bülten numarası doğrulanmadı.** Kupon sırası kaynağın sırasıdır; 51. hafta
bağımsız kaynakla çapraz doğrulanmıştır.

**Sağlık sabit kupon sınıfları üzerinde koşar.** HEALTHY, senin kuponunun
değil, motorun o dört sınıftaki davranışının doğrulandığı anlamına gelir.
Rastgele kupon determinizmi bozardı; geniş girdi taraması `pytest`'teki fuzz
testlerinin işidir. Kendi kuponun için ayrı bir uç var:
`POST /api/health/kupon`.

**Sağlık tek süreci anlatır.** Rapor, çağrıyı karşılayan süreci anlatır ve
bunu artık açıkça yazar (`ornek`: pid, host, etiket). Zaman serisi ve önbellek
de süreç başınadır: gunicorn iki worker ile koşarken her worker kendi tamponunu
tutar. İlk koşu (~2,1 sn) sonrakilerden (~520 ms) yavaştır; bu ısınmadır,
gerileme değil ve süre bütçeleri o koşuda uygulanmaz.

**Alarm varsayılan olarak kapalıdır.** `HEALTH_ALARM_URL` tanımlanmadıkça
kırmızıya dönüş yalnızca log'a ve sekme başlığına yansır; birinin bakıyor
olması gerekir. Tanımlıysa yalnızca **durum değişiminde** bildirim gider.

---

## 12. Sözlük

| Terim | Anlamı |
|---|---|
| **Banko** | Bir maça tek sembol işaretlemek |
| **Çifte / üçlü** | Bir maça iki / üç sembol işaretlemek; kolon bedelini çarpar |
| **Küme içi** | Gerçek sonucun, işaretlenen sembollerin içinde kalması |
| **14-garanti** | Tahmin küme içindeyse en fazla 1 hatayla en az 14 doğruyu garanti eden kaplama |
| **Fire** | Seçim kümesinin dışına çıkılan senaryo; garantinin geçerli olmadığı bölge |
| **Değişmez (invariant)** | Kodun her koşusunda doğru kalması gereken matematiksel zorunluluk; sağlık katmanının ölçtüğü şey |
| **DEGRADED** | Yalnızca kritik olmayan bir kontrol düşmüş: vaat geçerli, bir yetenek eksik (200 döner) |
| **Kolon bedeli** | Ödenecek tutar. Satır sayısıyla karıştırılmamalı |
| **Kaplama kodu** | Uzaydaki her noktanın en fazla r uzaklıkta bir kod sözcüğüne sahip olduğu küme |
| **Marj (overround)** | Bahisçi payı; ham olasılık toplamının 1'i aşan kısmı |
| **Kalibrasyon** | Modelin verdiği olasılığın gerçekleşme sıklığıyla örtüşmesi |
| **Favori** | Oranı en düşük sembol |
| **Underdog galibiyeti** | Favorinin karşı tarafının kazanması (beraberlik değil) |
| **Kapanış oranı** | Maç başlarken geçerli son oran; açılıştan daha bilgilidir |
| **Dilim** | `?last=N` ile seçilen son N hafta |
| **Geri test** | Bir stratejiyi geçmiş haftalarda çalıştırıp sonucunu ve bedelini ölçmek |
| **Aşırı uyum** | Geçmişe o kadar iyi uyan bir seçim ki geleceğe taşınmaz |
| **Hold-out** | Eşiği o haftayı görmeden seçip yine o haftada ölçmek; aşırı uyumun ölçüsü |
| **Brier skoru** | Σ(olasılık − gerçekleşme)². 0 kusursuz, 0,667 üç sembole eşit olasılık vermeye denk |
| **Wilson aralığı** | Küçük örneklemde oran için güven aralığı; kenarlarda 0–1 dışına taşmaz |

---

## 13. Belgeler

| Belge | İçerik |
|---|---|
| [`docs/ARCHITECTURE_NEXT.md`](docs/ARCHITECTURE_NEXT.md) | Mimari kararı ve API sözleşmesinin tamamı |
| [`docs/VERI_TOPLAMA_VE_ISLEME.md`](docs/VERI_TOPLAMA_VE_ISLEME.md) | Veri katmanının tek kaynak dokümantasyonu: doktrin, boru hatları, kalite güvencesi, vakalar |
| [`docs/ISTATISTIK_YOL_HARITASI.md`](docs/ISTATISTIK_YOL_HARITASI.md) | Ölçülmüş bulgular ve **baştan sona yol planı** (§6): hedefin üç eksene ayrışması, her eksenin durma kuralı, projenin bitiş tanımı |
| [`docs/SAGLIK_VIZYONU.md`](docs/SAGLIK_VIZYONU.md) | Sağlık katmanının vizyonu: kontrol sözleşmesi, kategori modeli, DEGRADED kararı, bilinçli sınırlar |
| [`docs/SAGLIK_GELISTIRME_RAPORU.md`](docs/SAGLIK_GELISTIRME_RAPORU.md) | Sağlık katmanının çalışma raporu ve ölçümleri |
| [`docs/FORMUL_GELISTIRME_RAPORU.md`](docs/FORMUL_GELISTIRME_RAPORU.md) | Formül sayfasının çalışma raporu: teşhis, F0–F6, bulunan hatalar, ölçümler |
| [`docs/FORMUL_YOL_HARITASI.md`](docs/FORMUL_YOL_HARITASI.md) | Formül sayfasının yol haritası ve yapılmayacaklar listesi |
| [`docs/DIS_INCELEME.md`](docs/DIS_INCELEME.md) | Dış bir makine öğrenmesi çalışmasının bu projeye ne kattığı ve **ne katmadığı** — sayılar o çalışmanın kendi belgelerinden, bizim ölçümümüz değil |
| [`docs/DIS_INCELEME_ALPHAPY.md`](docs/DIS_INCELEME_ALPHAPY.md) | Bir ML **çerçevesinin** (AlphaPy / AlphaPy Pro) incelemesi: çerçeve alınmadı, ama metrik paneline bakarken görülen eksik ölçüldü ve koda girdi — Brier'in Murphy ayrışımı |
| [`backend/README.md`](backend/README.md) | Motor + API kurulumu, ortam değişkenleri, oran arşivi kullanımı |
| [`frontend/README.md`](frontend/README.md) | Arayüz yapısı, tasarım sistemi, grafik kuralları, tip katmanı |
| [`replit.md`](replit.md) | Replit çalışma alanının hafızası: iş akışları, portlar, dağıtım |

Bu tablonun eksiksizliği `tests/test_belgeler.py` ile korunur: `docs/` altına
eklenen bir belge buraya da girmezse test düşer. Boşluk sessiz kalmasın diye —
`docs/DIS_INCELEME.md` tam olarak böyle, listede olmadan aylarca durdu.

---

## 14. Uyarı

Bu aracın amacı kazanma oranını artırmaktır; ancak kazanmayı **garanti etmez** ve
hedefe bugünkü mesafe açıkça ölçülmüştür (§1.1): piyasa oranlarından üretilen
stratejinin **hold-out isabeti 36 haftada 1'dir** (%2,8). Ölçülen bu sayı
iyileşmeden, aracın kazanma oranını artırdığı iddia edilemez.

Olasılık / Monte Carlo / Bayes / Markov çıktıları **beklenen-değer veya kâr hesabı
değildir**; ikramiye havuzu ve kolon bedeli hesaba katılmaz.

İstatistik katmanındaki bulgular tek sezonluk, 41 haftalık bir örneklem üzerinde
ölçülmüştür. Geçmişin tarifi geleceğin garantisi değildir.

**Geri test bir strateji önerisi değildir.** Bir kuralın geçmişteki bedelini ve
isabetini kaydeder; ölçülen sonuç, varsayılan eşiklerle 36 haftanın 3'ünde 14+ ve
hold-out'ta 0'dır. Eşik taramasındaki "en iyi" satır, tanımı gereği bu sezona uyan
satırdır.

**Sorumlu oynayın.**
