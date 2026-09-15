# Devam notu — oturumlar arası süreklilik

Bu dosya bir **koşum kaydıdır** (`.claude/olcum_kutugu.json` gibi): depodan
yeniden üretilemez, git'e girer. Amaç: bir oturum bitince "kaldığın yer"in
kaybolmaması. Sonraki oturum — taze klon, taze konteyner olsa bile —
`.claude/hooks/session-start.sh` bu dosyanın içeriğini otomatik olarak
bağlama enjekte eder.

**Bu bir hafıza DEĞİL, bir el notudur.** Claude'un "düşünceleri" aynı kalmaz;
burada yazan, bir sonraki oturumun sıfırdan keşfetmeden devam edebilmesi
için bırakılmış kısa bir özet ve nedendir.

## Kural

- Bir işi **yarım bırakıyorsan** bu dosyanın "Şu an" bölümünü GÜNCELLE.
- Üç satır yeter: **Şu an neredeyiz**, **Sıradaki adım**, **Neden böyle**.
- Eski "Şu an" girdisi **Geçmiş** bölümüne düşer. Kaç girdi tutulacağına
  sabit bir sayı yok — hâlâ işe yarayan bağlamı tut, tamamlanmış ve başka
  yerde (commit/PR/belge) kayıtlı olanı buda. Ölçüt fayda, sayı değil; her
  oturumda dosyanın tamamı bağlama giriyor.
- Gizli/kişisel veri, token, şifre yazma — bu dosya depoya girer.
- Bu not bir **niyet/durum** kaydıdır, kanıt değildir. Çelişkide commit/kod
  kazanır.

---

## Görev tanımı (2026-09-13, sahibinden — değişmedikçe geçerli)

Sahibi projeyi teknik olarak devretti. **Hedef: Spor Toto'da 15/15.**
Bütçe **haftada 210.000 TL** (₺10 kolon → 21.000 kolon). Kâr/zarar açıkça
**ölçüt değil**; sahibi bunu bilerek ve yazılı olarak istedi. Karar sormadan
alınacak.

> **GÜNCELLEME (2026-09-14): üç aylık kısıt gevşedi.** Sahibi *"süre
> sıkıntın olmasın"* dedi. Cümle iki anlama da gelebilir (çalışma temposu ↔
> hedefin ufku); ikisi de aynı yöne baktığı için **ufuk kısıtı bağlayıcı
> değil** varsayıldı. Farklı kastedildiyse tek düzeltilecek şey budur ve
> ölçümlerin hiçbiri boşa gitmez — §3.78 hedefi ufuk ufuk veriyor.
>
> Bunun iki sonucu ölçüldü: hedef **13 hafta %77,0 → 39 hafta %99,0**
> (§3.78), fatura **39 haftada −₺4,51 M** (§3.79).
>
> **İKİNCİ GÜNCELLEME (2026-09-14): toplam bütçe tavanı da yok.** Sahibinin
> sözü: *"Toplam bütçe tavan yok."* Bu ikisi birlikte hedefin türünü
> değiştiriyor — haftalık `P > 0` olduğu sürece tavansız oynayan **kesin**
> tutturur. *"Ulaşabilir miyiz"* kapandı; kalan iki soru ölçüldü (§3.80):
> hedefin kendisi **ortanca ₺42.649** ödüyor (tutturduğumuz haftalarda
> ortanca 528 kişi daha tutturuyor), ve bugünkü bütçede ilk isabete kadar
> beklenen brüt harcama **₺1,86 M** (beklenen 8,9 hafta, %90 için 19,3).
>
> **ÜÇÜNCÜ GÜNCELLEME (2026-09-14): haftalık tavan yine ₺210.000.**
> Sahibi cepheyi kendi seçti. Yani üç parametre de artık sabit ve yazılı:
> **haftalık ₺210.000 · toplam tavan yok · süre tavanı yok.** Cephede
> karar verilecek bir şey kalmadı; beklenen 8,9 hafta, %90 için 19,3 hafta,
> beklenen brüt ₺1,86 M (net ≈₺1,03 M).

**Kabul etmediğim iki şey ve nedeni** (karar bana bırakıldığı için bunlar da
benim kararım):

1. **Depo silinmeyecek.** 114 haftalık ölçülmüş geri test altyapısı,
   bekçili iddia sistemi ve ölçüm kütüğü bu projenin asıl sermayesi. Sıfırdan
   kurmak ayları yer ve hedefe giden yolu kısaltmaz.
2. **Ölçülmemiş sayı rapor edilmeyecek.** 15/15 sözü verilmedi ve
   verilmeyecek; verilen söz "ölçülen en iyi plan" üretmek. Bu kısıt işi
   yavaşlatmıyor, işi işe yarar kılan şeyin kendisi.

---

## Şu an (en güncel)

**2026-09-14 — dal `claude/kupon-kurma-sayfasi-u78o1v`**

### `/kupon` iki fiyat çizgisine açıldı ve ŞEKİLLİ kupon kuruyor

