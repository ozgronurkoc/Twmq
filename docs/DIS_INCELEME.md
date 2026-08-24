# Dış çalışma incelemesi — `zakariae-boui/football-prediction-ml`

**Kapsam:** Dışarıdan bir makine öğrenmesi çalışmasının bu projeye ne
kattığı ve **ne katmadığı**.
**Güncellendi:** 2026-08-22
**İlgili belgeler:** [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md)
§6.2 A4 (arayışın durma kuralı) · §6.3 (havuz ekseni)

> **Künye — bu bizim ölçümümüz değildir.** Aşağıdaki sayılar dış bir
> çalışmanın kendi belgelerinden alınmıştır. O çalışma bizim "geçti"
> ölçütümüzü (güven aralığının **tamamen** sıfırın altında kalması)
> kullanmıyor; isabet yüzdesi ve ROI raporluyor. Dolayısıyla buradaki
> hiçbir sayı bizim ölçümlerimizle aynı statüde değildir ve hiçbirinin
> yerine geçmez. Değeri **teyit**tir, kanıt değil.

---

## 1. Neden bakıldı, ne çıktı

Soru basitti: *"Bu repoda bize uyarlayabileceğimiz bir şey var mı?"*

Cevap: **kod olarak hiçbir şey, dış kanıt olarak bir şey.**

Çalışma baştan sona **tahmin ekseninde** yaşıyor — bizim §6.2 A4'te
ölçerek kapattığımız eksende — ve aynı yere varıyor. Kendi cümlesi:
*"Closing odds already price all public information, so a model built on
public data can match the bookmaker's accuracy but cannot out-predict
it."*

Bu, A4'ün cümlesinin başka kelimelerle yazılmış hâlidir.

---

## 2. Çalışmanın kendisi

İki uygulama var; yalnızca birincisi bizi ilgilendiriyor.

| | A: Lig bahsi (ilgili) | B: Dünya Kupası 2026 (ilgisiz) |
|---|---|---|
| Kesit | 6.080 maç · Premier Lig + La Liga · 2018/19–2025/26 | 49.493 milli maç (1872+), 17.588'de eğitim (2002+) |
| Yöntem | RF · XGBoost · SVM, 52–62 özellik | Elo + 20.000 Monte Carlo bracket |
| Kaynak | football-data.co.uk + Understat (xG) | Kaggle |
| Sonuç | Piyasa geçilemedi | Arjantin %22,3 · İspanya %15,2 · Fransa %14,1 |

**A'nın ölçtüğü:**

| Model | İsabet | ROI |
|---|---:|---:|
| SVM | %54,2 | — |
| Random Forest | %53,9 | — |
| XGBoost | %52,8 | **−%2,9** (Draw No Bet) |
| **Bahisçi favorisi (referans)** | **%54,7** | — |

Bütün stratejilerin ROI'si negatif (−%2,9 … −%8,4). Kendi ifadesiyle:
*"reaching the accuracy ceiling differs fundamentally from beating it"* —
aradaki fark bahisçi marjıdır.

> Özellik sayısı çalışmanın kendi iki belgesi arasında tutarsız (README 62,
> `docs/PROJECT.md` 52; kategori toplamları ikisini de tutmuyor). Aktarılan
> bulgu sayıya bağlı olmadığı için bu bir engel değil, ama künyeye yazılır.

---

## 3. Aktarılan tek şey — model sınıfı dış kontrolü

**Bu incelemenin asıl çıktısı budur.**

A4 bugün cevaplanmamış bir itiraza açık:

> *"Piyasayı geçen özellik yok demediniz. Sizin **doğrusal kademeniz** o
> özelliği kullanamadı demiş oldunuz."*

İtiraz haklı bir yere basıyor: dokuz denememizin **hepsi** tek bir model
ailesiyle yapıldı — `recalibrate.py`'ın yeniden kalibrasyon kademesi,
`ln p` üzerinde doğrusal, Newton ile uydurulan bir softmax. Etkileşim
yakalayan ya da doğrusal olmayan eşik kuran bir model sınıfı hiç
denenmedi.

Dış çalışma tam o sınıfı deniyor — ağaç toplulukları ve SVM, 52–62
özellikle — ve **aynı tavana çarpıyor.**

