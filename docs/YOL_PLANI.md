# Baştan Sona Yol Planı — Proje Ne Zaman Biter

**Kapsam:** projenin tamamı — tahmin, havuz, kaplama, ürün
**Oluşturuldu:** 2026-08-17
**İlgili belgeler:** [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) (katman
düzeyi yol haritası) · [`VERI_TOPLAMA_VE_ISLEME.md`](VERI_TOPLAMA_VE_ISLEME.md) (veri
doktrini) · [`../README.md`](../README.md) (amaç ve vaat)

---

## 0. Bu belge neyi vaat ediyor

Bu, **sonlanan** bir plandır. Bitirildiğinde geriye yapılacak iş kalmaz.

Böyle bir şey ancak plan **özellikler** yerine **sorular** etrafında kurulursa mümkündür.
Özellik listesi sonsuzdur: her karta bir kart daha eklenebilir. Soru listesi sonludur:
hedefe ulaşılıp ulaşılamayacağını belirleyen soruların sayısı bellidir ve her birinin bir
gün ölçülmüş bir cevabı olur.

Bu yüzden buradaki her maddenin bir **durma kuralı** vardır ve durma kurallarının bir kısmı
şudur: *"cevap hayır çıktı, bu eksen kapandı, bir daha açılmayacak."* Yalnızca başarıyla
bitebilen bir plan, plan değil temennidir.

**Planın sonlanabileceği iki uç var ve ikisi de meşru:**

1. Ölçülmüş bir üstünlük bulunur, ürüne çevrilir, proje amacına ulaşır.
2. Her eksende üstünlük olmadığı **kanıtlanır** ve proje bunu belgeleyerek biter. Bu bir
   başarısızlık değildir — bu alandaki araçların neredeyse tamamı birinci ihtimali *iddia
   eder*, hiçbiri ikincisini ölçmez.

---

## 1. Hedefin ayrıştırılması — planın neden sonlu olduğu

Amaç "kazanma oranını artırmak". Bu tek bir şey değil, **çarpımsal üç etkendir**:

```
Beklenen getiri  =  P(tutturma)  ×  Pay(tutturunca)  −  Bedel
                    ─────────────    ───────────────     ──────
                    tahmin ekseni    havuz ekseni        kaplama ekseni
```

| Eksen | Ne belirler | Bugünkü durum |
|---|---|---|
| **Tahmin** | 14+ tutturma olasılığı | İki bağımsız denemede ~sıfır artık bulundu (§2) |
| **Havuz** | Tutturunca ikramiyenin kaçta kaçını aldığın | **Hiç ölçülmedi.** Veri bile yok |
| **Kaplama** | Aynı garanti için ödenen kolon | **Çözüldü** — Hamming, kanıtlanmış optimal |

Plan sonludur çünkü **etken sayısı üçtür**. Biri kapalı (çözülmüş), biri neredeyse kapalı,
biri hiç açılmamış. Üçü de bir cevaba bağlandığında yapacak iş kalmaz.

> **Kaplama ekseninde iş yok ve olmayacak.** `solve_fix16` Hamming(7,4) tabanlı ve
> kanıtlanmış optimaldir. Bir optimum yenilemez; buraya harcanacak her saat, cevabı önceden
> bilinen bir soruya harcanmış olur.

---

## 2. Bugün nerede duruyoruz — ölçülmüş her şey

| Ölçüm | Değer | Kaynak |
|---|---|---|
| Piyasa Brier (kupon, 540 maç) | **0,5747** | T1 |
| Piyasa Brier (korpus, 31.103 maç) | **0,5940** | T3 |
| Eşit dağıtım (zemin) | 0,6667 | matematiksel |
| Yeniden kalibrasyonun kazancı | **≤ 0,0005** Brier | T2, T3 |
| Takım formunun **artık** değeri | **~0** (katsayı −0,031) | T5 |
| Takım formunun **ham** sinyali | %60,7 ↔ %27,9 ev galibiyeti | T5 |
| Geri test hold-out | **0 hafta** | F1 |
| İddaa marjı | **%17,2** | F5 |
| Piyasa marjı | %7,26 | F5 |
| İkramiye / havuz | **veri yok** | — |

