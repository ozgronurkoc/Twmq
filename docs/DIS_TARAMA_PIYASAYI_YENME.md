# Dış tarama — "piyasayı yenmenin yolu" var mı?

**Kapsam:** Depo dışındaki literatürün bu oyuna dair *ne* söylediği, hangi
iddianın bu depoda **denenmediği**, ve denenmemiş olanların bu oturumda
ölçülmesi.
**Tarih:** 2026-09-05 · HEAD `6871b36`
**İlgili belgeler:** [`DIS_INCELEME.md`](DIS_INCELEME.md) ·
[`DIS_INCELEME_ALPHAPY.md`](DIS_INCELEME_ALPHAPY.md) ·
[`DIS_INCELEME_SPORTS_BETTING.md`](DIS_INCELEME_SPORTS_BETTING.md) (aynı türün
ilk üçü) · [`KADEME_OLASILIKLARI.md`](KADEME_OLASILIKLARI.md) §6–§7 ·
[`KAZANMA_PLANI.md`](KAZANMA_PLANI.md) "Faz B" · `README.md` §1.1

> **Künye — dış sayılar bizim ölçümümüz değildir.** Aşağıda başkalarının
> yayımladığı her sayı **kaynağıyla** verilir ve bizim "geçti" ölçütümüzü
> (güven aralığının tamamı sıfırın dışında) kullanmaz. Değeri **teyit**tir.
> Buna karşılık §4 ve §5'teki sayılar **bizim ölçümümüzdür**, bu depoda ve
> tek komutla yeniden üretilir:
>
> ```bash
> cd backend && python scripts/devir_tavani.py
> ```

---

## 1. Önce sorunun kendisi: "15 bilmek" ölçülebilir bir hedef değil

Bu taramanın çıkış sorusu *"15 bilmenin yolunu bul"*du. Depo bu soruyu daha
önce ölçmüş ve cevabı [`KADEME_OLASILIKLARI.md`](KADEME_OLASILIKLARI.md)
§10'da duruyor: *"15/15 bir mühendislik problemi değil, bir piyangodur."*
114 haftalık gerçek veride modelin en iyi kolonu **hiç** 15 tutturmadı.

Buna sık gösterilen karşı kanıt 3. haftanın **14**'üdür. O kayıt bu depoda
var ve ne söylediği açıkça yazılı (`ISTATISTIK_YOL_HARITASI.md` §3.47):

* O 14'te **görüş yoktur** — sapma defteri **sıfır sapma** yazıyor, yani
  kupon mekanik azami kapsamanın birebir aynısıydı.
* Bugünkü kural geçen sezonun 36 haftasında koşulduğunda ortalama en iyi
  kolon **11,81**; haftaların %67'si 12+, yalnızca **%6'sı** 14+.

Yani 14, bir yeteneğin kanıtı değil, ortalaması 11,81 olan bir dağılımın
**üst kuyruğudur**. Onu kanıt saymak, deponun kendi §3.48'de uyardığı
sağkalım yanlılığıdır. **Bu belge o yüzden "15" sorusunu değil, onun
ölçülebilir hâlini alır:** *bir kolonun beklenen getirisi 1'i geçebilir mi?*

---

## 2. Niçin bakıldı: içeride açık kalan tek eksen

Depo hedefi üç çarpımsal eksene ayırıyor (tahmin · havuz · kaplama) ve
ikisi ölçülerek kapandı:

| eksen | durum | sayı |
|---|---|---|
| Tahmin | **kapalı** | model ↔ piyasa farkı 0,0005–0,0015 Brier; iddaa marjı **%17,2** (README §1.1) |
| Sütun (hakem) | **kapalı** | yayılım saf şansın 0,97–1,00 katı — etki zayıf değil **yok** (§3.59) |
| Omurga fiyatı | **kapalı** | `Avg` kaldı; BFE farkının %81'i seçim hiç değişmeden geliyor (§3.58) |
| Hedef kademe | **kapalı** | 12 kaldı; şekli bütçe belirliyor (§3.57) |
| Kaplama | teorem | garanti kombinatoryaldir, olasılık onu değiştirmez (README §1.1) |
| **Havuz / kalabalık** | **AÇIK** | canlı ölçüldü: makul kısıtta kazanç **+0 TL**, `n = 3` (Faz B) |