Sahibinin isteği: *"açılış ve kapanış oranlarını verdiğimde 6 banko 9 üçlü
ve 5 banko 5 çift 5 üçlü şekilde 2 ayrı kupon oluşacak (açılış kendi içinde
2, kapanış kendi içinde 2)"*, derecelendirme *"en fazla tekten en çok çifte,
en çok çiftten en çok üçlüye"*, ve *"çiftlilerde en mantıklı seçenekler"*.

Yapılan:

* **Girdi iki bloğa ayrıldı.** `KuponSatiri.oran` artık çizgi başına
  (`{acilis, kapanis}`); ızgarada iki fiyat bloğu yan yana, her birinin
  kendi marj sütunu. Bir blok boş bırakılabilir — o çizgi atlanır, öteki
  yine kupon verir.
* **`lib/kupon-sekil.ts`** (yeni): şekiller `b6u9` (3⁹ = 19.683 kolon — 5.
  haftada OYNANAN tek sistemin kolon sayısı) ve `b5c5u5` (2⁵·3⁵ = 7.776).
  Derecelendirme **iki anahtarlı**, çünkü iyi banko ile iyi çifte aynı maç
  değil: banko sırası `p₁`e, kalanların çift/üçlü sırası `p₃`e bakar
  (`spor_toto/secim.py`nin kaçak aritmetiği). Çiftte seçilen iki sembol
  ikili kuponunkiyle AYNI koddan geliyor (`satirOkumasi`). Kupon başına
  `P(15/15)` ve `P(kaçak ≤ 3)` Poisson-binom evrişimiyle yazılıyor.
* **Arşiv 3. sürüme geçti**: satır iki fiyat taşıyor, karne `analizler`
  sözlüğünde çizgi başına, şekilli kuponlar `sekilli` listesinde (kolon ve
  banko/çift/üçlü sayıları YAZILMAZ, hesaplanır). 2. sürüm kayıtları
  **göçle** okunuyor: düz oran ve tek analiz, kaydın kendi `ayar.cizgi`sine
  oturur. Diskte kayıt yoktu ama göç yine de yazıldı ve bekçilendi.

### 5. haftanın oranlarıyla uçtan uca ölçüldü (Pinnacle, tarayıcıda)

Dört kupon kuruldu ve gerçek sonuç `122012110010220` ile karşılaştırıldı:

| kupon | kolon | kaçak | en iyi kolon | karneye göre P(≥12) |
|---|---:|---:|---:|---:|
| açılış 6 banko + 9 üçlü | 19.683 | 3 | **12/15** | %96,1 |
| açılış 5/5/5 | 7.776 | 2 | **13/15** | %82,7 |
| kapanış 6 banko + 9 üçlü | 19.683 | 2 | **13/15** | %96,2 |
| kapanış 5/5/5 | 7.776 | 4 | 11/15 | %82,6 |

**Bu bir geri test DEĞİL, tek haftalık bir duman testi.** Fiyat Pinnacle
(sahibi iddaa bülteniyle çalışacak), hafta korpusun içinde — yani sızıntı
var. Okunacak tek şey zincirin uçtan uca çalıştığı.

### Motor kuponu SAYFAYA bağlandı (aynı gün, ikinci tur)

Sahibi düzeltti: *"hafta 5 için yaptığımız her şeyi, hafta 6 verilerini
girince tuşa basınca hafta 6 için yapmalı."* Ölçüldü ve **ilk turda yanlış
olanı yapmışım**: 5. haftanın OYNANAN kuponu karneden değil MOTORDAN
çıkmış (`hafta_05_kupon.json`). Karne kuponları kalıyor ama yanına asıl
zincir bağlandı.

* **`spor_toto/secim.sekilli_secim()`** (yeni): şekli sabitlenmiş planın
  kanıtlanmış en iyisi — DP'nin `(çifte, üçlü)` düğümüne kısıtlanmış hâli.
* **`spor_toto/kupon_motor.py`** (yeni): oran → `implied_probs` → `odul_secim`
  (bütçenin seçtiği şekil) + `sekilli_secim(5,5)` (sabit şekil). **Takım
  kimliği ya da model GEREKMİYOR** — `super_toto_hafta.py` da baştan beri
  öyle ("bu script tahmin üretmez"), o yüzden sayfanın elle girilen oran
  tablosu motoru beslemeye yetiyor.
* **`POST /api/kupon/motor`** + `/kupon`ta "Motoru çalıştır" düğmesi ve
  "Motor kuponları" kartı. Karne kartı "Karne kuponları" oldu.

**Bekçi: 5. hafta BİREBİR yeniden üretiliyor** (`tests/test_kupon_motor.py`,
10 test). Üç varyantın da on beş işareti ve `P(k≤3)`i tutuyor:

    kapanış · bütçe  6b/0ç/9ü  19.683 kolon  0,951801   (variants[0])
    kapanış · sabit  5b/5ç/5ü   7.776 kolon  0,799613   (variants[1])
    açılış  · bütçe  6b/0ç/9ü  19.683 kolon  0,945670   (variants[2])

`sekilli_secim` ayrıca kaba kuvvetle sınandı (küçük vakada bütün atamalar).
Bir kusur da bekçiden çıktı: `butce_tl: 0` sessizce ₺210.000'e düşüyordu
(`0 or VARSAYILAN`).

### Bu turda AÇIK KALAN (zaman kısıtıyla atlandı)

