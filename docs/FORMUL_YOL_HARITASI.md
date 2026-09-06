# Formül Sayfası — Yol Haritası

Bu belge `/` (Formül) sayfasında **sıradaki işleri** ve her birinin neden o sırada
olduğunu tutar. Bugüne kadar yapılanlar ayrı belgededir:
[`FORMUL_GELISTIRME_RAPORU.md`](FORMUL_GELISTIRME_RAPORU.md).

Boyut etiketleri: `[S]` bir oturum · `[M]` bir gün · `[L]` birden fazla gün.

> **Söküm sonrası gözden geçirildi (2026-09-06).** Bu yol haritası kaplama
> döneminde yazıldı (2026-08-17) ve maddelerinin ikisi o katmanın üzerine
> kuruluydu: **K4** (bütçe danışmanı) ve **K5** (varyant gezgini). Kaplama
> söküldü (`DUZ_SISTEME_GECIS.md`); `core.butce_danismani` ve `variant` diye
> bir şey kalmadı, yani o iki madde **konusuz kaldı** — silinmiyor, yerinde
> işaretleniyor, çünkü sıranın neden o sıra olduğu bilgisi onlarla birlikte
> yazılmıştı. Kalan altı madde (K1, K2, K3, K6, K7, K8) kaplamadan bağımsızdır
> ve **hâlâ geçerlidir**: `fire.by_match` duruyor, canlı kart ile çözümün
> olasılığı hâlâ ayrışıyor, mobil ve dışa aktarım işleri hiç dokunulmadı.
> §2'nin ölçümleri o günün ürününe aittir ve yeniden ölçülmedi.

---

## 1. Bugünkü durum

F0–F6 uygulandı: bedel söyleniyor, seçim kümesinin doğru sonucu içerme koşulu
üretmeden önce canlı görünüyor, sonuç bayatlayınca söyleniyor, sekmeler soruya
göre bölündü, maçların adı var, çalıştırılan kuponlar yan yana kıyaslanıyor,
kurulum kalıcı ve paylaşılabilir.

> Bu paragraf eskiden *"bedel **moda göre** söyleniyor"*, *"**14-garantinin**
> koşulu"* ve *"çalıştırılan **modlar** yan yana kıyaslanıyor"* diyordu. Kıyas
> ekseni artık mod değil **işaretlerdir** (`frontend/lib/senaryo.ts`), ve küme
> içindeyken kazanılan kademe 14 değil **15**.

Sayfanın **motoru eksik değil** — düz kupon üretimi, exact/Monte Carlo/Bayes/
Markov ve fire erişilebilir. Aşağıdaki işlerin hepsi *karar desteği* ve
*kullanım* tarafındadır; hiçbiri yeni motor yeteneği istemiyor.

---

## 2. Ölçülen açıklar

Aşağıdaki sayılar bu depodaki veriyle, bu makinede ölçüldü — **2026-08-17'de,
kaplama ayaktayken.** Yeniden ölçülmediler; son satır (`variant`) sökümle
birlikte konusuz kaldı ve işaretlendi.

| Ne | Ölçüm |
|---|---|
| Bayes açıkken canlı kart ile çözümün kullandığı olasılık ayrışıyor | canlı %0,0149 · çözüm %0,063 → **4,23 kat** |
| Telefonda sayfa uzunluğu (sonuçla birlikte) | **4.637 px** |
| Yapışkan çubuğun kapladığı bant | **92 px**, viewport'un %11'i (390×844) |
| Kuponu elle doldurmak için ekranda | 15 dar sütunlu tablo + TSV kopyala; yazdırma yok |
| ~~`variant` parametresinin arayüzdeki karşılığı~~ | ~~yalnızca bir sayı kutusu; ne değiştirdiği görünmüyor~~ — parametre sökümle kalktı (K5) |
| Fire'ın maç bazlı kırılımı | var (`fire.by_match`) ama maç ızgarasından iki sekme uzakta |

---

## 3. Yol haritası

**Sıra: K1 → K2 → K3 → ~~K4~~ → ~~K5~~ → K6 → K7 → K8.**

K1 önce geliyor çünkü bir *doğruluk* işi: ekranda aynı büyüklüğün iki farklı
değeri duruyor. K2 ikinci çünkü sayfanın asıl işinin bittiği yer orası ve orası
desteklenmiyor. K3–K5 karar desteğini derinleştirir, K6–K8 kullanım ve altyapıdır.

> **K4 ve K5 kaplamanın sökülmesiyle konusuz kaldı** (yukarıdaki künye).
> Sıra numaraları kaydırılmadı: madde adları başka belgelerde ve commit
> mesajlarında anılıyor, yeniden numaralandırmak o atıfları kırardı.
> Bugünkü fiilî sıra **K1 → K2 → K3 → K6 → K7 → K8**.