**Bu tablodan çıkan tek cümle:** piyasa 1X2 fiyatlarında bulduğumuz her artık, ölçüm
hatasıyla aynı büyüklükte. Buna karşılık aşmamız gereken marj %17,2. İki sayı arasında
iki büyüklük mertebesi fark var.

---

## 3. Faz A — Tahmin eksenini kapat ya da aç

**Amaç:** piyasanın 1X2 fiyatlarında sömürülebilir bir artık olup olmadığına **kesin** cevap
vermek. Bugünkü kanaat "yok" ama bu kanaat iki denemeye dayanıyor; kapatmak için daha
belirleyici deneyler gerekiyor.

Bu fazın bütün işleri **mevcut korpusla** yapılır. Yeni kaynak gerekmez.

### A1 — Kapanış çizgisi verimliliği (en belirleyici tek deney)

Bahis literatüründeki en güçlü tek sınama: **kapanış oranı, kendisinden önceki her şeyi
yener mi?** Korpus hem açılış (`Avg*`) hem kapanış (`AvgC*`) oranını taşıyor.

Ölçülecek: açılış → kapanış hareketi bilgi taşıyor mu, ve kapanışı yenen herhangi bir
tahminci var mı.

- **Neden belirleyici:** eğer kapanış çizgisi açılışı sistematik olarak yeniyorsa piyasa
  bilgiyi *soğuruyor* demektir; ve kapanışı hiçbir şey yenemiyorsa artık aramak boşunadır.
  Bu, tahmin ekseni hakkında tek deneyde en çok bilgi veren ölçümdür.
- **Durma kuralı:** kapanış açılışı anlamlı geçiyor **ve** hiçbir aday kapanışı geçemiyorsa
  → A2/A3 yine de koşulur (ucuzlar), sonra eksen kapanır.
- **Büyüklük:** küçük. Veri hazır, koşum hazır.

### A2 — Bahisçi anlaşmazlığı

Korpusta 12+ bahisçinin oranı var (`B365`, `PS`, `BW`, `BF`, …). Anlaşmazlığın büyük olduğu
maçlar, piyasanın kendi içinde emin olmadığı maçlardır.

Ölçülecek: bahisçiler arası dağılım (standart sapma) artık bir sinyal taşıyor mu — ortalama
fiyatın yanıldığı yerleri işaret ediyor mu.

- **Neden ayrı bir soru:** A1 "piyasa kolektif olarak doğru mu" diye sorar; A2 "kolektifin
  içindeki dağılım bilgi mi" diye sorar. İkisi bağımsız olarak yanlış çıkabilir.
- **Durma kuralı:** anlaşmazlık özelliği kademede kendi basamağını hak etmezse kapanır.
- **Büyüklük:** küçük.

### A3 — Piyasa dışı ama **türetilebilir** özellikler

**Burada bir hatayı düzeltiyorum.** `VERI_TOPLAMA_VE_ISLEME.md` §8.7'ye "veride piyasa dışı
hiçbir sinyal yok" yazmıştım. Bu doğru değil. Doğru olan şu: *ek kaynak gerektirmeyen* birkaç
özellik daha var ve hiçbiri denenmedi:

| Özellik | Nasıl türetilir | Neden aday |
|---|---|---|
| **Dinlenme günü** | Takımın bir önceki maçından geçen gün | Yorgunluk fiyatlanır ama tam mı? |
| **Fikstür sıkışıklığı** | Son 14 günde oynanan maç sayısı | Kupa/Avrupa yükü lig fiyatına tam yansımayabilir |
| **Seyahat** | Deplasman takımının lig değişimi / ülke | Kaba vekil ama sıfır maliyetli |
| **Derbi** | Aynı şehir/rekabet eşleşmeleri | Beraberlik oranı sapar mı? |
| **Sezon sonu bahis** | Tarih + lig konumu (küme düşme/şampiyonluk penceresi) | Motivasyon farkı; sezonun son %20'sinde |
| **Ev sahibi seri** | Evde/deplasmanda ayrı form | Form'u ayrıştırmak T5'te yapılmadı |

- **Neden T5'ten sonra hâlâ ümitli:** T5 formu tek bir birleşik özellik olarak denedi ve
  piyasanın onu fiyatladığını gösterdi. Bunlar farklı şeyler — özellikle **fikstür
  sıkışıklığı** ve **sezon sonu bahis**, piyasanın sistematik olarak eksik fiyatladığı
  bilinen adaylardır.
- **Dürüst beklenti:** büyük olasılıkla bunlar da fiyatlanmış. Ama ucuzlar ve denenmeden
  "piyasa dışı girdi yok" demek yanlış olur.
- **Durma kuralı:** her özellik kademede bir basamak olarak ölçülür; hiçbiri korpus içi
  sezon dışarıda bırakmalı ölçümde `piyasa`'yı geçemezse eksen kapanır.
- **Büyüklük:** orta. Özellik başına ~50 satır + test.

### A4 — Tahmin ekseninin durma kuralı

A1–A3 bittiğinde şu iki cümleden **biri** belgeye yazılır ve eksen kapanır:

> **(a)** *"31.103 maçta, sezon dışarıda bırakmalı ölçümde, şu özellik piyasayı şu kadar
> geçiyor: [sayı, güven aralığı]. Faz C'ye giriyor."*

> **(b)** *"31.103 maçta denenen N özelliğin hiçbiri piyasayı geçemedi. Tahmin ekseni
> kapalıdır. Bu bir kanaat değil, ölçümdür ve tekrar açılması için yeni bir **veri kaynağı**
> gerekir — yeni bir model değil."*

**(b) çıkarsa Faz A bir daha açılmaz.** Aynı veriyle yeni model denemek, aynı soruyu daha
yüksek sesle sormaktır.

---

## 4. Faz B — Havuz eksenini aç ve ölç

**Amaç:** projenin hiç dokunmadığı eksen. Ve muhtemelen **tek gerçek kaldıraç** — çünkü
piyasayı tahminde yenmeyi gerektirmez.

Spor Toto müşterek bahistir: ikramiye havuzdan kazananlara bölünür. Bu şu sonucu doğurur:

> Aynı olasılığa sahip iki sonuçtan **daha az oynananı** işaretlemek, tutturma olasılığını
> değiştirmeden **beklenen getiriyi artırır.**

14'ü 10.000 kişiyle paylaşmakla 12 kişiyle paylaşmak aynı şey değildir. Ve kalabalık
öngörülebilir davranır: favoriye yığılır. Projenin kendi verisi bunu zaten söylüyor — favori
567 maçın 311'inde tuttu (%54,9), yani kalabalığın gittiği yer maçların **yarısında yanlış**.

### B1 — İkramiye ve kazanan verisi

**Faz B'nin ön koşulu ve tek gerçek engeli.**

Gereken: hafta başına 13 ve 14 doğru için **kazanan adedi** ve **ödenen tutar**. Kaynak
Spor Toto'nun haftalık sonuç/ikramiye ilanlarıdır; erişilebilirliği ve biçimi **henüz
araştırılmadı.**

- **İlk iş bir fizibilite araştırması**, boru hattı değil. Veri yoksa Faz B'nin tamamı
  düşer ve bu da bir cevaptır.
- Doktrin aynen uygulanır: bulunamayan hafta boş bırakılır, tahmin edilmez.
- **Durma kuralı:** kaynak yoksa B2 vekille sınırlı kalır, B3 hiç ölçülemez ve bu belgeye
  yazılır.
