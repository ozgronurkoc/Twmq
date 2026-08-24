# Dış çalışma incelemesi — `ScottfreeLLC/AlphaPy` ve `alphapy-pro`

**Kapsam:** Bir makine öğrenmesi **çerçevesinin** bu projeye ne kattığı ve
**ne katmadığı**.
**Güncellendi:** 2026-08-24
**İlgili belgeler:** [`DIS_INCELEME.md`](DIS_INCELEME.md) (aynı türün ilk
örneği) · [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.23
(ayrışım), §6.2 A4 (arayışın durma kuralı)

> **Künye — bu bizim ölçümümüz değildir.** Aşağıdaki isabet ve AUC sayıları
> AlphaPy'ın **kendi belgelerinden** alınmıştır. O belgeler bizim "geçti"
> ölçütümüzü (güven aralığının **tamamı** sıfırın altında) kullanmıyor.
> Dolayısıyla hiçbiri bizim ölçümlerimizle aynı statüde değildir ve hiçbirinin
> yerine geçmez. Değeri **teyit**tir, kanıt değil.

---

## 1. Neden bakıldı, ne çıktı

Soru `DIS_INCELEME.md`'nin sorduğuyla aynı: *"Bu repoda bize uyarlayabileceğimiz
bir şey var mı?"*

Cevap bu kez farklı: **çerçeve olarak hiçbir şey, ölçü olarak bir şey — ve o
şey ölçüldü, koda girdi, sayı üretti** (§5, §6).

İlk incelemede (`zakariae-boui`) aktarılan tek şey bir *dış kanıttı*. Burada
aktarılan şey bir **eksik**: AlphaPy'ın metrik paneline bakarken bizde
olmayan bir ayrım fark edildi ve o ayrım şimdi `ortak.brier_ayrisimi`.

> **Bu belge iki aşamada yazıldı.** §1–§8 incelemenin kendisidir ve
> yazıldığı hâliyle duruyor. §7 sonradan bir sütun kazandı, §9 sonradan
> eklendi: projenin bütün kısıtları kaldırıldı, §7'nin *"denenmedi"*
> dediği beş maddenin beşi de koşuldu ve **hiçbiri kapanış fiyatını
> geçmedi**. Kısa cevap §9'da; tahmin doğruluğu için "hayır", ölçüm
> yeteneği için "evet".

---

## 2. İki depo, iki farklı şey

Kullanıcı önce klasik AlphaPy'ı, sonra *"çok daha gelişmiş versiyon"* diye
`alphapy-pro`'yu verdi. İkisi aynı proje değil:

| | **AlphaPy** (klasik) | **AlphaPy Pro** (v4.0) |
|---|---|---|
| Durum | `alphapy/` altına son commit **17 Nis 2023**; README aktif geliştirmenin Pro'ya taşındığını yazıyor | Etkin; 450 commit, 51 yıldız |
| Python | 3.7 / 3.8 | **>= 3.12** |
| Kapsam | Genel ML + `market_flow` + **`sport_flow`** | **Yalnızca genel ML** |
| Spor kodu | Var | **Yok** — finans ve spor `alphapy-finance` adlı **özel** depoya çıkarılmış |
| Çok sınıf | **Hayır** — `predict_proba(X)[:, 1]` | **Evet** — `argmax`, `shape[1] == 2` dallanması |
| Kalibrasyon | `CalibratedClassifierCV` (sigmoid / izotonik) | **+ Venn-Abers** |
| Arama | `GridSearchCV` / `RandomizedSearchCV` | **Optuna** (`OptunaSearchCV`, 100 tur) |
| Seçim | `SelectPercentile`, `RFECV` | **+ LOFO** |
| Topluluk | Harmanlama (**örneklem içi**) | Harmanlama + oylama + kat dışı yığınlama |
| Öğretici | Kaggle · Borsa · **NCAA basketbol** · Sistem | **Yalnızca Kaggle** |
| Lisans | Apache-2.0 | Apache-2.0 |

**Kayda değer:** Pro, bizi ilgilendiren tek alan modülünü (`sport_flow.py`)
**kaldırmış**. "Daha gelişmiş" genel ML tarafında doğru; spor tarafında
depoda artık hiçbir şey yok.

---

## 3. Üçüncü bağımsız tavan teyidi

AlphaPy'ın **kendi amiral gemisi spor öğreticisi** (`tutorials/ncaab.html`) —
Random Forest + XGBoost, RFECV, 50 turlu rastgele ızgara arama, iki yönlü
etkileşimler:

> *"the AUC of the ROC Curve will vary between **0.54 and 0.58**"*
> *"our model predicts between **52-54% accuracy**"*

Hedef `won_on_spread`: çizgiye karşı **ikili** bir bahis. Şansın karşılığı
%50, −110 fiyatında başabaş ≈ **%52,4**. Yani aracın yazarının kendi sonucu
başabaş çizgisinin üstünde değil. Borsa öğreticisi de aynı yerde:
*"The AUC is approximately **0.61**, which is not very high."*

| Teyit | Kesit | Sonuç |
|---|---|---|
| **Bizim ölçümümüz** | 31.100 maç · 22 lig · 9 özellik | Hiçbiri kapanış fiyatını geçmedi |
| `zakariae-boui` | 6.080 maç · RF/XGB/SVM · 52–62 özellik (xG dahil) | %54,2 vs bahisçi %54,7; ROI hep negatif |
| **AlphaPy'ın kendi belgesi** | NCAA · RF+XGB · RFECV + ızgara arama | %52–54 · AUC 0,54–0,58 |

Üç ekip, üç spor/lig, üç yöntem — aynı tavan.

> Bu kanıt **yalnızca klasik AlphaPy'ın belgelerinde** duruyor. Pro'nun
> öğretici listesinde artık sadece Kaggle var; spor ve borsa örnekleri alan
> koduyla birlikte kaldırılmış. Pro daha gelişmiş ama **kendi alan sonucunu
> artık raporlamıyor.**

---

## 4. Neden hiçbir sürüm doğrudan alınamaz

| # | Engel | Klasik | Pro |
|---|---|---|---|
| 1 | İkili sınıf kilidi (bizimki 3 sınıflı) | **Var** | Çözülmüş |
| 2 | Python / bağımlılık | `scipy==1.10.0` **sabit pin**; biz `>=1.11` | **Python >= 3.12.** Bizim `.replit` 3.10, CI matrisi 3.10–3.13. Ayrıca bokeh, seaborn, matplotlib, ipython, statsmodels, imbalanced-learn, catboost, polars, pyarrow, pydantic |
| 3 | **İç CV zamana kör** | `cross_val_score(cv=cv_folds)` | **Hâlâ:** `StratifiedKFold(n_splits=cv_folds, shuffle=shuffle)` |
| 4 | Harmanlama / yığınlama | **Sızdırıyor** — `model.probas[(algo, Partition.train)]`, yani örneklem içi olasılıklar | Düzeltilmiş (kat dışı) — **ama o CV de rastgele**, madde 3 |
| 5 | Metrik hataları yutuluyor | `except: logger.info("Metric not calculated")` | Aynı |
| 6 | Spor alanı | Var, ama ikili | **Yok** |

### 4.1 Madde 3 önemli, çünkü Pro'da **yarı yarıya** çözülmüş

- ✅ **Dış bölme kronolojik.** `time_series.option: True` iken
  `split_date = df_sorted[split_index, ts_date]`, sonra
  `pl.col(ts_date) <= split_date` / `> split_date`
- ✅ `sequence_frame()` gecikme (lag) ve tarih parçalarını üretiyor
- ❌ **İç CV rastgele kalıyor.** `OptunaSearchCV(cv=cv_folds)`,
  `RFECV(cv=cv_folds)`, `CalibratedClassifierCV(est, cv=cv_folds)` ve
  `cross_val_score` — hepsi `StratifiedKFold(..., shuffle=shuffle)`

Yani **her hiperparametre kararı, her özellik eleme kararı ve olasılık
kalibrasyonunun kendisi geleceği geçmişe karıştıran katlarla alınıyor.**
`projects/time-series/README.md`'nin *"5-fold time series split — no data
leakage"* cümlesi `model.py`/`optimize.py`'daki CV koduyla desteklenmiyor.

Bizde dış halka zaten sezon dışarıda bırakmalı (`evaluate.sezon_anahtari`) ve
bootstrap hafta üzerinden eşleştirilmiş. Eksik olan **iç halka**; yol
haritasındaki `arama.SezonKatlayici` tam olarak bunu kapatmak için var.

### 4.2 Bir düzeltme — `sport_flow` sızıntılı **değil**

İlk okumada klasik `sport_flow.py` sızıntılı sanıldı ve bu yanlıştı.
Birleştirme döngüsü özellikleri **bir maç geciktiriyor**: `gindex = index + 1`
hedef satırı seçerken

```python
mf = insert_model_data(mf, mpos, mdict, tf, index, ...)
```

bir **önceki** maçın (`index`) birikmiş istatistiğini yazıyor. Bu, bizim
`egitim.py`'daki kuralın aynısı (*önce özelliği oku, sonra maçı geçmişe ekle*;
bkz. `test_form_gelecegi_gormez`).

