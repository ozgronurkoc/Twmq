# Kazanma Planı — sekiz hafta, tek soru

> **Bu belge bir özellik listesi değil, bir ölçüm sırasıdır.** Her fazın
> **önceden yazılmış bir durma kuralı** vardır ve o kuralın *"hayır"* çıkması
> meşru bir bitiştir. `ISTATISTIK_YOL_HARITASI.md` §6'nın doktrini aynen
> geçerlidir: yalnızca başarıyla bitebilen bir plan, plan değil temennidir.
>
> Kapsam kararı (2026-09-04): bu plan **kaplama**, **arayüz/uygulama** ve
> **güvenlik** eksenlerine dokunmaz. Tek hedef, kazanma şansının ölçülerek
> artırılmasıdır.

---

## 1. Neden bu plan bu sırada

Hedef üç çarpanlı bir çarpımdır (`ISTATISTIK_YOL_HARITASI.md` §6.1) ve üç
çarpanın bugünkü durumu birbirinden çok farklıdır:

```
Beklenen getiri  =  P(tutturma)  ×  Pay(tutturunca)  −  Bedel
                    ─────────────    ───────────────     ──────
                    tahmin ekseni    HAVUZ ekseni        kaplama ekseni
                    ölçülü KAPALI    ÖLÇÜLMEDİ           ÇÖZÜLDÜ
```

### 1.1 Tahmin ekseni ölçülerek kapandı

On bir bağımsız denemede hiçbir aile kapanış çizgisini geçemedi (§5.1):
Elo (§3.27), Dixon-Coles (§3.28), H2H ve seriler (§3.29), gradyan artırmalı
ağaçlar (§3.30), yığınlama (§3.32), LOFO + Venn-Abers (§3.33), etkileşim
kademeleri (§3.26), türetilmiş 1X2 (§3.20), beraberlik düzeltmesi (§3.21),
takım formu (T5), xG (§3.42).

Üç ölçüm bunun *niçin* böyle olduğunu da söylüyor:

| Ölçüm | Sonuç |
|---|---|
| **Brier ayrışımı** (§3.23) | Kalibrasyon ekseninin tavanı: piyasanın toplam güvenilirlik borcu **0,00042**. Denenen etkiler bu tavanın **üstünde** — geçmemeleri kapasiteden değil, alınacak yolun kalmamasından |
| **Öğrenme eğrisi** (§3.24) | Eğri düzleşti, gap kapanmadan: son adım **0,00006**. *"Sorun satır sayısı değil sütun"* |
| **LOFO** (§3.33) | **Hiçbir özellik taşımıyor**; onun beşi net negatif |

### 1.2 Ve tahmin gücü artsa bile kazanç orantılı artmıyor

`KADEME_OLASILIKLARI.md` §6 bunu ölçtü ve bu, planın yönünü belirleyen tek
sayıdır:

> **Spearman(gerçek sonucun sırası, 15 bilen sayısı) = −0,843.**

Model favoriye gidiyor; kalabalık da favoriye gidiyor. **Tuttuğunuz hafta
herkesin tuttuğu haftadır.** Kişi başı ikramiye modelin en sevdiği bantta
13.228 TL, en sevmediği bantta 14.734.596 TL — **1.100 kat** fark.

Yani seyreltme, tahmin ekseninde kazanılanın büyük kısmını geri alıyor.
Bu, README §1.1'in *"yön doğru, miktar yetersiz"* teşhisine üçüncü boyutu
ekler: **yön doğru olsa ve miktar yetse bile seyreltme kazancı yiyor.**

### 1.3 Ölçülmemiş varlık — planın çekirdeği

Depoda iki arşiv yan yana duruyor ve **hiç birleştirilmedi**:

| Kaynak | Kapsama |
|---|---|
| `data/sportoto_arsiv/*.json` | **223 hafta** · kademe başına kazanan adedi + kişi başı ikramiye (resmî uç) |
| `data/st_history/*.json` + `data/odds/*.csv` | **112 hafta** · kuponun 15 maçı + piyasa oranı + gerçek sonuç (oran kapsaması %100) |
| **kesişim** | **112 hafta × 4 kademe = 448 gözlem** |

`getiri.KALABALIK_MODELLERI` bugün üç modelden ibaret ve **üçü de varsayımdır**
(`orneklem`, `favori`, `oynanma`). §3.34 ilk ikisi arasında **22 kat** getiri
farkı ölçtü:

> *"Bu eksende belirsizliğin kaynağı tahminci değil, kalabalık."*

O varsayım 448 gözleme **hiç oturtulmadı.**

### 1.4 Bu, "≈71 hafta" duvarını aşıyor

§6.3b Faz B için **≈71 ikramiyeli hafta** hesapladı ve elde 1 hafta olduğunu
yazdı. O güç analizi *kişi başı ikramiye ↔ `crowd_ratio`* regresyonu içindi ve
o regresyon, kişi başı ikramiyenin kazanan sayısına bölünmesinden gelen devasa
oynaklığı taşır.

**Kazanan adetlerinin kendisi çok daha bilgili bir gözlemdir** — kalabalığın
ortak dağılımının doğrudan ölçüsüdür, oranı alındığında haftalık ölçekten
bağımsızdır, ve **geçmişte 223 hafta boyunca zaten durmaktadır.**

§6.3b'nin durma kuralı bu yüzden değişmiyor, **karşılanıyor**: 3. şık *"kaç
hafta gerektiği şimdiden yazılır"* diyordu; bu plan o haftaların çoktan
biriktiğini gösteriyor, yalnızca başka bir kestirimciyle.

### 1.5 Planın tezi

> Piyasayı tahminde yenmeye çalışmayı bırak — on bir kez ölçüldü, olmuyor.
> **Kalabalığı ölç ve ondan kontrollü sap.** Bu, piyasayı geçmeyi gerektirmez
> (`getiri.py` başlığı: sabit oranlıda `edge = p_model − p_piyasa`, müşterekte
> `edge = p_piyasa − oynanma_payı`).

**Bütçe kararı.** Varsayılan bant **1.000–3.000 TL/hafta**; ama her para sonucu
ayrıca **bütçe → getiri eğrisi** olarak üretilir (`kademe_analizi.BUTCELER`
basamakları). Tek bir bütçeye kilitlenmek, kararı ölçümün içine gömmek olurdu.

**Ve bu bant kolon cinsinden okunmalıdır.** Kolon bedeli birinci elden **₺10**
teyit edildi (§3, Faz 0.1), yani:

| | |
|---|---|
| Bütçe | 1.000–3.000 TL = **100–300 kolon** |
| Alınabilen şekil (14-garanti) | `secim.bedel_hesapla` = `2^çifte · 3^üçlü / 8` → 10 çifte = **128 kolon** (1.280 TL) · 11 çifte = **256 kolon** (2.560 TL) · 12 çifte = 512 kolon, **bütçe dışı** |
| Geri testin bugünkü varsayılanı | **1.987 kolon/hafta ≈ 19.870 TL** — bütçenin **yedi katı** |

Faz S'nin çalışma noktası bu yüzden bugünkü geri testin çalıştığı yer değildir.
Bütün `secim` / `backtest` ölçümleri **100–300 kolon** bandında yeniden kurulur.
`en_iyi_secim(butce=…)` bütçeyi zaten kolon cinsinden alıyor — bu bir parametre
değişikliğidir, yeni makine değil.

---

## 2. Değişmeyen kurallar

Bu plan deponun doktrinini değiştirmez, ona uyar:

1. **Önceden yazılmış durma kuralı.** Her fazın kuralı ölçüm yapılmadan yazılır
   ve sonuca bakılarak değiştirilmez.
2. **Ölçüsüz sayı çıkmaz.** Her sayının yanında `n`, %95 aralık ve hangi
   koşumdan geldiği durur (`kosum.py`).
3. **Kayıt yeniden yazılmaz.** Ölçek değişirse yeni ölçekte yeniden ölçülür ve
   iki sayı ölçek notuyla yan yana durur (`odds.py:162-164` kalıbı).
4. **Ölçülen her şey §3'e gerekçesiyle yazılır.** §5.2'nin *"PR #14 ölçtü ama
   yazmadı, borç duruyor"* durumu tekrarlanmaz.

---

## 3. Hafta 1 — Faz 0: ölçümün önündeki üç blokaj

Bu üçü kapanmadan Faz K/S'nin ürettiği hiçbir para sayısı savunulabilir değil.
Üçünün de **durma kuralı yoktur** — ölçüm değil, borç kapatmadır.

### 0.1 Kolon bedeli — **cevaplandı: ₺10, birinci elden**

