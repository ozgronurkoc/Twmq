# Dış ufuk taraması — depo dışındaki her fikrin buradaki fiyatı

> **Bu belge bir literatür özeti değil, bir FİYAT LİSTESİDİR.** Sahibi
> 2026-09-13'te şunu istedi: *"vizyonu bu depoyla kısıtlama; profesörlerin
> makalelerine bak, gerekirse kuantum fiziğinden yararlan."* İstek yerinde ve
> bu belge onun cevabı — ama cevabın biçimi önemli: dışarıdan gelen her fikir
> burada **hedefin para biriminde** (üç ayda 15/15 olasılığının puanı)
> fiyatlanır. Fiyatlanamayan fikir bu belgeye girmez.
>
> Sıra kuralı değişmedi: **çalışan ölçüm > kod > belge > graf.** Aşağıdaki
> dış kaynaklar *belge* mertebesindedir; onları buradaki *ölçümler* yener.

---

## 1. Neden fiyat listesi, neden fikir listesi değil

Fikir listesi sonsuzdur. Bu problemde fikirlerin hepsini birden sınırlayan
**iki tavan** var ve ikisi de bu oturumda ölçüldü:

| tavan | ne sınırlar | ölçülen |
|---|---|---:|
| **Kombinatorik tavan** | her arama, her algoritma, her donanım | **%79,6** |
| **Bugünkü plan** (81 kupon) | — | **%77,0** |

Üretici: `cd backend && python scripts/ufuk_kiyasi.py --butce 21000 --serbest`
(114 tam hafta, 8 ayrık 13 haftalık pencere, 21.000 kolon).

Tavanın niçin tavan olduğu bir cümlelik bir teoremdir: **15/15 olayları
ayrıktır** — bir haftada tam olarak bir kolon tutar — dolayısıyla oynanan
kümenin `P(en az bir)` değeri, kolonların olasılıklarının **toplamıdır**. `N`
kolonluk bir kümenin toplamı ise en olası `N` kolonun toplamını geçemez.
Yani "en iyi `N` kolon"u bulmak NP-zor bir arama değil, bir **sıralamadır**;
zor olan onu Spor Toto'nun kupon biçimine (Kartezyen kutular) sığdırmaktır.

Bunun pratik sonucu sert: **bütün kombinatorik iş, geriye 2,6 puan
bırakıyor** ve onun 1,8 puanı yeni bir fikir değil, sadece 81 kupondan 729
kupona çıkmak (§3.73). Geriye kalan **0,8 puan**, dünyadaki bütün arama
algoritmalarının, ILP çözücülerinin ve kuantum tavlayıcılarının **toplam**
payıdır.

---

## 2. İkinci tavan: bilgi ekseninin fiyatı

Kombinatorik kapalıysa kalan tek eksen olasılıkların kendisidir. Onun da
parası ölçüldü — ve bu ölçüm bu oturumun asıl çıktısıdır.

`cd backend && python scripts/bilgi_esnekligi.py --butce 21000 --yayilmis`

### 2.1 Kesin bilgi — kaç maç bilirsek ne olur

| bilinen maç | `P(15)` hafta | **HEDEF** | kazanç |
|---:|---:|---:|---:|
| 0 (bugün, tavan) | %11,272 | **%79,6** | — |
| 1 | %20,244 | **%94,9** | **+15,3 p** |
| 2 | %33,962 | %99,6 | +20,0 p |
| 3 | %52,590 | %100,0 | +20,4 p |

Her satır bir **üst sınırdır**: kolon kümesi serbest, bilgi kesin, açılan
maçları kâhin seçiyor (en belirsiz olanı).

### 2.2 Yayılmış bilgi — "daha iyi model" ne kadar iyi olmalı

Kesin bilgi kurgudur; gerçek bir model bir maçı bilmez, **hepsinde biraz**
haklı çıkar. Aynı eğri o biçimde de ölçüldü (`λ` = her maça karıştırılan
gerçek payı):