- **Büyüklük:** araştırma küçük; boru hattı orta.

### B2 — Popülerlik modeli

Hangi kolonlar çok oynanıyor? Resmî veri gelene kadar bile **vekil** kurulabilir: favori
olasılığı → tahmini oynanma payı.

Ölçülecek: kalabalığın işaret dağılımı, favori ağırlığı, ve "herkesin aynı yere gittiği"
maçların profili.

- **B1 gelirse** vekil gerçek veriyle kalibre edilir — bu, projenin ilk gerçek *doğrulanmış*
  davranış modeli olur.
- **Büyüklük:** orta.

### B3 — Beklenen getiriye göre kupon kurma

**Kaplama katmanının ve havuz modelinin buluştuğu yer — ve projenin en özgün işi.**

Bugün motor şunu yapıyor: *verilen işaretler için en ucuz 14-garantili kaplama*. Faz B
sonrası sorabileceğimiz soru başka: *verilen olasılık vektörü ve popülerlik modeli için,
beklenen getiriyi maksimize eden işaret kümesi hangisi?*

Bu, "hangi maça kaç işaret" sorusunu ilk kez **ölçülmüş bir amaç fonksiyonuyla** cevaplar.
Ve dikkat: bu tahmin yapmak değildir — kalabalığın davranışını modellemektir.

- **Bağımlılık:** B1 + B2. Onlarsız amaç fonksiyonu yok.
- **Büyüklük:** büyük. Projenin en zor tek işi.

### B4 — Havuz ekseninin durma kuralı

> **(a)** *"Popülerlik modeli ve ikramiye verisiyle, şu strateji geçmiş sezonlarda pozitif
> beklenen getiri üretiyor: [sayı, güven aralığı, hold-out]. Faz C'ye giriyor."*

> **(b)** *"İkramiye verisi elde edilemedi"* — ya da — *"elde edildi ve %17,2 marj +
> havuz seyrelmesi, ölçülen popülerlik avantajını yutuyor. Havuz ekseni kapalıdır."*

---

## 5. Faz C — Karar katmanı ve ürün

**Yalnızca A veya B'den (a) çıkarsa açılır.** Hiçbiri çıkmazsa bu faz hiç yapılmaz ve bu
doğru davranıştır: ölçülmemiş bir üstünlüğü arayüze koymak, projenin karşı çıktığı şeyin ta
kendisidir.

| # | İş | Koşul |
|---|---|---|
| **C1** | Sentez katmanı (`insights.py`) — ölçülen bulguları cümleye çevirir | G2 kuralları geçerli: her cümle ölçümünü ve örneklemini taşır |
| **C2** | Tahmin/öneri arayüzü | Öneri ancak **ölçülmüş isabetiyle birlikte** çıkar |
| **C3** | Sayfanın soruya göre bölünmesi (G1) | Bağımsız; A/B beklemez |
| **C4** | Mobil ve gezinme cilası (G3–G5) | En sonda; kusursuz değil **okunabilir** hedefi |

---

## 6. Faz D — Sonlanma

Proje şu **dört sorunun tamamı** ölçülmüş bir cevaba bağlandığında biter:

| # | Soru | Bugün | Nasıl kapanır |
|---|---|---|---|
| 1 | Kapanış çizgisini yenebiliyor muyuz? | bilinmiyor | A1–A4 |
| 2 | Kalabalığı yenebiliyor muyuz? | bilinmiyor | B1–B4 |
| 3 | Pozitif beklenen getirili kupon kurulabiliyor mu? | bilinmiyor | B3 |
| 4 | Garanti hâlâ optimal mi? | **evet, kanıtlı** | kapandı |

**Bitiş belgesi.** Faz D'nin tek çıktısı, README'ye yazılacak şu bölümdür:

> ### Bu proje ne buldu
> [Dört sorunun her biri için: ölçülen sayı, örneklem, güven aralığı, ve "evet" ya da
> "hayır". Her "hayır"ın yanında onu tekrar açacak koşul.]

Bu bölüm yazıldığında **yapacak iş kalmaz.** Sonrasında yalnızca iki şey olabilir: veri
setlerinin bakımı (mevcut boru hatları), ya da yeni bir **veri kaynağının** ortaya çıkması
(§8).

---

## 7. Bilerek yapılmayacaklar

Bu liste planın sonlu kalmasını sağlar. Buradaki her madde, "yapılacaklar"a sızarsa planı
sonsuzlaştırır.

| Fikir | Neden hayır |
|---|---|
| Kaplama motorunu "iyileştirmek" | Kanıtlanmış optimal. Bir optimum yenilemez |
| Aynı veriyle yeni model mimarisi denemek (ağ, gradyan artırma) | A4(b) çıkarsa sorun model değil veridir. Daha karmaşık model, aynı soruyu daha yüksek sesle sormaktır |
| Takım bazlı istatistik | 216 takım, kupon takımlarında bile ~32 maç. Güvenilir *görünen* gürültü |
| Canlı bahis / maç içi | Bambaşka bir ürün; bu projenin vaadiyle ilgisi yok |
| Ölçülmemiş bir tahmincinin arayüze çıkması | Projenin karşı çıktığı davranışın kendisi |
| Kâr vaadi, "kazanma hissi" veren arayüz | Kurucu ilke; amaç değişse de bu değişmedi |
| Maçkolik ve otomatik erişime kapalı kaynaklar | Politika sınırı (doktrin 7) |
| İkramiye verisi olmadan "beklenen getiri" göstermek | Hesaplanamayan şeyi hesaplanmış gibi göstermek |

---

## 8. Bu planı neyin değiştirebileceği

Plan sonludur ama **kapalı değildir.** Yalnızca üç şey onu yeniden açar:

1. **Yeni bir veri kaynağı.** Sakatlık/kadro verisi, gerçek iddaa geçmiş oranı, resmî
   ikramiye arşivi. Yeni kaynak → yeni soru → Faz A veya B yeniden açılır.
2. **İkinci sezonun kupon verisi** (S1'in kapalı ayağı). Kupon düzeyindeki ölçümlerin
   gücünü ikiye katlar.
3. **Oyunun kurallarının değişmesi.** İkramiye dağıtımı, kolon fiyatı ya da maç sayısı
   değişirse havuz modeli baştan kurulur.

**Bunların dışında hiçbir şey planı uzatmaz.** Özellikle: daha güçlü bir model, daha uzun
düşünme, daha çok kod. Bu üçü de veride olmayan bir sinyali var edemez.

---

## 9. Sıra ve gerekçesi

```
A1 ─┐
A2 ─┼─► A4 (tahmin ekseni kapanır ya da açılır)
A3 ─┘
                    B1 ─► B2 ─► B3 ─► B4 (havuz ekseni)
C3 (sayfa bölme — bağımsız, her an yapılabilir)
                                        └─► C1, C2 (yalnızca A4(a) ya da B4(a) ise)
                                                        └─► C4 ─► D
```

**A önce, çünkü ucuz ve belirleyici.** Üçü de mevcut veriyle, yeni kaynak olmadan
yapılabilir; toplamı orta bir iş. Sonunda tahmin ekseni hakkında kesin bir cümle yazılır.

**B paralel başlayabilir** — B1 bir *araştırma*, kod değil. A koşarken yürütülebilir ve
sonucu Faz B'nin var olup olmayacağını belirler.

**C3 hiçbir şeyi beklemez.** Sayfanın bölünmesi ölçülmüş bir kusurdur (7.210 px, ilk ekranda
3/11 başlık) ve A/B'den bağımsızdır.

**C1/C2 koşulludur.** Gösterilecek ölçülmüş bir şey yoksa yapılmaz.