`getiri.KOLON_BEDELI = 10.0` zaten ölçülmüştü, ama künyesi onu varsayılan
hesabın dışında tutuyordu:

> *"Sayı resmî Spor Toto ekranından değil, üçüncü taraf bir kupon aracının
> ekranından geliyor. … Aracın kendi hizmet bedelini bedele katıp katmadığı
> **doğrulanmadı**. Bu yüzden sayı varsayılan hesaba GİRMEZ."*

`kademe_analizi.py:63` bu nedenle `VARSAYILAN_KOLON_BEDELI`'yi (₺1,50, açıkça
varsayım) kullanıyor — yani **`KADEME_OLASILIKLARI.md` §5'in bütün para tablosu
₺1,50 üzerinden hesaplanmıştır.**

**2026-09-04: bedel bayi / resmî Spor Toto uygulamasından ₺10 olarak teyit
edildi.** Üçüncü taraf aracın kaydından **bağımsız, birinci-el** bir gözlemdir
ve künyedeki hizmet-bedeli şüphesini kapatır.

Yapılacak iş:

1. `KOLON_BEDELI` künyesi güncellenir (dış kayıt → birinci el teyitli) ve
   `kademe_analizi.KOLON_BEDELI` ₺1,50'den **₺10'a** geçer.
2. `KADEME_OLASILIKLARI.md` §5 **yeniden ölçülür**; eski tablo ölçek notuyla
   yerinde bırakılır (`odds.py:162-164` kalıbı — kayıt geriye dönük yeniden
   yazılmaz).
3. `VARSAYILAN_KOLON_BEDELI` **silinmez**: ₺1,50'yle yayımlanmış her sayı hangi
   ölçekte olduğunu söyleyebilmelidir.

#### Ve sonucu şimdiden okunuyor — bu bir bulgudur, formalite değil

Geri dönüş oranı bedele ters orantılıdır, yani ₺1,50 → ₺10 geçişi yayımlanmış
her getiriyi **6,67'ye böler**:

| `KADEME` §5 satırı | tabloda (₺1,50) | ₺10'da |
|---|---:|---:|
| 3.000 TL bandı · medyan hafta | %19 | **%2,9** |
| 270.000 TL bandı · ortalama | %310 [%203, %433] | **%46** [%30, %65] |
| §5.3(c) *"en iyi 5 hafta çıkınca hâlâ %100 üstü"* | %102–207 | **%15–31** |

Yani `KADEME` §5.3'ün durma kuralının **(a) şıkkı sağlandı ve (c) şıkkı
düştü**: *"%100 üstü geri dönüş"* okuması gerçek fiyatta **hiçbir bütçede**
ayakta kalmıyor.

**Bu planı geçersiz kılmaz — doğrular.** Kaplama bedeli gerçek fiyatına
oturduktan sonra geriye kalan tek pozitif kenar adayı havuz eksenidir, ve bu
planın tamamı orayı ölçmek üzerine kuruludur. Kullanıcının bandında (100–300
kolon) §5.2'nin karşılık gelen satırı zaten **medyan %0** diyordu — tipik hafta
hiçbir şey döndürmüyor. **Faz S'nin sınavı bu sıfırı kımıldatıp
kımıldatamadığıdır.**

### 0.1b Bedel artık formülden değil **tablodan** — ✅ yapıldı

`secim.bedel_hesapla` bedeli `2^çifte · 3^üçlü / 8` diye hesaplıyordu. Formül
yanlış değil ama **dar**: yalnızca `core.solve_fix16`ın (Hamming(7,4)) bedeli,
en az yedi çifte şartıyla ve **tek** garanti seviyesinde.

Oynanan ürün o değil. Satıcının fiyat tablosu **84 şeklin tamamını** ve **üç
garanti seviyesini** taşıyor. Tablo `data/sistem_fiyat/st_extra.json`e birebir
girildi (elle girilen kayıt sınıfı) ve `spor_toto/sistem.py` onu okuyor.

**Tablo, kolon bedelinin üçüncü bağımsız teyidi.** 250 fiyatın 250'si de ₺10'un
tam katı — yani kolon sayısı her satırda tamsayı. Üç köken: `getiri.KOLON_BEDELI`
(ST EXTRA kupon ekranı) · kullanıcının bayi beyanı · tablonun kendi aritmetiği.

**Garanti artık kaçak eşiğini belirliyor.** `G`-garanti *"doğru sonuç kümedeyse
en az bir kolon en fazla `15 − G` hatalı"* demektir; `k` maç dışarıda kalırsa

    en iyi kolon ≥ (15 − k) − (15 − G) = G − k

`P(en iyi kolon ≥ 12)` için `k ≤ G − 12`, yani **14G → k≤2 · 13G → k≤1 ·
12G → k≤0**. `secim.VARSAYILAN_KACAK_ESIGI = 2` bu ailenin tek bir üyesiydi;
artık `sistem.kacak_esigi(garanti)` üçünü de veriyor.

`secim.sistem_secimi()` bütçeyi **TL** alır, adayları tablodan çeker (yedi çifte
şartı yok — tabloda sıfır çifteli satırlar da satılıyor) ve eşiği garantiden
türetir. `en_iyi_secim` yerinde duruyor: yayımlanmış bütün ölçümler ona bağlı ve
kayıt geriye dönük yeniden yazılmaz.

#### Ve ölçüldü: 13G ile 14G ayırt edilemiyor

114 tam kupon haftasında (4 sezon), aynı bütçede, aynı olasılıklarla:

| bütçe | 13G | 14G | 12G |
|---|---:|---:|---:|
| 1.000 TL | 34/114 (%29,8) | **36/114 (%31,6)** | 18/114 (%15,8) |
| 2.000 TL | 44/114 (%38,6) | **47/114 (%41,2)** | 30/114 (%26,3) |
| 3.000 TL | **52/114 (%45,6)** | 49/114 (%43,0) | 31/114 (%27,2) |

*(gerçekleşen `P(en iyi kolon ≥ 12)`; hafta düzeyinde eşleştirilmiş)*

13G − 14G farkının hafta düzeyinde bootstrap %95 aralığı **beş bütçenin beşinde
de sıfırı kesiyor** (1.000: [−0,088, +0,053] … 3.000: [−0,044, +0,096]). Yani
**13-garanti ölçülebilir biçimde daha kötü değil**; 3.000 TL'de nominal olarak
önde ama fark gürültü içinde. 12-garanti ise üç bütçede de **açık ara kötü** —
`k ≤ 0` şartı hiç kaçak affetmiyor.

Karar: varsayılan **13G** (`sistem.VARSAYILAN_GARANTI`), çünkü oynanan bu ve
ölçüm onu dışlamıyor. Faz S bu üç seviyeyi `E[TL]` altında yeniden yarıştırır —
bugünkü ölçü `P(k ≤ eşik)`, para değil.

### 0.1c Para karnesi kuruldu — ve iki kusur daha çıktı ✅ yapıldı

`spor_toto/karne.py`: kupon artık **gerçek ikramiye tablolarına** karşı
ölçülüyor. Kesit iki arşivin kesişimi (`karne.kupon_kesiti`) — projenin
bugüne kadar birleştirmediği yer: **114 hafta**, 15 maçında da oran olan ve
ikramiyesi ilan edilmiş.

**Ne ölçülüyor: garanti tabanı.** Kolon listesi elde yok (şekle biz karar
veriyoruz, kolonları satıcı üretiyor), dolayısıyla hangi kolonun kaç
tutturduğu bilinemez. Bilinen tek şey garantidir: `k` kaçakta **bir** kolon
`G − k` kademesindedir. Karne tam olarak onu sayar — yani üretilen her sayı
bir **alt sınırdır**.

#### Kusur 1 — taban garantiler arası kıyas için kullanılamaz

Arşivdeki 223 haftada `14 bilen ödülü / 13 bilen ödülü` oranının medyanı
**15,1**. Kaçaksız bir haftada taban 14-garantiye 14. kademeyi, 13-garantiye
13. kademeyi yazar; aradaki on beş kat farkın **tamamı sınırın eseridir** —
288 kolonluk bir 13G sistemi o hafta 14'ü de büyük olasılıkla tutar ama
garanti bunu *söylemediği* için taban saymaz.

Sonuç: **"13G mi 14G mi daha çok para getirir" sorusu bu araçla
cevaplanamaz** ve öyle yazıldı (`karne.gecerli_kiyas` yalnızca aynı seviyeyi
kabul eder, bekçisi `test_garantiler_arasi_kiyas_YASAK`). Aynı garanti
içindeki karşılaştırmalar geçerlidir — yanlılık iki kolda da aynıdır ve
eşleştirilmiş farkta götürür. Faz S'nin asıl sorusu (kalabalıktan sapmak
para getiriyor mu) tam olarak o türdendir, yani bu sınır onu engellemiyor.