| `λ` | Brier | Brier kazancı | **HEDEF** | kazanç | **1 puan için gereken Brier** |
|---:|---:|---:|---:|---:|---:|
| 0,00 | 0,5584 | — | %79,6 | — | — |
| 0,01 | 0,5473 | 0,0111 | %79,8 | +0,2 p | **0,047** |
| 0,02 | 0,5363 | 0,0221 | %80,1 | +0,5 p | 0,040 |
| 0,05 | 0,5040 | 0,0545 | %81,5 | +1,9 p | 0,028 |
| 0,10 | 0,4523 | 0,1061 | %85,0 | +5,4 p | 0,020 |

**Kilit satır sonuncu sütundur.** Hedefte **bir puan** kazanmak için Brier'i
**0,02 ile 0,047** arası iyileştirmek gerekiyor.

Şimdi bunu bu projenin ölçülmüş gerçeğiyle yan yana koyun:

| ölçülen | ΔBrier | hedefteki karşılığı |
|---|---:|---:|
| Projede piyasayı geçen **tek** tahminci (Betfair Exchange, §3.52) | −0,00100 | **≈ 0,02 puan** |
| Denenen 11 model ailesinin en iyisi dışındakiler | \|Δ\| < 0,0005 | < 0,01 puan |
| Piyasanın toplam kalibrasyon borcu (§3.23, **tavan**) | 0,00042 | ≈ 0,01 puan |

Yani: **projenin bugüne kadarki en iyi model bulgusu, hedefte binde iki
puan ediyor.** Ve §3.23'ün ölçtüğü kalibrasyon tavanı — yani mükemmel
kalibre edilmiş bir piyasanın bile bırakabileceği en büyük açık — hedefte
bir puanın yüzde biri.

---

## 3. Dışarıdaki literatür — ne buldum, burada ne ediyor

Aşağıdaki her satır gerçekten okundu ve buradaki fiyatıyla yazıldı.

### 3.1 "Football pool problem" — bu problem literatürde **isimli**

Spor Toto'nun matematiksel çekirdeği kodlama kuramında kendi adıyla anılan
açık bir problemdir: `K₃(n,1)`, yani uzunluğu `n` olan üçlü alfabede kaplama
yarıçapı 1 olan en küçük kod. En küçük çözülmemiş hâli **63 ≤ K₃(6,1) ≤ 73**;
dokuz maç için en iyi bilinen üst sınır 1269'a ancak 2003'te indi. Yani bu,
sahibinin "milenyum problemi" benzetmesinin karşılığı olan **gerçek** yer.

**Buradaki fiyatı: sıfır.** Çünkü o problem *"en az kolonla 14 garanti"*
sorusunu çözer ve bu proje o soruyu **ölçerek terk etti**
(`docs/DUZ_SISTEME_GECIS.md`): aynı kolon bütçesiyle en çok para/olasılık
sorulduğunda kaplama kaybediyor, çünkü "en az yedi çifte" şartı şekli bozuyor.
Optimal cevap, yanlış soruya verilmişti. Bugünkü soru — *"`N` kolonla en büyük
`P(15/15)`"* — yukarıda gösterildiği gibi **sıralamayla** çözülüyor.

Kalan gerçek kombinatorik soru şudur ve adı da vardır: en olası `N` kolonu
**en az sayıda Kartezyen kutuyla** örtmek (rectangle/box cover; genel hâli
NP-zor, `O(log n)` yaklaşımları var). Bu depoda o iş §3.75'te yapıldı (grup
birleştirme, fixpoint'e kadar) ve bütçesi yukarıda: **0,8 puan**.

### 3.2 Çoklu kupon ve **entropi** — dışarıdan gelen en ciddi itiraz, ve niçin geçmiyor