Dış tarama bu yüzden kapanmış eksenlere değil, **havuz eksenine** ve
"denenmemiş bir şey var mı" sorusuna yapıldı.

---

## 3. Dışarıda ne var

Dört kaynak konuyla gerçekten ilgili çıktı. Üçü teyit, biri **rakip iddia**.

| # | Kaynak | Ne diyor | Bize karşılığı |
|---|---|---|---|
| K1 | Thaler & Ziemba, *Parimutuel Betting Markets*, JEP 2(2), 1988 | Müşterek havuzda pozitif BD **az oynanan** kombinasyonlardan doğar; piyangoda "en az sevilen" sayılar ortalamanın %15–30 altında oynanıyor ve devir varken BD 1$ başına ~2,25$'a kadar çıkıyor | Bizim `getiri.py` + `kalabalik.py` ekseninin **kuramsal atası**. Ama piyangoda olasılık **düzgün**; Spor Toto'da kalabalık orana bakıyor, o yüzden sapma çok daha küçük — §4 |
| K2 | Ziemba, *…Revisited*, Annu. Rev. Financ. Econ., 2021 | Aynı çerçeve, güncel: BD'nin üç bileşeni yazılıyor ve **devir** açıkça ayrı terim; profesyonel at yarışı sendikaları var ama "bu kolay değil" | Devir terimini bir *hipotez* olmaktan çıkarıp **hesaplanabilir** kılıyor — §4 |
| K3 | arXiv:2303.16648, *Beating the average* | **Birebir bizim oyunumuz**: Alman TOTO 13'lü Wette, müşterek havuz. "Tutarlı kâr" iddia ediyor; reçete tek cümle — ev sahibi galibiyeti en sık sonuçtur, hep `1` işaretle (Bundesliga'da %50,4) | Taramanın bulduğu **tek** rakip iddia. Korpusumuzda koşuldu — §5 |
| K4 | Wilkens, *Can simple models predict football…*, J. Sports Analytics, 2026 | xG + Skellam + izotonik kalibrasyon, 11 Bundesliga sezonu: ortalama oranla ~%10, en iyi fiyatla ~%15 ROI; kâr **yalnızca ev galibiyeti** bahislerinden | **Sabit oranlı** piyasada, hat alışverişiyle. Kupona taşınmaz (§6). Ayrıca deponun xG vekili ölçüldü ve piyasayı geçmedi (§3.42) |

Taramanın **bulamadığı** şey de bir bulgudur: müşterek bir futbol havuzunda
işaret seçimiyle sürdürülebilir kâr gösteren, hakemli ve tekrarlanmış bir
çalışma yok. K3 bunu iddia eden tek çalışmadır ve §5'te düşüyor.

---

## 4. Ölçüm 1 — devir tavanı: literatürün koşulu, deponun verisi

**Yeni olan bu.** K1/K2'nin koşulu (*"pozitif BD dışarıdan giren parayı
ister; o para devirdir"*) bu depoda bir **istatistik sorusu** gibi
kurulmuştu — `kademe_analizi.py` bölüm G, devirli/normal ikili ayrımı, 25
hafta, sonuç *"tutarlı bir yön YOK"*. Oysa aritmetik kapalı biçimde çözülür.

### 4.1 Özdeşlik

Bir haftada kolon başına geri dönüş `dağıtılan_toplam / (N × bedel)`'dir.
`dagitilan` haftanın **kendi** payıdır ve hasılatın sabit bir oranıdır
(`odeme_orani × N × bedel`); `devir_gelen` ise havuza bilet karşılığı
olmadan giren paradır. Yerine koyunca:

```
getiri = odeme_orani × (1 + devir_gelen / dagitilan) = odeme_orani × (1 + d)
```

`odeme_orani` düzenlemeyle sabit olduğuna göre **haftaları birbirinden
ayıran tek çarpan `(1 + d)`'dir** ve pozitif BD'nin koşulu tek bir
eşitsizliktir:

```
1 + d  >  1 / odeme_orani
```