#### Kusur 2 — enflasyon: sezonlar toplanamaz

Kademe ödülleri nominal TL ve dört sezonda **72 kat** büyümüş:

| sezon | 12 bilen (medyan) | 13 bilen | 14 bilen |
|---|---:|---:|---:|
| 2022/23 | ₺62 | ₺415 | ₺6.497 |
| 2023/24 | ₺166 | ₺1.244 | ₺18.554 |
| 2024/25 | ₺181 | ₺1.206 | ₺19.183 |
| 2025/26 | ₺928 | ₺6.357 | ₺122.154 |
| 2026/27 | ₺4.486 | ₺46.913 | ₺1.177.927 |

Maliyet ise **bugünün** fiyatından hesaplanıyor. İkisini bölmek sezonlar
arasında anlamsız — ve etkisi ölçüldü: **2022/23 haftaların %15'i olduğu
hâlde toplam ödülün %1'ini taşıyor.** Yani `kademe_analizi` §5'in *"114
hafta"* ortalaması gerçekte bir 114-hafta ortalaması değil; eski haftalar
sıfıra yakın ağırlıkla sayılıyor ve sayı fiilen son iki sezonun ölçümü.

**Bu, ₺1,50 → ₺10 kusurundan bağımsız İKİNCİ bir kusurdur** ve ters yönde
çalışır (biri getiriyi şişiriyordu, bu söndürüyor). İkisi birbirini
götürmez — ölçüleri farklı. `karne()` bu yüzden her zaman **sezon kırılımı**
döndürür ve havuzlanmış ortalamayı `uyari` alanıyla verir.

#### Ölçülen: 13-garanti, 114 hafta, garanti tabanı

| bütçe | ödül alan hafta | medyan ROI | ortalama ROI | en iyi 5 hafta çıkınca | en iyi 5'in payı |
|---|---:|---:|---:|---:|---:|
| 500 TL | 25/114 | %0,0 | %3,5 | %1,6 | %54,6 |
| 1.000 TL | 34/114 | %0,0 | %4,9 | %2,6 | %48,3 |
| 2.000 TL | 44/114 | %0,0 | %4,3 | %2,2 | %52,2 |
| 3.000 TL | 52/114 | %0,0 | %5,4 | %2,9 | %48,6 |
| 5.000 TL | 58/114 | %0,1 | %5,6 | %2,8 | %52,8 |

Sezon kırılımı (2.000 TL): 2022/23 %0,2 · 2023/24 %1,9 · 2024/25 %5,0 ·
2025/26 %7,8 — **medyan her sezonda %0.**

**Üç okuma.** (1) Medyan hafta hiçbir şey döndürmüyor ve bu sonuç enflasyondan
da tabandan da etkilenmiyor — `KADEME` §5.2'nin bulgusu ayakta. (2) Ödülün
yarısı 114 haftanın **beşinden** geliyor; `KADEME` §5.3-1'in kuyruk uyarısı
bu kesitte de aynen geçerli. (3) Ortalamalar **alt sınırdır**, gerçekleşen
getiri bunlardan büyüktür — ama ne kadar büyük olduğu ancak gerçek kolon
listeleriyle bilinir ve o, canlı haftalarda ST EXTRA kaydından gelecek (Faz D).

### Faz K — kalabalık modeli **ölçüldü ve durma kuralını geçti** ✅

`spor_toto/kalabalik.py`. Kesit: **112 hafta × 3 kademe**. Model:

```
o_i(s)  ∝  p_i(s)^λ          (λ=1 → orneklem · λ→∞ → favori)
```

Ölçek uyuma **hiç girmiyor**: gözlenen kazanan adetleri `N · P(k)` ile
orantılı olduğu için kademeler arası oranlar `N`'den bağımsız ve modelin
şeklini tek başına tanımlıyor. 15. kademe bilerek dışarıda — 14/13/12
**kolon** sayar, 15 **kupon** (§3.48). Kazanan adedi ağırlık olarak
kullanılmıyor: bir haftanın 40.000 kazananı 40.000 bağımsız gözlem değil,
aynı 15 maçın 40.000 kez sayılmasıdır.

#### Sonuç: λ = 1,7608 · %95 [1,669, 1,865]

**Aralık 1'i içermiyor.** Kalabalık favoriye piyasadan daha keskin
yığılıyor ve bu artık varsayım değil ölçüm. λ dört katın dördünde de
kararlı (1,746–1,782).

**Model bilerek tek parametreli.** `δ` (beraberlik) ve `h` (ev sahibi)
denendi ve düştü: sezon sezon kestirildiğinde `δ` −0,19 ↔ +0,61, `h`
−0,26 ↔ +0,50 arasında **işaret değiştiriyor**; üç parametreli model sezon
dışarıda bırakmalı karşılaştırmada tek parametreliden **ayırt edilemiyor**
(−0,00012, %95 [−0,00047, +0,00012]). Kazanmayan parametre modelde durmaz.

#### K4 durma kuralı — üç şartın üçü de

| tutulan sezon | hafta | olculen | orneklem | favori |
|---|---:|---:|---:|---:|
| 2022/23 | 17 | **0,3840** | 0,3849 | 1,7209 |
| 2023/24 | 31 | **0,4123** | 0,4149 | 1,8068 |
| 2024/25 | 29 | **0,4029** | 0,4052 | 1,9624 |
| 2025/26 | 35 | **0,3598** | 0,3627 | 2,0545 |

* `olculen − orneklem` = −0,00236, %95 **[−0,00317, −0,00156]** — sıfırı kesmiyor
* `olculen − favori` = −1,52229, %95 **[−1,63701, −1,41023]** — sıfırı kesmiyor
* aynı yön **4/4**

**GEÇTİ.** Ve bu, projede bir eksende **önceden yazılmış bir durma kuralını
geçen ilk ölçüm** — tahmin ekseninde on bir deneme geçememişti.

#### K5 bağımsız sınav: `favori` ikinci kez çürüdü

Uyum kademeler arası orana bakar ve `N`'yi hiç görmez; oradan çıkan `N` ise
dağıtılan havuzla karşılaştırılabilir. **Sezon içinde** (havuz nominal TL ve
dört sezonda 72 kat büyüdü — havuzlanmış korelasyon işaret bile değiştiriyor,
ölçüldü: −0,21):

| model | ort. sezon içi `r` | ima ettiği haftalık kolon |
|---|---:|---|
| olculen | **+0,542** | 10,4M – 31,3M |
| orneklem | **+0,580** | 18,8M – 70,7M |
| favori | **−0,298** | **10¹⁷ – 10¹⁹** |

`favori` haftada 10¹⁷ kolon ima ediyor — dünya nüfusu 8×10⁹. Fiziksel
olarak imkânsız, ve korelasyonun işareti de ters.

**Sınav `olculen` ile `orneklem`'i ayırmıyor** ve niçin ayıramadığı zaten
kodda yazılıydı: `havuz_karnesi` notu *"tek bir sistem kuponu aynı hafta
onlarca kolonla kazanabilir; bağımsız-kolon modeli bu ilişkiyi göremez ve
seviye tahmini bu yüzden şişer."* Seviye sınavı bu yüzden yalnızca
makuliyet kontrolüdür — ve onu geçiyor: `orneklem` 2025/26'da kolon başına
₺5,41 dağıtılan pay ima ediyor, ₺10 kolon bedelinin ~%54'ü.

#### §3.34'ün 22 katlık belirsizliği kapandı

§3.34 *"bu eksende belirsizliğin kaynağı tahminci değil, kalabalık"* diyor
ve `orneklem` (getiri 0,156) ↔ `favori` (0,007) arasında **22 kat** fark
ölçüyordu. `favori` ucu iki bağımsız yoldan çürüdü. Gerçek kalabalık
`orneklem` ile `olculen` arasındadır — yani aralığın **iyimser** ucunda.

`getiri.KALABALIK_MODELLERI` dördüncü modelini aldı (`olculen`) ve üç
modelin ikisi artık varsayım değil.

**Ama bu bir kâr vaadi değildir.** Ölçülen şey kalabalığın *şekli*; bundan
para çıkıp çıkmadığı Faz S'nin sorusu ve `karne`nin garanti tabanı o soruyu
henüz cevaplamıyor.

### Faz S — `VARSAYILAN_KAYIP_ORANI` ölçüldü: **sıfır** ✅