*Entropy-Based Strategies for Multi-Bracket Pools* (arXiv 2308.14339),
müşterek havuzlara **birden çok kupon** yatırmanın teorisini kuruyor ve şunu
söylüyor: optimal `n`-kupon portföyü **en olası `n` sonuç değildir**; `n`
büyüdükçe portföyün *entropisini* artırmak gerekir (asimptotik eşbölüşüm
özelliği — gerçek sonuç tipik kümede yatar, uç kümede değil).

Bu, bu projenin bütün arama gövdesine doğrudan bir itirazdır. **Geçmiyor, ve
sebebi tek cümle:** o sonuç **kısmi puanlı ve göreli** bir yarışma içindir
(bracket skoru, rakiplerin en iyisini geçmek). Bizim hedefimiz **mutlak ve
ya hep ya hiç**: 15/15. Ya hep ya hiçte olaylar ayrıktır, `P(∪) = Σ p` olur
ve toplamı en büyüten küme **tanım gereği** en olası `N` kolondur. Entropi
ödünleşmesi doğar ama başka bir hedefte doğar.

**Yeniden açılma şartı — şimdiden yazılı:** hedef "15/15 olasılığı"ndan
"beklenen para"ya çevrilirse entropi sonucu **anında geçerli olur**, çünkü o
zaman havuz seyrelmesi devreye girer (tuttuğunuz hafta herkesin tuttuğu
haftadır: `KADEME_OLASILIKLARI.md` §6, Spearman = −0,843). Sahibi kâr/zararı
açıkça ölçüt saymadığı için bugün geçerli değil.

### 3.3 Piyasayı yenmek — dışarısı bizimle aynı yere varıyor

* **Sistematik derleme** (arXiv 2410.21484, makine öğrenmesi ve spor bahsi):
  tutarlı biçimde piyasayı geçen bir stratejinin gösterilebilmiş olmadığı
  sonucuna varıyor.
* **Wilkens (2026)**, on bir Bundesliga sezonu, xG + Skellam + izotonik
  kalibrasyon: **bahisçi oranları kalibrasyonda daha iyi**, ama model
  fiyatlara tam yansımamış bir sinyal yakalıyor ve simülasyonda ~%10 ROI
  üretiyor (en iyi fiyatlarla ~%15), kazancın hemen tamamı **ev sahibi**
  bahislerinden.
* **Düşük likidite** yazını: verimsizlik küçük liglerde ve niş pazarlarda
  daha uzun yaşıyor; Süper Lig'i içeren bir çalışma ise en iyi oranlarla bile
  komisyonu aşan bir getiri bulamıyor.

**Buradaki fiyatı.** Wilkens'ın bulgusu bu projeye **ROI olarak** çevrilemez
(müşterek bahis, sabit oranlı bahis değil) ama **Brier olarak** çevrilebilir
ve çeviri §2.2'de: kazanç Brier'de 0,001 mertebesindeyse hedefte **binde
birkaç puan**. Üstelik o çalışmanın kendi cümlesi, kalibrasyonda bahisçinin
önde olduğudur — ve `P(15/15)` kalibrasyondan beslenir, ROI'den değil.

> **Bu bir "okumadık" reddi değil.** Bu depo aynı aileyi on bir kez
> bağımsız denedi (§5.1) ve arayışın kapanışını üç kez sınadı; dışarıdaki
> literatür dördüncü bağımsız teyit. Yeni olan şey, **reddin fiyatının**
> artık yazılı olması.

### 3.4 Kuantum — dürüst cevap

Sahibi açıkça sordu, o yüzden açıkça cevaplanıyor.

Kuantum tavlama (D-Wave) küme örtme ailesi için gerçekten çalışılıyor:
eşitsizlik kısıtlarını taşıyan QUBO/HUBO formülasyonları standart yaklaşımı
geçiyor, ve bugünkü Advantage makineleri **~400 küme (değişken)**
mertebesinde problemleri çözebiliyor; daha büyüğü ayrıştırma teknikleriyle.
2025'te spin camlarının dinamiğinde bir üstünlük gösterimi de yapıldı.

