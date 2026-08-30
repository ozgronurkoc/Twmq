# "Gelecek Mimarisi" makalesi — depoyla madde madde eşleme

**Kapsam:** Depo dışından gelen bir akademik makalenin (`TWMQ: … Gelecek
Mimarisi`, 30 bölüm + Faz I–VIII yol haritası) madde madde karşılığı:
**hangisi zaten var ve ÖLÇÜLDÜ, hangisi kısmen var, hangisi gerçekten yeni,
hangisi ölçülmüş bir null'a geri dönüyor — ve makalenin hiç görmediği eksen.**
**İncelenen belge:** `TWMQ_Gelecek_Mimarisi_Akademik_Makale.md` (dış, depoda
değil)
**Bu belgenin tarihi:** 2026-08-30 · taban `9c40337`
**İlgili belgeler:** [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md)
§5.1 (ölçülmüş bulgular) ve §6 (projenin kendi sonlanan planı) ·
[`DIS_INCELEME_AZ_RAPORU.md`](DIS_INCELEME_AZ_RAPORU.md) ·
[`GELISTIRME_PLANI_ESLEMESI.md`](GELISTIRME_PLANI_ESLEMESI.md) (aynı türün
önceki örnekleri) · [`ARCHITECTURE_NEXT.md`](ARCHITECTURE_NEXT.md)

> **Künye — bu makale depo okunmadan yazıldı.** Projeyi **başlangıç
> çizgisinde** tarif ediyor: ölçüm altyapısı kurulacak, market intelligence
> eklenecek, Elo ve Poisson denenecek, ML gelecek, ensemble kurulacak,
> kalibrasyon merkeze alınacak. Bunların **tamamı** depoda var ve
> **koşuldu**; koşumların sonucu §5.1'de, kesitleri ve güven aralıklarıyla
> duruyor. Bu, makaleyi değersiz yapmaz — **iki buçuk gerçek boşluğa parmak
> bastı** (§4) ve depo o boşlukları henüz yazılı hâle getirmemişti. Ama
> statüsü **dış görüştür**, teyit değil.

---

## 1. Kısa cevap

| Kova | Sayı | Ne |
|---|---:|---|
| **Zaten var ve ölçüldü** | Faz I–V'in tamamı | ölçüm altyapısı · market intelligence · Elo/Poisson/form · ağaç toplulukları · yığın + kalibrasyon · model arenası · ileri yürüyüş · yeniden üretilebilirlik · veri kalitesi |
| **Kısmen var, bağlanmadı** | 2 | ortak dağılım (bağımsızlık varsayımıyla) · beklenen fayda (hesap var, kupon kurmaya bağlı değil) |
| **Gerçekten yeniydi → ölçüldü** | 1 | maçlar arası bağımlılığın **kuyruk** etkisi — ölçüldü ve **eksen kapandı** (§3.46, `spor_toto/kuyruk.py`) |
| **Ölçülmüş null'a geri dönüyor** | 1 | entropi / bahisçi anlaşmazlığını *sinyal* olarak kullanmak |
| **Makalede hiç yok** | 3 | havuz ekseni (müşterek bahis) · iddaa marjı · kupon-zamanı fiyat |

Sonuncu satır bu belgenin asıl bulgusudur. Makale baştan sona **tahmin
eksenine** bakıyor; projenin kendi ölçümü o ekseni kapattı ve açık kalan tek
kaldıraç makalede **bir kez bile geçmiyor**: "müşterek", "havuz", "oynanma
payı", "kalabalık" ve "iddaa" kelimelerinin tamamı metinde **sıfır** kez
bulunuyor.

---

## 2. Faz Faz eşleme