1. **Kapı koşulmadı.** Sahibi "testleri atla, direkt commit et" dedi. Koşan:
   `tsc`, `eslint`, sözleşme üretimi. **Koşmayan:** `pytest` (tamamı),
   `check.mjs`, tarayıcı dumanı. Bir sonraki oturumun İLK işi budur.
2. **Motor kuponları arşive YAZILMIYOR.** `sekilli` listesi yalnızca karne
   kuponlarını taşıyor; motorunkiler kaydedilince kayboluyor.
3. Belgeler (README §6.1, ARCHITECTURE_NEXT uç tablosu) yeni ucu anmıyor;
   test sayısı bekçisi de bayat (2.105 → 2.115).

### Sıradaki adım

1. **Sızıntısız ölçüm**: aynı dört şekil, `tarih` kesmesiyle (maç gününden
   önce) geçmiş haftalarda koşulmalı. Şu anki tablo bunu söylemiyor.
2. Dört kuponun toplamı **₺549.180 = haftalık tavanın 2,62 katı**. Hangisinin
   oynanacağı sahibinin kararı; sayfa dördünü de gösteriyor ve toplamı
   tavanla kıyaslıyor.
3. Önceki listedeki maddeler duruyor: 729 kupon operasyonu (fiyatı
   ₺191.887,44), 6. haftanın kendi gününde dondurulması, olasılık kaynağı
   kararı (piyasa ↔ karne ↔ karışım), §3.81'in öbeklenme sınavı.
4. **Bant sabiti İKİYE AYRILDI — dokunmadan önce oku.** `odds.FAVORI_BANTLARI`
   *modelin* sınırlarıdır; arayüzünki ayrı: `FAVORI_BANTLARI_RAPOR`.

### Neden böyle

Şekil sahibinin kararı ve arayüzden değiştirilmiyor: `SEKILLER` sabit.
Değişebilir olan tek şey **derecelendirme** ve o da veriden okunuyor —
karne varsa karneden, yoksa piyasadan, ikisi de yoksa satır üçlüye düşüyor
ve "karne yok" diye işaretleniyor. Uydurulmuş banko yok. İkili kupon
(2¹⁵ = 32.768 kolon) kaldırılmadı: kural sahibinin önceki kuralı ve
şekilli kuponların yanında duruyor.

## Geçmiş girdiler

### 2026-09-14 — dal `claude/weekly-results-error-lessons-yrxc8i`

#### 5. haftanın sonucu girildi ve dersleri çıkarıldı (§3.82)

Sonuç `122012110010220` (1/0/2 = **5/5/5**), skorlar, **program saatleri**
ve ikramiye tablosu birlikte girildi. İkramiye tablosu bu hafta **iki
bağımsız kaynakla** doğrulandı (ekran görüntüsü + resmî uç, arşiv yeniden
çekildi); sonuç dizisi hâlâ tek kaynak ve dosya bunu yazıyor.

    oynanan tek sistem   19.683 kolon · 12/15 · ₺4.436,90   (%2,25)
    coklu plan (donmus,  19.683 kolon · 13/15 · ₺196.324,34 (%99,74)
    OYNANMADI)           fark +₺191.887,44 = 44,2 kat

**Üç kaçağın üçü de BANKOYDU** (9, 10, 12); çift/üçlü işaretlenen dokuz
maçın dokuzu tuttu. Beklenen kaçak 1,67, `P(kaçak ≥ 3) = %21` — hafta
dağılımın içinde, kural kırılmadı.

### Bu turda kapatılan üç boşluk (hepsi bekçili)

1. **Çoklu planın parası hiçbir çıktıda yazmıyordu** — §3.69'dan beri plan
   her hafta donuyordu ama yalnızca *kademe* olarak puanlanıyordu. Haftanın
   en büyük sayısı elle hesaplanınca çıktı. `coklu_getiri()` eklendi, tek
   sistemle **aynı gövdeden** (`getiri_karnesi`), rapor ikisini yan yana
   yazıyor.
2. **"Kapanış" etiketi üçüncü kez fazlaydı** — program saatleri girilince
   ölçülebildi: fiyat 2026-09-10'da kaydedildi, kupon 2026-09-11 19:55'te
   kapandı (20 saat). İki haftadır elle yazılmış bir itiraf olarak
   duruyordu; artık **hesaplanıyor** (`super_toto_hafta._yas_uyarilari`,
   resmî `close_date` arşivden). Geriye dönük: beş haftanın **üçünde**
   kusur var (hf 2: 69 s, hf 3: 21 s, hf 5: 20 s).
3. **Durma kuralları sözle kontrol ediliyordu** — `scripts/durma_kurallari.py`
   ikisini de koşuyor. İkisi de **geçmedi** ve biri ters yönde:
   §3.64 havuzlanmış `n = 175 < 300` (canlı sezon −9,2 puan, tarihsel +%5…+%10
   **artı** yöndeydi); §3.65 canlı `n = 38 < 150`, canlı −17,6 puan ↔ 2025/26
   arşivi **+4,7 puan** (n = 266, ters yön ve yedi kat örneklem).

### Defter: `n = 5` hâlâ karar vermiyor