**Buradaki fiyatı: en fazla 0,8 puan, ve gerçekçi olarak sıfır.** Üç sebep,
sırayla:

1. **Tavan zaten ölçüldü.** Kombinatorik eksenin tamamı 2,6 puan ve 1,8'i
   kuponu artırmakla alınıyor. Kuantumun oynayabileceği yer kalan **0,8
   puan** — bir kuantum bilgisayarın *mükemmel* çözdüğü varsayımıyla.
2. **Klasik taraf zaten tavanın %97,9'unda.** Açgözlü sırt çantası (§3.71)
   bu işi hafta başına 0,38 saniyede yapıyor. Kuantum tavlamanın yenmesi
   gereken şey "NP-zor bir problem" değil, **%97,9'luk bir çözüm**.
3. **Ölçek uymuyor.** Bizim örtme problemimiz `3¹⁵ = 14,3 milyon` nokta
   üzerinde; bugünkü donanımın rahat çalıştığı mertebe yüzlerce değişken.

**Yeniden açılma şartı — şimdiden yazılı:** kuantum ekseni ancak (a) operasyon
729 kuponu kaldırabilir hâle gelir **ve** (b) kalan 0,8 puanın en az yarısını
alan klasik bir yöntem bulunamazsa açılır. İkisi birden olmadan bu eksen
maliyetinin karşılığını veremez.

### 3.5 Veri kaynakları — dışarıda ne var, hangisi denenmedi

| kaynak | durum | buradaki fiyatı |
|---|---|---|
| Understat xG | **kapalı** — `robots.txt` tam yasak, üstelik Süper Lig yok | — |
| FBref | **kapalı** — Cloudflare | — |
| Kadro/sakatlık | **geçersiz** — kupon kapanırken kadro yok (eğitim/servis ayrışması, §3.36) | — |
| UEFA fikstürü, kulüp–şehir | **alındı ve ölçüldü** (§3.36), ikisi de geçmedi | ölçüldü |
| Betfair Exchange | **alındı, GEÇTİ** (§3.52) — ΔBrier −0,00100 | **≈ 0,02 puan** |
| **FootyStats** (Süper Lig xG, CSV/API) | **DENENMEDİ** — tek açık kapı | beklenen ≈ 0,0x puan |
| İç kupalar (Türkiye Kupası vb.) fikstürü | **DENENMEDİ** | beklenen ≈ 0 |