---

### K1 — Canlı koşul ile çözümün olasılığını hizala `[M]`

**Sorun.** Küme-içi kartı kullanıcının **ham** girdisini kullanır; çözüm ise Bayes
açıkken **posterior**'u kullanır (`web_app.py`: `work_probs = posterior`). Aynı
büyüklük ekranda iki farklı değerle duruyor:

```
canlı kart (ham girdi)                : %0,0149
çözüm (bayes=dengeli, posterior)      : %0,063     → 4,23 kat
```

Kullanıcı için bu, "girdi tarafında gördüğüm sayı üretince neden değişti"
sorusudur ve bugün hiçbir yerde cevabı yok. Sayfanın geri kalanı bu tür
ayrışmaları açıkça yazdığı için (§1.4 kaynak dürüstlüğü) bu bir tutarsızlıktır.

**Ne yapılacak.** İki seçenek var, kararı ölçüm verecek:

1. **Dirichlet güncellemesini istemciye taşı.** Hesap kapalı formda ve küçük:
   posterior ∝ α·prior + n·evidence. Kart Bayes açıkken posterior'u kullanır,
   canlılık korunur. Risk: aynı formülün iki yerde durması — CLI/API ile
   sapmaması gerekir, o yüzden `check.mjs` backend'in `bayes` bloğuyla birebir
   tutmayı bekçiye bağlamalı.
2. **Kartı açıkça etiketle.** "Bu sayı senin ham girdine göredir; Bayes açık
   olduğu için üretilen sonuç posterior'u kullanacak" der ve sonuç geldiğinde
   ikisini yan yana gösterir.

Ölçmeden karar verilmez: (1) daha iyi bir ürün ama çift kaynak riski taşır;
(2) dürüsttür ama kullanıcıyı iki sayıyla baş başa bırakır.

**Kabul kriteri.** Bayes açıkken girdi tarafındaki sayı ile "Ne kadar riskli"
sekmesindeki `exact.p_kume_ici` ya **aynıdır**, ya da aradaki farkın sebebi
ekranda yazıyordur. `check.mjs` bu eşitliği (ya da etiketin varlığını) denetler.

---

### K2 — Kupon doldurma görünümü `[M]`

**Sorun.** Sayfanın asıl işi, üretilen satırların fiziksel kupona
geçirilmesiyle biter. (Burada *"16–32 satır"* yazıyordu — kaplamanın ölçeği.
Düzde satır sayısı `2^çifte · 3^üçlü`dur ve haftalık bütçede yüzlerle
binler arasında gezer, yani bu madde sökümle birlikte **daha da** ağırlaştı.) Bugün bunun için elde olan: 15 dar sütunlu bir tablo ve
TSV kopyalama. Yazdırma stili yok, büyük punto görünümü yok, "hangi satırdayım"
işareti yok. En hataya açık adım en az desteklenen adım.

**Ne yapılacak.**
- **Doldurma modu:** satırlar büyük puntoyla, 4'erli gruplar hâlinde, satır başına
  işaretlenebilir bir kutu (yalnızca görsel ilerleme — kaydedilmez).
- **Yazdırma stili:** `@media print` ile kenar çubuğu, kartlar ve gezinme dışarı;
  yalnızca kupon tablosu, maç adları ve toplam kolon bedeli.
- Maç adları başlıkta; bugün yalnızca fare ipucunda.

**Kabul kriteri.** Yazdırma önizlemesinde okunabilir bir kupon çıkar ve toplam
kolon bedeli üstünde durur. Doldurma modunda satırlar gruplar hâlinde, kaybolmadan
takip edilebilir.

**Neden yeni bir sekme değil.** "Ne yazacağım" sekmesinin içinde bir görünüm
anahtarı olmalı; sekme sayısı soruya göre bölünmüştü, görünüm farkı yeni bir soru
değildir.

---

### K3 — Fire'ı maç ızgarasına bağla `[M]`

**Sorun.** Fire, ürünün en dürüst parçalarından biri (§1.2: "ya yanılırsam?") ve
maç bazlı kırılımı zaten hesaplanıyor (`fire.by_match`). Ama ızgaradan iki sekme
uzakta duruyor; oysa cevapladığı soru — "bu maç dışarı çıkarsa ne kaybederim" —
tam olarak işaret koyarken sorulan soru.

**Ne yapılacak.** Sonuç geldikten sonra her ızgara satırının yanında o maçın fire
etkisi: "dışarı çıkarsa en iyi kolon 13 doğru". Küme-içi kartının kütle çubukları
gibi, ama **seçim dışı** taraf için.

**Kabul kriteri.** Fire hesaplanmadıysa (atlandıysa) ızgara sessizce boş kalmaz,
sebebini söyler. Kapama maçlar fire üretemez; onlarda gösterge çıkmaz.