Plan §5 S1 şunu istiyordu: *"`0.05` bir girdi olmaktan çıkar, çıktı olur."*
Çıktı oldu — ve değeri **sıfır**.

Önce alet kuruldu: `getiri.kosullu_kademe_dagilimi` + `getiri.beklenen_tl`.
`kalabalik_kademeleri` rakibin isabetini **koşulsuz** hesaplıyor ve kendi
docstring'i bunu söylüyordu — *"bu sayı iki farklı plan için birebir aynı
çıkar"* — yani kalabalık ayarının kazancını tanım gereği göremez. Oysa havuz
**biz kazandığımızda** bölünür. `_kosullu_rakip` bu soruyu yalnızca 15
kademesi için cevaplıyordu; ortak DP onu bütün kademelere açıyor: her maçta
`(sonuç kümede mi) × (rakip uydu mu)` dört yolu birlikte taşınıyor.

#### Üç bağımsız yol, aynı cevap

1. **Kayıp bütçesi taraması.** `kalabalik_ayari`, ölçülen kalabalık modeliyle
   bütçe 0'dan **0,70**'e çıkarılsa bile **tek bir maçın işaretini
   değiştirmiyor** — yedi basamağın yedisinde de `değişen maç = 0,00`.
2. **Doğrudan `E[TL]` yerel araması.** 25 haftanın 25'inde taban plan zaten
   en iyi; tek maçlık en iyi değişimin kazancı **tam 1,0000×**. Arama
   dejenere değil: aynı maçta favoriyi bırakmak E[TL]'yi **0,39×**'e,
   ikinci alternatif **0,23×**'e düşürüyor.
3. **Mekanizma analitik.** Ölçülen model `o(s) ∝ p(s)^λ` **monotondur**,
   yani sembol sıralamasını korur. Kalabalıktan sapmanın tek yolu daha
   düşük olasılıklı sembole geçmektir ve tutturma kaybı, pay kazancını
   her bantta eziyor.

`secim.VARSAYILAN_KAYIP_ORANI = 0.0` oldu ve künyesi artık *"harcama
kararı"* değil ölçüm. **Sıfır "ayar kapalı" demek değil:** hedefi hiç
düşürmeyen değişimler hâlâ yapılır; değişen şey, tutturma olasılığının
**satılmamasıdır**.

#### Ama bulgunun sınırı keskin ve kenar tam orada

Bu sonuç **modelin monotonluğuna** bağlıdır. Kayıtlı oynanma payları
(2026/27, 4 hafta, 60 maç) bunu doğrudan çürütüyor:

> **60 maçın 21'inde (%35) oynanma sıralaması piyasa sıralamasından
> farklı.** Monoton bir model bunu **asla** üretemez.