**Denenmedi ile denenemez ayrımı korunuyor** (A3'ün kuralı). FootyStats
gerçekten denenmemiş tek kaynak ve Süper Lig kapsaması var — ama beklenen
değeri §2.2'nin çeviri oranıyla peşinen biliniyor: Betfair kadar iyi çıksa
bile hedefte **binde iki puan**.

---

## 4. Fiyat listesi — her şeyin yan yana hâli

Aşağıdaki tablo bu belgenin tamamıdır. Sütun, **üç ayda 15/15 olasılığına**
eklenen puandır.

| iş | puan | durum |
|---|---:|---|
| Haftada **1 maçı kesin bilmek** | **+15,3** | kurgu — meşru karşılığı yok (§2.1), suç olanı aranmaz |
| **81 → 729 kupon** | **+1,8** | **açık ve gerçek** — engel operasyon (458,7 slip, §3.75) |
| 81 → 243 kupon | +1,1 | açık, ara adım (162,6 slip) |
| Kalan **bütün** kombinatorik (algoritma, ILP, kuantum) | **+0,8** | araştırma; klasik taraf zaten %97,9'da |
| Projenin en iyi model bulgusu kadar bir yenisi (ΔBrier 0,001) | **+0,02** | ölçülü kapalı |
| Piyasanın kalibrasyon borcunun tamamı (§3.23 tavanı) | **+0,01** | tavan, ulaşılamaz |

**Bu tablonun okunuşu tek cümledir:** hedefe giden yolda kalan tek **gerçek**
kaldıraç matematik değil **operasyon** — haftada kaç kupon fiilen
yatırılabildiği. Geri kalan her şey, dünyadaki bütün literatür ve bütün
donanım dâhil, birinci ondalığın altında.

---

## 5. Bunun kabul etmediği iki okuma

**"Demek ki proje bitti."** Hayır. Tablo hedefin **%79,6'da tavanlandığını**
söylüyor, %100'de değil — ve bugün %77,0'deyiz. Aradaki 2,6 puanın 1,8'i
alınabilir durumda. Bitmiş olan şey *arayışın bir kolu*, hedef değil.

**"Demek ki daha iyi model aramak boşuna."** Bu da hayır, ama gerekçesi
değişti: boşuna olduğu için değil, **fiyatı belli olduğu için**. Bir model
işi ancak Brier'i 0,02 mertebesinde oynatma ihtimali varsa bu hedefe hizmet
eder — yani bugüne kadar ölçülen en iyi bulgunun **yirmi katı**. Böyle bir
iddiayla gelen her fikir sınanır; gelmeyen fikir sıraya girmez.

---

## 6. Durma kuralları — ölçüm görülmeden yazıldı

1. **Kombinatorik eksen**, `ufuk_kiyasi.py --serbest` tavanı ile plan
   arasındaki fark **1 puanın altına** indiğinde kapanır. Bugün 81 kuponda
   2,6; 729 kuponda **0,8** — yani 729'a çıkıldığı anda eksen **kapanır**.
2. **Model ekseni**, bir aday ΔBrier ≥ 0,02 iddiasıyla gelmedikçe açılmaz.
   Açılırsa ölçüt projenin geri kalanıyla aynı: sezon dışarıda bırakmalı,
   hafta eşleştirmeli bootstrap, %95 aralık tamamen sıfırın bir yanında.
3. **Kuantum ekseni** §3.4'teki iki şart birlikte gerçekleşmeden açılmaz.
4. **Bilgi ekseni** (§2.1) yalnız meşru ve **kupon kapanmadan önce** var olan
   bir kaynak bulunursa açılır. Bugün böyle bir kaynak yok.

---

## 7. Kaynaklar

* [An improved upper bound for the football pool problem for nine matches](https://www.sciencedirect.com/science/article/pii/S0097316503000104) — `K₃(9,1) ≤ 1269`
* [A new lower bound for the football pool problem for 7 matches](https://www.numdam.org/item/JTNB_1996__8_2_481_0.pdf)
* [Entropy-Based Strategies for Multi-Bracket Pools](https://arxiv.org/pdf/2308.14339) — çoklu kupon + entropi
* [A Systematic Review of Machine Learning in Sports Betting](https://arxiv.org/pdf/2410.21484)
* [Wilkens (2026), Can simple models predict football — and beat the odds? Lessons from the German Bundesliga](https://journals.sagepub.com/doi/10.1177/22150218261416681)
* [Are Betting Markets Inefficient? Evidence From Simulations and Real Data](https://journals.sagepub.com/doi/10.1177/15270025231204997)
* [Quantum annealing with inequality constraints: the set cover problem](https://arxiv.org/pdf/2302.11185)
* [Benchmarking Advantage and D-Wave 2000Q quantum annealers with exact cover problems](https://arxiv.org/pdf/2105.02208)
* [Close Approximations of Minimum Rectangular Coverings](https://link.springer.com/article/10.1023/A:1009879504783) — kutu örtme
* [Pari-Mutuel Betting Markets: Racetracks and Lotteries Revisited](https://www.annualreviews.org/content/journals/10.1146/annurev-financial-053122-021925)
* [FootyStats — Türkiye Süper Lig xG](https://footystats.org/turkey/super-lig/xg) — denenmemiş tek kaynak