AlphaPy'ın zaman sızıntısı **özellik tarafında değil, doğrulama tarafında** —
ve o gerçekten var (§4.1). Yanlış teşhis kayda geçiyor çünkü bir aracı
olmadığı bir şeyle suçlamak, onu hak ettiği yerde eleştirmeyi zayıflatır.

---

## 5. Aktarılan — ve ölçülen

**Bu incelemenin asıl çıktısı budur ve bir belge satırı değil, koştu.**

AlphaPy'ın `generate_metrics` paneli bizde olmayan üç ölçü içeriyordu
(karışıklık matrisi, sınıf başına duyarlılık, dengeli isabet). Onlara
bakarken asıl eksik görüldü — ve o AlphaPy'da da yok:

> **Brier tek bir sayı olarak raporlanıyordu. Ayrıştırılmıyordu.**

Brier iki ayrı kusuru aynı torbaya koyar: olasılığın **yanlış ayarlı** olması
(yeniden kalibrasyonla geri alınır) ve **ayırt edememesi** (alınmaz, yeni
bilgi ister). Murphy (1973) ayrışımı bunları ayırır. `ortak.brier_ayrisimi`
sembol başına dört terim veriyor ve `Σ_s BS_s` tam olarak `ortak.brier`in maç
ortalaması — yeni ölçek uydurulmadı.