| | oynanan | çoklu |
|---|---:|---:|
| 5 haftalık ROI | **0,698** | **0,699** |
| 3. hafta çıkınca | 0,041 | 0,719 |
| 5. hafta çıkınca | 1,890 | 0,164 |

§3.69'un *"ilk dört hafta aleyhte"* okuması **geçersiz**. İki taraf da tek
haftanın üstünde duruyor; biri öne geçtiğinde ilk soru "hangi hafta" olmalı.

### Sıradaki adım

1. **729 kupona çıkmanın operasyonu** — sıra değişmedi ama fiyatı artık
   canlı: **₺191.887,44, tek haftada.** Bu haftanın 81 kuponu
   `sadelestir` ile **25 slipte** birleşiyordu (§3.75'in havuzlanmış
   ortalaması 60,1); yani engel sanıldığından küçüktü.
2. **6. hafta `--yaz` ile dondurulacak** ve fiyat **kupon kapanışının kendi
   gününde** (18 Eylül Cuma, kapanış 19:55) alınacak. Kapı artık bunu
   denetliyor.
3. Hâlâ karara bağlanmamış: olasılık kaynağı (piyasa ↔ karne ↔ karışım),
   `benzer`in ileri yürüyüş ölçümü (§6.1), kupon kuralının 2¹⁵ = 32.768
   kolonluk bedeli (₺327.680, tavanın 1,56 katı — hangi maçlar bankolaşacak).
4. Kesintisiz 13 haftalık pencere çıkınca §3.81'in öbeklenme sınavı.
5. **Bant sabiti İKİYE AYRILDI — dokunmadan önce oku.** `odds.FAVORI_BANTLARI`
   *modelin* sınırlarıdır (`recalibrate.KADEMELER` içinde oturtulan bir
   kademe); arayüzünki ayrı: `FAVORI_BANTLARI_RAPOR`. İkisini
   "aynılaştırmak" akla yatkın görünüyor ve **yapılmamalı**.

### Neden böyle

Bu turun asıl bulgusu bir model kusuru değil bir **ölçüm hattı** kusuru:
en pahalı karar (planı oynamamak) hiçbir ekranda fiyatlanmıyordu ve
haftalardır öyleydi. 4. haftanın 4. dersi aynı şeydi. Kural değişmedi,
çünkü değiştirmeyi haklı çıkaracak hiçbir ölçüm eşiği geçmedi — ve iki
haftadır aynı yerde kaybetmek tam olarak durma kurallarının **yazılma
sebebidir**.


### 2026-09-14 — dal `claude/match-analysis-coupon-page-p7w5dd`

### `/kupon` sayfası — **zincirin tamamı ayakta**

    15 maç elle giriş  →  tek ayarla tüm liglerin korpusunda karne
                       →  karnenin en yüksek İKİ sembolü = işaret
                       →  adıyla arşive kayıt (girdi + ayar + analiz + işaret)

**Kupon kuralı sahibinden, kendi cümlesiyle:** *"mevcut olan oran analizden
en yüksek ikiliyi alıp seçeceksin."* Beşiktaş–Erzurumspor örneği
(1 %80,9 · 0 %12,4 · 2 %6,7 → `1-0`) `check.mjs`te bekçi olarak koşuyor.

Kural KARNEDEN okur, piyasadan değil. Eşitlikte sıra piyasaya, o da eşitse
sembol düzenine (1, 0, 2) göre bozulur — rastgele seçilseydi aynı girdi iki
farklı kupon verir ve kayıt yeniden üretilemez olurdu. Karnesi olmayan
satır piyasadan seçilir ve **işaretlenir**, sessizce geçmez.

### ÖLÇÜLEN VE SAHİBİNE SÖYLENEN: bedel tavanı aşıyor

Kural her maça iki sembol verdiği için kolon sayısı **girdiden bağımsız**:

    2^15 = 32.768 kolon · ₺10 = ₺327.680   ↔   haftalık tavan ₺210.000
    1,56× tavan

Aşımı kapatmanın tek yolu bazı maçları **bankoya** indirmektir; hangi
maçların bankolaşacağı **henüz karara bağlanmadı**. Sayfada kırmızı kutuda
ve uyarı bloğunda yazılı, gizlenmedi.

Kolon bedeli ve haftalık tavan arayüzde SABİT DEĞİL: `/api/meta`ya bağlandı
(`getiri.KOLON_BEDELI`, `backtest.VARSAYILAN_BUTCE_TL`). İki yerde
yaşasaydı biri değiştiğinde öteki sessizce yalan söylerdi.

### Arşiv: birim KUPON, kayıt zincirin dördünü taşır

Bir haftanın birden çok kuponu olur (biri açılışla, öteki kapanışla).
Kimlik `no` (yeniden kullanılmaz), ad serbest, hafta yalnızca etiket.
Analiz **damgalı** kaydediliyor (`olculdu` + `evren`) — ilk sürümde bilerek
atılıyordu, o karar geri alındı: kupon o analizden çıkıyor, analiz atılırsa
kayıt kendi gerekçesini kaybeder.

### Bu turda eklenen: **lig kapsamı seçilebilir**

