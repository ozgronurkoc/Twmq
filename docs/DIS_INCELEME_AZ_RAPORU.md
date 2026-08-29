# Dış inceleme — "A'dan Z'ye geliştirme raporu" (86/100)

**Kapsam:** Depo dışından gelen, 64 bölümlük bir değerlendirme raporunun
madde madde karşılığı: **hangisi zaten var, hangisi geçersiz, hangisi
gerçekten eksikti, hangisi bilerek reddedildi.**
**İncelenen rapor:** `twmq_AZ_gelistirme_raporu1.md` · rapor tarihi
2026-08-26 · raporun baktığı commit `cc16d74`
**Bu belgenin tarihi:** 2026-08-29 · HEAD `2905c30`
**İlgili belgeler:** [`DIS_INCELEME.md`](DIS_INCELEME.md) ·
[`DIS_INCELEME_ALPHAPY.md`](DIS_INCELEME_ALPHAPY.md) (aynı türün ilk iki
örneği) · [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.41
(bu incelemenin ürettiği ölçüm), §5.1, §6, §7

> **Künye — bu bizim ölçümümüz değildir.** 86/100 notu ve alt başlık
> puanları raporu yazanın değerlendirmesidir. Rapor kendi kaynak notunda
> bulgularının **README, `pyproject.toml`, test dosyası listesi ve commit
> başlıkları** üzerinden üretildiğini yazıyor; modüllerin içi okunmadı.
> Bu, raporu değersiz yapmaz — aksine bir dış gözün *belgelerden* ne
> görebildiğini ölçer, ki bu da bir bulgudur. Ama puanların statüsü
> **teyit**tir, ölçüm değil.

---

## 1. Kısa cevap

Rapor 64 bölümde onlarca öneri sıralıyor. Dördü hariç hepsinin karşılığı
zaten depoda vardı. Üçü gerçekten eksikti ve **bu incelemeden sonra
uygulandı**; biri bilerek reddedildi ve gerekçesi ölçülmüştü.

| Kova | Sayı | Örnek |
|---|---:|---|
| **Zaten var** | çoğunluk | bootstrap güven aralığı, iç içe CV, LOFO, Venn-Abers, yığınlama, kapanış çizgisi (raporun "CLV"si), koşum defteri, model kaydı, baseline kaydı |
| **Rapor bir PR geride** | 1 blok | `fiyatlar.py`, 3. hafta, sonuç sekmesi — PR #22, raporun baktığı commit'ten sonra |
| **Gerçekten eksikti → uygulandı** | 3 | **Model Arena** · **ileri yürüyüş** · **sızıntı sözleşmesi** |
| **Reddedildi, gerekçesi ölçülmüş** | 4 | ROI/Max DD sütunları · SHAP · kadro/sakatlık özellikleri · ölçülmemiş sayının arayüze çıkması |

**Ve uygulanan üçünün ürettiği sayı, raporun ana tezini değiştirmedi —
sertleştirdi.** Ayrıntı §4'te: ileri yürüyüş, §3.26–§3.35'in küçük
kazançlarının bir kısmının **kronoloji dışı eğitimin** eseri olduğunu
gösterdi.

---

## 2. Zaten var — rapor niçin göremedi

Raporun P0/P1 listesindeki maddelerin karşılığı:

| Rapor maddesi | Depodaki karşılığı | Nerede ölçüldü |
|---|---|---|
| §13 bootstrap CI, paired bootstrap | `evaluate.bootstrap_farki` — eşleştirilmiş, hafta üzerinden, sabit tohum | her koşumda; kural `gecti` bayrağında |
| §12 walk-forward | **yoktu** → bkz. §3 | — |
| §31 ablation framework | `agac.lofo` (Leave-One-Feature-Out, sezon katlarıyla) | §3.33 |
| §11 ensemble + calibration | `yigin.YiginTahminci` (kat dışı yığınlama) + `kalibre` (Venn-Abers) + `recalibrate` (19 basamaklı kademe) | §3.32, §3.33 |
| §16 CLV | `cizgi.py` — kapanış çizgisi verimliliği; kapanış açılışı **+0,0025 Brier** geçiyor, aralık [+0,0019, +0,0030] | §3.14 |
| §19 market benchmark / baseline registry | `predict.referans_fabrikalar()` — `duzgun` (mutlak zemin), `sezon_sabiti` (naif), `piyasa` (aşılması gereken çizgi) | §3.10, §3.13 |
| §22 reproducibility, experiment manifest | `kosum.py` — dataset sha256, git commit, kirli durum, paket sürümleri, tohumlar | §2.6 |
| §36 model registry | `artefakt.py` — zarf + korpus parmak izi + **bayatlık** denetimi | §2.5 |
| §33 multiple testing | §8'in kendi risk maddesi; hold-out dokunulmaz, tarama ile hold-out ayrı | §8 |
| §30 model drift (rolling Brier) | `evaluate.ogrenme_egrisi` + haftalık Brier; **tam bir `drift.py` hâlâ yok** | §3.24 |
| §43 Monte Carlo CI | `analysis.monte_carlo_report` + sağlık kontrolü | — |
| §18 Bayesian model comparison | kısmen: `bayes.py` tahmin katmanında, model kıyası bootstrap ile yapılıyor | — |

**Niçin göremedi:** README 77 bin karakter ve yol haritasının kendisi ayrı
bir belgede (4.300 satır). Rapor README §10'a bakmış — ve o tablo
**gerçekten bayattı** (§5). Yani raporun kaçırdığı şeylerin bir kısmı
raporun kusuru değil, belgenin kusuruydu.

---

## 3. Gerçekten eksik olan üç şey

### 3.1 Model Arena — `spor_toto/arena.py`

Raporun §10'u haklıydı ve itiraz koda bağlandı.

Depoda on bir ölçüm koşumu vardı ve her biri **kendi modülünde kendi
tablosunu** yazıyordu (`cizgi`, `disari`, `kalibrasyon`, `bahisci`, `agac`,
`recalibrate`, `yigin`, `kalibre`, `beraberlik`). Bu tabloların sayıları
doğrudan kıyaslanamıyordu: kesitleri farklı, gruplamaları farklı, bir kısmı
farklı marj arındırma çevriminde ölçülmüştü (§3.18'in ölçek uyarısı tam
olarak bunun izidir).

Yani *"Elo geçmedi"* ile *"Dixon-Coles geçmedi"* aynı cinsten iki cümle
değildi. Arena bunu düzeltir: **aynı haftalar, aynı gruplama, aynı bootstrap
tohumu, aynı referans.**

İki tasarım kararı raporun istediğinden farklı:

- **Aile başına tek temsilci.** Kademenin 19 basamağını tabloya dökmek
  arenayı `recalibrate.rapor()`un kopyası yapardı; daha kötüsü, 19 adayın
  en iyisine bakıp "aile geçti" demek tam da §8'in uyardığı çoklu test
  hatasıdır. Temsilci seçme kuralı **ölçüm görülmeden** yazıldı: kademe
  kümülatif olduğu için temsilci `KADEMELER[-1]`, "en iyi basamak" değil.
- **`ROI` ve `Max Drawdown` sütunları konmadı.** Rapor §17'de istedi.
  `getiri.py` o hesabı kapalı formda veriyor (§3.34) ama havuz ekseninde
  elde 3 haftalık ikramiye kaydı var ve §6.3b ölçülmüş biçimde yazıyor:
  orta büyüklükte bir etkiyi ayırt etmek ≈71 ikramiyeli hafta ister. Boş
  bir `ROI` sütunu, ölçülmemiş bir sayıya tabloda yer ayırmak olurdu.

Arenanın **yan ürünü** raporun hiç sormadığı bir kusuru açığa çıkardı ve o
kusur bu incelemenin en somut kazancı olabilir — bkz. §3.4.

### 3.2 İleri yürüyüş — `evaluate.ileri_yuruyus`

Raporun §12'si haklıydı ve itiraz **ölçüldü**.

Depodaki en güçlü ölçüm `sezon dışarıda bırakmalı`ydı (`sezon_anahtari`) ve
o ölçüm bir şeyi ölçmüyordu: **zamanı.** 2021/22 sezonu ölçülürken model
2022/23, 2023/24 ve 2024/25'te eğitiliyordu — yani geleceği gören bir
ölçüm.

Bu, dışarıda bırakmalı ölçümü geçersiz kılmaz: soru *"bu sinyal veride var
mı?"* ise doğru araç odur. Ama başka bir soruyu cevapsız bırakıyordu ve o
soru **ürünün kendi sorusudur**:

> O hafta, yalnızca o güne kadar bilinenle, ne kadar iyi tahmin
> edebilirdik?

Sonuç §4'te.

### 3.3 Sızıntı sözleşmesi — `tests/test_sizinti.py` + `health.sizinti_sozlesmesi`

Raporun §21'i haklıydı ama gerekçesi eksikti. Sızıntı denetimleri **vardı**
(`test_arama.py`, `test_recalibrate.py`, `test_egitim.py`, `test_elo.py`) ve
hiçbiri kaldırılmadı. Eksik olan şey bir **sözleşme**ydi: yeni bir tahminci
eklendiğinde onu kimse otomatik denetlemiyordu. Kural yazılı değil, âdetti —
ve âdet, `arena.py` gibi bütün aileleri tek listede toplayan bir kayıt
geldiğinde ilk bozulacak şeydir.

Bu kontrolün kovaladığı hata **sessizdir ve ters yönlüdür**: sızan bir model
*daha iyi* skor verir, yani hata gibi değil **başarı gibi** görünür. Sağlık
katmanına girmesinin sebebi budur.

**Yazarken iki gerçek kusur çıktı** ve ikisi de raporun listesinde yoktu:

1. **İlk yazdığım kronoloji denetimi boştu.** Eğitim setinin en büyük grup
   indeksinden bir fazlasını "sınav" sayıyordu — yani iddiayı denetlenecek
   setin kendisinden türetiyordu ve **her zaman doğruydu**. Bekçilik testi
   (`hafta_disarida_birak`ı yerine koy, kırılmalı) bunu yakaladı. Denetim
   artık eğitim setini **ve sınavı** ayrı ayrı kaydediyor.
2. **`test_egitim.py`'deki katman ayrımı bekçisi iki yönden de yanlıştı.**
   Kaynakta `"egitim"` dizgesini arıyordu. *Yanlış pozitif:* "eğitim seti"
   sıradan bir Türkçe ifadedir ve `odds.py` bugün `korpus_haftalari`den bir
   **performans notunda** bahsediyor. *Yanlış negatif:* dizge araması
   `importlib` ile ya da korpus dosyasını doğrudan açarak yapılan bir
   okumayı kaçırırdı. Denetim artık **import düzeyinde** (AST) çalışıyor ve
   gövdenin tamamını geziyor — tembel (fonksiyon içi) import de yakalanıyor.

### 3.4 Çökme tespiti — raporun sormadığı, arenanın bulduğu

Arena kupon kesitinde koşturulunca dört satır *"ölçtük, fark yok"* gibi
görünen bir sayı yazdı:

    izotonik      0,5740   +0,0000
    yigin         0,5740   +0,0000
    dixon_coles   0,6667   +0,0927

Dördü de ölçüm değildi. Depodaki tahmincilerin çoğu eğitilemediğinde
**sessizce bir tabana düşer**: `yigin` üst-öğrenici kurulamazsa ilk tabanına
(`piyasa`), `beraberlik` yeterli nokta yoksa piyasayı olduğu gibi geçirir,
`dixon_coles` takım eşleşemezse düzgüne düşer. Her biri kendi yerinde
**doğru** bir karar — uydurma bir katsayı üretmektense bilinen bir görüşü
taşımak. Ama arenada bedeli var: `+0,0000` yazan satır "model hiç koşmadı"
demektir ve öyle okunmaz.

`arena.cokme` bunu haftalık skor vektörü üzerinden yakalar (bir aday
kesitteki **her** haftada bir zeminle aynı Brier ve log kaybını veriyorsa o
zeminin kendisidir) ve satırı `↳piyasa` diye işaretler. 138 haftanın
hepsinde dört basamak birden tesadüfen tutmaz.

---

## 4. Uygulananın ürettiği sayı — ve raporun ana sorusuna cevabı

Raporun §7'si en kritik soruyu doğru soruyor:

> Bu küçük iyileşme gerçek bir sinyal mi, yoksa örneklem gürültüsü mü?

Arena + ileri yürüyüş bu soruya **üçüncü bir cevap** getirdi. Tam tablolar
ve koşum künyesi §3.41'de; buradaki özet o bölümün sonucudur.

**Birinci bulgu — arena, on bir ayrı ölçümü ilk kez tek tabloda topladı ve
sonuç değişmedi:** 183 hafta, 31.103 maç, 10 aile, sezon dışarıda
bırakmalı — **hiçbir aile piyasayı geçmedi.** En yakın olan `yigin`,
ΔBrier −0,0001, aralık [−0,0004, +0,0002] — sıfırı kesiyor.

**İkinci bulgu — ve bu yeni:** ölçüm kronolojik hâle getirilince, piyasanın
üstüne bir düzeltme öğrenen ailelerin **hepsi kötüleşti.** Aşağıdaki iki
sütun **birebir aynı 138 haftada** ölçüldü (2021/22 her ikisinden de
dışarıda); değişen tek şey her katın eğitim setidir:

| aile | dışarıda bırakmalı ΔBrier | ileri yürüyüş ΔBrier | değişim |
|---|---:|---:|---|
| `kalibre_etkilesim_favori` | +0,0008 | +0,0018 | **2,3× kötü** |
| `agac` (LightGBM) | +0,0004 | +0,0011 | **2,8× kötü** |
| `venn_abers` | +0,0002 | +0,0006 | **3× kötü** |
| `izotonik` | +0,0001 | +0,0000 | ~aynı |
| `beraberlik_bant` | +0,0000 | −0,0000 | ~aynı |
| `yigin` | −0,0002 | −0,0001 | ~aynı |
| `dixon_coles` | +0,0167 | +0,0167 | dört basamakta aynı |

Kalıp okunaklı: **piyasanın artığını öğrenen üç aile 2–3 kat kötüleşti;
piyasaya bir düzeltme takmayanlar kıpırdamadı.** `dixon_coles` gollerden
çalışır ve oranı hiç okumaz — dört basamakta yerinde durması bu okumayla
tutarlı.

Bunun anlamı §5.1'in sonucunu **zayıflatmıyor, sertleştiriyor**:
§3.26–§3.35'te ölçülen küçük kazançların bir kısmı sinyal değil,
**kronoloji dışı eğitimin** eseriydi. Ürünün gerçek kuralı — bu haftayı
yalnızca geçmişle tahmin etmek — uygulandığında fark kapanmıyor, açılıyor.

Raporun *"predictive edge 5,5/10"* notu bu yüzden yerinde. Ama gerekçesi
raporun yazdığından farklı: eksik olan **ölçüm** değildi (ölçüm zaten
vardı), eksik olan **ölçülen etkiydi** — ve kronoloji eklendiğinde o etki
küçülmedi, işaretini korudu ve büyüdü.

---

## 5. Raporun bir PR geride kaldığı yer

Rapor `cc16d74`'e bakıyor; HEAD `2905c30`. Aradaki PR #22 raporun iki
maddesini zaten karşılamıştı:

| Rapor maddesi | PR #22'de ne oldu |
|---|---|
| §15 *"oran snapshot'ı `market/timestamp/home/draw/away` olarak saklanmalı; açılış ≠ orta ≠ kapanış"* | `fiyatlar.py` (257 satır) tam bunu yapıyor: üç bahisçi × açılış/kapanış, marj ve kapsama ile — ve **omurga bilerek değiştirilmedi**, gerekçesi ölçülerek yazıldı (Pinnacle kapsaması %40 ve eksiklik zamana bağlı: football-data 2026-01'de yayımlamayı bıraktı) |
| §5 *"son commitler"* dökümü | 3. hafta donduruldu (ilk kez üç bahisçi), oynanan kupon kural birebir sürüme çevrildi, sonuç kendi sekmesine alındı (tahmin kayıtlarının üstüne yazmıyor) |

Ayrıca raporun §6.3'te "n = 2 hafta" diye aktardığı havuz kaydı bugün
**3 haftadır** — durma kuralını değiştirmiyor (≈71 gerekiyor) ama sayı
kaydın kendisidir.

---

## 6. Reddedilenler — ve gerekçelerinin nerede ölçüldüğü

| Rapor maddesi | Neden hayır |
|---|---|
| §17 tabloya `ROI` / `Max DD` sütunları | Havuz ekseninde 3 haftalık kayıt var, ölçüm ≈71 hafta ister (§6.3b). Boş sütun ölçülmemiş sayıya yer ayırmaktır |
| §20 SHAP / permutation importance | Model sınıfı itirazı §3.30'da kapandı: LightGBM koşuldu ve **geçmedi**. Geçmemiş bir modelin özellik önemini yorumlamak, olmayan bir sinyali açıklamak olurdu. LOFO zaten var (§3.33) ve korelasyonlu özelliklerde tekil önemden daha doğru |
| §14 kadro / sakatlık özellikleri | §7'nin değişmez maddesi: **eğitim/servis ayrışması.** Gerçek kadro ancak ilk vuruşta bellidir; korpusta kullanıp `/tahmin`de kullanamamak ölçümü ürünün tarifi olmaktan çıkarır. Kural kaynak hakkında değil **zamanlama** hakkındadır |
| §27, §46, §48 arayüz önerileri (provenance paneli, açıklanabilirlik) | Kısmen zaten var (`/tahmin` gövdesi `tahminler` ve `olculmus_isabet` bloklarını **ayrılmaz** taşır) ve kalanı §7'nin tek kalan ürün kuralına takılıyor: **ölçülmemiş sayı arayüze çıkmaz.** Arena ve ileri yürüyüş çıktıları da bu yüzden CLI + belgede kaldı |
| §38 `spor_toto/{data,market,features,...}` domain refactor'ü | Raporun kendisi de "bir anda yapmayın" diyor. Bugünkü modül sınırları ölçüm koşumlarına göre kurulu ve `test_egitim.py`'nin katman bekçisi onları koruyor. Bedeli faydasından büyük |

---

## 7. Rapordan alınmayan ama kaydedilen: `drift.py`

Raporun §29'u (`drift.py` — PSI / KL / Jensen-Shannon ile oran dağılımı,
beraberlik oranı, ev avantajı kayması) bu turda **uygulanmadı** ve
reddedilmedi. Bugünkü karşılığı kısmi: `evaluate.ogrenme_egrisi` ve haftalık
Brier zamanla değişimi gösteriyor, `artefakt.bayat_mi` modelin bayatlığını
ölçüyor, ama dağılım kaymasını ölçen bir modül yok.

Sıraya girmesi için ölçülmüş bir gerekçesi de var: §3.41'in ileri yürüyüş
bulgusu, eğitim setinin **hangi döneme ait olduğunun** sonucu değiştirdiğini
gösterdi. Kaymayı ölçmek, o farkın nereden geldiğini söyleyebilecek tek şey.

---

## 8. Puanlama üzerine tek not

Rapor 86/100 veriyor ve alt başlıklarda "Model doğrulama 7,5/10", "gerçek
predictive edge kanıtı 5,5/10" diyor.

İkincisi yerinde ve bu belge onu **düşürecek** bir bulgu getirdi (§4). Ama
birincisi, LOFO / Venn-Abers / yığınlama / öğrenme eğrisi / iç içe CV
ölçümleri görülmeden verilmişti. Bugünkü hâliyle model doğrulama
katmanındaki gerçek eksik üçtü — arena, ileri yürüyüş, sızıntı sözleşmesi —
ve üçü de bu incelemeden sonra kapandı.

Bu, notu yükseltmek için bir gerekçe değildir. Notu veren biz değiliz ve
projenin kendi ölçütü not değil, **durma kuralıdır** (§6). Arena'nın
söylediği şey o ölçüte göre tek cümledir:

> Aynı kesitte, aynı gruplamayla, aynı referansa karşı ölçüldüğünde
> **hiçbir model ailesi piyasayı geçmiyor** — ve kronoloji eklendiğinde
> aradaki fark kapanmıyor, açılıyor.