Ortalama mutlak artık 0,060 (λ=1'e göre), en büyük sapma **0,28**. Ve
sapmaların yönü sistematik: en büyük beş sapmanın dördü favorinin
payını **düşürüyor** (−0,24, −0,23, −0,18, −0,17) — yani o platformun
kullanıcıları piyasadan **daha yayvan** oynuyor.

Bu, λ = 1,76 ile (kademe oranlarından: kalabalık piyasadan **daha keskin**)
**çelişiyor**. İki açıklama var ve ikisi de kayda değer: ya platform
havuzu temsil etmiyor (§6.3b'nin zaten yazılı sınırı), ya da iki ölçümden
biri başka bir şeyi ölçüyor. `n = 4 hafta`, karar için yetmez.

#### Faz B yeniden yönlendi

Hedef artık **şekil parametresi değil, artık**. `p^λ` ailesinin içinde
kenar yok — üç yoldan ölçüldü. Kenar varsa kalabalığın piyasadan
**monoton olmayan** biçimde saptığı yerdedir ve onu görmek için oynanma
payı kaydı gerekir, kademe adetleri değil: kademe adetleri yalnızca
dağılımın *şeklini* taşır, hangi maçta hangi sembole yığıldığını değil.

Bu, haftalık veri girişini planın en değerli parçası yapıyor — ve
biriktirmekten başka yolu yok.

### Faz S ekleri — artığın tavanı ölçüldü, ve bir tuzak yakalandı

#### Önce tuzak: kademe bölüşümü **varsayılamaz**

Artığın tavanını ölçerken kademe havuzlarını elle yazdım
(`{13: 1e7, 12: 1e6}`, yani oran 10,0). Sonuç **2,63× tavan** çıktı ve
yayımlanmak üzereydi. Yayımlanmadı, çünkü aynı kurulum Faz S'nin *"monoton
kalabalıkta sapmak kazandırmaz"* bulgusunu da çürütüyordu — iki ölçümüm
çelişiyordu.

Çelişkinin kaynağı arama derinliği değil, **benim varsayımım**:

| kademe bölüşümü | 13/12 oranı | monoton modelde sonuç |
|---|---:|---|
| **gerçek** ikramiye tablosu | **0,800** | 1,000× · 20 haftanın **0**'ında artıyor |
| elle yazdığım | 10,0 | 12,17× · 20 haftanın **19**'unda artıyor |

Gerçek oran `havuz.BOLUSUM`'un 20/25'idir ve üç haftada da birebir 0,800.
Benim yazdığım 12,5 kat sapıyordu ve **cevabı ters çevirdi.**

`getiri.kademe_havuzlari(payout)` eklendi: havuz sözlüğü artık resmî
tablodan **türetiliyor**, elle yazılmıyor. Bekçisi
`test_kademe_havuzu_ELLE_yazilinca_cevap_DEGISIYOR` — tuttuğu şey yön değil
**duyarlılık**, çünkü yönün kendisi kuponun şekline bağlı.

#### Düzeltilmiş tavan: **1,003×** (2,63× değil)

Gerçek kademe havuzlarıyla, 2026/27'nin ikramiyesi olan üç haftası:

| hafta | taban E[TL] | monoton model | **gerçek oynanma payı** | değişen maç |
|---|---:|---:|---:|---:|
| 1 | 75,05 | 1,000× | **1,003×** | 1 |
| 2 | 93,59 | 1,000× | **3,013×** | 5 |
| 3 | 93,03 | 1,000× | **1,000×** | 0 |

**Medyan 1,003×.** Üç haftanın ikisinde kazanç yok; biri 3,01× veriyor ve
ortalamayı tek başına taşıyor. `n = 3`. **Hiçbir şey kurulmuş değil.**

Yani artık ekseni ne Faz S'nin kapattığı kadar ölü, ne benim ilk (hatalı)
ölçümümün dediği kadar zengin. Bugünkü dürüst cümle: **ölçülmedi.**

#### Ve tavana ulaşmak için payı ÖNCEDEN bilmek gerekiyor

Tavan, o haftanın kendi oynanma payına karşı optimize edilerek hesaplandı —
yani **mükemmel eşzamanlı bilgi** varsayıyor. Geçen haftanın payıyla
optimize edip o haftanın payıyla ölçtüğümde:

| hafta | geçen haftanın payıyla | o haftanın payıyla (tavan) |
|---|---:|---:|
| 2 | **0,660×** | 3,013× |
| 3 | 1,000× | 1,000× |

Geçen haftanın payı **taşımıyor** ve bir haftada belirgin biçimde
**zararlı**. Yani bu eksen ancak oynanma payları **kupon kapanmadan önce**
okunabiliyorsa açıktır. Bu teknik değil **operasyonel** bir soru ve cevabı
planın geri kalanını belirliyor.

### Faz 0.1 kapandı — kolon bedeli koda geçti, §5 yeniden ölçüldü ✅

Faz 0.1 *"`kademe_analizi.KOLON_BEDELI` ₺1,50'den ₺10'a geçer"* diye yazılmıştı
ve belgeye yazılmış ama **koda uygulanmamıştı**. Uygulandı.

`getiri.KOLON_BEDELI` künyesi güncellendi: sayı artık üç bağımsız kökenden
doğrulanıyor (ST EXTRA kupon ekranı · bayi/resmî uygulama beyanı · sistem
fiyat tablosunun 250 satırının 250'sinin de 10'un katı olması), yani
*"aracın hizmet bedelini katıp katmadığı doğrulanmadı"* şüphesi kapandı ve
sayı **varsayılan hesaba girdi**.

**Yeniden koşumun sonucu, öngörülen aritmetiği doğruluyor:**

| haftalık | medyan | ortalama | −5 hafta | **P(zarar)** |
|---:|---:|---:|---:|---:|
| 1.000 TL | %0 | %42 | %13 | — |
| 2.000 TL | %0 | %39 | %16 | — |
| 200.000 TL | %5 | %44 | %20 | **%99** |
| 1.800.000 TL | %8 | %47 | %35 | **%100** |
| 5.400.000 TL | %6 | %49 | %29 | **%100** |

`KADEME_OLASILIKLARI.md` §5.2'ye yeniden ölçüm bloğu eklendi ve eski tablo
ölçek notuyla **yerinde bırakıldı**. §5.3'ün dördüncü sınırı (*"kolon bedeli
doğrulanmadı"*) kapandı; üçüncü şartı (*"en iyi 5 hafta çıkınca %100 üstü"*)
**düştü** — hiçbir bütçede %100'e yaklaşan gözlenen getiri yok.

### Faz 0.3 — H1/H2 kapandı: canlı kaydı kirleten saat hatası ✅

Denetimin iki bulgusu, ikisi de canlı haftalık kaydı doğrudan etkiliyordu:

* **H1** — `tahmin.fixtures_maclari` **hiçbir zaman filtresi uygulamıyordu**,
  oysa `yaklasan_maclar` fikstürü *tercih* ediyor. Yani maç gününde sabah
  oynanmış bir maç, akşam hâlâ "yaklaşan maç" olarak maç öncesi
  olasılığıyla servis ediliyordu — modülün kendi docstring'inin açıkça
  yasakladığı şey. Filtre bağlandı.
* **H2** — `_simdi()` naive **yerel** saatti; `snapshot_iddaa` ise kickoff'u
  açıkça UTC yazıyor. `TZ=Europe/Istanbul` altında üç saatlik bir
  **sızıntı penceresi** açılıyordu (konteyner UTC koştuğu için sessizdi).
  `_simdi()` artık UTC ve zaman dilimi bilinçli.

Ayrıca `GUVENLIK_PAYI = 2 saat` eklendi: iki kaynak iki farklı saat
ekseninde yazıyor (biri UTC, öteki football-data'nın yerel saati) ve pay o
belirsizliği yutuyor. Yön kasıtlı — bir maçı erken elemek, başlamış maça
maç öncesi olasılığı vermekten ucuzdur.

Üçü de bekçiye bağlandı (`test_BASLAMIS_mac_fikstur_kaynagindan_da_elenir`,
`test_simdi_UTC_ve_zaman_dilimi_bilincli`,
`test_guvenlik_payi_baslamak_UZERE_olan_maci_eler`).

### İki bekçi düştü ve ikisi de haklıydı

Faz S'de `VARSAYILAN_KAYIP_ORANI`'nı 0,05'ten 0'a çekerken **yalnızca
ilgili süitleri koştum**, tamamını değil. İki kapı bunu yakaladı:

1. `test_olculen_ve_varsayilan_kolon_bedeli_KARISTIRILMIYOR` — betiğin
   hangi sabiti okuduğunu tutuyordu. Değişiklik kasıtlıydı; bekçinin asıl
   işi (*"üçüncü kopya geri gelmesin"*) korunarak güncellendi.
2. `test_diskteki_kayit_bayat_degil` — dondurulmuş 2. hafta kaydı bugünkü
   kodun ürettiğiyle uyuşmuyordu. **Kayıt bayat değildi:** 0,05 ile
   donduruldu ve öyle oynandı. Bugünün varsayılanıyla yeniden üretmek
   kaydı geriye dönük yeniden yazmak olurdu. Bekçi artık kaydı **kendi
   beyan ettiği** `meta.kayip_orani` ile yeniden üretiyor — daha güçlü bir
   sınav, çünkü beyan eksikse ya da yanlışsa yine düşer.

### Faz 0.2 kapandı — anormal hafta bayrağı arşiv okuma yolunda ✅

`KADEME §8`'in önerisi buydu: *"`sportoto_arsiv` okunurken aynı denetim
`data_quality` bloğuna bağlanmalı — bu eksen bugün denetimsizdir."* Bağlandı.

`havuz.anormal_haftalar()` eşiği **arşivin tamamından** hesaplıyor (çağıranın
alt kesitinden değil — öyle olsaydı aynı hafta bir ölçümde anormal, ötekinde
normal çıkardı) ve `arsiv_haftalari` her satıra `anormal` bayrağını koyuyor.
**225 haftanın 32'si** işaretli — §8'in sayısıyla birebir.

Bayrak **elemez, beyan eder**: kademe ortalaması alan her hesap eleyip
elemediğini söylemek zorunda kalsın diye. Sessiz eleme de sessiz kirlenme
kadar kötüdür.

### Faz D başladı — haftalık koşum ve canlı karne ✅

`scripts/hafta_kos.py` iki uçlu: `--oncesi` kupon öncesi girdilerden planı
üretir ve bütün varsayımlarıyla basar, `--sonrasi` sonucu ve resmî ikramiye
tablosunu okuyup `docs/KAZANMA_KARNESI.md`'yi **baştan yazar** (ekleme değil
yeniden üretim — ekleme bir kez bozulunca sessizce bozuk kalır).

#### İlk karne — 2026/27, üç sonuçlanmış hafta

| hf | şekil | kolon | P(k≤1) | E[TL] | kaçak | kademe | ödül | net | fiyat |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 6b/1ç/8ü | 162 | 0,249 | 75 | 4 | 9 | 0 | −1.620 | `iddaa` |
| 2 | 6b/1ç/8ü | 162 | 0,219 | 94 | 1 | 12 | 1.439 | −181 | `iddaa-acilis` |
| 3 | 6b/1ç/8ü | 162 | 0,282 | 93 | 1 | 12 | 1.230 | −390 | `pinnacle-kapanis` |
| 4 | 6b/1ç/8ü | 162 | 0,175 | — | — | — | — | — | `pinnacle-kapanis` |

**Toplam:** maliyet 4.860 TL · ödül 2.668 TL · net **−2.192 TL** ·
geri dönüş **%54,9**.

Üç okuma ve üçü de karnenin kendi başlığında yazılı:

1. **Bu bir tahmin kaydı değildir.** Plan, kupon öncesi girdilerden
   *bugünkü* motorla yeniden türetildi. Sızıntı yok (girdiler
   `entered_at`te, sonuç `results_entered_at`te; kalabalık modeli 2026/27'yi
   hiç görmedi), ama motor o gün bugünkü hâlinde de değildi.
2. **Ödül alt sınırdır.** 162 kolonluk bir 13-garanti sistemi, garantinin
   söylediği tek kolondan fazlasını da tutturur; karne onları saymaz çünkü
   kolon listesi bizde değil. Gerçekleşen getiri bu tablodan **büyüktür**.
3. **Fiyat ölçeği haftalar arasında değişti** (~%18 marjlı iddaa → ~%4,6
   marjlı Pinnacle) ve olasılıklar bu yüzden doğrudan karşılaştırılamaz.
   Sütun bunu her satırda söylüyor.

`n = 3`. Bu tablo bir strateji karnesi değil, bir **kayıt başlangıcı**.

### Faz 0.3 tamamlandı — çoklu karşılaştırma düzeltmesi (H5) ✅

Denetimin H5'i şunu diyordu: `arena.roster` on'dan fazla aile deniyor ve
her biri **tekil** %95 aralığa karşı ölçülüyor; on bağımsız denemede en az
bir yanlış "geçti" görme olasılığı %40'a yaklaşır. *"Bugün bunu maskeliyor
ama biri geçtiği gün iddia savunulamaz olur."*

Eklenenler:

* `evaluate.bootstrap_farki` artık **tek yönlü bootstrap p-değeri** de
  döndürüyor: `(k+1)/(n+1)`, yani sıfır p yayımlanmıyor.
* `evaluate.holm()` — Holm–Bonferroni, adım adım. Bonferroni'den **kesinlikle
  daha güçlü**: p'ler sıralanır, `i`. sıradaki `α/(m−i)` ile karşılaştırılır,
  ilk kırılmada kalanların hepsi düşer.
* Her satırda `gecti_holm` ve `denenen_aday_sayisi`; arenanın gövdesinde
  `gecen_holm` listesi.

**`gecti` bayrağının anlamı DEĞİŞMEDİ** — tekil aralık okuması yerinde
kaldı ki yayımlanmış sayılar yeniden yorumlanmasın. Holm onun *yanına*
yazılıyor ve iddia hangisine dayanıyorsa o söyleniyor. Bugün ikisi de aynı
cevabı veriyor, çünkü hiçbir aile geçmiyor.

Bekçilerin tuttuğu asıl şey H5'in kendisi: aynı `p = 0,03` tek başına
geçerken on aday arasında **geçmiyor**.

### Faz F1 — kupon-zamanı fiyatı: **kapandı, %22 geri alınamıyor** ✅

Soru şuydu: kupon ilk maçtan önce kapanır, oranlar her maçın saatine kadar
oynar — haftanın son maçlarında kapanış fiyatı kupon verilirken elimizde
yok ve bedeli **%22 kolon** (2.686 → 3.290, §5.2 eki). Kapanışı açılıştan
öngörebilir miyiz?

Bu soru piyasayı yenmeyi gerektirmiyordu: hedef sonuç değil, piyasanın
kendi kapanışı. `cizgi.cizgi_tahmini()`, merkezlenmiş log uzayında tek
katsayılı bir ölçekleme kuruyor (`L_kapanış ≈ b · L_açılış`) ve sezon
dışarıda bırakmalı ölçüyor:

| tutulan sezon | n | `b` | açığın geri alınanı |
|---|---:|---:|---:|
| 2021/22 | 7.821 | 1,0073 | %2,7 |
| 2022/23 | 7.800 | 1,0096 | %6,2 |
| 2023/24 | 7.797 | 1,0099 | %2,9 |
| 2024/25 | 7.681 | 1,0095 | %2,3 |
| **toplam** | **31.099** | **≈1,009** | **%3,3** |

Açılış–kapanış açığı Brier'de **+0,002458**; ölçeklemenin kazandırdığı
**+0,000082**.

**Okuma sert:** `b ≈ 1`, yani açılış zaten kapanışın **yansız
kestiricisidir**. Aradaki fark açılıştan *sonra gelen bilgidir* ve tanımı
gereği açılışta yoktur. A1'in *"hareket kapanışın ötesinde bilgi
taşımıyor"* bulgusunun simetriği bu: **kapanış da açılışın içinden
çıkarılamıyor.**

§5.2'nin %22'lik kolon bedeli bu yolla geri alınamaz. Madde kapandı;
durma kuralı (hafta düzeyinde aralık sıfırı kesiyorsa kapan) fazlasıyla
sağlandı — dört katın dördünde de kazanç açığın onda birinin altında.

### 0.2 Otuz iki anormal haftayı kapıya bağla — `KADEME_OLASILIKLARI.md` §8

223 haftanın **32'sinde** 12. kademe kazanan sayısı medyanın (41.516) onda
birinden az. Elenmeden alınan kademe ortalaması, tek kolonun beklenen değerini
**4,99 TL** gösteriyor — yani %332 geri dönüş, imkânsız bir sayı.

`kademe_analizi.anormal_haftalar()` bugün var ama **yalnızca o script'te**.
Denetim `havuz.arsiv_haftalari()` okuma yoluna `data_quality` bloğu olarak
bağlanır; kademe ortalaması alan her hesap **eleyip elemediğini beyan etmek
zorunda** olur. Bekçi: anormal hafta elenmeden ortalama alan bir çağrı testte
düşsün.

### 0.3 Çoklu karşılaştırma ve canlı kaydın bütünlüğü

**H5 — çoklu karşılaştırma düzeltmesi yok** (denetim §H5). `arena.roster` 10+
aile deniyor, `gecti` bayrağı **tekil** %95 aralığa bakıyor (`evaluate.py:638`,
`tahmin.py:383`). Bugün *"hiçbiri geçmedi"* bunu maskeliyor; **Faz K ya da S'de
bir şey geçtiği gün iddia savunulamaz olur.** Holm/BH düzeltmesi + gövdede
`denenen_aday_sayisi` alanı — projenin kendi köken doktriniyle birebir uyumlu.

**H1/H2 — üç saatlik sızıntı penceresi** (denetim §H1, §H2).
`tahmin.fixtures_maclari` (`tahmin.py:102-128`) **hiçbir zaman filtresi
uygulamıyor**, oysa `yaklasan_maclar` fikstürü tercih ediyor (`tahmin.py:255`);
`_simdi()` (`tahmin.py:76-78`) naive yerel zaman kullanıyor, `snapshot_iddaa`
UTC yazıyor. `TZ=Europe/Istanbul` altında **son üç saatte başlamış her maç
"gelecekte" sayılır**. Modülün kendi docstring'i (`tahmin.py:81-93`) bunu açıkça
yasaklıyor. Bu haftadan itibaren her hafta canlı kayıt tutulacağı için doğrudan
karneyi kirletir. `_gelecekte` tek yol olur; `build_fixtures.py:115` `Time`
sütununu gerçekten kullanır.

---

## 4. Hafta 2–4 — Faz K: kalabalık modelini 448 gözleme oturt

Planın en yüksek beklenen değerli işi. Yeni modül: **`spor_toto/kalabalik.py`**.

### K1 — Veri hattı

`(sezon, hafta) → [15 maç × shin olasılığı] + gerçek sonuç + kademe kazanan
adetleri`. Yeniden kullanılanlar: `odds.load_odds` / `market_odds` /
`implied_probs`, `data/st_history/*.json`, `havuz.arsiv_haftalari`,
`kademe_analizi.ikramiye_tablolari`. Çıktı, 112 haftalık **tek** kesit; kapsama
raporu 0.2'nin `data_quality` bloğuyla birlikte.

### K2 — Model: iki parametre ve bir çarpan

Bir halk kolonunun `i` maçında `s` sembolünü işaretleme payı:

```
o_i(s)  ∝  p_i(s)^λ · (1 + δ·[s = "0"]) · (1 + h·[s = ev])       (normalize)
```

- `λ > 1` → kalabalık favoriye piyasadan **daha çok** yığılıyor (beklenen yön;
  §5.2 bulgu 6 ve `KADEME` §6 bu yönü destekliyor).
- `δ` beraberlik iştahı, `h` ev sahibi yanlılığı.
- Üçü de **ölçülür**, varsayılmaz.

**Kademe sayımının iki farklı şeyi saydığı zaten kodda yazılı** ve tanımlamayı
bedava veriyor (`super_toto_degerlendir.havuz_karnesi` notu, §3.48):

| kademe | ne sayıyor |
|---|---|
| **15** | **kupon** — iki kolon tanım gereği en az bir maçta ayrışır, yani bir kuponun en fazla bir kolonu 15 yapar |
| **14 / 13 / 12** | **kolon** — tek bir sistem kuponu onlarca kolonla kazanır |

Dolayısıyla `kazanan_14 / kazanan_15` oranı **sistem çokluğunun ölçüsüdür** ve
223 haftada gözlenebilir. Haftalık ölçek `N_hafta` sıkıntı parametresi olarak
serbest bırakılır; **kademeler arası oranlar `N`'den bağımsızdır** ve modelin
şeklini tek başına tanımlar.

### K3 — Kestirim

Kazanan adetleri üzerinde negatif binom olabilirlik (aşırı yayılımı soğurur;
Poisson kesin olarak fazla dar aralık verir). `λ, δ, h` ve çokluk çarpanı
global, `N_hafta` profil dışı. Kaçak dağılımı için `ortak.kacak_dagilimi` zaten
Poisson-binom hesaplıyor.

### K4 — Yanlışlanabilirlik · **durma kuralı, şimdiden yazıldı**

Sezon dışarıda bırakmalı çapraz doğrulama: üç sezonda kestir, dördüncüde sına.

> **Geçti sayılması için** `olculen` modeli, tutulan sezonun kazanan adetleri
> üzerindeki log-olabilirlikte hem `orneklem` hem `favori` modelini geçmeli;
> **hafta düzeyinde bootstrap %95 aralığı sıfırı kesmemeli**; ve dört sezonun
> dördünde de aynı yön çıkmalı.
>
> **Geçmezse** havuz ekseni *"kalabalık ölçülemedi"* diye daralır. Faz S
> yalnızca 2026/27 oynanma paylarıyla (n = 12) **betimleyici** koşulur ve bu
> belgeye öyle yazılır. Bu meşru bir bitiştir.

### K5 — Vekilin doğrulanması — §6.3b'nin *"bilinen sınır"*ı

2026/27 hafta dosyalarındaki oynanma payları **tek bir platformun
kullanıcılarıdır**, Spor Toto havuzunun tamamı değil, ve temsil edip etmediği
**hiç ölçülmedi** — bütün `crowd_*` ölçüleri bu vekile dayanır.

K4 geçerse kestirilen `o_i(s)` ile kaydedilmiş oynanma payı karşılaştırılır.
Sistematik sapma varsa vekilin yanlılığı **sayıya dönüşür** ve bugünkü nitel
uyarının yerine ölçülmüş bir sayı geçer. Bu, §6.3'ün B2 maddesinin ta kendisidir.

### K6 — Seyreltme yasası

Kestirilmiş modelle 112 haftanın her biri için kademe kazanan adetleri öngörülür
ve gözlenenle karşılaştırılır. `KADEME` §6'nın Spearman −0,843'ü böylece
**kullanılabilir bir fonksiyona** çevrilir: `E[pay | seçim kümesi]`.

**Çıktı.** `getiri.KALABALIK_MODELLERI` dördüncü modelini alır — `"olculen"` —
parametreler `artefakt.py` kalıbıyla sürümlenir ve bayatlığı görünür olur, koşum
`kosum.py` defterine yazılır. `getiri.beklenen_getiri` artık varsayımla değil
**ölçümle** çalışır.

---

## 5. Hafta 5–6 — Faz S: seyreltmeyi hesaba katan kupon (B3)

§6.3'ün *"kaplamanın ve havuzun buluştuğu yer; projenin en özgün işi"* dediği iş.

### S1 — Amaç fonksiyonunu değiştir

Bugün `secim.en_iyi_secim` `P(k ≤ 2)`'yi enbüyüklüyor ve **kalabalığı hiç
görmüyor**. `secim.kalabalik_ayari` var ama iki kısıtı taşıyor:

- işaret **sayılarını sabit tutuyor**, yalnızca *hangi sembol* sorusunu yeniden
  soruyor — bedeli değiştirmemek için alınmış bilinçli bir sadeleştirme;
- ödünleşme `VARSAYILAN_KAYIP_ORANI = 0.05` ile **elle** veriliyor ve
  docstring'i bunu dürüstçe *"ölçüm değil, harcama kararı"* diye etiketliyor.

Yeni `secim.getiri_secim` Pareto DP'yi **`(bedel, P(k≤2), E[TL])`** üzerinde
koşar: `getiri.beklenen_getiri` + K6'nın `olculen` modeli + arşivden gelen
gerçek kademe havuzları. **`0.05` bir girdi olmaktan çıkar, çıktı olur** — ne
kadar tutturma olasılığı satmanın optimal olduğu ölçülür.

Budamanın geçerliliği korunur (`secim.py:203` gerekçesi aynen geçerli):
kümülatifler gelecekteki her evrişimde pozitif doğrusal birleşimdir, `E[TL]` ise
kademeler üzerinden toplamsaldır. Cephe taşınamazsa `kirpildi` bayrağı açılır —
sessizce yaklaşık olunmaz.

### S2 — 112 hafta üzerinde **gerçek parayla** geri test

Üç kural yan yana: bugünkü `en_iyi_secim` ↔ bugünkü `kalabalik_ayari` ↔ yeni
`getiri_secim`, **arşivdeki gerçek ikramiye tablolarına** karşı, aynı bütçede.

Bütçe: **100–300 kolon** (₺10'da 1.000–3.000 TL) **ve**
`kademe_analizi.BUTCELER`in tamamı üzerinde bütçe → getiri eğrisi. `BUTCELER`
zaten kolon cinsinden yazılı; TL'ye çevrimi bedel sabiti yapar, yani 0.1'den
sonra etiketler kendiliğinden düzelir.

Rapor edilen sayı **medyan** haftadır, ortalama değil — `KADEME` §5.2: 100 kolon
bandında ortalama %277 iken medyan **%0** (ve bunlar ₺1,50 ölçeğinde; ₺10'da
ortalama %41,6, medyan yine %0).

**Sınav açıkça budur:** 100–300 kolon bandında medyan hafta bugün **sıfır**
döndürüyor. `getiri_secim` bu sıfırı kımıldatabiliyor mu? Ortalamayı büyütmek
yetmez — ortalamayı üç hafta taşıyor (`KADEME` §5.3-1).

### S3 — Durma kuralı · **şimdiden yazıldı**

`KADEME` §5.3'ün üç şartı devralınır ve bir dördüncüsü eklenir:

| # | Şart |
|---|---|
| **a** | ✅ **Sağlandı** — kolon bedeli ₺10, bayi/resmî uygulamadan birinci elden teyitli (Faz 0.1) |
| **b** | `getiri_secim` − `en_iyi_secim` farkında hafta düzeyinde bootstrap %95 aralığı sıfırı kesmiyor |
| **c** | **En iyi 5 hafta çıkarıldığında fark hâlâ pozitif** — kuyruk taşımıyor |
| **d** | Sezon dışarıda bırakmalı: kalabalık üç sezonda kestirildi, kupon dördüncüde kuruldu |

Dördü birden sağlanmazsa Faz B *"ölçüldü, üstünlük yok"* diye kapanır ve
`ISTATISTIK_YOL_HARITASI.md` §6.5'in 2. ve 3. soruları **hayır** cevabıyla
kapanır. Bu da meşru bir bitiştir — ve bu alandaki araçların neredeyse tamamı
birinciyi *iddia eder*, hiçbiri ikinciyi **ölçmez**.

### S4 — Anormal hafta duyarlılığı

Bütün S2 sayıları, 0.2'nin 32 anormal haftası **elenmiş** ve **elenmemiş** iki
kolonda raporlanır. İki kolon işaret değiştiriyorsa sonuç stratejiden değil
**veri kalitesinden** geliyordur ve öyle yazılır.

---

## 6. Hafta 7 — Faz F: tahmin ekseninden kalan üç ölçülmüş iş

Eksen kapalı, ama bu üç işin **hiçbiri piyasayı yenmeyi gerektirmiyor** —
bu yüzden buradalar.

### F1 — Kupon-zamanı fiyatı: ölçülmüş %22'yi geri al

§5.2 eki şunu ölçtü: kupon ilk maçtan önce kapanır, oranlar her maçın saatine
kadar oynar — **haftanın son maçlarında kapanış fiyatı kupon verilirken elde
yoktur.** Bedeli isabet değil **kolon: %22 artış (2.686 → 3.290)**.

Bu, piyasayı yenmek değil **piyasanın kendi kapanışını öngörmektir.** Korpus
31.103 maçta hem `acilis_*` hem `kapanis_*` taşıyor (`egitim.py`); hedef sonuç
değil **kapanış fiyatının kendisi**. `cizgi.py`'ye `cizgi_tahmini` eklenir.

**Ölçü:** geri testte kolon sayısındaki %22'nin ne kadarı geri alınıyor.
**Durma kuralı:** kolon farkında hafta düzeyinde bootstrap aralığı sıfırı
kesiyorsa madde kapanır.

### F2 — Betfair Exchange: denenmemiş tek *fiyat*

`build_egitim.A2_KAYNAKLARI` bilerek `("B365C", "PSC", "MaxC", "AvgC")` —
BFE dışarıda ve gerekçesi kodda yazılı: *"BW/WH/BF/1XB/BFE eklenirse kesit
sezona göre dengesizleşir"* (`build_egitim.py:131`). Ama kupon kesitinde
`fiyatlar.py`'nin ölçtüğü tablo şunu diyor:

| fiyat | kapsama | marj | Brier |
|---|---:|---:|---:|
| Avg | %92 | %7,99 | 0,5515 |
| Pinnacle | %40 | %3,73 | 0,5522 |
| **Betfair Exchange** | **%94** | **%0,71** | **0,5508** |

A2'de yalnızca B365 ve PS denendi; **BFE hiçbir zaman arenaya girmedi** ve
marjı bir büyüklük mertebesi düşük — yani gerçek olasılığa en yakın fiyat.
Denenmemiş olan bir model değil, **bir fiyattır**.

BFE'nin tam olduğu sezonlarla sınırlı bir kesit kurulur, `arena.roster`'a
`b_BFE` eklenir ve **0.3'ün Holm düzeltmesiyle** ölçülür. Geçse bile tek başına
bir ürün değildir: Faz S'nin **girdisini** iyileştirir.

### F3 — Seçim koşullu kalibrasyonu seçime bağla (§3.49)

§3.49 ters seçimi ölçtü ve **yüksek eşikte gerçek** buldu: seçtiğimiz yerde
piyasa ortalamadan kötü kalibre. Bu bugün yalnızca bir **rapordur** —
`secim_kalibrasyonu.py`'nin düzeltmesi `secim`in girdisine uygulanmıyor.
Uygulanır; `P(k≤2)` ve S2'nin para sayıları üzerindeki etkisi ölçülür.
**Durma kuralı:** S3(b) ile aynı ölçüt.

---

## 7. Hafta 8 — Faz D: karar defteri, haftalık koşum, belge

### D1 — Tek komutluk haftalık döngü

Canlı hafta bugün dört script'e dağılmış (`super_toto_hafta.py`,
`super_toto_tahmin2.py`, `super_toto_degerlendir.py`, `super_toto_sezon.py`).
`scripts/hafta_kos.py` iki alt komuta indirir:

- `--oncesi`: bülten + oran + oynanma payı → kupon → **dondurulmuş** kayıt
- `--sonrasi`: sonuç + ikramiye tablosu → karne → defter

Kayıt donduğu an `kosum.py` defterine girer ve sonradan düzeltilemez — karne
ancak böyle dürüst kalır.

### D2 — `docs/KAZANMA_KARNESI.md` — asıl "eğitim" döngüsü

Her hafta tek satır: öngörülen `P(k≤2)` ve `E[TL]` ↔ gerçekleşen kademe ve TL;
kümülatif net; %95 aralık; kalabalık modelinin o haftaki öngörüsü ↔ gözlenen
kazanan adetleri.

**Model kendi hatasından burada öğrenir:** K2'nin `λ, δ, h` parametreleri her
hafta yeniden kestirilir ve **kayması izlenir**. Kayıyorsa kalabalık zamanla
değişiyor demektir — bu da bir bulgudur ve yazılır.

### D3 — Belgeye ve grafa yaz

- `ISTATISTIK_YOL_HARITASI.md` §3'e Faz K ve Faz S'nin gerekçeli yazımı.
- §5.1 tablosuna yeni satırlar; §6.5'in 2. ve 3. soruları **cevaplanır**.
- `.claude/olcum_kutugu.json`'a her sayının koşumu; `graf_sorgu.py tazelik`
  temiz döner.

---

## 8. Sekiz hafta boyunca, paralel: canlı kayıt

Her hafta elle girilen: bülten + iddaa oranları + **oynanma payları** + sonuç +
ikramiye tablosu. `n` **4 → 12** olur.

Bu, planın **satın alınamayan** tek parçasıdır ve iki iş görür: örneklemi
büyütür, ve 2026/27 kesitini Faz K/S için **tamamen dokunulmamış** bir doğrulama
seti olarak tutar — geçmiş 112 hafta üzerinde kestirilen model, hiç görmediği 12
haftada sınanır.

---

## 9. Dokunulacak dosyalar

| Faz | Dosya | İş |
|---|---|---|
| 0.1 | `spor_toto/getiri.py` · `scripts/kademe_analizi.py` | kolon bedeli tek kaynak + para sayılarının yeniden ölçümü |
| 0.2 | `spor_toto/havuz.py` · `scripts/kademe_analizi.py` · `tests/test_havuz.py` | `anormal_haftalar` → `data_quality` kapısı |
| 0.3 | `spor_toto/evaluate.py` · `spor_toto/arena.py` · `spor_toto/tahmin.py` | Holm/BH + `denenen_aday_sayisi` |
| 0.3 | `spor_toto/tahmin.py` · `scripts/build_fixtures.py` | H1/H2 — saat filtresi ve UTC |
| K | **`spor_toto/kalabalik.py`** *(yeni)* · `spor_toto/getiri.py` | kalabalık modeli + `"olculen"` |
| K | `spor_toto/artefakt.py` · `spor_toto/kosum.py` | parametre sürümleme + koşum defteri |
| S | `spor_toto/secim.py` | `getiri_secim` — Pareto DP'ye `E[TL]` boyutu |
| S | `spor_toto/backtest.py` · `scripts/kademe_analizi.py` | 112 hafta gerçek parayla geri test + bütçe eğrisi |
| F1 | `spor_toto/cizgi.py` · `spor_toto/egitim.py` | kapanış öngörüsü |
| F2 | `scripts/build_egitim.py` · `spor_toto/arena.py` · `spor_toto/fiyatlar.py` | `b_BFE` |
| F3 | `spor_toto/secim_kalibrasyonu.py` · `spor_toto/secim.py` | düzeltmeyi seçime bağla |
| D | **`scripts/hafta_kos.py`** *(yeni)* · **`docs/KAZANMA_KARNESI.md`** *(yeni)* | haftalık döngü + karne |

---

## 10. Çalıştırma ve doğrulama

Her fazın sonunda, sırayla:

```bash
bash scripts/check.sh                        # 13 adımlik tek kalite kapisi
python -m spor_toto.health                   # 27 degismez
python -m spor_toto.kalabalik --capraz       # K4 sezon disarida birakmali CV
python scripts/kademe_analizi.py --bolum C   # kademe: model diyor / gozlenen
python -m spor_toto.secim --kiyas            # en_iyi_secim <-> getiri_secim
python scripts/faz_b.py                      # elde ne var, durma kurali neresi
python -m spor_toto.arena                    # butun aileler tek tabloda (~10 dk)
python3 .claude/graf_sorgu.py tazelik        # bayat sayi kaldi mi
```

**Uçtan uca kabul.** `hafta_kos.py --oncesi` ile kurulan kupon, hafta bitince
`hafta_kos.py --sonrasi` ile karnesini alır ve `KAZANMA_KARNESI.md`'ye tek satır
ekler; öngörülen ile gerçekleşen yan yana durur.

---

## 11. Riskler ve şimdiden kabul edilenler

1. **K4 geçmeyebilir.** Kalabalık modeli kazanan adetlerini varsayım
   modellerinden iyi üretemezse havuz ekseni daralır. Plan bunu bugünden
   yazıyor; sonucu görünce hedef değiştirilmez.
2. **112 hafta, para kuyruğu ağır.** Kalabalık *kestirimi* için 448 gözlem
   boldur; ama para geri testi hâlâ 112 haftadır ve toplam kârın %34–55'i üç
   haftadan geliyor (`KADEME` §5.3-1). S3(c) — en iyi 5 hafta çıkarılınca hâlâ
   pozitif — tam bu yüzden kuralın içinde.
3. **Bedel çözüldü, ama tabloyu 6,67 kat küçültüyor.** ₺10 teyitli; yayımlanmış
   her para sayısı hâlâ ₺1,50 ölçeğindedir ve **yeniden ölçülene kadar
   okunmamalıdır** (Faz 0.1). Beklenen sonuç: §5.3'ün *"%100 üstü"* okuması
   hiçbir bütçede ayakta kalmıyor.
4. **Ölçülen kupon, oynanan kupon olmayabilir.** Motor yalnızca **14-garanti**
   üretir (`core.py` yarıçap 1'e kilitli: *"Toplam hata bütçesi 1 olduğu için
   yalnızca TEK bir alt küme r=1 olabilir"*); kullanıcı 13-garantiyi **başka bir
   yerden** oynuyor (karar: 2026-09-04). Faz S'nin `E[TL]`si bu yüzden
   **motorun kuponunu** tarif eder. Plan buna dokunmuyor, ama karne yazılırken
   ayrım not düşülür — yoksa ölçüm oynanmayan bir ürünü övüyor olur.
5. **Oynanma payı bir vekildir.** Tek platformun kullanıcıları. K5 bunu ölçer
   ama **kaldıramaz**; kaldırılamayan sınır olarak yazılı kalır.
6. **Piyasa oranı ≠ iddaa oranı.** Seviye tutmaz, yapı tutar (marj %7,26 ↔
   %17,2). Faz S'nin para sayıları piyasa oranından türer. İddaa ekseninin
   kalibrasyonu **45 kupon haftası** ister (§3.22) ve bu planda **kapanmaz**,
   yalnızca birikir.
7. **Kendi oynamamızın havuzu etkilemesi modellenmiyor** (`KADEME` §9). 1.000–
   3.000 TL bandında geçerli bir varsayımdır; eğrinin üst ucunda (30.000 TL+)
   tartışmalıdır ve orada işaretlenir.

---

## 12. Yapılmayacaklar

| Fikir | Neden hayır |
|---|---|
| Yeni model ailesi aramak | On bir ölçüm var ve tavan ölçüldü (§3.23). F2 bir model değil bir **fiyattır** |
| Kaplama ekseni | Hamming(7,4) mükemmel kod; optimallik kanıtlı. Bir optimum yenilemez |
| **Yarıçap-2 kaplama kodu ÜRETMEK** | Gerekmiyor: 13-garanti ST EXTRA'da oynanıyor ve fiyat tablosu bedeli zaten veriyor (§3.0). Motorun işi kolon üretmek değil **şekle karar vermek**; sütun üretimini satıcı yapıyor. `core.py` yarıçap 1'de kalır |
| Arayüz / uygulama / güvenlik | Bu planın kapsamı dışı. Tek istisna 0.3'ün H1/H2'sidir, çünkü **canlı karneyi kirletiyor** |
| Ölçülmemiş bir üstünlüğü karneye ya da arayüze yazmak | Doktrinin değişmeyen kuralı. Süslenmiş bir olasılık, süslenmemiş bir yalandır |
| Otomatik erişime kapalı kaynaktan veri çekmek | Hukuki; §7'de tek tek denetlendi ve bu planda değişmedi |