`d`'nin paydası `dagitilan`dır ve jackpot haftası kalabalıklaştığında o da
büyür — yani `d` hacim artışına karşı **kendiliğinden normalizedir**. Ölçüm
bu yüzden *"devirli hafta zaten daha çok oynanıyor"* itirazına bağışıktır.

### 4.2 Ölçülen

`spor_toto.havuz` devir zincirini altı sezon boyunca zaten geri hesaplıyor
(222 hafta, zincirin gelen ÷ giden oranı ortanca 1,000). Onun üstünde:

| | |
|---|---:|
| havuzu hesaplanabilen hafta | **222** |
| devir **alan** hafta | 41 (%18,5) |
| çarpan `1+d` — medyan | 1,000 |
| p90 / p95 | 1,252 / 1,319 |
| **azami (altı sezon)** | **1,645** |

En büyük beş: `2025_26` hf34 **1,645** · hf10 1,407 · `2023_24` hf27 1,403 ·
`2024_25` hf49 1,378 · `2025_26` hf26 1,368.

`odeme_orani` arşivden doğrudan okunamaz — veri brüt hasılatı taşımıyor
(`VERI_TOPLAMA_VE_ISLEME.md` §10.1) ve doktrin 2 gereği uydurulmaz. Ama
geriye doğru ima edilir: `KADEME_OLASILIKLARI.md` §5.2 ölçülmüş ortalama
getiriyi ₺10 ölçeğinde **%37–%54** bandında veriyor ve
`odeme_orani = ortalama_getiri / ortalama(1+d)`. Band olduğu için sonuç da
band bırakılır:

| ölçülen ort. getiri | ima edilen ödeme oranı | **gereken `1+d`** | en iyi haftanın getirisi | ulaşıldı mı |
|---:|---:|---:|---:|---|
| %37 | %35,2 | **2,84** | %57,9 | **HAYIR** |
| %54 | %51,4 | **1,95** | %84,5 | **HAYIR** |

### 4.3 Ne çıkıyor

**Altı sezonun en büyük devri bile eşiğin altında.** Pozitif BD için gereken
çarpan 1,95–2,84; 222 haftanın azamisi 1,645. Yani devir haftasında oynamak
getiriyi ölçülebilir biçimde **büyütür** (en iyi haftada %57,9–%84,5, normal
haftada %35,2–%51,4) ama **hiçbir hafta 1'i geçmez**.

Bu, deponun bugünkü *"25 haftada gürültü baskın, ölçülemez"* satırını
değiştirir: eksen **ölçülemedi değil, hesaplandı ve yetmiyor**. Ve
yetmemesinin sebebi örneklem değil **yapı** — devirin büyüklüğünü Spor
Toto'nun bölüşüm kuralı sınırlıyor, `n` biriktirmek bunu değiştirmez.

> **Sınır — bu ölçüm neyi kanıtlamaz.** `odeme_orani` ölçülmedi, ima edildi;
> bandın kendisi §5.2'nin kesitine bağlı. Ve sayı **ortalama** kolon
> içindir: beceri ortalamanın üstüne çıkabilir, aşağıdaki §6 tam olarak
> onu soruyor. "Hiçbir hafta pozitif değildir" değil, **"hiçbir hafta
> kendiliğinden pozitif değildir"** okunmalıdır.

---

## 5. Ölçüm 2 — "hep ev sahibi" kuralı korpusta düşüyor

K3 taramanın bulduğu tek rakip iddiadır ve reçetesi tek cümledir: ev sahibi
galibiyeti en sık sonuçtur, hep `1` işaretle. Makale isabet oranını
Bundesliga'da **%50,4** alıyor. Aynı kural bizim 31.103 maçlık korpusumuzda:

| kural | p | %95 aralık | E[doğru/15] | P(12+) | P(14+) |
|---|---:|---|---:|---:|---:|
| **hep ev** (makalenin kuralı) | **%43,37** | [%42,82, %43,92] | 6,50 | %0,438 | %0,0074 |
| piyasa favorisi | **%51,09** | [%50,54, %51,65] | 7,66 | %2,156 | %0,0649 |

Üç şey birden çıkıyor:

1. **Kuralın öncülü bu kesitte tutmuyor.** Ev oranı %50,4 değil **%43,4** ve
   aralık %50,4'ü içermiyor. Makalenin sayısı tek lige (Bundesliga) aittir;
   kuponun yarısı Süper Lig'den gelir ve korpus 22 lig taşır.
2. **Piyasa favorisi kuralı 7,7 puan geçiyor** ve P(12+)'yı 4,9 kata
   çıkarıyor. Yani kural piyasadan üstün değil, piyasadan **zayıf**.
3. **Kural ayrı bir eksen bile değil:** favorinin **%68,4'ü zaten ev
   sahibi**. "Hep ev" kuralı, favori kuralının bilgi atılmış hâlidir.

Ayrıca makale kendi sonuç bölümünde kârın *"çabayı sorgulatacak ölçüde
eridiğini"* yazıyor ve seyreltmeyi hiç modellemiyor — oysa
[`KADEME_OLASILIKLARI.md`](KADEME_OLASILIKLARI.md) §6 tam bunu ölçmüş:
**Spearman(sonucun beklenirliği, 15 bilen sayısı) = −0,843**. Herkesin
işaretlediği sonucu işaretlemek, tuttuğunda ikramiyenin en küçük olduğu
haftaya düşmek demektir (modelin en sevdiği bantta kişi başı 13.228 TL, en
sevmediği bantta 14,7 milyon TL — **1.100 kat**). "Hep ev" bu ölçeğin tam
olarak yanlış ucudur.

> **Sınır.** Yukarıdaki P(12+)/P(14+) sütunları maçlar arası
> **bağımsızlık** varsayar; bağımlılık ölçülmedi (§9). İki kuralı
> kıyaslamak için verildi, kupon isabeti ölçüsü olarak değil.

---

## 6. Gereken ↔ eldeki: açık tek sayıya iniyor

§4'ün özdeşliği, deponun bütün eksenlerini tek bir orana çeviriyor. Bir
kolonun pozitif BD'li olması için o kolonun **ortalama kolonun kaç katı**
ödeme alması gerektiği:

| durum | gereken kat |
|---|---:|
| normal hafta (`d = 0`) | **1,95 – 2,84** |
| altı sezonun en büyük devir haftası (`1+d = 1,645`) | **1,18 – 1,73** |

Buna karşılık **ölçülmüş** olarak elde ne var:

| kaynak | ölçülen kat | künye |
|---|---:|---|
| kalabalık ayarı — tavan, mükemmel eşzamanlı bilgiyle | **1,003×** (medyan, `n=3`) | `KAZANMA_PLANI.md` "düzeltilmiş tavan" |
| kalabalık ayarı — makul kısıtla, gerçekleşen ödülle | **1,000×** (+0 TL) | Faz B canlı |
| tahmin ekseni | 0,0005–0,0015 Brier | README §1.1 |

**Açık budur ve büyüklük mertebesi tartışılır değil: gereken ~2×, ölçülen
~1,003×.** Üstelik ikisi bağımsız da değil — §6'nın seyreltme ölçümü
(−0,843) tahminde kazanılanın bir kısmının ikramiyede geri verildiğini
söylüyor.

Dış literatürün bu tabloya kattığı tek şey, farkın **niçin** bu kadar büyük
olduğudur. K1'in piyangosunda kalabalık doğum günü seçer ve olasılık
düzgündür: sapma bedavadır, %15–30'luk oynanma farkı doğrudan BD'ye geçer.
Spor Toto'da kalabalık **oranı** izler. Bu yüzden `p/q` sapması piyangonun
mertebesinde değildir ve tavanın 1,003× çıkması bir kusur değil,
**kalabalığın iyi kalibre olmasının sonucudur.**

---

## 7. Ne kapandı, ne açık kaldı