Sahibi istedi: *"tüm ligleri kapsayarak yapıyor ya, bunu seçilebilir yapıp
sadece maçları kendi liglerinde değerlendirebileceğimiz bir sistem."*

`tum` (varsayılan, bütün korpus) ↔ `kendi` (her satır kendi lig koduyla).
Kapsam **kayda giriyor** (`ayar.kapsam`) — aynı oranlar, aynı çizgi, farklı
kapsam farklı karne verir; kayıt hangisinin sorulduğunu söylemek zorunda.

**Sessiz kusur kapatıldı.** Korpusun tanımadığı bir lig koduyla arama 400
DÖNMEZ, **boş** döner — kullanıcı "bu fiyatta benzer maç yok" ile "yazdığın
kodu tanımıyorum"u ayırt edemezdi. Yeni uç `GET /api/benzer/ligler` korpusun
lig envanterini veriyor (17 lig, kod + etiket + n); kapsam `kendi` iken
tanınmayan kod taşıyan satır analizi ENGELLİYOR ve sayfada adıyla yazıyor.

**Envanterin ilk sürümü YANLIŞTI ve bekçi yakaladı:** `r.get("kapanis")`
ile süzüyordu, oysa korpusta kapanış fiyatı `oranlar` anahtarında durur —
liste 23.083, arama 23.085 diyordu. Evrenin tanımı artık tek yerde
(`_cizgi_orani`, aramanın kendi fonksiyonu) ve bekçi ikisinin eşitliğini
tutuyor.

### ÖLÇÜLEN: kendi liginde bakmanın bedeli

5. haftanın 15 maçı, kapanış, shin, hedef örneklem 200:

    tüm ligler   yarıçap tavanı  1/15   az örnek 0/15
    kendi ligi   yarıçap tavanı 10/15   az örnek 1/15

Evren 23.085'ten bir ligin boyuna düşüyor (T1 1.415, D1 1.224). En uç
örnek Levante–Barcelona: tüm liglerde n=123, kendi liginde **n=2**.

Bu, seçeneği kötü yapmaz — **başka bir soru** sordurur. Sayfa bedeli
gizlemiyor: her satırda n ve yarıçap yazıyor, tavana dayanan satır
işaretleniyor. Kütükte.

### Sıradaki adım

1. **Bütçe kararı** — kupon kuralı her maça iki sembol verdiği için kolon
   sayısı sabit 2¹⁵ = 32.768 (₺327.680, tavanın 1,56 katı). Aşımı kapatmanın
   tek yolu bazı maçları bankoya indirmek; kuralı sahibi koyacak.
2. Hâlâ karara bağlanmamış: olasılık kaynağı (piyasa ↔ karne ↔ karışım),
   `benzer`in ileri yürüyüş ölçümünün (§6.1) sırası.
3. İsteğe bağlı, sorulmadı: işaretleri elle değiştirebilmek.

Teknik olarak bekleyenler değişmedi: 729 kuponun operasyonu (§3.75),
6. haftada `--yaz` ile dondurma, kesintisiz 13 haftalık pencere çıkınca
§3.81'in öbeklenme sınavı.

### Neden böyle

Kupon ekrandaki analizden kuruluyor, ayrı bir sorgu atılmıyor: ikisinin
ayrışabilmesi için bir sebep yok. **Bayat analizden kupon kurulmuyor** ve
kaydedilmiyor — ekrandaki karne şu anki girdiye ait değilse ondan çıkan
işaretler de değildir.

Ölçüm kütüğünde bir alıntı kırılganlığı düzeltildi: `frontend/lib/types.ts`
satır numarasıyla anılıyordu ve dosyaya alan eklendikçe kayıp bekçiyi
kırmızıya çeviriyordu. Numara düşürüldü; iddia aynı kaldı, kırılgan kısmı
gitti.


**2026-09-14 (önceki, aynı dal)** — `/kupon`un 1. aşaması (giriş tablosu). Ayrıntısı yukarıdaki güncel girdide; commit `c9f1b48`.


### 2026-09-14 — dal `claude/proje-durumu-ilerleme-8h7l86`

### Bu oturumda: parametreler kilitlendi, **son açık varsayım sınandı** (§3.81)

Sahibi haftalık tavanı ₺210.000'de bıraktı. Üç parametre de sabit artık
(haftalık ₺210.000 · toplam tavan yok · süre tavanı yok) ve §3.80'in
cephesi tek satıra indi. Geriye sahibinin ilgilendiği **tek** sayı kaldı:
*ne kadar sürer* (8,9 hafta beklenen, %90 için 19,3).

O sayı tek bir ölçülmemiş varsayıma dayanıyordu — **haftalar arası
bağımsızlık** — ve bu oturumda sınandı (`scripts/haftalar_arasi.py`, yeni
hat). Aranan şey heterojenlik değil (o zaten modelde), **artık** bağımlılık:

* `p` serisi gecikme-1: **r = +0,1852**, permütasyon %95 null
  [−0,206, +0,213], p = 0,0842 → geçmedi.
* İsabet öbeklenmesi: 4 haftada 23 ↔ null [13,0 · 27,0]; 8 haftada 3 ↔
  [0,0 · 4,0] → geçmedi.