**Bağımlılık.** Fire pahalıdır ve sınır aşılırsa atlanır. Bu gösterge bir sonuç
gerektirir; girdi tarafında canlı olamaz. Küme-içi kartıyla karıştırılmaması için
görsel dili farklı olmalı.

---

### ~~K4 — Bütçe danışmanını girdi tarafına taşı~~ `[M]` — **KONUSUZ KALDI**

> `core.butce_danismani` kaplamayla birlikte söküldü ve `onPlanSec`
> arayüzden kalktı (`frontend/app/page.tsx`). Düzde bütçeyi motora verip
> plan istemezsin: kısmak için ızgarada işareti değiştirirsin, bedel
> `2^çifte · 3^üçlü` olarak anında görünür. Maddenin *sorun* tespiti —
> "bilgi ile karar ayrı yerlerde duruyor" — böylece kendiliğinden çözüldü.
> Aşağısı o günün kaydıdır.

**Sorun.** `butce` modu "hangi maçı kısmalıyım" planları üretir ve bunlar sonuçta
listelenir. Ama o karar **girdide** verilir: kısılacak maç, ızgarada işareti
kaldırılacak maçtır. Bilgi ile karar ayrı yerlerde duruyor.

**Ne yapılacak.** Plan seçilince önerdiği değişiklikler ızgarada **önizleme**
olarak gösterilir (hangi maçtan hangi sembol düşecek), tek tıkla uygulanır. Bugün
plan yalnızca yeniden çalıştırılıyor; kullanıcı neyin değiştiğini metinden
okuyor.

**Kabul kriteri.** Önizleme uygulanmadan geri alınabilir. Uygulandığında sonuç
bayatlar (F2 zaten bunu söyler).

---

### ~~K5 — Varyant gezgini~~ `[M]` — **KONUSUZ KALDI**

> `variant` Hamming(7,4) bloğunun alternatif 16 satırını seçiyordu; blok
> `spor_toto/kaplama_arsiv.py`ye çekildi ve parametre hem CLI'dan hem
> `/api/solve` gövdesinden kalktı. Düzde seçilecek bir satır kümesi yok —
> kümenin tamamı oynanır, yani "varyant" diye bir eksen kalmadı.
> Aşağısı o günün kaydıdır.

**Sorun.** `variant` bugün kör bir sayı kutusu. Aynı garantiyi veren farklı 16
satır üretir, ama aralarındaki fark hiçbir yerde görünmez — oysa fark gerçektir:
hata frekansı dağılımları ayrışır, bazı varyantlar hatayı maçlara daha eşit
dağıtır.

**Ne yapılacak.** N varyantı arka arkaya çalıştırıp hata frekansı profillerini
kıyaslayan bir görünüm. F6'nın senaryo listesi altyapısı buna hazır: aynı tablo,
mod yerine varyant kırılımıyla.

**Kabul kriteri.** Karşılaştırma yalnızca aynı seçim üzerinde yapılır (F6 kuralı
1 burada da geçerli). Varyantlar arasında bedel/garanti farkı **yoktur** ve bu
yazılır — kullanıcı "daha iyi varyant" arayışına itilmez.

**Risk.** Bu, kolayca bir "en iyi varyantı bul" oyununa dönüşebilir; oysa hepsi
aynı garantiyi aynı bedele verir. Görünüm bunu baştan söylemeli.

---

### K6 — Mobil bilgi mimarisi `[M]`

**Sorun.** Telefonda sayfa 4.637 px. F5'te en can yakan iki kusur giderildi
(yatay taşma, üretimden sonra kaydırma) ama girdi kolonu hâlâ tek uzun şerit:
ızgara, küme-içi, motor, olasılık, motor ayarları alt alta.

**Ne yapılacak.** Aşamalı açma: telefonda "Maçlar / Ayarlar / Olasılık" adımları
ya da katlanır bölümler. Ölçüt sayfa uzunluğu değil, **ilk ekranda kaç başlık
görünüyor** olmalı — istatistik sayfasının G1'inde kullanılan ölçütün aynısı.

**Kabul kriteri.** Yapışkan çubuğun 92 px'i hâlâ hiçbir kontrolü erişilemez
bırakmıyor (mevcut test korunur).

---

### K7 — Uçtan uca testleri repoya al `[M]`

**Sorun.** Bu çalışmada altı Playwright süiti yazıldı ve koşuldu (kalıcılık,
devir, F0–F2, sekme yapısı, maç adları, örtüşme) ama repoya **girmedi**. F5'teki
"hiçbir kontrol erişilemez değil" invariantı gibi bazı iddialar yalnızca gerçek
bir tarayıcıda ölçülebilir; bugün onları koruyan bir bekçi yok.