| | Bizim | Dış çalışma |
|---|---|---|
| Kesit | 31.100 maç · 22 lig · 4 sezon | 6.080 maç · 2 lig · 8 sezon |
| Model ailesi | Kademe (ln p'de doğrusal, Newton) | RF · XGBoost · SVM |
| Özellik | 9 | 52–62 (xG dahil) |
| Ölçüt | Brier + hafta üzerinden eşleştirilmiş bootstrap; **aralık tamamen sıfır altında** | İsabet %, ROI |
| Sonuç | Hiçbiri geçmedi | Hiçbiri geçmedi |

**Sınırları:** farklı ligler, farklı dönem, farklı ölçüt, bizden bağımsız
bir ekip. Bu bir **teyit**tir — bizim koşmadığımız bir model sınıfının
aynı sonuca vardığını gösterir, ama bizim kesitimizde o sınıfın ne
yapacağını **ölçmez.** İtirazı ortadan kaldırmaz; ucuzlatır.

---

## 4. xG — açık uç sanılan, ölçülmüş negatif

§6.2 A4 tahmin ekseninin yeniden açılma kaynaklarını üç maddeyle
sayıyordu: fikstür verisi (kupa + Avrupa), kadro/sakatlık, şehir/rekabet
tablosu. **xG listede yoktu**, yani örtük olarak açık duruyordu.

Dış çalışmada vardı: Understat'tan 14 xG özelliği, *"shot quality beyond
raw volume"* gerekçesiyle. **Yine geçmedi.**

Bizim için ayrıca iki kez zayıf:

1. **Understat Süper Lig'i kapsamıyor.** Kapsadığı altı lig bizim
   korpusumuzun bir parçası ama kuponun ağırlık merkezi değil. 2025/26
   kuponunun yarısı Süper Lig'den geliyordu; 2026/27'nin ilk iki haftası
   **tamamen** Süper Lig. Yani xG'nin kör olduğu yer tam da ölçmek
   istediğimiz yer.
2. **Aynı ailenin başka üyesi zaten denendi.** Korpus şut, isabetli şut ve
   korner taşıyor (%93,01 kapsama) ve bunlardan türetilen takım formu (T5)
   geçmedi. xG bu büyüklüklerin şut kalitesiyle ağırlıklandırılmış hâlidir
   — daha iyi bir ölçüm, **yeni bir eksen değil.**

**Sonuç:** xG, A4'ün kaynak tablosuna *"denendi (dışarıda), geçmedi"*
satırı olarak girer — açık uç olarak değil.

---

## 5. Beraberlik — dışarıdan gelen üçüncü teyit

Dış çalışma bütün modellerinde beraberlikte ~sıfır recall ölçüyor:
*"draws represent ~25% of matches but lack distinctive statistical
patterns."*

Bizde bunun iki karşılığı var ve ikisi farklı şey söylüyor:

| Ölçüm | Kesit | Sonuç |
|---|---|---|
| Beraberlik profili (§5) | 567 maç | Favori−ikinci farkı 0–0,05 iken %32,7, 0,50+ iken %14,3 — sinyal var ama zayıf ve tam monoton değil |
| Çiftede atılan sembolün gelme oranı | 567 maç | Beraberlik **%25,8**, ev sahibi %16,0, deplasman %15,6 |

İkincisi ürün açısından daha keskin: beraberlik yalnızca tahmin edilemez
değil, **atılması 1,6 kat pahalı.** Kaplama motorunun bütçesini neden
oraya harcadığının cevabı budur ve dış çalışma bunun tahmin tarafını
bağımsız olarak doğruluyor.

---

## 6. Aktarılmayanlar ve gerekçeleri

| Ne | Neden aktarılmıyor |
|---|---|
| **Değer bahsi çerçevesi** | **Bizde zaten var.** Bu incelemenin ilk taslağı *"çerçeveyi al, rakibi bahisçiden kalabalığa çevir"* diye öneriyordu; `super_toto_hafta.py::kamuoyu()` bunu satır satır yapıyor (`diff = play − prob`, `ratio = play / prob`). Ayrıntı §7 |
| ROI / Kelly staking | **Biz müşterek bahisiz.** Kelly sabit bir fiyata karşı optimaldir; havuzda ödeme kaç kişinin tutturduğuna bağlıdır. Aynı alet burada yanlış cevap verir |
| Dünya Kupası Elo + Monte Carlo bracket | Kupon karşılığı yok. Monte Carlo bizde `analysis.py`'da zaten var |
| Sızıntı disiplini (`shift(1)`, `LEAKAGE_COLS`) | Bizimki daha sert: sezon dışarıda bırakmalı ölçüm + hafta üzerinden eşleştirilmiş bootstrap + aralığın tamamen sıfır altında kalması + **ölü sütun yakalayan bekçi testleri** (`test_hareket_sutunu_gercekten_calisiyor`) |
| Kronolojik train/val/test bölmesi | Aynı gerekçe. Ayrıca kademede ayarlanacak hiperparametre yok |
| Kalibrasyon eğrisi | `odds.py`'da var, 8 kova, sayfada duruyor |

---

## 7. Aynı fikre iki yerden varılması

Kayda değer bir çakışma: dış çalışmanın değer bahsi mantığı
(`edge = p_model − p_piyasa`, pozitifse oyna) ile bizim havuz mantığımız
aynı biçimde kurulu, yalnızca **rakip farklı.**

```
Sabit oranlı bahis :  edge = p_model    − p_piyasa(marj arındırılmış)
Müşterek bahis     :  edge = p_piyasa   − oynanma_payı
```

Fark yüzeysel değil, belirleyici: sabit oranlıda kazanmak için **piyasayı
yenmek gerekir** ve dış çalışma bunun olmadığını ölçmüştür. Müşterek
bahiste **gerekmez** — piyasa olasılığını olduğu gibi kullanıp yalnızca
kalabalığın ondan saptığı yeri işaretlemek yeter.

Bu, §6.3'ün havuz eksenini *"muhtemelen tek gerçek kaldıraç"* diye
işaretlemesinin sebebidir.

**Ama fikir dışarıdan alınmadı** — `kamuoyu()` bağımsız olarak kurulmuş ve
docstring'i gerekçeyi kendi cümlesiyle yazıyor. Burada kaydedilen şey bir
aktarım değil, **bir yakınsama**: aynı yapıya iki farklı bahis biçiminden
varılması, yapının kendisinin doğru olduğuna dair zayıf ama gerçek bir
işarettir.

---

## 8. Elo ve H2H — **ikisi de denendi, ikisi de geçmedi**

Dış çalışmada olup bizde **hiç bulunmayan** iki özellik var. Kod taramasıyla
doğrulandı: `elo`, `h2h` ve `xg` dizgeleri `backend/` altında hiç geçmiyor.

| Özellik | Bizde neden yok | Denenebilir mi |
|---|---|---|
| **Elo** (rakip gücüne göre düzeltilmiş takım gücü) | Dokuz denemenin hiçbirinde yok. `kalibre_form` **ham** formdu — rakip gücüne göre düzeltilmemişti; Elo tam o eksiği kapatan standart sinyaldir | **Evet**, korpustan türetilebilir. Yeni kaynak gerekmez |
| **H2H** (son 5 karşılaşma) | Aynı | **Evet**, aynı şekilde |

> **Güncelleme (2026-08-24): Elo artık denendi ve geçmedi.**
> Aşağıdaki üç gerekçe yazıldığı gün doğruydu; Faz 1'in ölçümleri
> (§3.23 kalibrasyon tavanı 0,00042 · §3.24 öğrenme eğrisi piyasaya
> yetişmeden düzleşiyor) *"eksik olan sütun"* dediği için tahsis kararı
> değişti. Sonuç: ham sinyal devasa (ev galibiyeti %16,8 → %68,1), artık
> **sıfır**, `kalibre_elo` +0,000086 [−0,000242, +0,000429] ve uydurulan
> katsayı **negatif**. Ayrıntı:
> [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.27.
>
> **H2H de denendi (§3.29) ve geçmedi**: ham yayılım 28 puan, artık sıfır,
> `kalibre_h2h` +0,000146 [−0,000208, +0,000517] ve katsayı +0,0050 —
> sıfıra yapışık. Kayıtlı sınır: `h2h_var` maçların yalnızca %41'inde açık.
>
> Bu satırın açık ucu kalmadı; aşağıdaki gerekçeler tarihçe olarak duruyor.

**Yazıldığı günkü gerekçeler.** Üç tanesi, sonuncusu belirleyici:

1. **A4 durma kuralı** — *"Gelmediği sürece aynı veriyle yeni model
   denenmez."* İkisi de aynı veriden türer; onuncu ve on birinci deneme
   olurlar.
2. **Null neredeyse kesin.** A1 piyasanın **kendi çizgi hareketinin** bile
   kapanışı yenemediğini ölçtü (uzatma %1,01). Piyasanın kendi bilgisi
   kendini yenemiyorsa, korpustan türetilen bir sıralama özelliğinin
   yenmesi için sebep yok.
3. **Fırsat maliyeti.** Havuz ekseni artık veri taşıyor ve hiç ölçülmedi.
   Kapanmış bir sorunun onuncu denemesine döngü harcamak, açık ve
   ölçülmemiş bir eksen dururken yanlış tahsistir.

**Yeniden açılma koşulu:** havuz ekseni ölçülüp kapanırsa (§6.3 B4/b), ya
da A4'ün saydığı üç kaynaktan biri gelirse.

> Bu satır, A3'ün seyahat ve derbi satırlarıyla aynı statüdedir:
> *"denenmedi"* ile *"denenemez"* farklı şeylerdir ve ikisi de yazılır.
> Elo ve H2H **denenebilir ama denenmedi** — bilinçli bir tahsis kararıdır,
> unutulmuş bir iş değil.

---

## 9. Özet

| # | Bulgu | Nereye gitti |
|---|---|---|
| 1 | Model sınıfı dış kontrolü — RF/XGB/SVM aynı tavana çarpıyor | §6.2 A4'e yeni alt bölüm |
| 2 | xG denendi (dışarıda) ve geçmedi; üstelik Süper Lig'i kapsamıyor | §6.2 A4 kaynak tablosuna satır |
| 3 | Beraberlik null'ı dışarıdan teyit ediliyor | Bu belge (§5); ürün metni değişmiyor |
| — | Elo ve H2H denenmedi, gerekçesiyle | §6.2 A4'e yeni tablo |
| — | Aktarılacak sanılıp aktarılmayan: değer bahsi çerçevesi | Bu belge (§7) |

**Kod değişikliği yok, ölçüm koşumu yok.** Dış bir çalışmanın sonucu bizim
ölçümümüzün yerine geçmez; yalnızca hangi soruların sorulmaya değer
olduğunu değiştirir.