Holm'lu ikisi de geçmedi → **ön kayıtlı kurala göre eksen kapandı**,
bekleme sayıları duruyor. **Ama kapanışın iki sınırı var ve ikisi de
çıktıya yazılı:** (1) ilişki sıfır *ölçülmedi*, sıfırdan **ayrılamadı** ve
işaret **pozitif** — gerçek olsaydı kuyruğu uzatırdı; (2) sınav yalnız 4 ve
8 haftalık pencerede koşabildi, ilgilendiğimiz 13–26 hafta arşivde
kesintisiz bulunmadığı için **hiç sınanmadı** ("ÖLÇÜLEMEDİ" satırı bekçili).

**Yan ölçüm, iyi haber:** model `p` %10,489 (E 9,5 hafta) ↔ gerçekleşen
%18,421 (E 5,4 hafta). §3.68 bu açığı ölçtü ve *"güncel değil"* dedi, o
yüzden hüküm arada — ama bugünkü tablo **muhafazakâr** taraftan yazılı.

### Sıradaki adım

Karar tarafında bekleyen bir şey **kalmadı**; sıradakiler teknik:

1. **729 kupona çıkmanın operasyonu** — birinci iş (+1,8 puan **ve**
   +₺7.660/hafta). Engel: 458,7 slip; giriş süresi kaydı sahibinden.
2. 6. hafta geldiğinde `--yaz` ile dondur; 5. haftanın sonucu girilince
   ilk ileriye dönük satır okunacak (**o kaydın üstüne yazma**).
3. **Kesintisiz 13 haftalık pencere çıkınca** §3.81'in öbeklenme sınavı o
   boyda tekrarlanır (yeniden açılma şartı yazılı).
4. Havuz ekseni (§3.51) `n = 3`te; sönüm ekseni birikmeyi bekliyor.
5. **Bant sabiti İKİYE AYRILDI — dokunmadan önce oku** (favori karnesi işi,
   dal `claude/favori-match-statistics-tp6lg4`). `odds.FAVORI_BANTLARI`
   **modelin** sınırlarıdır: `recalibrate.KADEMELER` içinde `"bant"`
   *oturtulan* bir kademe, yani sınırlar oynarsa model başka kovalarla
   yeniden oturur ve ona bağlı bütün ölçümler sessizce değişir. Rapor
   tablosunu incelttiğimde önce bu sabiti değiştirdim ve
   `test_recalibrate::test_bant_sinirlari` kırmızıya döndü — kusuru o
   yakaladı. Arayüzün sınırları ayrı: `FAVORI_BANTLARI_RAPOR` (8 bant).
   İkisini "aynılaştırmak" akla yatkın görünüyor ve **yapılmamalı**;
   raporun modelin *inceltmesi* olduğunu bir bekçi tutuyor.

### Neden böyle

Üç parametre kilitlenince proje bir "karar" işi olmaktan çıkıp bir
**yürütme** işine döndü. Bu oturumda yapılan son şey, yürütmenin dayandığı
tek ölçülmemiş varsayımı sınamaktı — geçti, ama nerede sınanamadığı da
yazıldı. Bundan sonrası hafta biriktirmek ve 729 kuponun operasyonu.


**2026-09-14 (önceki, aynı dal)** — iki tavan da kalktı (§3.80): hedef
**kesin**, soru fiyatı ve süresi. 15/15 tutturunca alınan **ortanca
₺42.649** (o haftalarda ortanca 528 kazanan daha var); bütçe cephesi
kuruldu (`butce_egrisi.py`): bütçe büyüdükçe bekleme kısalır, beklenen
harcama büyür.

**2026-09-14 (önceki, aynı dal)** — ufuk açıldı, **fatura ölçüldü**
(§3.79): görev ölçeğinde ROI **0,449** (729 kuponda 0,486), hafta başı
net −₺115.541, 39 haftada −₺4,51 M. Ölçerken bulgu: **devir haftası
bizim haftamız değil** — 26 devir haftasının **0'ında** tutturmuşuz
(beklenen 4,79; p = 0,0023). `scripts/coklu_karne.py` + 7 bekçi.

**2026-09-14 (önceki, aynı dal)** — varlık kanıtları arandı (§3.77:
Benter/Ranogajec/Mandel, üçü de burada tekrarlanamıyor), **yığma ekseni**
ölçülüp kapandı (kâhin 13 kat seçeneği varken kullanmadı, ×1,0312), ve
dış bakış **kurala** bağlandı (`dis-tarama` becerisi + CLAUDE.md +
bekçisi). Ayrıca §3.78: hedef bir **süre** sorusu — 13/26/39 hafta →
%77,0 / %94,9 / %99,0.