| Eksen | Bu taramadan önce | Bu taramadan sonra |
|---|---|---|
| **Devir** | "25 haftada gürültü baskın, **ölçülemez**" (`KADEME_OLASILIKLARI` §7) | **Kapandı.** Hesaplandı: gereken 1,95–2,84, altı sezonun azamisi **1,645**. Yapısal, `n` ile açılmaz |
| **"Hep ev" / naif sabit kural** | denenmemişti | **Kapandı.** Korpusta %43,37; piyasa favorisi 7,7 puan üstün |
| **Havuz / kalabalık** | açık, `n = 3` | **Açık kaldı** — ve tek açık eksen o. Gereken kat §6'da yazılı artık |
| **Sabit oranlı piyasa** (K4) | kapsam dışı | **Kapsam dışı kalıyor** — ama gerekçesi artık ölçülü, §8 |

---

## 8. Yapılmayacaklar — ve niçin

| Fikir | Niçin hayır |
|---|---|
| K3'ün "hep ev" kuralını kupona almak | §5'te ölçüldü, piyasa favorisinden **zayıf** |
| K4'ün ROI'sini kupona taşımak | Farklı **enstrüman**. K4 sabit oranda, hat alışverişiyle ve yalnızca ev galibiyeti alt kümesinde kâr buluyor; kupon müşterek havuzdur ve orada ödeme kaç kişinin tutturduğuna bağlıdır. Aynı sayı burada geçerli değildir (`DIS_INCELEME.md` §6 ile aynı gerekçe) |
| Devir haftalarını beklemek için kupon kuralını değiştirmek | §4: en iyi devir haftası bile 1'in altında. Getiriyi büyütür, işaretini değiştirmez |
| K1'in "az oynanan sembol" reçetesini kısıtsız uygulamak | Denendi ve **ölçüldü**: kısıtsız `E[TL]` 2. haftada ödülü 1.439 TL → 0 TL yaptı (Faz B). `GETIRI_KAYIP_TAVANI` o yüzden var |
| Yeni model ailesi | On bir ölçüm + tavan (§3.23); K4 de dahil dışarıdaki hiçbir çalışma bu kesitte geçme ölçütümüzü karşılamıyor |

---

## 9. Bu belgenin ürettiği tek iş

Devir çarpanı `1+d` **karar anında bilinebilir** (devreden tutar kupon
açılmadan ilan edilir) ve §4 onun getiriyi %35 → %58–85 bandına taşıdığını
gösteriyor. İşareti değiştirmiyor ama **bütçe zamanlamasını** değiştirebilir:
aynı yıllık bütçeyi düz dağıtmak yerine yüksek `1+d` haftalarına yığmak,
beklenen kaybı ölçülebilir biçimde küçültür.

Bu bir kazanç iddiası **değildir** — 1'in altında kalan bir sayıyı daha az
kaybettiren hâline getirmektir, ve `KAZANMA_KARNESI.md`'nin `n`'i (bugün 3)
büyümeden karara bağlanmaz. Durma kuralı şimdiden yazılır: **yığma kuralı,
ancak `1+d ≥ 1,25` haftalarının gerçekleşen getirisi düz dağıtımı %95
aralığın tamamıyla geçerse** varsayılan olur.

---

## 10. Kaynaklar

1. Thaler, R. H. & Ziemba, W. T. (1988), *Anomalies: Parimutuel Betting
   Markets: Racetracks and Lotteries*, Journal of Economic Perspectives
   2(2), 161–174. <https://www.aeaweb.org/articles?id=10.1257/jep.2.2.161>
2. Ziemba, W. T. (2021), *Parimutuel Betting Markets: Racetracks and
   Lotteries Revisited*, Annual Review of Financial Economics.
   <https://researchonline.lse.ac.uk/id/eprint/120846/>
3. *Beating the average: how to generate profit by exploiting the
   inefficiencies of soccer betting*, arXiv:2303.16648.
   <https://arxiv.org/abs/2303.16648>
4. Wilkens, S. (2026), *Can simple models predict football — and beat the
   odds? Lessons from the German Bundesliga*, Journal of Sports Analytics.
   <https://journals.sagepub.com/doi/10.1177/22150218261416681>
5. Kéri, G., *Tables for bounds on covering codes* (futbol havuzu
   probleminin kombinatoryal tarafı; bu depoda kaplama bir teoremdir ve
   kolonları satıcı üretir, o yüzden yalnızca künye olarak anılır).
   <http://old.sztaki.hu/~keri/codes/>