**Ölçülen (31.103 maç · 183 hafta · sezon dışarıda bırakmalı · `shin`):**

| | REL (güvenilirlik) | RES (çözünürlük) | UNC (belirsizlik) | ICI (bant içi) |
|---|---:|---:|---:|---:|
| **piyasa** | **0,00042** | 0,05657 | 0,65058 | −0,00079 |
| izotonik | 0,00022 | 0,05660 | 0,65058 | −0,00056 |

*(sapma payı 0,00021 — §6)*

Ayrıntı, sembol kırılımı ve okuma:
[`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.23.

---

## 6. Aktarılmayanlar ve gerekçeleri

| Ne | Neden aktarılmıyor |
|---|---|
| **SMOTE / azınlık örneklemesi** (`data.sampling`) | **Aktif zararlı.** Yeniden örnekleme sınıf oranını bozar, dolayısıyla **kalibrasyonu yok eder**. Birincil ölçütümüz Brier ve kalibrasyon eğrisi; SMOTE'lu bir model isabette oynar, olasılıkta yalan söyler. Zaman sıralı veride sentetik satır üretmek ayrıca sızıntıdır |
| `data.shuffle: True` (şablonda **varsayılan**) | Aynı sebep — kronolojik yapıyı bozar |
| Kodlayıcı zoo'su (Target / CatBoost / WOE / JamesStein) | **Bizde kategorik özellik yok.** `recalibrate._tasarim_satiri` lig ve bandı zaten gösterge sütunu olarak kuruyor; az örnekli gruplar `EN_AZ_ORNEK=30` ile `"diger"`e havuzlanıyor ve **bu havuzlama kat başına yeniden hesaplanıyor** (`_gruplari_belirle`). Hedef kodlama aynı işi sızıntı riskiyle yapardı |
| PCA / Isomap / t-SNE / KMeans özellikleri | Tasarım tensörümüz `k ≤ ~41` sütun. Boyut indirgeme bizde çözülmemiş bir sorun değil |
| `CalibratedClassifierCV` | İç halkası rastgele KFold; Pro'nun Venn-Abers'ı da rastgele `cal_size=0.2` kullanıyor |
| polars / pyarrow | 31 bin satırda kazanç yok |
| `portfolio.py` / `system.py` / Kelly | `DIS_INCELEME.md` §6'nın gerekçesi aynen geçerli: **biz müşterek bahisiz.** Kelly sabit bir fiyata karşı optimaldir; havuzda ödeme kaç kişinin tutturduğuna bağlıdır |
| `variables.py` Değişken Tanım Dili (`xma_20_50 => xma(20,50)`) | Zarif, ama `pandas.eval` üzerine kurulu ve 41 sütun için altyapı ağırlığı |
| Çerçevenin kendisi (`pip install alphapy-pro`) | Madde 2 + 6: Python 3.12 zorunluluğu 3.10 çalışma zamanımızı kırar (`.replit`, CI matrisi), ve spor alanı zaten yok |

---

## 7. Denenmedi diye yazılmıştı — **hepsi denendi**

Bu bölüm ilk yazıldığında beş satırlıktı ve başlığı *"Denenmedi,
gerekçesiyle"*ydi. Sonra projenin bütün kısıtları kaldırıldı ve beşi de
koşuldu. Tablo **olduğu gibi duruyor**, sağına bir sütun eklendi — çünkü
"neden şimdi denenmedi" gerekçelerinin ne kadar isabetli olduğu da bir
bilgidir.

| Özellik | Kaynak | O zamanki gerekçe | **Ölçüldü** |
|---|---|---|---|
| **Seriler (streak)** | `sport_flow.get_streak` | *"Onuncu deneme olur; `kalibre_form` geçmedi, seri aynı büyüklüğün başka okuması"* | `takim.seri_tablosu`; ham sinyal güçlü, artık sıfır. `kalibre_seri` **geçmedi** (§3.29). **Gerekçe isabetliydi** |
| **İkili etkileşimler** | `get_polynomials(interaction_only=True)` | *"Yol haritasında `etkilesim` basamağı olarak duruyor"* | Kondu ve koşuldu: **anlamlı biçimde kötü** (§3.26, §3.29) — doğrusal kademe bir kısıt değil, bir koruma |
| **Venn-Abers** | Pro `model.py` | *"§5'in ölçümü beklenen değerini düşürdü: kalibrasyon borcu 0,00042"* | `kalibre.py` (kendi PAV'ımız üzerine IVAP, **sezon bazlı** bölme). Geçmedi (+0,000264) ama yeni bir sayı verdi: ortalama aralık genişliği **0,00472** — §5'in bağımsız teyidi (§3.33). **Gerekçe isabetliydi** |
| **LOFO önem** | Pro `features.py` | *"Önce ölçülecek bir özellik kümesi gerekiyor"* | Küme kuruldu (10 özellik) ve LOFO koşuldu: **hiçbiri taşımıyor**, beşi net negatif (§3.33) |
| **Optuna** | Pro `optimize.py` | *"Ancak `cv=`'ye kendi sezon katlayıcımız verilerek"* | `arama.SezonKatlayici` yazıldı ve **Optuna alınmadı**: ızgara araması 4 aday için yeterli, yeni bir üretim bağımlılığı gerekmedi. Alınan şey **desendi**, paket değil |

**Bir tanesi ters çıktı ve kayda değer.** Venn-Abers'ın `venn-abers` paketi
bu ortamda kurulamadı; IVAP projenin kendi `recalibrate._pav`ı üzerine
yazıldı ve **çalıştı**. Yani *"opsiyonel pakete bağımlanma"* doktrini bir
tercih olmaktan çıkıp **ölçülmüş bir olgu** oldu: ihtiyaç duyulan şey
paketin kendisi değil, içindeki 40 satırlık fikirdi.

---

## 8. Özet

| # | Bulgu | Nereye gitti |
|---|---|---|
| 1 | **Brier ayrışımı** — piyasanın kalibrasyon borcu 0,00042, çözünürlüğü 0,05657 | **Koda girdi**: `ortak.brier_ayrisimi`, `tests/test_ortak.py`, `health.tahmin_referanslari` · §3.23 |
| 2 | **Beraberlik çözünürlüğü ~on kat düşük** (0,00257 ↔ 0,02922 / 0,02478); duyarlılık 0,003 | **Koda girdi**: `ortak.karisiklik_matrisi` · §3.23 |
| 3 | Model sınıfı dış kontrolü — AlphaPy'ın kendi spor öğreticisi de aynı tavana çarpıyor (%52–54) | §6.2 A4'ün teyit tablosuna üçüncü satır |
| 4 | Pro'nun iç CV'si zamana kör — bizim `SezonKatlayici` ihtiyacımızın dış doğrulaması | Yol haritası Faz 0.2 |
| — | `sport_flow` sızıntı teşhisi yanlıştı, düzeltildi | Bu belge (§4.2) |
| — | Aktarılacak sanılıp aktarılmayan: SMOTE, kodlayıcı zoo'su, Kelly | Bu belge (§6) |

**İlk incelemeden farkı:** `DIS_INCELEME.md` *"kod değişikliği yok, ölçüm
koşumu yok"* diye bitiyordu. Bu inceleme bir ölçüm koşumu ve bir kod
değişikliği üretti — ama ürettiği şey **yeni bir tahminci değil, daha iyi bir
cetvel**. Aradaki fark önemlidir: cetvel, hangi soruların sorulmaya değer
olduğunu daha keskin söyler, ve §5'in sayısı tam bunu yaptı — kalibrasyon
ekseninde alınacak yolun 0,00042 olduğunu ölçtü.

---

## 9. Sonradan: cetvel kuruldu, sorular soruldu

Bu belge yazıldıktan sonra projenin **bütün kısıtları kaldırıldı** ve
§7'nin beş maddesi dahil, çerçeveden gelen her desen koşuldu. Beş fazın
tamamı bitti; sayılar `ISTATISTIK_YOL_HARITASI.md` §3.23–§3.36'da.

**AlphaPy'dan gerçekten ne alındı:**

| Alınan | Nereye | Sonuç |
|---|---|---|
| Brier'in ayrıştırılması gerektiği fikri | `ortak.brier_ayrisimi` | **Cetvel düzeldi** — serinin en değerli tek çıktısı |
| Çok sınıflı metrik paneli | `ortak.karisiklik_matrisi`, `siralama_olculeri` | Beraberlik çözünürlüğünün on kat düşük olduğu görüldü |
| Kat dışı **yığınlama deseni** (paket değil) | `yigin.py` — katlar `SezonKatlayici`dan | Serinin ilk negatif nokta tahmini, ama geçmedi (§3.32) |
| LOFO **fikri** (paket değil) | `agac.lofo` | Hiçbir özellik taşımıyor (§3.33) |
| Venn-Abers **fikri** (paket değil) | `kalibre.py` | Geçmedi, ama aralık genişliği yeni bir sayı verdi (§3.33) |
| İç içe CV ihtiyacının dış doğrulaması | `arama.SezonKatlayici` | Pro'nun **yapmadığı** şey; bizde bekçili |

**Ne alınmadı:** çerçevenin kendisi, Optuna, `venn-abers`,
`lofo-importance`, polars, SMOTE, kodlayıcı zoo'su. Altı desen alındı,
**sıfır yeni üretim bağımlılığı** eklendi. `scikit-learn` ve `lightgbm`
yalnızca `model` ekstrasında, ölçüm için.

**Ve asıl cevap.** Kullanıcının sorusu şuydu: *"bizim sistemimize entegre
edebileceğimiz herhangi bir şey var mı — özellikle tahminlerin doğruluğunu
artırmaya yönelik?"* Dürüst cevap iki parçalı:

1. **Tahmin doğruluğu için: hayır.** AlphaPy'ın işaret ettiği her desen
   koşuldu ve on ikisinin on ikisi de kapanış fiyatını geçemedi. Üstelik
   AlphaPy'ın **kendi** spor öğreticisi de aynı tavana çarpıyor (§3) —
   yani bu bir uygulama kusuru değil, alanın kendisi.
2. **Ölçüm yeteneği için: evet, ve bu daha değerli çıktı.** Ayrışım
   olmadan *"kalibrasyonda alınacak yol 0,00042"* denemezdi; o sayı
   olmadan Venn-Abers'ın beklenen değeri **koşumdan önce** bilinemezdi.
   Cetvel, hangi soruların sorulmaya değmediğini de söyler — ve bir
   projede en pahalı şey, cevabı önceden bilinebilecek bir soruya
   harcanan zamandır.