**2026-09-14 (önceki, aynı dal)** — **iki tavan ölçüldü** (§3.76):
kombinatorik eksenin tamamı **+2,6 puan** (81 kupon %77,0 → serbest küme
%79,6; 1,8'i yalnızca 729 kupon), ve model ekseninde **1 hedef puanı =
0,02–0,047 Brier** — projenin piyasayı geçen tek bulgusu (Betfair,
ΔBrier −0,00100) hedefte ≈0,02 puan. `scripts/bilgi_esnekligi.py` +
`ufuk_kiyasi.py --serbest` + 9 bekçi + `docs/DIS_UFUK_TARAMASI.md`.
Yön: kalan tek gerçek kaldıraç matematik değil **operasyon**.

**2026-09-13 (önceki, dal `claude/devam-edelim-sltxrg`)** — **kupon ≠ slip**
ölçüldü (§3.75). "81 kupon = 81 slip" sessiz bir varsayımdı ve yanlıştı: tek
konumda ayrışan iki kutu **özdeş** olarak birleşiyor (sapma ≤ 7,2·10⁻¹⁶).
Ölçülen (114 hafta, 21.000 kolon): tavan 81'de 81 kupon → **60,1 slip** (en
kötü 75), kutucuk 1.945 → 1.447; en büyük birleşmiş slip 6.561 kolon, deponun
zaten tek giriş saydığı kuponun üçte biri. Asıl bulgu: **tahsis birleşmeyi
öldürüyor** (tekdüze 27,5 ↔ tahsisli 60,1 slip, ×2,19) — ama §3.71 **ayakta**:
tahsisin hedefteki +2,22 puanı zarara dönmek için 1 slipte 5 (takas) ya da 1
slipte 9 (atlama) hata ister. `coklu_kupon.py` artık kayda `slipler` yazıyor,
özdeşlik donmuş artefaktın üstünde bekçili. Yan iş: `sadelestirme.py` + 24
bekçi + `sadelestirme_kiyasi.py`.