**Ne yapılacak.** Playwright'ı devDependency olarak ekle, süitleri
`frontend/e2e/` altına al, CI'da ayrı bir iş olarak koştur (arayüz + API birlikte
ayağa kalkmalı).

**Neden bugün yapılmadı.** Bağımlılık eklemek ayrı bir karardır; `check.mjs`
bilerek bağımlılıksız tutuldu. Bu maddenin bedeli CI süresi ve bakım; faydası
tarayıcı gerektiren invariantların korunması.

**Kabul kriteri.** CI'da `frontend-e2e` işi yeşil; en az örtüşme testi ve kurulum
kalıcılığı korunuyor.

---

### K8 — Sonuçların dışa aktarımı `[S]`

Kupon tablosu bugün yalnızca panoya TSV olarak çıkıyor. İstatistik sayfasında CSV
dışa aktarma zaten var; aynı şey burada da olmalı (kupon + kolon bedelleri + maç
adları). Küçük iş, K2'nin yanında yapılabilir.

---

## 4. Masada duran, sırada olmayan

| Fikir | Durum |
|---|---|
| Kurulumu sunucuda saklamak (hesap/oturum) | Ürün bugün kimlik istemiyor; `localStorage` + bağlantı yetiyor |
| Birden fazla kuponu aynı anda yönetmek ("kupon klasörü") | Gerçek bir ihtiyaç ölçülmedi; önce K2 kullanılsın |
| Olasılıkları hafta detayı dışında bir kaynaktan çekmek | Veri katmanı kararı, sayfa kararı değil (`VERI_TOPLAMA_VE_ISLEME.md`) |
| Bütçeyi para birimiyle göstermek | Kolon bedeli birimi kolondur; TL'ye çevirmek ikramiye/kâr çağrışımı yapar |

---

## 5. Yapılmayacaklar

| Fikir | Neden hayır |
|---|---|
| Sayfanın **ölçülmemiş** işaret önermesi ("şu maçı banko yap") | Amaç tahmin olduğu için öneri artık hedeftedir, ama isabeti hold-out ile ölçülmemiş bir öneri sayfaya çıkmaz. Bugün küme-içi kartı çarpanı ve bedeli gösterir; işareti kullanıcı koyar |
| ~~"Önerilen mod" rozeti~~ | **Konusuz kaldı:** seçilecek mod yok, tek yol düz. Kural yine de anlamlıdır ve *işaret* eksenine taşınmıştır — kıyas tablosu sayıları verir, kararı vermez |
| Beklenen değer / kâr hesabı | İkramiye havuzu ve kaç kişinin tuttuğu bilinmiyor; hesaplanabilirmiş gibi göstermek yanıltıcı olur |
| Maç adlarının bağlantıya girmesi | 15 takım adı URL'i üç katına çıkarır; `transfer.ts`'te aynı karar verildi |
| Senaryo listesinin kalıcı olması | Türetilmiş veri kaydedilmez; kalıcı olan tek şey kurulumdur |
| Kupon geçmişini "hangi hafta ne oynadım" arşivine çevirmek | Sonucu tutup tutmadığını kaydetmek, aracı bir tahmin performansı takipçisine dönüştürür — §1.6'da yapmayacakları arasında |

---

## 6. Riskler

| Risk | Etki | Azaltma |
|---|---|---|
| Küme-içi hesabının backend'den sapması | Ekranda iki farklı gerçek | `check.mjs` backend'in `exact` değeriyle birebir tutmayı zaten denetliyor; K1'de Bayes dalı da bağlanacak |
| Karar desteğinin "tavsiye"ye dönüşmesi | Ürünün kurucu iddiası çürür | Her yeni gösterge, ne söylemediğini de yazar (K5 bunu açıkça kabul kriteri yapıyordu; K5 konusuz kaldı, kural kaldı) |
| Yapışkan çubuğun içerik örtmesi | Kontrol kaçırma | Tam çözümü yok; "hiçbir kontrol erişilemez değil" invariantı testle korunuyor |
| Arayüz testlerinin tarayıcısız kalması | Regresyon sessizce geçer | K7 |

---

## 7. Çalıştırma ve doğrulama

```bash
# Arayüz + API birlikte (repo kökünden)
bash scripts/run_next_dev.sh      # UI :3000, API :8080

# Arayüz denetimi
cd frontend
npm run check                     # tip denetimi + 37 saf mantık vakası
npm run build                     # üretim derlemesi
```

`npm run check` tarayıcı gerektirmez ve bağımlılık eklemez. Kapsadığı üç şey:
kurulum kodlaması (kalıcılık + bağlantı), küme-içi hesabı, senaryo
karşılaştırması. Ayrıntı: [`FORMUL_GELISTIRME_RAPORU.md`](FORMUL_GELISTIRME_RAPORU.md) §6.