Makalenin §28'deki yol haritası ile deponun bugünkü hâli. Ölçüm sütunundaki
her sayı [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §5.1'den
**alıntıdır**; bu belge için yeni koşum yapılmadı.

| Makale fazı | Depo karşılığı | Ölçülen sonuç |
|---|---|---|
| **Faz I** — bilimsel ölçüm altyapısı | `evaluate.py` · `ortak.py` · `kosum.py` · `artefakt.py` | **Bitti.** Sezon dışarıda bırakmalı ölçüm, hafta üzerinden eşleştirilmiş bootstrap, koşum defteri (korpus parmak izi + git commit + tohum), Brier'in Murphy ayrışımı |
| **Faz II** — market intelligence | `odds.py` · `cizgi.py` · `bahisci.py` · `pazar.py` | **Bitti, üç null.** Kapanış açılışı geçiyor **+0,0025 [+0,0019, +0,0030]** (piyasa bilgiyi soğuruyor); çizgi hareketinin kapanış ötesine uzatması **%1,01**; bahisçi anlaşmazlığında ham sinyal favori gücüyle karışık, sabitlenince **kayboluyor** (güven kısma %0,02). §3.14–3.15 |
| **Faz III** — Elo · Poisson · takım gücü · form | `elo.py` · `dixon_coles.py` · `takim_gucu.py` · `takim.py` · `xg.py` | **Bitti, dördü de geçmedi.** `kalibre_elo` **+0,000086 [−0,000242, +0,000429]**, katsayı **negatif** (−0,0597); `kalibre_dc` **+0,000100 [−0,000261, +0,000472]**, katsayı **negatif** (−0,0492), tek başına Brier 0,6153 (piyasa 0,5933); `kalibre_form` −0,0003 [−0,0007, +0,0001]; `kalibre_h2h` +0,000146, `kalibre_seri` +0,000145. §3.10–3.13 (T1–T5), §3.27–3.29 |
| **Faz IV** — makine öğrenmesi (GBM/LightGBM) | `agac.py` | **Bitti, model sınıfı itirazı kapandı.** `agac` +0,000368 [−0,000009, +0,000750]; `agac_ham` **+0,000667 [+0,000282, +0,001068]** — anlamlı biçimde *kötü*. Kapasite monoton zararlı: yaprak 4 → 31'de Brier 0,5940 → 0,6120. Mekanizma ayrışımda: kalibrasyon iyileşiyor (REL 0,00042 → 0,00015), **çözünürlük kaybediliyor** (0,05657 → 0,05597). §3.30 |
| **Faz V** — ensemble + kalibrasyon | `yigin.py` · `kalibre.py` · `kalibrasyon.py` · `recalibrate.py` | **Bitti, geçmedi.** Kat-dışı yığın (üst-öğrenici sezon katlarıyla, **sezon** sınırlarında) **−0,000137 [−0,000402, +0,000148]** — serinin ilk negatif nokta tahmini, ama aralık sıfırı kesiyor. Ağırlıklar sebebini söylüyor: piyasa +0,5307 · kademe +0,3242 · agac +0,2347 (**üçü de piyasa çıpalı**), piyasadan bağımsız tek taban Dixon-Coles **−0,0693**. İzotonik `orantili` üzerinde geçti (−0,00036 [−0,00067, −0,00003]), `shin` üzerinde **hiçbir şey eklemiyor**. §3.32, §3.18 (A5) |
| **Faz VI** — joint probability | `secim.py` · `getiri.py` | **Kısmen.** Kupon düzeyi dağılım hesaplanıyor ve karar katmanı onu kullanıyor (B0, §3.19: seçim `P(k≤2)`'ye göre kurulunca **+6,02 puan** ve **%26 daha az kolon**) — ama `secim.py:271` açıkça *"maçlar bağımsız varsayılarak"* diyor. Makalenin §12–13'ü **gerçek bir boşluğa** basıyor; ayrıntı §4.1 |
| **Faz VII** — decision optimization | `getiri.py` · `secim.py` · `havuz.py` · `core.py` (kaplama) | **Kısmen.** Müşterek beklenen değer **kapalı formda** hesaplanıyor (§3.34) ama kupon **kurma** motoruna bağlı değil. Kaplama tarafı kapandı: Hamming, kanıtlanmış optimal. Ayrıntı §4.2 |
| **Faz VIII** — araştırma platformu | `kosum.py` · `arena.py` · `health.py` · `/saglik` | **Bitti.** Koşum kaydı (veri sürümü + kod commit'i + tohum + paket sürümleri), 1.801 satırlık sağlık katmanı, kayıtlı kontrol envanteri, `data_quality` blokları |
| §18 **model karşılaştırma laboratuvarı** | `arena.py` | **Bitti — ve makalenin istediğinden sıkı.** On bir ayrı koşum ilk kez tek kesitte: aynı haftalar · aynı gruplama · aynı bootstrap tohumu · aynı referans. Sonuç: **hiçbir aile piyasayı geçmedi.** Aile başına **tek temsilci** kuralı ölçüm görülmeden yazıldı. §3.41 |
| §10 **walk-forward** | `arena.py` ileri yürüyüş | **Bitti — ve tabloyu sertleştirdi.** Kronoloji zorlandığında piyasanın artığını öğrenen aileler **2–3 kat kötüleşiyor**: §3.26–§3.35'in küçük kazançlarının bir kısmı kronoloji dışı eğitimin eseriymiş. §3.41 |
| §21 **reproducibility** | `kosum.py` | **Bitti.** `data/kosumlar/<zaman>-<ad>/` altında `cikti.json` + `ortam.json` |
| §22 **DataQualityScore** | `health.py` · `/api/stats` `data_quality` | **Bitti.** Sayım çelişkileri, tekrar eden diziler, eksik haftalar, kapsama kapıları; sağlık katmanı DEGRADED kararını ayrı veriyor |
| §5 **zaman sızıntısının önlenmesi** | `test_sizinti.py` · `arena.py` sızıntı sözleşmesi · `benzer.py` `tarih` kesmesi | **Bitti.** Sızıntı sözleşmesi §3.41'de dış incelemeden gelen üç eksikten biriydi ve uygulandı |

---

## 3. Makalenin dört araştırma sorusu

Makale §2'de dört soru soruyor. Üçünün cevabı **ölçülmüş** durumda.

### RQ1 — "Piyasa kapanış olasılıklarını aşan ek bilgi tarihsel verilerden çıkarılabilir mi?"

**Cevap: hayır — ölçüldü.** Dokuz özellik, dört bağımsız açı, 31.103 maçlık
korpus, sezon dışarıda bırakmalı, hafta üzerinden eşleştirilmiş bootstrap.
"Geçti" ölçütü güven aralığının **tamamen** sıfırın altında kalmasıdır.
Tek bir "geçti" yok (§6.2 A4). Model arenası aynı sonucu tek kesitte
doğruladı (§3.41).

İki bağımsız teyit: açılış çizgisi kapanışın **altında** (+0,0025, aralık
tamamen sıfırın üstünde) ve **piyasanın kendi hareketi bile kapanışı
yenemiyor** (uzatma %1,01). Bu, *"iyi model bulamadık"* demekten farklı bir
cümledir.

Üçüncü teyit LOFO'dan: **hiçbir özellik taşımıyor**, onun beşi net negatif —
en zararlısı `ayrisma` (−0,000159), `elo_farki` (−0,000042) ve `h2h_farki`
(−0,000065) de negatif (§3.33).

**Not — kapanan şey soru, eksen değil.** §6.2 A4 bu ayrımı bir kez yanlış
yazıp düzeltti: kapanan soru *"elimizdeki veriden türetilen bir özellik
piyasayı geçebilir mi"*dir. **Tahmin ekseni açıktır ve kapatılmaz** — projenin
amacı odur.

### RQ2 — "Bu ek bilgi sızıntıdan ve aşırı uyumdan arındırılmış out-of-sample testlerde de devam ediyor mu?"

**Cevap: soru ters yönde cevaplandı.** Ek bilgi zaten yoktu; out-of-sample
sıkılaştırma kalan küçük etkileri **daha da** silmiştir. İleri yürüyüş
ölçümü tam olarak bunu gösterdi (2–3 kat kötüleşme, §3.41).

Ayrıca bir tavan ölçüldü: Brier ayrışımına göre piyasanın toplam
**güvenilirlik borcu 0,00042** (sapma payı 0,00021), çözünürlüğü 0,05657.
Kalibrasyon ekseninde alınacak yol **0,0004 kadardır** — aranan etkiler bu
tavanın üstünde, yani geçmemeleri kapasiteden değil (§3.23).

Öğrenme eğrisi üçüncü kez aynı yeri işaret etti: `kalibre_bant` 2.216 →
23.327 maçta 0,00348 iniyor ama **son adım 0,00006** ve 0,59373'te duruyor;
piyasa 0,59364. **Sorun satır sayısı değil sütun** (§3.24).

### RQ3 — "Farklı bilgi kaynakları tek tek modellerden daha iyi bir ensemble kurabilir mi?"

**Cevap: hayır — ölçüldü** (§3.32, yukarıda). Ve ağırlıklar *neden* olmadığını
söylüyor: dört tabandan üçü piyasa çıpalı, dördüncüsünün katsayısı negatif.
**Yeni bilgi değil, aynı bilginin farklı paketlenmesi.**

### RQ4 — "Kupon düzeyindeki ortak yapı kullanılarak sabit bütçe altında daha etkin kararlar üretilebilir mi?"

**Cevap: evet, ve kısmen ölçüldü — ama makalenin sandığı yerden değil.**
Karar katmanı B0'da (§3.19) seçim `P(k≤2)`'ye göre kurulunca **+6,02 puan** hedef ve
**%26 daha az kolon** geldi; eşik kuralı 36 haftanın 35'inde optimalin
altındaydı. Aynı kazancı tahmin tarafında elde etmek **~0,10 Brier**
gerektirirdi — yani üç mertebe daha büyük bir kazanç.

Sebebi §3.25 verdi: **piyasanın sıralaması Brier'inin ima ettiğinden çok
güçlü.** Taban isabet %51,1 iken en emin 5 maç **%82,3 [%79,7, %84,6]**,
NDCG 0,8971 (bilgisiz zemin 0,7896). `en_iyi_secim` Brier'i değil **sıralamayı**
kullanıyor.

Bu, makalenin en isabetli sezgisidir ve deponun kendi ölçümüyle
doğrulanmıştır: **kazanç karar katmanındadır, tahmin katmanında değil.**

---

## 4. Gerçekten yeni olan — iki buçuk madde

Her birine, deponun §6 disiplini gereği, **ölçüm görülmeden yazılmış durma
kuralı** eklendi.

### 4.1 Maçlar arası bağımlılık — makalenin §12–13'ü · **ÖLÇÜLDÜ (§3.46)**

> **Bu bölüm bir kez yanlış yazıldı ve düzeltildi (2026-08-30).** İlk sürüm
> boşluğun *"hiç ölçülmediğini"* söylüyordu. Yanlıştı:
> `tests/test_invariants.py` varsayımı zaten sınıyordu. Doğru cümle
> *"sınandı ama dar sınırlı bir bekçiyle, güven aralığı olmadan, yalnızca
> kupon kesitinde, ve kuyruğa çevrilmeden"*dır. Aradaki farkı yutmak, var
> olan bir bekçiyi yok saymak olurdu.

`secim.py:271` açıkça yazıyor:

```python
def _carpim(dagilimlar, secimler) -> float:
    """Maçlar bağımsız varsayılarak seçim kümesine düşme olasılığı."""
```

Makale bunu doğru teşhis ediyor. Ama **önemi tahminde değil, kuyruktadır** —
ve bu ayrım makalede yok:

* **Tahminde önemsiz.** Bağımsızlık varsayımı tek tek `P(Y_i)`'leri
  değiştirmez; Brier de log kaybı da bu varsayımı hiç kullanmaz.
* **Kuyrukta önemli olabilir.** `P(k ≥ 12)` korelasyonlu Bernoulli
  toplamında **şişer**. Hedefin `P(en iyi kolon ≥ 12)` olduğu ölçüldüğüne
  göre (§5.2 bulgu 1) bu doğrudan hedef ölçüsünü ilgilendirir.

**Ölçüldü, ve eksen kapandı** (`spor_toto/kuyruk.py`, §3.46). Ön kayıtlı
kural — *aralık sıfırı kesiyorsa eksen kapanır* — üç kesitte de sağlandı:

| Kesit | Hafta | Maç | ρ | %95 aralık |
|---|---:|---:|---:|---|
| Kupon (varsayılan) | 36 | 540 | −0,02022 | [−0,03926, +0,00079] |
| Kupon (geniş) | 114 | 1.710 | −0,00349 | [−0,01724, +0,01020] |
| **Korpus** | **183** | **31.103** | **−0,00009** | **[−0,00102, +0,00080]** |

Kuyruğa çevrildiğinde (tek faktör Gauss kopulası + Gauss-Hermite, RNG yok):
korpus aralığının üst sınırında `P(k≥14)` yalnızca **%5** şişiyor. Nokta
tahminleri negatif, yani kuyruk şişmiyor.

**Kapanışın sınırı da yazıldı.** Kupon kesiti *tek başına* bu sonucu
veremezdi: 114 haftanın aralığı üst ucunda %82'lik bir şişmeye hâlâ izin
veriyor. Sonucu taşıyan şey korpusun 183 haftasıdır.

**Yan ürün — makalenin dolaylı katkısı.** Ölçüm iki kusur buldu:
(1) eski bekçinin istatistiği yanlıştı (`Var(K)` yerine `Var(K−M)` olmalıydı;
korpusta 36,09 yerine 0,98) ve `ortak.kacak_dagilimi`nin docstring'i o yanlış
sayıyı varsayımın kanıtı diye anıyordu — ikisi de düzeltildi;
(2) ham artıklarla görünen `ρ = +0,0077` tamamen **kalibrasyon
yanlılığıydı** (favori, fiyatın söylediğinden maç başına ~5 puan sık tutuyor).
Ayrılmasalardı ölçüm var olmayan bir bağımlılık raporlayacaktı.

### 4.2 Beklenen fayda optimizasyonu — makalenin §15'i

Makale `max U(C) = Beklenen Getiri − Bedel − Risk` diyor. Yarısı hazır:
`getiri.py` müşterek beklenen değeri **kapalı formda** hesaplıyor (§3.34).
Eksik olan **bağlantı**: `secim.py`/`havuz.py` kupon kurarken bu amaç
fonksiyonunu kullanmıyor.

Bu, projenin kendi belgesinin **"kaplamanın ve havuzun buluştuğu yer;
projenin en özgün işi"** dediği B3'tür (§6.3).

**Ama makalenin formülasyonu bir şeyi atlıyor** ve bu §3.34'te ölçüldü:
sonucu belirleyen tahminci değil **kalabalık varsayımıdır**. Kalabalık modeli
`orneklem`den `favori`ye çevrildiğinde getiri oranı 0,156 → 0,007, yani
**22 kat** düşüyor. Havuz büyüklüğü getiriyi hiç belirlemiyor. Yani §15'in
amaç fonksiyonu, `Beklenen Getiri` terimi **ölçülmüş bir kalabalık modeline**
dayanmadıkça bir sayı değil bir varsayımdır.

**Durma kuralı:** B4 zaten yazılı (§6.3) — bağıntı bootstrap %95 aralığıyla
sıfırı kesmiyorsa eksen açık, kesiyorsa kapalı.

### 4.3 (yarım) Risk katmanı — makalenin §17'si

Sunum önerisi **iyi ve alınmalı**: her tahminin yanında güven, entropi, model
anlaşmazlığı ve veri kalitesi göstermek, deponun *"süslenmiş bir olasılık,
süslenmemiş bir yalandır"* kuralıyla aynı yöne bakar.

**Ama bir ayrım şart.** Bunları *gösterge* olarak sunmak ile *sinyal* olarak
kullanmak farklı şeylerdir ve ikincisi **ölçülüp elendi**: bahisçi
anlaşmazlığında ham ilişki favori gücüyle karışıktı, favori sabitlenince
tamamen kayboldu; model ortalama anlaşmazlıkta güvenini **%0,02**
değiştiriyor (§3.15). Venn-Abers de aynı yeri gösterdi: ortalama aralık
genişliği **0,00472** — piyasanın olasılıkları sıkı destekleniyor (§3.33).

Yani §17 bir **arayüz** maddesidir (Faz C/C4), bir model maddesi değil.

---

## 5. Makalenin görmediği üç şey

Bunlar ürünü doğrudan vuran, **ölçülmüş** gerçekler.

### 5.1 Havuz ekseni — açık olan tek kaldıraç

Makale baştan sona tek bir çarpana bakıyor. Projenin hedefi ise **çarpımsal
üç etkendir** (§6.1):

```
Beklenen getiri  =  P(tutturma)  ×  Pay(tutturunca)  −  Bedel
                    ─────────────    ───────────────     ──────
                    tahmin ekseni    havuz ekseni        kaplama ekseni
```

| Eksen | Durum |
|---|---|
| **Tahmin** | İki bağımsız denemede ~sıfır artık (§5.1) — makalenin tamamı burada |
| **Havuz** | **Motor hazır, veri geldi, ölçüm yok** — makalede **hiç yok** |
| **Kaplama** | Çözüldü: Hamming, kanıtlanmış optimal — makale §14'te doğru tespit ediyor |

Spor Toto **müşterek bahistir**: ikramiye havuzdan kazananlara bölünür.
Sonuç, makalenin çerçevesine hiç sığmayan bir cümledir:

> Aynı olasılığa sahip iki sonuçtan **daha az oynananı** işaretlemek,
> tutturma olasılığını değiştirmeden beklenen getiriyi artırır.

Bunun için **piyasayı yenmek gerekmiyor.** RQ1'in ölçülmüş "hayır"ı bu ekseni
kapatmaz. Altyapı da hazır: `super_toto_hafta.kamuoyu` oynanma yüzdesini
taşıyor, `kupon_kur` `crowd_ratio` hesaplıyor (1. haftada 0,451 — kupon
kalabalığın seyrek olduğu yere düşüyor).

İki bulgu tezi zayıflatıyor ve ikisi de kayıtlı (§6.3): halkın modal kuponu
ile piyasanın favori kuponu **birebir aynı** çıktı (oynanma verisi yön için
sinyal taşımıyor, yalnızca **pay** için); ve **isabet kalabalıkla birlikte
geliyor** — 13+ haftalarda ortalama 9,00 favori, 11 ve altı haftalarda 7,47.
Yani avantaj, onu kazandığın haftaların aynı zamanda payın küçüldüğü haftalar
olmasıyla kısmen kendini yiyor. **Ölçülmesi gereken artık "avantaj var mı"
değil, "net mi".**

### 5.2 İki marj birbirinin yerine geçmiyor

Makalenin "piyasayı geç" ölçütü tek bir fiyat evreni varsayıyor. Ölçülen
gerçek şu: ölçümlerin dayandığı piyasa marjı **%7,26**, oynanan iddaa marjı
**%16,93 (bayi) / %21,32 (web)**. Seviye tutmaz, **yapı tutar** (favori
sıralaması ve marj arındırılmış olasılıklar).

Bunun iki sonucu var. Birincisi: 0,0005–0,0015'lik Brier kazançları %17'lik
marjın yanında hiçtir — makalenin §25'teki `CI(ΔBrier) < 0` ölçütü *gerekli*
ama **yeterli değil**. İkincisi: iddaa ekseninde kalibrasyon ölçmek için
**45 kupon haftası** gerekiyor (ölçülen sd 0,00358, aranan etki 0,0015) ve
elde bir hafta var (§3.22 Ö4). Bugün ölçülebilen tek parça: bayi–web
arındırmadan sonra ortalama **0,53 puan** ayrışıyor — marj ayrı, görüş aynı.

### 5.3 Kapanış fiyatı kupon verilirken elimizde yok

Bütün ölçüm çerçevesi **kapanış** fiyatına dayanıyor. Ama kupon ilk maçtan
önce kapanır ve oranlar her maçın saatine kadar oynar: **haftanın son maçları
için kapanış fiyatı kupon verilirken yoktur** (commit `14650a7`).

Bedeli isabet değil **kolon: %22 artış** (2.686 → 3.290). Hareket 4 puanı
aştığında kapanış gerçeği neredeyse birebir tutturuyor, açılış sapıyor — yani
kayıp gerçek. Makalenin §4 "zaman damgası" ilkesi doğru ama bu somut vakayı
görmüyor; ilke burada bir **ürün kusuruna** çeviriliyor.

### 5.4 Ve bir eksik daha: örneklem aritmetiği

Makale §11 ve §25'te "istatistiksel anlamlılık gösterilecek" diyor ama **süre
bütçelemiyor.** Depo bunu ölçtü, tahmin etmedi:

| Soru | Gereken | Elde |
|---|---|---|
| Havuz ekseni bağıntısı (`scripts/faz_b.py --guc`) | **≈71 ikramiyeli hafta ≈ 3,5 sezon** | 3 hafta (README §12; §6.3'ün bloğu yazıldığında 2 idi) |
| İddaa ekseni kalibrasyonu (§3.22) | **45 kupon haftası** | 1 hafta |

Zaman bütçesi olmayan bir yol haritası, plan değil temennidir. Bu iki sayı
makalenin Faz VI–VIII'ini bu sezon **fiilen imkânsız** kılıyor ve bunu
şimdiden bilmek, yıl sonunda öğrenmekten iyidir.

---

## 6. Neden yol haritası olarak benimsenmiyor

Üç gerekçe, üçü de ölçüme dayanıyor.

**1. Cevabı bilinen soruyu tekrar sormak.** Faz I–V koşuldu. Aynı veriyle yeni
model denemek, **aynı soruyu daha yüksek sesle sormaktır** (§6.2). Makalenin
§7.3'teki liste (Logistic Regression · Random Forest · Gradient Boosting ·
LightGBM · XGBoost) `agac.py`de denendi ve kapasite **monoton zararlı** çıktı.

**2. Çoklu test kapısını yeniden açmak.** `arena.py` bunu ölçüm görülmeden
yazılmış bir kuralla kapattı: **aile başına tek temsilci**, ve temsilci seçme
kuralı her aile için tek cümle. Gerekçesi modülün kendi docstring'inde:
*"on dokuz adayın en iyisine bakıp 'aile geçti' demek çoklu test
problemidir."* Makalenin "model ailesi ekleyelim, ensemble'a katalım" listesi
o korumayı geri açar — ve bu, makalenin **kendi §26'sıyla** (Bilimsel
Dürüstlük İlkesi) çelişir. Yeterince model denenirse biri şansa "geçer";
o an §26 ihlal edilmiş olur, üstelik ihlali yapan şey §28 olur.

**3. Fırsat maliyeti.** Açık olan tek eksen havuz ve **veri birikmesi zaman
alıyor** (§5.4). Tahmin ekseninde geçirilen her hafta, havuz ekseninde
toplanmamış bir haftadır — ve toplanmamış veri hiçbir zaman ölçülemez.

---

## 7. Ne değişiyor, ne değişmiyor

**Değişmiyor:** [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md)
§6'daki sonlanan plan. Faz A kapandı (arayış), Faz B açık (havuz), Faz C
yürüyor (ürün), Faz D bitiş tanımı. Makale bu planı değiştirmiyor çünkü
sorduğu soruların üçünün cevabı o planın içinde zaten var.

**Değişti, sonra kapandı:** makalenin tek gerçek katkısı olan **kuyruk
bağımlılığı** önce §6.2'ye durma kuralıyla düşüldü, sonra **ölçüldü** ve kural
işletildi — eksen kapandı (§3.46). Ölçüm `spor_toto/kuyruk.py`de, koşumu
`python -m spor_toto.kuyruk`.

Makale böylece kendi türünün en iyi sonucunu verdi: bir dış görüş, cevabı
bilinen sorular listesi getirdi ama içinde **bir tane** gerçekten açık soru
vardı, o soru ölçüldü ve iki kusur ortaya çıkardı (yanlış istatistikli bir
bekçi, ve yanlılıkla karışan bir korelasyon). Dış incelemelerin bu depoda
tuttuğu yer tam olarak burasıdır.

**Makalenin kalıcı değeri** yol haritasında değil, §1–§2 ve §26–§30'daki
**çerçevede**: tahmin ile garantiyi ayırması, kalibrasyonu doğruluktan
ayırması, "ölçülmeyen üstünlük, üstünlük değildir" ilkesi. Bunlar deponun
zaten uyguladığı kurallardır ve makale onları **iyi ifade ediyor**. Bir dış
gözün aynı ilkelere bağımsız olarak varması, ilkelerin kendisi hakkında
bilgi taşır.

> **Tek cümlelik cevap.** Makale *nereye gidilmesi gerektiğini* doğru
> anlatıyor; oraya **çoktan gelinmiş** olduğunu ve orada **ne bulunduğunu**
> bilmiyor. Bulunan şey bir başarısızlık değil, projenin cevaplamak için
> kurulduğu sorunun cevabı: bu alandaki araçların neredeyse tamamı üstünlük
> *iddia eder*; hiçbiri üstünlüğün yokluğunu **ölçmez**.