**2026-09-13 (önceki, dal `claude/devam-edelim-w8mob0`)** — **operasyon**
fiyatlandı (§3.74). Önce bir gövde hatası çıktı: `coklu.p_onbes` **oynanan**
kuponu puanlayamıyor (olasılıkları topluyor, bu yalnız kuponlar ayrıkken
doğru) ve sapma tek yöne bakıyor — gerçek %9,563 iken %9,601 diyor, yani
denetim en çok ihtiyaç duyulduğu anda iyimser; `operasyon.birlesim_p_onbes`
kolonları tek tek sayıyor. Ölçülen (114 hafta, 21.000 kolon): `fazla` işaret
`P`yi **yükseltiyor** ve bedeli parada (81 kuponda +65.610 TL, bütçenin
%31'i); ortalama slip küçük ama en kötüsü 35 kat büyük ve sebebi yoğunlaşma
(**81 kuponun ortalama 11'i hedefin yarısını taşıyor**, en kötü haftada 2);
eşikler uzak — 81 → 729 çıkmak ancak 11 kuponda 1 hatada zarara dönüyor.
Hüküm: operasyon hatası **hiçbir kararı değiştirmiyor**. Yoğunlaşmadan çıkan
denetim sırası kayda girdi (`coklu_kupon.py` kuponları azalan yazıyor,
`plan.denetim` bloğu) ve bekçi **artefaktın kendisini** sınıyor — aramanın
çıktısı azalan değildi (51 hafta × tavan kıyasının 6'sında karışık).
`spor_toto/operasyon.py` + 22 bekçi + `scripts/operasyon_kiyasi.py`.

**2026-09-13 (önceki, dal `claude/devam-edelim-51rff7`)** — **hedefin kendisi**
ölçüldü (§3.73). Deponun her ölçüsü haftalıktı, sahibinin hedefi değil; çeviri
(`1 − Π(1 − p_w)`) hiç yapılmamıştı. Ölçülen: 114 hafta, 8 ayrık 13 haftalık
pencere, 21.000 kolon — 1 kupon %64,2 · 27 kupon %75,2 · 81 kupon %77,0 ·
729 kupon **%78,8** (pencere aralığı %69,9–86,7, haftalar arası `P` on altı
kat ayrışıyor). §3.67–3.71'in işi hedef kademesinde **14,6 puan**; haftalık
×1,47 olan kazanç hedefte ×1,23 ve fark **doymadır**. Aynı oturumda zamanlama
ekseni açıldı ve **kapandı** (`ufuk.kahin_tahsisi` üst sınırı ×1,031 ortalama,
en çok ×1,051 — `1 − Π(1 − p)` doyuyor); yaklaşıklığın Jensen yanlılığı
ölçülüp `coklu_kiyasi.py` kesin hesaba çevrildi. `spor_toto/ufuk.py` +
`tests/test_ufuk.py` (9 bekçi) + `scripts/ufuk_kiyasi.py`.

**2026-09-13 (önceki, aynı dal)** — değişken derinlikli eksen (§3.72) kuruldu,
ölçüldü ve **beklenti yanlandı**: kuponlar artık eminlik sırasının ön ek
ağacında bir antizincir (sabit derinlik özel hâli, yani arama üst küme), ama
kazanç binde birler (×1,0001–×1,0003, 570/570 geri gidiş yok). Niçin'i de
ölçüldü ve sezgisel içermiyor: sabit derinlikli plan bu ailede **yerel en
iyi** (aynı yuva sayısında en iyi takas binde 0,23). Plan eksen kütlesinin
%83,3'ünü terk ediyor ve bu bir fırsat değil — kapatmak kupon yuvası da
harcıyor. Aynı oturumda kendi ilk sürümümdeki bir ölçüm hatası yakalandı
(`λ` ikili araması yanlış hedefe koşuyor, aday dejenere tek sisteme
düşüyordu) ve `tahsis_kiyasi.py` `degisken_derinlik=False`a alındı ki
§3.71'in tablosu tek mekanizmayı yalıtsın.

**2026-09-13 (önceki, dal `claude/devam-edelim-q99bac`)** — kupon başına
**ayrı** alt sistem bütçesi (§3.71). Arama ayrılabilir bir sırt çantası
çözüyor (`_tahsis`, cephenin üst konveks kabuğunda açgözlü): gerçek bütçede
729 kuponda %10,602 → %11,031 (×1,041), serbest küme tavanının %94,1'inden
%97,9'una. 570 kıyasın 570'inde geri gidiş yok (tek tip aday aramada kaldı,
referans gövde `scripts/tahsis_kiyasi.py::tek_tip_arama`). Aynı oturumda
eksen kuralı ilk kez ölçüldü (ters sıra ×0,755, tek takas ×1,0002),
`en_iyi_secim` cephenin son noktası oldu, arama 0,63 → 0,38 sn/haftaya indi
ve bağlı sayıların hepsi yeniden ölçüldü.

**2026-09-13 (önceki, aynı dal)** — bağımsızlık varsayımı çoklu kupon
kesitinde ölçüldü (§3.70). `kuyruk.kapsama` §3.46'nın tek faktörünü üç
sembole taşıdı (rütbe eşikleri → favori göstergesinde ikili modelin birebir
aynısı, `ρ` yeniden kalibre edilmedi); kupon başına ikili eşik kurma yolu
reddedildi ve bekçisi yazıldı. Ölçülen: oran **gerilemedi, büyüdü** (×1,42 →
×1,48 en kötü makul `a`da), 0/114 haftada çoklu plan geride, mutlak değerler
%12'ye kadar şişiyor. Aynı oturumda `coklu.p_alt`ın ham sözlükten okunması
düzeltildi (binde 0,3'lük sayı yalanı, arama sıralamasını da
oynatabiliyordu), §3.46'nın senaryo tablosundaki bayat satır yeniden ölçüldü
ve `scripts/setup.sh`e `--ignore-installed blinker` yedeği eklendi (uzak
oturumda kurulum bitmiyordu).

**2026-09-13 (önceki)** — çoklu kupon üretim hattına bağlandı (§3.69):
`coklu_kupon.py --yaz` planı `hafta_NN_coklu.json` olarak donduruyor, kayıt
kuponların kendisini taşıyor ve `super_toto_degerlendir.py` onu tek sistemle
aynı gövdeyle puanlıyor. **5. hafta sonuç görülmeden donduruldu** (81 kupon ×
243 kolon, `P(15/15)` %15,937 ↔ tek sistem %13,081). İlk dört canlı hafta
**aleyhte** çıktı (12+ kolon: tek sistem 194, çoklu 10; farkın neredeyse
tamamı 3. haftadan) ve "küçük bütçe rejimi" açıklaması ölçülüp **yanlandı**
(3.888 kolonda da 12+ kolon 5.309 → 8.673). `n = 4` hiçbir şey kanıtlamaz ve
bu cümle iki yöne de bakıyor.

**2026-09-13 (önceki)** — banko ekseni açıldı ve kapandı (§3.68).
Planın `P(15/15)` iddiası ilk kez plan düzeyinde sınandı: havuzlanmış 114
haftada model karamsar (tek sistemde 8,54 ↔ 15, ×1,76) ve bağımsız ölçülen
banko sapması açığı kapatıyor — **ama açık güncel değil** (2025/26'da 729
kuponda ×1,00; düzeltilmiş model o sezonda fazla iyimser olurdu) **ve karar
değişmiyor** (oynanan kupon 114/114 haftada birebir aynı). Sonuç:
`BANKO_Q_DUZELTMESI = 0,0` kalıyor, `P(15/15)` sayıları yeniden
ölçeklenmedi, beklemenin bedeli sıfır. Aynı oturumda §3.67 yazıldı (çoklu
kupon bulgusu yol haritasında hiç yoktu).


**2026-09-13 (önceki)** — çoklu kupon işi: `coklu.py` + 13 bekçi +
`coklu_kiyasi.py` + `coklu_kupon.py`. Çarpım kısıtı kalktı, `P(15/15)` aynı
bütçede ×1,45 (19.683 kolon), gerçek bütçede (21.000) ×1,42. Alt kademe
beklentisi **yalanlandı**: 12+ tutturan kolon 18.628 → 26.274 (+%41), yani
ödünleşme yok. Ayrıntı artık belgede: `docs/ISTATISTIK_YOL_HARITASI.md`
§3.67 (bu oturumda yol haritasına bağlandı) ve `coklu.py` başlığı.


**2026-09-13 (önceki)** — `docs/PROJE_GECMISI.md` yazıldı: 521 commit, ilk
commit'ten HEAD'e kronolojik, hash+tarih+mesaj+stat. Depo sığ klonlanmıştı,
`git fetch --unshallow` gerekti (yoksa yalnız 273 commit görünüyor). Aynı
oturumda bu devam notu mekanizması kuruldu.
