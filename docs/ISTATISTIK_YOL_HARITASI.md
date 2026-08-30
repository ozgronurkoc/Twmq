# İstatistik Katmanı — Durum ve Yol Haritası

**Kapsam:** `/istatistik` sayfası, onu besleyen veri + oran altyapısı, tahmin katmanı ve
**projenin tamamını kapsayan yol planı** (§6). Dosya adı tarihsel; kapsam §6 ile genişledi.
**Güncellendi:** 2026-08-17 (proje amacı güncellendi — aşağıya bakınız)

> **Amaç değişikliği (2026-08-17).** Projenin amacı artık **veriyi analiz ederek
> kazanma oranını artıracak sonuçlar üretmek ve maç sonucu tahmini yapmaktır**
> (bkz. [`../README.md`](../README.md) §1). Bu belgedeki ölçüm disiplini aynen
> geçerlidir ve daha da kritik hale gelmiştir: tahmin iddiası, ölçülmemiş hiçbir
> sayının arayüze çıkmamasıyla dengelenir. Hold-out **1 hafta**, piyasa Brier
> **0,579**, iddaa marjı **%17,2** — bu üç sayı tahmin katmanının başlangıç
> çizgisidir ve ilerleme bunlara karşı ölçülür.
>
> **Ölçek uyarısı.** 2026-08'de marj arındırma varsayılanı `orantili`dan `shin`e
> çevrildi (§3.18). O tarihten önceki bölümlerdeki sayılar orantısal ölçekte
> ölçülmüştür ve bugünküyle **doğrudan kıyaslanamaz**. §3.10–§3.16 (T1–T5,
> A1–A3) böyle bölümlerdir ve **bilerek olduğu gibi bırakıldı** — bir ölçüm
> kaydı sonradan yeniden yazılmaz. Bugünkü sayılar §3.18 ve §5'tedir.
**İlgili belgeler:** [`VERI_TOPLAMA_VE_ISLEME.md`](VERI_TOPLAMA_VE_ISLEME.md) (veri üretiminin
tek kaynak dokümantasyonu) · [`ARCHITECTURE_NEXT.md`](ARCHITECTURE_NEXT.md) (API sözleşmesi) ·
[`DIS_INCELEME_AZ_RAPORU.md`](DIS_INCELEME_AZ_RAPORU.md) (dış incelemenin karşılığı; §3.41'in kaynağı)

---

## 1. Bu belge ne işe yarar

İstatistik katmanı kısa sürede büyüdü: sayfa yeniden yazıldı, veri setinde bir sıra hatası
bulunup kapatıldı, veri maç düzeyine indirildi, oran arşivi kuruldu ve maç sonucu oranları
arayüze bağlandı. Bu kararların gerekçesi ve sıradaki işler tek bir yerde toplanmazsa altı ay
sonra kimse "burada neden böyle yapılmış" sorusunu cevaplayamaz.

Belge üç soruya cevap verir: **ne yapıldı**, **bugün ne var**, **sırada ne var**. Sayfa ile
altyapı birlikte ele alınır, çünkü sayfadaki her kart doğrudan bu boru hattına dayanır.

---

## 2. Bugünkü mimari

### 2.1 Veri akışı

```
sportototahmin hafta payload'ları
        │  scripts/build_history.py   (haftanın kendi matches dizisi, sırayla)
        ▼
data/st_history_2025_26.json          41 hafta · 615 maç · maç listesiyle
        │  spor_toto/history.py       (analiz blokları, dilimleme, veri kalitesi)
        ▼
GET /api/stats[?last=N] ─────────────► /istatistik
GET /api/stats/<week>   ─────────────► /istatistik/<hafta> ──┐
        ▲                                                     │ 15 maçın olasılığı
        │  spor_toto/odds.py          (1X2 özeti, banko bantları, kalibrasyon,   │
        │                              çift kapsama, beraberlik, lig, Brier)     ▼
data/odds/odds_2025_26.csv            567 maç · 108 oran sütunu             /  (formül)
        ▲       │
        │       │  spor_toto/backtest.py   (eşikli seçim → kaplama → skor)
        │       ▼
        │  GET /api/backtest[?banko=&uclu=&last=&sweep=] ──► /istatistik/geri-test
        │
        │  scripts/build_odds.py      (tarih ±1 gün + birebir skor + bulanık ad)
football-data.co.uk arşivi (38 dosya)

iddaa açık bülteni  ──► scripts/snapshot_iddaa.py ──► data/iddaa/iddaa_<tarih>.csv
                        (haftalık, ileriye dönük arşiv — henüz analize girmiyor)

──────────── TAHMİN KATMANI (ayrı; /istatistik'e girmez) ────────────

football-data (22 lig × 4 sezon)
        │  scripts/build_egitim.py
        ▼
data/egitim/egitim_korpus.csv         31.103 maç
        │  spor_toto/egitim.py        (ISO haftası → sözde-hafta + sezon)
        ▼
spor_toto/evaluate.py  ◄── spor_toto/predict.py     (sözleşme + 3 referans)
   (ölçüm koşumu)      ◄── spor_toto/recalibrate.py (kademe)
        │
        └─► rapor: hiçbir uç yok — sayfaya çıkan bir şey yok (T6)
```

### 2.2 Dosya haritası

| Katman | Dosya | Satır | Rol |
|---|---|---:|---|
| Üretim | `backend/scripts/build_history.py` | 284 | Veri setini kaynağından üretir, doğrulamadan yazmaz |
| Üretim | `backend/scripts/build_odds.py` | 441 | Oranları kupon maçlarına eşleştirir, CSV + SQLite yazar |
| Üretim | `backend/scripts/snapshot_iddaa.py` | 339 | İddaa açık bültenini tarih damgalı saklar (F5) |
| Okuma | `backend/spor_toto/history.py` | 423 | 6 analiz bloğu, `last=N` dilimleme, veri kalitesi denetimi |
| Okuma | `backend/spor_toto/odds.py` | 489 | 1X2 seçimi, banko bantları, kalibrasyon, çift kapsama, beraberlik profili, lig kırılımı, haftalık Brier |
| Analiz | `backend/spor_toto/backtest.py` | 458 | Eşikli strateji, kaplama önbelleği, skorlama, tarama, hold-out |
| API | `backend/web_app.py` | — | `api_stats`, `api_stats_week`, `api_backtest` |
| UI | `frontend/app/istatistik/page.tsx` | 522 | Sayfa |
| UI | `frontend/app/istatistik/[week]/page.tsx` | 391 | Hafta detayı + "formüle gönder" |
| UI | `frontend/app/istatistik/geri-test/page.tsx` | 266 | Geri test sayfası |
| UI | `frontend/components/istatistik/charts.tsx` | 1.238 | 12 görsel + ipucu bileşeni |
| UI | `frontend/components/istatistik/backtest.tsx` | 441 | Strateji seçici, tarama tablosu, hold-out, hafta hafta |
| UI | `frontend/components/istatistik/parts.tsx` | 282 | Filtre (URL'e yazar), kesit notu, sayı kutusu, veri kalitesi |
| UI | `frontend/components/istatistik/weeks-table.tsx` | 292 | Sıralanabilir/aranabilir tablo + Brier + CSV |
| UI | `frontend/components/istatistik/viz.ts` | 69 | Renk sözleşmesi, sequential ramp, sütun yolu |
| UI | `frontend/lib/transfer.ts` | 84 | Hafta → formül devri (idempotent) |
| Test | `backend/tests/test_history.py` | 229 | Veri seti denetimi ve analiz blokları (19) |
| Test | `backend/tests/test_api_stats.py` | 193 | Uç sözleşmesi, dilim, oran + karar destek blokları (15) |
| Test | `backend/tests/test_odds.py` | 82 | Arşivin geçmiş veriyle hizası (7) |
| Test | `backend/tests/test_backtest.py` | 193 | Strateji, skorlama, Wilson, tarama, hold-out (17) |
| Test | `backend/tests/test_api_backtest.py` | 98 | `/api/backtest` sözleşmesi (11) |
| Test | `backend/tests/test_snapshot_iddaa.py` | 204 | Bülten ayrıştırma ve yazma (13) |
| Tahmin | `backend/spor_toto/predict.py` | — | Tahminci sözleşmesi, 3 referans |
| Tahmin | `backend/spor_toto/evaluate.py` | — | Dışarıda bırakmalı + çapraz ölçüm, bootstrap |
| Tahmin | `backend/spor_toto/recalibrate.py` | — | Yeniden kalibrasyon kademesi (Newton) |
| Tahmin | `backend/spor_toto/cizgi.py` | — | Kapanış çizgisi verimliliği (A1): açılış tahmincisi, hareket ölçümü |
| Tahmin | `backend/spor_toto/bahisci.py` | — | Bahisçi anlaşmazlığı (A2): tekil bahisçiler, ayrışma ölçümü |
| Tahmin | `backend/spor_toto/disari.py` | — | Piyasa dışı türetilebilir özellikler (A3): artık taraması, kör nokta |
| Ortak | `backend/spor_toto/ortak.py` | — | Paylaşılan hesapların tek kaynağı: Wilson, Brier, **Brier'in Murphy ayrışımı**, karışıklık matrisi, Poisson-binom, bantlama |
| Tahmin | `backend/spor_toto/elo.py` | — | Rakip gücüne göre düzeltilmiş takım gücü (Faz 3.2): Elo defteri, gol farkı çarpanı, sezon taşıma |
| Tahmin | `backend/spor_toto/dixon_coles.py` | — | Gollerden hücum/savunma güçleri (Faz 3.1): ağırlıklı IPF, düşük skor `τ` düzeltmesi, tur tur yeniden uydurma |
| Tahmin | `backend/spor_toto/takim.py` | — | Eşleşmeye özel geçmiş ve anlık gidişat (Faz 3.3): H2H son 5 karşılaşma, ardışık galibiyet/mağlubiyet serisi |
| Tahmin | `backend/spor_toto/arama.py` | — | İç içe CV (Faz 0.2): `SezonKatlayici` (sklearn splitter arayüzü) + ızgara araması; hiperparametre ayarı hold-out'u bozmadan serbest |
| Tahmin | `backend/spor_toto/agac.py` | — | LightGBM çok sınıflı (Faz 2.2): piyasanın log-olasılığı `init_score`, ağaç yalnızca artığı öğrenir |
| Pazar | `backend/spor_toto/pazar.py` | `/api/pazar` | 1X2 dışı pazarlar (Faz 4.1): alt/üst 2,5 (Brier'li) ve Asya handikabı (getiri kalibrasyonlu), ölçülmüş kalibrasyonlarıyla |
| Tahmin | `backend/spor_toto/yigin.py` | — | Kat dışı yığınlama (Faz 2.4): sezon katlarıyla üretilmiş olasılıklar üzerinde multinom logit üst-öğrenici; taban başına tek ağırlık |
| Tahmin | `backend/spor_toto/kalibre.py` | — | Venn-Abers (Faz 2.3): kendi PAV'ımız üzerine indüktif IVAP, sezon bazlı kalibrasyon bölmesi, olasılık **aralığı** |
| Tahmin | `backend/spor_toto/arena.py` | 386 | **Model Arena** (§3.41): bütün tahminci aileleri **tek kesitte, tek tabloda**, tek referansa karşı. Aile başına tek temsilci (kural ölçüm görülmeden yazıldı); dar kesit isteyen aile `disarida()`da **gerekçesiyle**; eğitilemeyip bir tabana düşen aday `cokme` ile işaretlenir |
| Tahmin | `backend/spor_toto/evaluate.py` | — | `ileri_yuruyus` (§3.41): kronolojik ölçüm — `k`. grup yalnızca `0..k-1`de eğitilmiş modelle ölçülür. `hafta_disarida_birak`ın geleceği gördüğü yerde tek fark budur |
| Havuz | `backend/spor_toto/getiri.py` | — | Müşterek beklenen değer (Faz 4.2): `E[1/(1+W)]` kapalı formu, üç kalabalık modeli (`orneklem` `favori` **`oynanma`** — sonuncusu ölçülmüş paylardan), duyarlılık eğrileri — **arayüze çıkmaz**, sayı ölçülmemiştir |
| Tahmin | `backend/spor_toto/gorus.py` | — | Piyasadan **bağımsız** görüş (§3.37): yaklaşan maça Dixon-Coles + Elo; lig kısıtlı, bulanık olmayan ad eşleme. **İşaret değiştirmez** |
| Takım | `backend/spor_toto/takim_gucu.py` | `/api/takimlar` | Küçültülmüş takım gücü (Faz 4.3): ampirik Bayes, lig içinde; her satırda `n`, `kucultme` ve %95 aralık |
| Tahmin | `backend/spor_toto/avrupa.py` | — | UEFA fikstürü (Faz 3.4): 768 maç takvime **enjekte edilir**; `dinlenme` ve `sikisiklik` artık o günleri de görür |
| Tahmin | `backend/spor_toto/sehir.py` | — | Şehir ve derbi (Faz 3.4): `openfootball/clubs` (CC0) tablosu; derbi bir **sıcaklık** değişkeni olarak girer |
| Tahmin | `backend/spor_toto/xg.py` | — | xG vekili (Faz 3.5, §3.42): korpusun kendi `sut`/`isabet` sayımı **ölçülmüş** katsayılarla beklenen gole çevrilir. Katsayı StatsBomb'un 2015/16 dört lig kesitinde uydurulur — kaynak bir **girdi değil referanstır** |
| Üretim | `backend/scripts/build_xg.py` | — | xG kalibrasyonu (Faz 3.5): 1.517 maç, **(lig, tarih±1, skor)** ile eşleme; **veri değil katsayı üretir** (lisans md. 1.2.1) |
| Altyapı | `backend/spor_toto/kosum.py` | — | Koşum defteri (Faz 0.4): yedi ölçüm CLI'sında `--kaydet`; korpus sha256 + commit + tohum yazılır, defter **sürümlenmez** (§2.6) |
| Altyapı | `backend/spor_toto/artefakt.py` | — | Model kalıcılığı (Faz 0.3): eğitilmiş modelin JSON zarfı (korpus sha256 + eğitim tarihi + sürüm); bayatlık `health`te kırmızı (§2.5) |
| **Ürün** | `backend/spor_toto/tahmin.py` | — | **Tahmin ürünü (C2)**: yaklaşan maça olasılık + ölçülmüş isabet |
| Üretim | `backend/scripts/build_fixtures.py` | — | Yaklaşan maçlar ve oranları (football-data `fixtures.csv`) |
| UI | `frontend/app/tahmin/page.tsx` | — | Tahmin sayfası |
| UI | `frontend/components/tahmin/parts.tsx` | — | Olasılık çubuğu, isabet kartı, sınırlar |
| Tahmin | `backend/spor_toto/egitim.py` | — | Eğitim korpusu okuyucusu (**istatistiğe girmez**) |
| Üretim | `backend/scripts/build_egitim.py` | — | Korpus üretimi (football-data, 4 sezon, **iki çizgi + bahisçi kırılımı**) |
| Test | `backend/tests/test_predict.py` · `test_evaluate.py` · `test_recalibrate.py` · `test_egitim.py` · `test_cizgi.py` · `test_bahisci.py` · `test_disari.py` · `test_tahmin.py` | — | Tahmin katmanı, **ürün** ve ayrım bekçisi (229) |

**İşleyen sezon (2026/27)** — bu satırlar yukarıdaki haritanın parçasıdır,
ayrı tabloda tutulmuştur.

| Katman | Dosya | Rol |
|---|---|---|
| Okuma | `backend/scripts/super_toto_hafta.py` | Haftayı **geçen sezonun kendi ölçümlerine** oturtur (favori bantları, çift kapsama, beraberlik profili, lig kırılımı). Arşive **yazmaz**. `kamuoyu()` havuz kenarını ölçer |
| Analiz | `backend/scripts/super_toto_degerlendir.py` | Sonuç sonrası: kaçakların Poisson-binom dağılımı, banko karnesi, **kalabalık karnesi**, ikramiye özeti; **iki kaydın kıyası ve birleşimi**, kalabalık ayarı karnesi, atılan sembol defteri, görüş ve ölçek karneleri, **gerçeğin sırası** (§3.38); **dış kuponlar**, oynanma biçimi (`fix16`/`tam`), P(15) ve **azami kapsamadan sapma defteri** (§3.39); **gerçekleşen/beklenen getiri** ve **havuz karnesi** (§3.40) |
| Üretim | `backend/scripts/super_toto_sayfa.py` | Hafta raporu sayfası; sayfadaki hiçbir sayı elle yazılmaz, boru hattından okunur |
| **2. Tahmin** | `backend/scripts/super_toto_tahmin2.py` | Aynı haftayı bugünkü aletlerin tamamıyla yeniden okur (§3.37): `shin` ölçek + `hedef` kural + **kalabalık ayarı** + bağımsız görüş + marj duyarlılığı. 1. Tahmin'in kaydını **değiştirmez** |
| Karar | `backend/spor_toto/secim.py` → `kalabalik_ayari` | İşaret **sayıları** sabit, hangi sembol sorusu yeniden sorulur; `küme-içi / kalabalık-içi` oranını Pareto DP ile enbüyükler |
| Analiz | `backend/scripts/acilis_kapanis.py` | Açılış ↔ kapanış fiyatı, **kupon zamanlamasıyla** (§5.2) |
| Veri | `backend/data/super_toto/<sezon>/hafta_NN{,_kupon,_tahmin2}.json` | Elle girilen hafta verisi, dondurulmuş kupon ve **ikinci kayıt** — köken sınıfı ayrı ([`VERI_TOPLAMA_VE_ISLEME.md`](VERI_TOPLAMA_VE_ISLEME.md) §6B) |
| UI | `frontend/app/super-toto/page.tsx` · `components/super-toto/haftalar.tsx` · `lib/super-toto.ts` | Sezonun hafta şeridi; `?hafta=N` adreste durur |
| UI | `frontend/components/super-toto/tahmin2.tsx` | **2. Tahmin** paneli — `1. Tahmin` / `2. Tahmin` sekmeleri arasında geçilir; para birimli hiçbir sayı yok. Hafta kapandığında sonuç sütunu ve ayar karnesi açılır (§3.38) |

Backend istatistik/oran/geri test katmanı ~2.434 satır, frontend ~3.585 satır. Backend test
paketi toplam **1.829 test**; **85'i** istatistik katmanına (`history` `odds` `backtest`
`api_stats` `api_backtest` `snapshot_iddaa`), **567'si** tahmin katmanına ait (`predict`
`evaluate` `recalibrate` `egitim` `cizgi` `bahisci` `disari` `kalibrasyon` `tahmin`
`benzer` `elo` `dixon_coles` `takim` `arama` `agac` `yigin` `kalibre`
`avrupa` `sehir` **`arena`** **`sizinti`**), **29'u** 2. Tahmin'e (`tahmin2`), **30'u** sonuç değerlendirmesine (`degerlendir`). Dosya adlarıyla sayılıdır ki tablo elle bakım gerektirmesin —
`tests/test_belgeler.py` onları gerçek koleksiyona karşı denetler.
`python -m spor_toto.health` **27 değişmez** çalıştırır — ikisi (`oran_arsivi`, `geri_test`)
istatistik katmanını, biri (`tahmin_referanslari`) tahmin katmanının ölçüm koşumunu korur,
biri (`artefakt_tazeligi`) diskteki modelin hâlâ bugünkü korpustan geldiğini denetler (§2.5).

**Korpusun bütünlüğü sağlık katmanında değil test paketinde korunur** ve bu bir üründür
kararıdır: korpus yalnızca tahmin katmanına aittir, `/api/health` ondan hiçbir sayı okumaz
(`test_egitim.py::test_ayrim_*` bunu bekçiye bağlar). Korpus çalışma anında da kaymaz —
git'e işlenmiş bir dosyadır — dolayısıyla bozulma ancak bir kod değişikliğiyle gelir ve
orayı bekleyecek yer test paketidir.

### 2.3 API sözleşmesi

`GET /api/stats?last=N` — `last` verilirse **bütün bloklar** o dilim üzerinden hesaplanır.

| Alan | Kaynak fonksiyon | İçerik |
|---|---|---|
| `meta` | `history_summary` | sezon, hafta/tarih aralığı, `sliced` |
| `totals`, `weekly_avg`, `bands` | `history_summary` | toplam, ortalama, min–maks–ortanca–σ, ortalama üstü/altı |
| `analytics.positions` | `position_stats` | 1.–15. maç sırasına göre dağılım |
| `analytics.transitions` | `transition_stats` | ardışık maçlarda 3×3 geçiş matrisi |
| `analytics.distribution` | `count_distribution` | "bir haftada k adet" histogramı |
| `analytics.streaks` | `streak_stats` | hafta içi en uzun aynı-sembol serileri |
| `analytics.extremes` | `extreme_weeks` | sembol başına en yüksek/en düşük hafta |
| `analytics.recent` | `recent_form` | son 6 haftanın ortalaması ve sezona göre farkı |
| `data_quality` | `_data_quality` | sayım/maç çelişkileri, mükerrer dizi, eksik hafta |
| `odds` | `season_1x2_summary` | kapsama, favori isabeti, kırılım, çapraz tablo, banko bantları, kalibrasyon, marj |
| `odds.set_coverage` | `_kume_kapsama` | ilk iki olasılık toplamı bandına göre çift/banko kapsaması |
| `odds.draw_profile` | `_beraberlik_profili` | favori−ikinci farkına göre beraberlik oranı |
| `odds.leagues` | `_lig_kirilimi` | lig başına maç, beraberlik, favori isabeti, kupon payı |
| `odds.weekly_brier` | `_haftalik_brier` | hafta hafta piyasanın yanılma ölçüsü + sezon ortalaması |
| `weeks` | `normalized_weeks` | hafta satırları (`counts`, `max_streak`, `matches`, …) |

`GET /api/stats/<week>` — `history_week_detail` + `week_1x2`: komşu haftalar, sezon
ortalamasına sapma, sıra, ardışık bloklar, sıra-sıra sezon bağlamı, maç listesi ve maç
numarasına göre 1X2 oranı (`odds`, `odds_hit`).

`GET /api/backtest[?banko=&uclu=&last=&sweep=0]` — `backtest`: seçili stratejinin sezonu
(`season`), hafta hafta sonuç (`weeks`), 28 eşikli tarama (`sweep`, `sweep_best`) ve
**hold-out** (`holdout`). Sonuç sunucuda önbelleklenir: tek strateji ~1,2 sn, tarama ilk
çağrıda ~15 sn, sonrasında milisaniye.

`GET /api/meta` → `backtest`: eşik ızgarası ve varsayılanlar. Arayüz bunları sabit kodlamaz.

### 2.4 Değişmez kurallar

Bunlar katmanın tasarım sözleşmesidir; yeni kart eklerken bozulmamalı:

1. **Renk kimliği takip eder, sıralamayı değil.** Seriler `--sym-1/0/2` token'larından gelir;
   grafiklerde sabit hex yoktur (`viz.ts`), koyu tema bu yüzden bedava çalışır. Filtre hafta
   sayısını değiştirdiğinde hiçbir seri renk değiştirmez.
2. **Her görselin tablo karşılığı vardır.** Hiçbir değer yalnızca renge ya da fare ipucuna
   bırakılmaz; hafta tablosu tam veriyi taşır.
3. **Tek filtre satırı.** Kart içine filtre konmaz; aralık seçimi `?last=N` ile API'ye gider ve
   bütün bloklar aynı dilimden hesaplanır — iki görsel asla farklı veriyi anlatmaz.
4. **Arayüze yalnızca maç sonucu (1X2) çıkar.** 2.5 alt/üst, Asya handikap ve maç
   istatistikleri arşivde kalır; `test_api_stats.py` bunu denetler.
5. **Veri kendini denetler.** Maç listesi, sonuç dizisi ve sayımlar birbirini tutmadan dosya
   yazılmaz; tutmazsa `data_quality` bunu sayfada gösterir.
6. **Geçmişe uydurulan sayı tek başına gösterilmez.** Eşik taraması her zaman hold-out ile
   birlikte durur; aradaki fark aşırı uyumun büyüklüğüdür ve kartın üstündeki uyarı
   kaldırılmamalıdır.
7. **Doğrulanmayan bedel raporlanmaz.** Geri testte her haftanın kaplaması bağımsız olarak
   denetlenir; açık nokta bırakan ya da uzay sınırını aşan hafta tabloya girmez, "atlandı"
   diye görünür.

---

### 2.5 Model kalıcılığı — artefakt (Faz 0.3)

Üretimdeki tahminci ilk istekte eğitiliyordu (`lru_cache(maxsize=1)`). İki
şey birden bozuluyordu: **ilk isteğin bedeli** (31.103 satır okunuyor ve
model uyduruluyor) ve **hangi korpusla eğitildiğinin kayıtsızlığı** — süreç
yeniden başlarsa model sessizce yeni korpusla yeniden eğitilir ve değişen
bir şey olduğu hiçbir yerde görünmez.

`artefakt.py` modeli diske yazar, dosya **hangi korpustan** geldiğini taşır
ve korpus değiştiğinde `health.artefakt_tazeligi` **kırmızı** olur.

**Turşu (pickle) değil JSON — üç sebeple.** (1) Yeni üretim bağımlılığı
gerekmiyor: `joblib`in faydası büyük dizileri bellek eşlemeli yazmaktır,
bizim durumumuz bir avuç katsayı. (2) `pickle.load` dosyadaki talimatları
**yürütür**; bozuk bir artefakt sessiz bir yürütme yüzeyidir. (3) Artefakt
bir ölçüm kaydıdır — hangi korpustan, ne zaman, hangi sürümle — ve `cat`
ile okunabilmesi bu belgenin işine yarar.

Bedeli, her tahmincinin durumunu **açıkça** yazması (`durum`/`yukle`). Bu
bir maliyet gibi görünür ama kazançtır: turşu sınıfın *bütün* iç durumunu —
önbellekler, kaza eseri kalmış her şey — sessizce taşır; açık durum
taşınanı **seçmeye** zorlar. `KalibreTahminci` üç alan yazar ve üçü de
zorunludur: `theta` tek başına taşınsaydı katsayılar geri gelir ama
**başka sütunlara** binerdi (`ligler`/`bantlar` tasarım matrisinin düzenini
belirler). Bekçisi `test_artefakt.py::test_yuklenen_model_ayni_tahmini_veriyor`.

**Üç kural kayda geçiyor:**

| Kural | Neden |
|---|---|
| Servis **yazmaz**, yalnızca okur | Bir HTTP isteği sessizce diski değiştirmemeli; yazmak `--yaz`ın işidir |
| Artefaktın **yokluğu hata değildir** | Sistem o zaman istekte eğitir ve doğru sonucu verir, yalnızca yavaş olur. Kırmızı olan tek şey **bayat** artefakttır |
| Artefakt **sürümlenmez** (`.gitignore`) | Türetilmiş çıktı; projenin diğer bütün boru hatlarında olduğu gibi kaynağından üretilir |

    python -m spor_toto.artefakt --yaz    # egit ve diske yaz
    python -m spor_toto.artefakt          # durumu goster

---

### 2.6 Koşum defteri (Faz 0.4) — *"bu sayı hangi koşumdan geldi?"*

Bu belgedeki her sayı bir koşumdan gelir ve o bağ bugüne kadar **elle**
kuruluyordu: bir insan CLI'yı çalıştırıyor, çıktıyı okuyup buraya
yazıyordu. Ara adım üç şeyi kaybediyor — sayının hangi **korpustan**,
hangi **kod sürümünden** ve hangi **tohumdan** geldiğini.

**Kaybın maliyeti soyut değil.** §3.16 uzun süre `+0,0655` yazıyordu;
Faz 3.4'te aynı hücre kontrollü koşumda `+0,0613` çıktı. İkisi de
doğruydu — farklı korpus sürümleriydi — ama bunu anlamak **yeni bir
koşum** gerektirdi. Koşum kaydı olsaydı fark bakılarak görülürdü.

`kosum.py` yedi ölçüm CLI'sına `--kaydet` bayrağı ekler ve
`data/kosumlar/<zaman>-<ad>/` altına iki dosya yazar:

| dosya | ne |
|---|---|
| `cikti.json` | ölçümün gövdesi, olduğu gibi |
| `ortam.json` | **asıl olan** — korpus sha256'sı, git commit'i + *kirli mi*, paket sürümleri, tohumlar |

`kirli` alanı olmadan commit kimliği **yanıltır**: commit edilmemiş
değişikliklerle koşulan bir ölçüm o commit'ten üretilemez.

**Defter sürümlenmez** (`.gitignore`) ve bu bilinçli: her ölçüm koşumu
depoya girseydi depo bir veri ambarına dönerdi. Kayıt yerel bir defterdir
— bir sayıyı savunmak gerektiğinde bakılır, paylaşılmaz. Belgeye giren şey
sayının kendisi ve koşum kimliğidir.

Bekçi `test_kosum.py::test_olcum_clileri_kaydet_bayragini_tasiyor`: yedi
CLI'nın biri unutulursa o ölçümün sayısı yine belgeye girer ama **izsiz**
girer — Faz 0.4'ün bütün amacı o izin var olmasıdır.

    python -m spor_toto.disari --kaydet   # olc ve deftere yaz
    python -m spor_toto.kosum             # kayitli kosumlar
    python -m spor_toto.kosum --son agac  # son `agac` kosumunun ortami

---

## 3. Yapılanlar

| Commit | İş |
|---|---|
| `81cc5cf` | Analiz katmanı + sayfanın yeniden yazımı |
| `3392135` | Veri seti düzeltmesi, veri maç düzeyine indi |
| `5cdcb71` | Oran arşivi (arayüze bağlı değil) |
| `6fdcffc` | Maç sonucu oranları arayüze |
| `10a5d7f` | Favori tuttu/tutmadı kırılımı + çapraz tablo |
| `90d0102` | Lig etiketini boşaltan BOM hatası |
| `1558aeb` | Banko güvenilirliği tablosu |
| `51da077` | Filtre altına kesit açıklaması |
| `44a83e4` | **F1** — geri test: strateji, kaplama, skorlama, tarama, hold-out |
| `2d90b64` | **F3** — karar destek kartları: çift kapsama, beraberlik profili, lig kırılımı |
| `9d9cfac` | **F2** — hafta detayından formül sayfasına olasılık devri |
| `c6a8d0f` | **F4** — URL'de filtre, CSV dışa aktarma, haftalık Brier |
| `f1eb65c` | **F5** — iddaa bülten snapshot boru hattı |
| `68e5ff9` | **T1** — tahminci sözleşmesi + değerlendirme koşumu |
| `2362539` | **T2** — piyasanın yeniden kalibrasyonu (kademe) |
| `d7a5623` | **T3** — eğitim korpusu + çapraz ölçüm |

### 3.1 Analiz katmanı ve sayfanın yeniden yazımı (`81cc5cf`)

**Sorun.** Sayfa üç sayı kutusu ve düz bir tablodan ibaretti. Hafta bağlantısı 404 veriyordu —
`/istatistik/<hafta>` sayfası hiç yoktu. API'den gelen `bands` verisi hiç gösterilmiyordu.

**Çözüm.** `history.py`'a altı analiz bloğu eklendi (maç sırası dağılımı, geçiş matrisi, adet
histogramı, seriler, uç haftalar, son 6 hafta formu); bantlar dosyadan okunmak yerine
haftalardan hesaplanır oldu — dilim alındığında da doğru kalsın diye. Sayfa yeniden yazıldı,
hafta detayı eklendi.

**Doğrulama.** Grafikler bağımlılıksız inline SVG; palet renk körlüğü ve kontrast
doğrulamasından geçirildi.

### 3.2 Veri seti düzeltmesi (`3392135`)

**Sorun.** `results` dizisi 41 haftanın **15'inde yanlış sıradaydı**, **6'sında sayım da
yanlıştı**. Dosyadaki `n1/n0/n2` alanları baştan doğruydu (41/41 kaynakla uyuşuyor). Sezon
toplamları etkilenmemişti ama **sıraya bağlı her analiz** — maç sırası dağılımı, geçiş matrisi,
seriler — 15 haftada kirliydi. İki hafta çifti (22–25, 24–26) birebir aynı diziyi taşıyordu.

**Sebep.** Payload içinde maça benzeyen birden fazla blok var: haftanın kendi `matches` dizisi
ve komşu haftaların `featuredMatches` blokları. İlk üretim diziyi düz tarayıp hepsini
topluyordu, kupon sırası böyle bozuluyordu.

**Çözüm.** `scripts/build_history.py`: hafta nesnesini `weekNumber` ile bulur, **yalnızca onun
`matches` dizisini** sırasıyla çözer. Skor yine maçın kendi referans zincirinden gelir. Liste,
dizi ve sayımlar birbirini tutmadan dosya yazılmaz.

**Doğrulama.** 26 hafta aynı kaldı, 9'unda sıra, 6'sında sıra + sayım düzeldi, mükerrer diziler
kalmadı. `close_date` alanlarının 41/41'i önceki sürümle aynı çıktı — hafta eşlemesi baştan
doğruymuş, bozuk olan hafta *içindeki* sıraymış. 51. hafta, `VERI_TOPLAMA_VE_ISLEME.md` §7.2'de
Misli ile bağımsız doğrulanmış satırla birebir tutuyor (`000111122212011`).

**Yan kazanç.** Veri seti artık her hafta için maç listesini taşıyor: takım adı, başlama saati,
skor, kod. Oran eşleştirmesinin ön koşulu buydu.

### 3.3 Oran arşivi (`5cdcb71`, `90d0102`)

`scripts/build_odds.py` football-data.co.uk arşivinden 38 dosya çeker ve kupon maçlarına
**tarih (±1 gün) + birebir skor + bulanık takım adı** ile eşleştirir. Skor şartı yanlış
eşleşmeye karşı en güçlü korumadır.

- Kapsama **567/615 maç (%92,2)**, 41 haftanın 36'sı tam
- Eşleşmeyen 48 maçın 45'i milli maç (5., 10., 15. hafta) — kaynak milli maç yayınlamıyor
- Pazarlar: 1X2 (11 bahisçi × açılış/kapanış), 2.5 alt/üst, Asya handikap → **108 oran sütunu,
  51.683 değer**; ayrıca 14 maç istatistiği
- `90d0102`: latin-1 okunan dosyalarda UTF-8 BOM ilk sütunun adına yapışıyordu (`ï»¿Div`);
  539 maçın lig etiketi boş kalıyordu. Düzeltildi, 15 lig doğru etiketli

**Bunlar iddaa oranı değildir.** İddaa geçmiş bültenini yayınlamıyor (resmi API yalnızca açık
bülteni veriyor, ölçümde 8 günlük pencere), Maçkolik ise `robots.txt` ile otomatik erişime
kapalı. Piyasa oranının **seviyesi** iddaa ile tutmaz (marj farkı), **favori sıralaması ve marj
arındırılmış olasılık yapısı** tutar.

**Nerede duruyor:** `backend/data/odds/` — `odds_2025_26.csv` ve `odds_rapor.json` sürümlenir;
`odds.sqlite3` (uzun biçim `mac`/`oran`/`istatistik` tabloları) ve `_kaynak/*.csv` üretilir,
git dışıdır.

### 3.4 Oranların arayüze bağlanması (`6fdcffc`, `10a5d7f`, `1558aeb`, `51da077`)

- **"Oranlar ne diyordu?" kartı** — favori isabeti, favori dağılımı, kalibrasyon grafiği
- **Favori kırılımı ve çapraz tablo** — tuttu/tutmadı × 1/0/2; sayfa "tuttu" satırında `0`
  sütununun neden boş olduğunu açıkça yazar: beraberlik hiçbir zaman favori olmadığı için her
  beraberlik tanımı gereği "tutmadı" tarafına düşer
- **Banko güvenilirliği tablosu** — favori oranı bandına göre tuttu/tutmadı; tutmadı ayrıca
  beraberlik ve karşı tarafın kazanması diye ikiye ayrılır (banko kararında farklı riskler)
- **Hafta detayı** — maç tablosuna kapanış oranı sütunu, favori vurgulu
- **Kesit açıklaması** — filtrenin altında hangi haftaların hesaba girdiği; "son 12 hafta"nın
  ardışık 12 numara değil, veri setindeki son 12 kayıt olduğu görünür

---

### 3.5 Geri test (`44a83e4`)

**Soru.** "Bu strateji geçen sezon ne yapardı?" Sayfadaki her şey geçmişi *anlatıyordu*; hiçbiri
bir kararın ne kadara mal olacağını söylemiyordu.

**Zincir.** Kapanış oranı → marj arındırılmış olasılık → eşikli seçim (favori olasılığı ≥ banko
eşiği ise banko, < üçlü eşiği ise üçlü, arası çifte) → `solve_fix16` (ya da blok/sezgisel yedeği)
→ gerçekleşen sonucun skoru. Yeni olan yalnızca eşik katmanı ve skorlama; geri kalanı var olan
modüller.

**Ölçülen** (orantısal ölçek — ölçüldüğü günkü hâli). Varsayılan eşiklerle 36 haftanın
**3'ünde** 14+ tutuyor, hafta başına ortalama **2.686 kolon**. Shin ölçeğinde aynı tablo
1.987 kolon/hafta ve hold-out'ta 1 hafta (§3.18). Küme içi kalan hafta **yok** — 15 maçın tamamını işaretlerin içinde tutmak
piyasa oranlarıyla pratikte olmuyor. Bu bir bulgu, kusur değil.

**Aşırı uyuma karşı üç önlem.** Wilson %95 güven aralığı (41 hafta küçük örneklem; normal
yaklaşım kenarlarda 1'i aşıyordu) · 28 eşikli tarama, "en iyi satır" diye sunulmadan ·
**hold-out**: eşik o haftayı görmeden seçildiğinde ne oluyor. Taramanın en iyisi 4 hafta,
hold-out **0** — fark aşırı uyumun büyüklüğü.

**Hız.** Kaplama, boyut imzasına göre önbelleklenir: 8 çifte + 2 üçlü, hangi maçlarda olursa
olsun aynı bedeli verir. Tek strateji 41 haftada 1,2 sn. ILP bilerek dışarıda — tek imza için
~3 sn harcıyor ve taramayı 95 sn'ye çıkarıyordu; tek kupon çözerken değerli, yüzlerce imza
tararken değil.

### 3.6 Karar destek kartları (`2d90b64`)

Bölüm 5'te ölçülmüş üç bulgu sayfaya çıktı. Üçü de `?last=N` dilimine uyuyor, 30 maçın altındaki
satırlar "az örnek" işaretli.

**Çift kapsaması.** Üç sayı yan yana: piyasanın dediği kapsama, gerçekleşen kapsama ve aynı
bantta banko yapılsaydı ne olacağı. İlk-iki toplamı %70–80 iken çifte %77,4 tutuyor ama banko
%48,7; %90+ bandında banko zaten %84,4 tutuyor ve ikinci işaret yalnızca 12,5 puan ekliyor —
kolonu ikiye katlayan karar bu tablonun işi.

**Beraberlik profili.** Fark 0–0,05 iken %32,7, 0,50+ iken %14,3. Eğilim var ama tam monoton
değil. Tahmin katmanının **girdilerinden biri**; tek başına tahminci olarak
kullanılamayacak kadar zayıf ve isabeti ölçülmeden karara bağlanmaz (bkz. §7).

**Lig kırılımı.** Kuponun yarısı Süper Lig'den (kupon başına 7,5 maç), orada beraberlik %29,8;
Premier Lig'de %19,7. Lig kodları okunur ada çevrildi; eşleşmeyen değer olduğu gibi geçiyor.

### 3.7 Formüle devir (`9d9cfac`)

Hafta detayındaki düğme 15 maçın marj arındırılmış olasılığını formül sayfasına taşıyor.
**İşaretler taşınmıyor** — bugün hangi maça kaç işaret konacağı kullanıcının kararı. Amaç
değişikliğiyle birlikte bu bir tasarım ilkesi değil, **bir sonraki adımın konusu** oldu:
işaret önerisi ancak isabeti hold-out ile ölçülmüş bir tahminci çıktığında devreye girer
(§6, G2/S2). Oranı bulunamayan maç 1/3'e düşüyor ve hangileri olduğu notta yazıyor.

Devir mekaniği tarayıcıda ölçülerek oturdu. App Router istemci geçişinde hedef sayfa **iki kez
bağlanıyor** (ölçüldü: `getItem` sırasıyla "dolu", "null"); "oku ve sil" yaklaşımında ilk
bağlanma paketi tüketiyor, ayakta kalan ikincisi boş buluyordu. İşareti URL'den düşürmek de
çözmedi — düşürünce ikinci bağlanma paketi *uygulayamaz* hale geliyor. Çözüm: işaret URL'de
(`?hafta=51`), paket depoda ve ikisi de tüketilmiyor; kaç kez bağlanırsa bağlansın aynı değerler
yazılıyor.

### 3.8 Kullanım cilası (`c6a8d0f`)

**URL'de filtre.** `/istatistik?last=12` paylaşılabilir; adres okunmadan istek atılmıyor, yani
paylaşılan bağlantı önce tüm sezonu çekip sonra dilime dönmüyor. Yazma yolu `router.replace`
*değil* `history.replaceState`: router üzerinden aynı rotaya replace sayfa bileşenini yeniden
bağlıyor ve her filtre tıkında iskelet parlıyordu.

**CSV.** Hafta tablosundan **görünen** satırlar iniyor — arama ve sıralama neyi bırakıyorsa o.
Noktalı virgül ayraç, virgüllü ondalık, BOM: üçü de Excel'in Türkçe yereldeki davranışı için.

**Haftalık Brier.** Favori isabeti tek başına yanıltıcı: 1,05 oranlı favorinin tutmasıyla 2,40
oranlınınki aynı sayılmaz. Brier olasılığın tamamını cezalandırıyor. Sezon ortalaması **0,579**;
üç sembole eşit olasılık vermenin karşılığı 0,667 — piyasa bilgi taşıyor ama az.

### 3.9 İddaa bülten arşivi (`f1eb65c`)

`scripts/snapshot_iddaa.py` açık bültenin o anki halini tarih damgalı saklıyor. Canlı bültene
karşı yazıldı: maç sonucu pazarı `t=1, st=1`, 226 futbol etkinliğinin 225'inde var, iki fiyat
listesi (`odd` kupon, `wodd` web) ve lig adı ayrı uçtan geliyor.

**İlk ölçüm: iddaa ortalama marjı %17,2.** Piyasa marjı %7,26 idi — "seviye tutmaz, yapı tutar"
cümlesinin artık sayısı var.

225 maçın 3'ünde üçlü `17.95 / 8.48 / 1.00` gibi çıkıyor: 1.00 fiyat değil, askıya alınmış
ayağın yer tutucusu. `match_1x2` zaten aynı kuralı uyguluyordu; snapshot da eliyor ve kaç maçın
neden elendiğini raporluyor.

**Haftalık tetik açık** (`.github/workflows/snapshot-iddaa.yml`): her pazartesi 06:00 UTC
(TR 09:00), hafta kuponu açıktayken. İş yalnızca `backend/data/iddaa/` altına yazar, değişiklik
yoksa commit atmaz ve aynı anda tek çalışma yapar. **Zamanlanmış işler yalnızca varsayılan
daldan çalışır** — arşiv, bu dal `main`'e geçtiği anda birikmeye başlar. Durdurmak: Actions →
bu iş → "Disable workflow".

### 3.10 Tahminci sözleşmesi ve değerlendirme koşumu (T1)

**Soru.** Amaç tahmine döndü — ilk ne yazılmalı? Cevap: model değil, **modeli ölçen koşum.**
Gerekçe projenin kendi geçmişi: eşik taraması 4 hafta gösterirken hold-out 0 çıkmıştı.

`predict.py` sözleşmeyi kurdu — `egit(eğitim_haftaları)` / `tahmin(hafta)`. Ayrım sızıntıya
karşı tek savunma: veriden öğrenen tahminci ölçüldüğü haftayı görerek eğitilemez.
`evaluate.py` koşumu kurdu: hafta dışarıda bırakmalı ölçüm, Brier + log kaybı, **hafta
üzerinden eşleştirilmiş bootstrap** (aynı haftanın maçları bağımsız değil).

Karşılaştırma kuralı koddadır: `gecti`, ancak güven aralığının **tamamı** sıfırın altındaysa
`True`. "Ortalaması daha iyi çıktı" yeterli değil.

**Ölçülen çizgi** (36 hafta, 540 maç): `piyasa` 0,5747 · `sezon_sabiti` 0,6505 · `duzgun`
0,6667. Belgedeki 0,579 ile fark bilinçli — o sayı 2 kısmi haftayı da içeren 38 haftanın
ortalaması; koşum yalnızca 15 maçı tam oranlı haftaları alır, çünkü bütün tahminciler aynı
haftalarda ölçülmezse karşılaştırma anlamsızdır.

### 3.11 Piyasanın yeniden kalibrasyonu (T2)

Mevcut veriyle dürüst tek aday sınıfı. Tek model yerine **kademe** kuruldu — asıl soru "bu
model iyi mi" değil, *"kaçıncı basamakta yardım bitip aşırı uyum başlıyor"*.

| model | parametre | eğitim-içi | dışarıda | fark |
|---|---:|---:|---:|---:|
| piyasa | — | 0,5747 | 0,5747 | 0 |
| kalibre_sicaklik | 1 | 0,5736 | 0,5745 | +0,0009 |
| kalibre_bias | 3 | 0,5727 | 0,5757 | +0,0030 |
| kalibre_lig | 9 | 0,5698 | 0,5777 | +0,0079 |
| kalibre_bant | 15 | 0,5654 | 0,5787 | +0,0133 |

Eğitim-içi monoton iyileşiyor, dışarıda monoton kötüleşiyor, fark kapasiteyle büyüyor.
**Hiçbir basamak geçmedi.** Ölçülmüş lig farkı (%29,8 / %19,7) ve 1,75–2,00 bandı zaten
fiyatlanmış görünüyordu.

**Yol boyunca bulunan iki hata.** (1) `karsilastir` sıraya bağlı `KeyError` veriyordu —
referans listenin başındayken kendi kayıtlarını erken siliyordu. (2) Uydurucu
**yakınsamıyordu**: gradyan inişi 15 parametreli modelde 20.000 adımda hâlâ sürükleniyordu.
Eksik uydurulmuş bir model aşırı uyumla **aynı görüntüyü** verir, yani bulgu yanlış
yorumlanacaktı. Newton yinelemesine geçildi (10 adımda makine hassasiyeti, koşum 27 sn →
1,7 sn) ve bütçe yeterliliği gerileme testine bağlandı. Sonuç iki düzeltmeden sonra da aynı
çıktı.

### 3.12 Eğitim korpusu ve çapraz ölçüm (T3)

540 maçlık kesitte "piyasayı geçen var mı" sorusuna verilen cevap zayıf kalıyordu. Aynı
kaynak (football-data) kupon dışı maçların hem sonucunu hem oranını taşıyor; bir tahminciyi
ölçmek için gereken üçlü budur ve **kupon bileşimi bu iş için ilgisizdir.**

Korpus: **31.103 maç · 4 geçmiş sezon · 22 lig.** Ayrıntı ve ayrım kuralları
[`VERI_TOPLAMA_VE_ISLEME.md`](VERI_TOPLAMA_VE_ISLEME.md) §6A'da.

İki yeni ölçüm kipi: **sezon dışarıda bırakmalı** (aynı sezonun başka haftaları da bilgi
sızdırır) ve **çapraz** (`capraz_olc` — bir sette eğit, ortak maçı olmayan başka bir sette ölç).

| Ölçüm | Sonuç |
|---|---|
| Korpus içi, sezon dışarıda bırakmalı (31.103 maç) | `kalibre_sicaklik` −0,0004 ve `kalibre_bias` −0,0005 **geçti**; lig/bant geçmedi |
| Korpusta eğit → 2025/26 kuponunda ölç (540 maç) | Dört basamak da piyasadan **iyi** (−0,0010…−0,0015) ama **hiçbiri geçmedi** |

**Bulgu.** T2'de kupon üzerinde eğitilen aynı modeller piyasadan *kötü* çıkıyordu; büyük
korpusta eğitilince hepsi *iyi* tarafa geçti. Yani T2'deki aşırı uyum modelin
kapasitesinden değil **örneklem küçüklüğünden** geliyormuş.

**Ama miktar yetersiz.** 31 binde anlamlılık kuruluyor, 540 maçta kurulamıyor. Etki
0,0005–0,0015 Brier; tabanı 0,57–0,59 olan bir sayıda. İddaa marjı %17,2 iken bu büyüklük
pratik eşiğe yakın bile değil. **Yön doğru, miktar yetersiz** — T5'in gerekçesi budur.

### 3.13 Referans skorları sağlık değişmezine bağlandı (T4)

**Soru.** Tahmin katmanının bütün ölçümleri bir koşuma dayanıyor. O koşum sessizce
kayarsa — veri bozulur, oran arşivi eksilir, ölçüt kodu değişir — bunu bugün hiçbir şey
fark etmiyordu.

`tahmin_referanslari` 23. değişmez olarak eklendi (`analiz` kategorisi). Denetlediği şey
**modelin kalitesi değil, ölçümün tekrarlanabilirliğidir** — isabet istatistik katmanının
işidir (geri test, hold-out), sağlık katmanı vaadin canlıda geçerliliğini ölçer.

Üç şey sabitlendi:

1. **Matematiksel özdeşlikler** — `duzgun` Brier'i tam olarak 0,667, log kaybı tam olarak
   ln(3). Kayarsa bozulan şey ölçüt kodudur.
2. **Sıralama** — `piyasa < sezon_sabiti < duzgun`. Bozulursa bozulan model değil **oran
   arşividir.**
3. **Çizgi kendisini geçemez** — hiçbir referans `piyasa`'yı geçmemeli.

**Piyasanın kendi değeri bilerek dar bir eşiğe bağlanmadı.** Kupon seti ikinci sezonla
büyürse değer meşru olarak kayar ve sağlık bundan kırmızı olmamalıdır. Yerine geniş bir
akıl sağlaması var (eşit dağıtımdan iyi, kusursuzdan uzak) ve tam değer mesajda raporlanır:

```
[OK ] tahmin_referanslari  75 ms  hafta=36 mac=540 | piyasa=0.5747 sezon=0.6505 duzgun=0.6667
```

Kontrolün gerçekten bir şey koruduğu ayrıca sınandı: sıralama ya da `duzgun` değeri
bozulduğunda kontrol kırılıyor. Kırılmasaydı dekoratif olurdu.

### 3.14 Kapanış çizgisi verimliliği (A1)

Yol haritasının "tek deneyde en çok bilgi veren ölçüm" dediği iş. Piyasa maç öncesinde
**iki kez** konuşur — bir açılış, bir kapanış çizgisi. Aradaki fark iki ayrı soruyu birden
cevaplar.

**Önce veri.** Korpus bugüne kadar maç başına *tek* bir oran üçlüsü taşıyordu: tercih
sırasındaki ilk tam kaynak, pratikte hep kapanış. Kapanış varsa açılış kayboluyordu — yani
A1'in ölçmek istediği şeyin ta kendisi. Üretici artık iki ucu ayrı sütunlara yazıyor, tek
kuralla: **çift yalnızca aynı bahisçi ailesinden kurulur** (`Avg`↔`AvgC`, `B365`↔`B365C`,
`PS`↔`PSC`). Açılışı `Avg`'den kapanışı `B365C`'den alsaydık aradaki fark piyasanın fikir
değiştirmesini değil, iki farklı fiyatlayıcıyı ölçerdi.

Kesit: **31.099 / 31.103 maç** (%99,99). Çifti olmayan maç elenmedi — `oran_*` tam olduğu
için tahminci ölçümüne giriyor, yalnızca A1 kesitine giremiyor. Korpus boyutu sabit kaldığı
için önceki ölçümler karşılaştırılabilir.

#### Soru 1 — piyasa bilgiyi soğuruyor mu? **Evet.**

Aynı kesitte, aynı maçlarda, sezon dışarıda bırakmalı ölçüm:

| Tahminci | Brier | log kaybı | Fark | %95 aralık |
|---|---:|---:|---:|---|
| **kapanış** (`piyasa`) | **0,5940** | 0,9945 | — | referans |
| açılış (`acilis`) | 0,5964 | 0,9981 | +0,0025 | [+0,0019, +0,0030] |

Aralık **tamamen sıfırın üstünde.** Açılış ile kapanış arasında geçen sürede gelen bilgi
(kadro, sakatlık, hava, para) fiyata işleniyor. Bu, piyasanın *çalıştığının* dolaylı değil
**doğrudan** ölçümüdür.

#### Soru 2 — kapanışın kendisi verimli mi? **Evet; hareket bir şey eklemiyor.**

Kademeye altıncı basamak eklendi: `hareket` = kapanış + açılış→kapanış hareketi, **tek
paylaşılan katsayı.** Tek katsayı kasıtlı, çünkü işareti doğrudan soruyu cevaplıyor.

| Tahminci | Brier | Fark | %95 aralık | Geçti |
|---|---:|---:|---|---|
| `kalibre_form` | 0,5937 | −0,0003 | [−0,0007, +0,0001] | hayır |
| `kalibre_hareket` | 0,5937 | −0,0003 | [−0,0007, +0,0001] | hayır |

İki satır aynı. **Katsayı okuması Brier farkının veremediğini veriyor:** logit
`z_s = β·ln p_kapanış + γ·(ln p_kapanış − ln p_açılış)` biçiminde kurulduğu için **γ/β,
kapanışın ötesine ne kadar uzatılacağıdır.** Ölçülen: β = 1,094, γ = 0,0111, yani
**%1,01.** Model harekete baktı ve kapanışın ötesine uzatmak için kayda değer bir sebep
bulamadı. Bu ayrım önemli: fark sıfıra yakın çıkınca "model harekete bakmadı mı, yoksa baktı
da söyleyecek bir şey mi bulamadı?" sorusu açık kalırdı.

#### Ham sinyal gerçek — ve bu kritik

"Hareket bilgi taşımıyor" bir **yokluk iddiasıdır** ve hareketin *hiç* bilgi taşımamasından
da gelebilirdi. Gelmiyor:

| Hareket büyüklüğü | Lehine tuttu | Aleyhine tuttu | n |
|---|---:|---:|---:|
| <0,05 | %33,4 | %33,5 | 4.577 |
| <0,15 | %36,2 | %33,2 | 12.861 |
| <0,30 | %41,1 | %32,0 | 9.221 |
| ≥0,30 | **%47,2** | %30,2 | 4.440 |

Çizgi ne kadar çok oynarsa yönü o kadar çok tutuyor — güçlü ve monoton bir sinyal. **Ama
tamamı zaten kapanış fiyatında.** Kapanış çizgisinin verimliliğinin ders kitabı tanımı
budur. T5'te aynı disiplin uygulanmıştı: bir yokluk iddiasını yorumlamadan önce ham sinyali
doğrula.

Hareket **marj arındırılmış olasılık** üzerinden ölçülür, ham oran üzerinden değil. Ham
oranın hareketi iki şeyi karıştırır: piyasanın fikir değiştirmesi ve bahisçinin marjını
değiştirmesi. Bütün ayakları aynı oranda kısan bir bahisçi fikrini değiştirmemiştir.

#### Neyi bekçiye bağladık

İki test, bulgunun ölçümden geldiğini kanıtlıyor — koddan değil:

- `test_hareket_sutunu_gercekten_calisiyor` — hareket katsayısı elle değiştirildiğinde
  tahmin **değişmeli**. Değişmiyorsa sütun ölüdür ve "yardım etmiyor" bulgusu bağlanmamış
  bir koddan gelir.
- `test_korpusta_cizgi_gercekten_oynuyor` — üretici bir gün iki ucu da aynı sütundan
  doldurursa açılış = kapanış olur, hareket her maçta sıfır çıkar ve **A1 raporu sapasağlam
  görünür.** Aynı çizgi iki kez yazılmış bir korpusta bunu başka hiçbir şey yakalamaz.

### 3.15 Bahisçi anlaşmazlığı (A2)

A1 baştan sona `Avg` — bütün bahisçilerin **ortalaması** — üzerinden ölçtü. Ortalamanın
etrafındaki **dağılım** ayrı bir büyüklüktür ve ortalamanın kendi değerinde görünmez. A2
kolektifin içine bakıyor: daha iyi bir üye var mı, ve üyeler arasındaki dağılım bilgi mi?

#### Kaynak seçimi ölçümü belirledi

football-data yedi tekil bahisçi veriyor ama **kapsamaları sezona göre değişiyor** (31.132
maçta ölçüldü):

| Kaynak | 2122 | 2223 | 2324 | 2425 |
|---|---:|---:|---:|---:|
| `B365C`, `PSC` | %100 | %100 | %100 | %100 |
| `BWC` | %99 | %100 | %97 | **%63** |
| `WHC` | %99 | %91 | %94 | **%76** |
| `BFC`, `1XBC`, `BFEC` | %0 | %0 | %0 | %100 |

Hepsini isteyen bir filtre 2425'in %40'ını atardı. **Sezon dışarıda bırakmalı ölçümde bu
sessiz bir yanlılıktır** — model bir sezonu diğerlerinden farklı bir maç evreninde öğrenir.
Bu yüzden yalnızca dört sezonda da ~%100 olan dört kaynak taşındı: `B365C`, `PSC`, `MaxC`,
`AvgC`. Kesit **31.100 maç** ve sezonlara göre dengeli.

İkinci karar aynı gerekçeden: iki anlaşmazlık ölçüsü var ve biri bilerek ikincil.

| Ölçü | Tanım | 2122 | 2223 | 2324 | 2425 |
|---|---|---:|---:|---:|---:|
| `ayrisma` | ½·Σ\|p_B365 − p_PS\| | 0,0142 | 0,0122 | 0,0125 | 0,0124 |
| `en_iyi_prim` | ort ln(Max/Avg) | 0,0712 | 0,0641 | 0,0629 | 0,0577 |

`en_iyi_prim` daha geniştir (bütün bahisçi evrenini görür) ama **bahisçi sayısına
duyarlıdır**: football-data kaynak ekledikçe `Max` mekanik olarak kayar — %20'lik bir
sürüklenme. Modele yalnızca `ayrisma` verilir; sürüklenen bir özellik modele anlaşmazlık
değil **sezon kimliği** öğretir.

#### Soru 1 — kolektifin içinde daha iyi bir üye var mı? **Evet: Pinnacle**

| Tahminci | Brier | log kaybı | Fark | %95 aralık | Geçti |
|---|---:|---:|---:|---|---|
| `ps` (Pinnacle) | **0,5936** | 0,9938 | −0,0004 | [−0,0006, −0,0002] | **EVET** |
| **kolektif** (`piyasa` = `Avg`) | 0,5940 | 0,9945 | — | referans | — |
| `b365` | 0,5943 | 0,9951 | +0,0003 | [+0,0001, +0,0005] | hayır |

**Projede referansı geçen ilk tahminci.** Ama bunu doğru okumak şart — ayrıntısı §6.2 A4'te:
bu bir *model* başarısı değil, bir **kaynak seçimi** bulgusudur ve asıl söylediği şey
referans çizgimizin 0,0004 kadar yumuşak olduğudur. Bulgu `PS`'e özgü: `B365` kolektiften
*kötü*, yani "tekil kaynak kolektifi geçer" diye bir genelleme çıkmıyor.

#### Soru 2 — anlaşmazlık bilgi mi? **Hayır — ve sebebi T5/A1'dekinden farklı**

Ham tablo önce aksini söylüyor gibi:

| Ayrışma | n | Kolektif Brier | Ort. p_favori |
|---|---:|---:|---:|
| <0,01 | 13.532 | 0,6048 | 0,4841 |
| <0,02 | 12.492 | 0,5941 | 0,4989 |
| <0,04 | 4.774 | 0,5662 | 0,5273 |
| ≥0,04 | 302 | **0,5402** | 0,5336 |

Anlaşmazlık arttıkça kolektif *daha* isabetli. Ama sağdaki sütun karışmayı ele veriyor:
**favori gücü de aynı yönde artıyor** ve güçlü favorili maçların Brier'i zaten mekanik
olarak düşüktür (0,85'lik bir favori tuttuğunda ~0,05; üç yönlü bir maçta ~0,66).
Bahisçiler, favorinin belirgin olduğu maçlarda daha çok ayrışıyor.

Favori gücü sabitlenince ilişki **tamamen kayboluyor**:

| p_favori | <0,01 | <0,02 | <0,04 |
|---|---:|---:|---:|
| <0,40 | 0,6611 | 0,6639 | 0,6622 |
| <0,50 | 0,6429 | 0,6447 | 0,6415 |
| <0,65 | 0,5673 | 0,5674 | 0,5682 |
| ≥0,65 | 0,3758 | 0,3788 | 0,3645 |

Katsayı da bunu tekrarlıyor: δ = 0,0158, yani ortalama anlaşmazlıkta kolektife duyulan
güveni **%0,02** değiştiriyor. Model zaten `ln p_s` taşıdığı için favori gücüne
koşullanmış durumda; anlaşmazlık üstüne hiçbir şey eklemiyor.

**Bu farklı bir null.** T5'te form, A1'de çizgi hareketi **gerçek** ham sinyaldi ve piyasa
onları fiyatlamıştı. Burada ham sinyalin **kendisi bir yanılsama**. İkisini ayırmadan
"anlaşmazlık yardım etmiyor" demek, doğru sonucu yanlış sebeple kaydetmek olurdu.

### 3.16 Piyasa dışı ama türetilebilir özellikler (A3)

Faz A'nın son işi. §6.2 A3 altı özellik listelemişti; **ilk iş listeyi denetlemek oldu** ve
ikisi elendi — korpusta türetilecek bir şey yok:

| Elenen | Neden |
|---|---|
| **Seyahat** | Şehir/koordinat yok. Ayrıca bir maçın iki takımı **her zaman aynı ligde** (`Div` tek değer); "deplasman takımının lig/ülke değişimi" maç düzeyinde bir büyüklük değil |
| **Derbi** | Şehir eşlemesi ya da rekabet tablosu yok. Elle derbi listesi yazmak *türetme* değil **küratörlük** olurdu |

İkisi de yeni bir **veri kaynağı** ister, yani A4(b)'nin yeniden açılma şartına aittir.
Denemiş gibi yapıp sessizce atlamaktansa gerekçesiyle kayda geçti — *"denenmedi"* ile
*"denenemez"* farklı şeylerdir ve A4 bu ayrımı yazmak zorunda.

Kalan dördü türetildi ve kademeye birer basamak olarak eklendi (`egitim._takvim_tablosu`):

| Tahminci | Brier | Fark | %95 aralık | Geçti |
|---|---:|---:|---|---|
| `kalibre_dagilim` (taban) | 0,5937 | −0,0003 | [−0,0007, +0,0001] | hayır |
| `kalibre_dinlenme` | 0,5936 | −0,0003 | [−0,0007, +0,0001] | hayır |
| `kalibre_sikisiklik` | 0,5937 | −0,0003 | [−0,0007, +0,0001] | hayır |
| `kalibre_ic_dis` | 0,5937 | −0,0003 | [−0,0007, +0,0001] | hayır |
| `kalibre_sezon_sonu` | 0,5937 | −0,0003 | [−0,0007, +0,0001] | hayır |

**Dört özellik üstüste eklendiğinde taban çizgisi hiç kımıldamadı.**

#### Betimleyici tablo ham farkı değil **artığı** raporluyor

A2'nin dersi buraya taşındı. Artık = gerçekleşen ev oranı − **piyasanın beklediği** ev oranı.
Ham fark özelliğin bilgi taşıyıp taşımadığını söyler; artık, o bilginin **fiyata girmemiş**
kısmını. A3'ün sorusu ikincisidir.

En öğretici örnek iç/dış saha formu:

| Özellik | Ham fark (ev galibiyeti oranı) | En büyük artık |
|---|---:|---:|
| `ic_dis_form_farki` | **+0,247** | +0,090 |
| `sezon_sonu_pay_farki` | +0,106 | +0,060 |
| `dinlenme_farki` | −0,028 | −0,044 |
| `sikisiklik_farki` | −0,021 | −0,018 |

İç/dış form ham haliyle devasa bir sinyal taşıyor — ev takımının iç saha formu iyiyken ev
galibiyeti oranı 25 puan yüksek. Piyasa onu neredeyse tamamen fiyatlamış. **Güçlü sinyal,
sıfır katkı.**

`sikisiklik` taramasının eşiği 1,0'dan 0,5'e indirildi: 1,0'da kuyruklarda 300 maç kalıyor,
favori dilimlerine bölününce hücreler 30–130'a düşüyor ve tarama **sessizce cevapsız**
kalıyordu. Cevapsızlığın "artık yok" diye okunması A3'ün en kolay yapılacak hatası olurdu;
`dilimlenemedi` bayrağı artık bunu açıkça taşıyor.

#### Korpusun kör noktası — iddia değil ölçüm

Korpus 22 lig taşıyor; **kupa ve Avrupa maçları içinde yok.** Dinlenme olduğundan uzun,
sıkışıklık olduğundan düşük ölçülür — ve hata rastgele değil, Avrupa oynayan takımlarda
yoğunlaşır. Bunu yazıp geçmek kolay olurdu; sınandı:

| Lig katmanı | Ev dinlenmiş | Dengeli | **Dep dinlenmiş** |
|---|---:|---:|---:|
| Avrupa'ya takım veren | +0,0026 | −0,0032 | **+0,0655** (n=445) |
| Diğer | +0,0072 | +0,0046 | +0,0162 (n=1.136) |

Deplasman "dinlenmiş" göründüğünde ev takımı piyasanın beklediğini aşıyor ve etki Avrupa
liglerinde **dört kat** güçlü — korpusta görünmeyen bir maç oynanmış olmasıyla tutarlı.

**Ama bu bir bulgu değil.** n=445, çok hücreli bir taramadan okunuyor ve dışarıda bırakmalı
ölçümde katkısı sıfır. Değeri, A4(b)'nin yeniden açılma koşulunu **somutlaştırması**: eksik
olan model değil, **fikstür verisi**.

> **Sonradan (Faz 3.4, §3.36):** fikstür verisi geldi ve hipotez **doğrulandı**. UEFA
> maçları takvime katılınca aynı hücre **+0,0613'ten +0,0325'e** düştü (yukarıdaki
> +0,0655 daha eski bir korpus koşumundandır; kontrollü karşılaştırma §3.36'da). Yani bu
> satırın yarısı bir sinyal değil, **görünmeyen bir maçtı**. Kalan yarı hâlâ duruyor ve
> dışarıda bırakmalı ölçümde hâlâ sıfır.

### 3.17 Tahmin ürünü — olasılık, ölçülmüş isabetiyle birlikte (C2)

Tahmin katmanı bu işten önce **ürüne hiç bağlı değildi**: `web_app.py` onu import
etmiyordu, API uçlarının hiçbiri tahmin döndürmüyordu, `/tahmin` diye bir sayfa yoktu.
Ölçüm aracı olarak yaşıyordu, ürün olarak değil — oysa projenin amacı (README §1) *maç
sonucu tahmini yapmak*.

#### Kaynak seçimi ölçümü belirledi (C2a)

Oynanmamış maçın hiçbir arşivde oranı yok. Kaynak football-data'nın `fixtures.csv`
dosyası ve seçim kasıtlı: **ölçümü yaptığımız kaynağın ta kendisi.** Kupon setinde
ölçülen isabet aynı fiyatlayıcıya ait olduğu için ürüne meşru biçimde taşınabilir.

İddaa bülteni yedektir ve **kalibrasyonu ölçülmemiştir** (marj %17,2'ye karşı %7,26).
İkisi birleştirilmez, **sıralanır**: fikstürde maç varsa o gösterilir. Karıştırmak,
gövdedeki tek bir isabet sayısının iki farklı fiyatlayıcıya aitmiş gibi okunmasına yol
açardı.

Fikstür **yuvarlanan bir penceredir**; hafta oynandığında boşalır. "Yaklaşan maç yok"
normal bir durumdur, hata değildir — ve gövde bunu sessizce boş dönerek değil,
`bos_sebep` alanıyla söyleyerek bildirir.

#### Kırmızı çizgi: olasılık isabetinden ayrılamaz (C2b)

`/api/tahmin` gövdesi iki bloğu **ayrılamaz** biçimde taşır: `tahminler` ve
`olculmus_isabet`. `?limit=` yalnızca listeyi kırpar; isabet ve uyarılar hep tam gelir.
Bekçisi `test_api_tahmin_isabeti_hep_tasir`.

İsabet **elle yazılmadı, arşivden koşuyor** — elle yazılmış bir sayı, veri kaydığında
sessizce yalan söylemeye başlar:

| Ölçü | Değer |
|---|---|
| Maç başına isabet | **%55,6** (540 maç · 36 hafta) |
| Haftada ortalama doğru | **8,33 / 15** · en iyi hafta 12 |
| Brier · log kaybı | 0,5747 · 0,9660 |
| 14+ tutan hafta | **0 / 36** |

`uyarilar` bloğu gövdenin sınırlarını taşır ve **kısaltılmaz**. İkisi her zaman var:

- **`tek_kolon_14_tutmaz`** — ürünün söyleyebileceği en büyük yalanı engelleyen uyarı.
  Metin "zor" demiyor, **ölçülmüş sayıyı** söylüyor: P(14+) ≈ 1/1.161 hafta, 36 haftada
  beklenen 0,031, gözlenen 0. 14+'a kaplama motoru taşır, tahminci değil.
- **`model_yok`** — olasılıklar piyasa fiyatıdır; dokuz özellik denendi, hiçbiri geçemedi.

İkisi koşullu: açılış oranı olduğu (A1'in ölçtüğü bedel +0,0025 Brier) ve iddaa kaynaklı
maçların kalibrasyonunun ölçülmediği.

**Başlamış maça maç öncesi olasılığı verilmez:** canlı işaretli maçlar, başlama saati
geçmiş maçlar ve saati çözülemeyen maçlar elenir. Sonuncusu doktrin 2 — belirsiz bir
zamana "maç öncesi" demek, iddiayı doğrulanamaz kılar.

`/api/tahmin` **önbelleklenmez** ve bu kasıtlı: diğer uçlar sürümlenmiş dosya okur, burası
yaklaşan maçları okur ve cevap zamanla değişir. Önbelleklenmiş bir tahmin, başlamış bir
maça maç öncesi olasılığı göstermeye devam ederdi.

#### İki tahminci yan yana — 31 binlik korpusun ürüne dönüşü

Ürün ilk sürümünde yalnızca eğitimsiz `piyasa`yı taşıyordu ve **31.103 maçlık
korpusun ürüne katkısı sıfırdı.** Korpusun işi "eğitmek yardım ediyor mu" sorusunu
cevaplamaktı; cevap *"yön doğru, miktar kurulamadı"* çıkmıştı.

Çapraz sınav (korpusta eğit → 540 maçlık kuponda ölç, **ortak maç yok**) şunu veriyor:
eğitilmiş basamakların **on biri de** piyasadan iyi (0,5732–0,5737'ye karşı 0,5747) ama
**hiçbiri geçmiyor** — her birinin güven aralığı sıfırı içeriyor.

Bu bir çifte dürüstlük sorunu yarattı:

| | Sonuç |
|---|---|
| Geçmemiş modeli **manşet yapmak** | Ölçülmemiş bir üstünlüğü arayüze koymak olurdu |
| Ölçülmüş modeli **hiç göstermemek** | Ölçülen bir şeyi saklamak olurdu |

Çözüm ikisini **yan yana** koymak:

| Tahminci | Brier | Fark | %95 aralık | Geçti |
|---|---:|---:|---|---|
| `piyasa` (manşet, eğitimsiz) | 0,5747 | — | referans | — |
| `kalibre_bias` | **0,5732** | −0,0015 | [−0,0035, +0,0004] | **hayır** |

**`bias` basamağı seçildi ve seçim kasıtlı.** Üç parametresi var (sıcaklık + iki sınıf
sabiti) ve yalnızca `probs` okur — lig, form, çizgi hareketi gibi yaklaşan maçta
**elimizde olmayan** hiçbir alana ihtiyaç duymaz. Üst basamaklar o alanları nötr sıfır
görüp aynı sayıyı üretirdi; fazladan parametre, fazladan iddia demek olurdu.

**Ve bir şey ölçüldü:** alternatif, 117 maçın **hiçbirinde** farklı sembol seçmiyor.
Yalnızca güveni keskinleştiriyor (%70,8 → %74,0). Yani *tek kolon oynayan biri için iki
tahminci aynıdır*; fark ancak olasılığa dayalı bir kupon kurarken anlam taşır.
`alternatif_farkli_secim` alanı bunu her koşumda sayar — kullanıcının tahmin etmesi değil
**görmesi** gereken bir şey.

**Sessiz ve zehirli bir hatanın bekçisi.** `recalibrate._mac_ozellikleri`, `ozellikler`
alanı yoksa oran arşivine `(hafta, maç no)` ile bakar — kupon setine özgü bir yol.
Yaklaşan maçta o arama **tamamen başka bir maçın** özelliğini döndürürdü. `_sozde_hafta`
alanı açıkça doldurur ve `test_alternatif_sozde_haftada_kupon_arsivine_bakmaz` bekçidir.

`test_alternatif_gecmedi_diye_etiketli` bilerek kırılgan: alternatif bir gün **geçerse**
test kırılır ve manşet kararı bilinçli olarak gözden geçirilir — sessiz bir güncelleme
olmaz.

#### Sayfanın sıralaması bir karardır (C2c)

**Ölçülmüş isabet, tahmin tablosunun üstündedir.** Kullanıcı önce bu tahmincinin 540 maçta
ne yaptığını görür, sonra bu haftanın sayılarını. Ters sırada olsaydı isabet bir dipnot
olurdu; sayfanın amacı ise onu dipnot olmaktan çıkarmak. Aynı sebeple sınırlar katlanmaz —
bir uyarıyı açılır kutuya koymak, onu göstermemektir.

Çalıştırılarak iki kusur ölçülüp düzeltildi: 117 maç tek blok hâlinde **5.841 px**
sürüyordu (C3'ün kaydettiği kusurun aynısı) — tablo günlere bölündü; ve kaynağın tamamı
ölçüm dışıyken satır başına yıldız hiçbir şeyi ayırt etmiyordu — kaldırıldı, uyarı bir kez
tepede söyleniyor.

#### Çelişen metinler düzeltildi

Kabuk altbilgisi ve formül sayfası *"bu araç maç sonucu tahmin etmez"* diyordu. `/tahmin`
sayfasından sonra bu yanlış — ama alttaki ayrım **gerçek ve korunmalı**: kaplama motoru
tahmin etmez, garanti verir. Metinler kapsamlarına göre ayrıldı; "bu araç" yerine "kaplama
motoru" yazıldı ve formül sayfası `/tahmin`e bağlandı.

---

### 3.18 Marj arındırma ve ampirik sorgu (A5)

Faz A dört cepheden (T5, A1, A2, A3 — dokuz özellik) piyasayı geçmeye çalıştı ve hiçbiri
geçemedi. Bu iş, **hiç sorulmamış bir soruyu** sordu: piyasa oranını olasılığa çeviren
adımın kendisi doğru mu?

İş, istenen bir üründen çıktı: *"bu oranda geçmişte ne olmuş?"* — `spor_toto/benzer.py`.
Araç yazılınca ilk gösterdiği şey aradığı cevap değil, **kendi girdisinin yanlılığı** oldu.

#### Eşleme neden olasılık uzayında yapılır

Ölçüldü. 1.82/3.04/2.44 (marj %28,8) korpusta aranınca:

| Eşleme | Bulunan |
|---|---:|
| Birebir aynı oran | **0** |
| Oran ±%2 | **0** |
| Oran ±%10 | **0** |
| Olasılık ±2 puan | **710** |

Aynı gerçek olasılık, farklı marjda tamamen farklı oran verir. Oran uzayında arama sessizce
"sonuç yok" der. `tests/test_benzer.py::test_oran_uzayinda_arama_bos_doner` bunu çiviler.

#### Bulgu: orantısal arındırma favoriyi eksik fiyatlıyor

Her sembol kendi olasılık bandında, gözlenen ↔ piyasanın dediği (31.103 maç, Wilson %95):

| Band | n | Piyasa | Gerçek | Fark | GA dışında |
|---|---:|---:|---:|---:|:--:|
| %5–10 | 1.697 | %7,9 | %5,7 | **−2,2** | ✗ |
| %10–15 | 3.557 | %12,8 | %10,6 | **−2,2** | ✗ |
| %15–20 | 6.530 | %17,7 | %16,6 | −1,2 | ✗ |
| %20–25 | 11.924 | %22,8 | %21,7 | −1,1 | ✗ |
| %25–40 | 45.074 | — | — | ~0 | içeride |
| %40–45 | 6.828 | %42,4 | %43,6 | +1,2 | ✗ |
| %50–55 | 3.757 | %52,4 | %54,3 | +1,9 | ✗ |
| %55–60 | 2.820 | %57,3 | %60,1 | +2,8 | ✗ |
| %60–70 | 3.346 | %64,5 | %67,2 | +2,7 | ✗ |
| **%70–80** | 1.702 | %74,5 | **%78,9** | **+4,4** | ✗ |
| %80+ | 627 | %83,8 | %86,8 | +3,0 | ✗ |

Sapma **tek yönlü ve düzenli**: sürprizler abartılıyor, favoriler küçümseniyor — klasik
favourite–longshot yanlılığı. 15 banttan **10'u** anlamlı sapıyor.

Bu bir model kusuru değil, bir **çevrim** kusuru. `implied_probs` marjı her sonuca eşit
oranda dağıtıyordu (`p = (1/o) / Σ(1/o)`); oysa bahisçi marjı sürprizlere daha ağır yükler.

#### Düzeltme: Shin ve güç yöntemi

`odds.implied_probs` artık üç yöntem taşıyor. Marj sıfırken üçü **çakışır**; ayrıştıkları
yer yüksek marjdır — iddaa bülteni (~%18) tam olarak orası.

| Yöntem | Brier (31.103) | Log | Anlamlı sapan bant |
|---|---:|---:|---:|
| `orantili` (varsayılan) | 0,5940 | 0,9945 | **10 / 15** |
| `guc` | **0,5936** | **0,9937** | — |
| `shin` | **0,5936** | 0,9938 | **4 / 15** |

Brier farkı **0,00042**. Kıyas: A2'de "projenin piyasayı geçen ilk tahmincisi" diye kaydedilen
Pinnacle bulgusu 0,0004 idi. Aynı büyüklükteki kazanç, **yeni veri kaynağı ve model eğitimi
gerektirmeden**, tek fonksiyonda duruyordu.

En büyük bant hatası (%70–80) +4,4 → +3,0 puana iniyor; kalan sapma ampirik/izotonik bir
kademeyle kapatılabilir ve o iş **henüz yapılmadı**.

#### Varsayılan `shin`e çevrildi — ve eşiklerin değişmesi gerekmedi

`ARINDIRMA_VARSAYILAN` 2026-08'de **`shin`** oldu. Karar dört ölçüme dayanıyor:

| Ölçüm | orantısal | shin |
|---|---:|---:|
| Brier (31.103 maç) | 0,5940 | **0,5936** — fark −0,00035 [−0,00049, −0,00021], **geçti** |
| Anlamlı sapan bant | 10 / 15 | **4 / 15** |
| Geri test kolon/hafta (hold-out) | 6.897 | **2.228** |
| Hold-out'un seçtiği eşik | 36 haftanın 31'inde 0,68/**0,42** | 34'ünde 0,68/**0,38** |

Son satır en öğreticisi. Orantısal ölçekte hold-out eşiği projenin varsayılanından
(0,68/0,38) **uzağa** kaydırıyordu; Shin ölçeğinde 36 haftanın 34'ünde tam varsayılanı
seçiyor. **Eşik baştan doğruymuş; eğri olan onu besleyen olasılıktı.** Bu yüzden
`VARSAYILAN_BANKO`/`VARSAYILAN_UCLU` değiştirilmedi — değiştirilmesi için bir sebep
çıkmadı.

Hold-out'ta 14+ sayısının 0'dan 1'e çıkması **okunmaması gereken** satırdır: tek olay,
ve aralıklar fazlasıyla örtüşüyor (%0,5–14,2 ↔ %0–9,6). Sağlam olan sayı maliyettir.

Çevrimin bedeli ödendi: `/api/stats` oran tabloları, geri test sayıları, README §5.4 ve
bu belgedeki tablolar yeniden koşuldu; `health` yeşil kaldı (kupon seti Brier 0,5747 →
**0,5740**). Çevrimden önce yayımlanmış sayılar orantısal ölçekte ölçülmüştür ve
belgede o etiketle durur.

#### İki ölçü bilerek `orantili`da bırakıldı — ve bunu projenin kendi testi yakaladı

Çevrim yapıldığında `test_hareket_saf_marj_degisimini_gormez` kırıldı. Testin çivilediği
değişmez şuydu: bahisçi bütün ayakları aynı çarpanla kısarsa **fikri değişmemiş**, yalnızca
marjı büyümüştür; arındırılmış olasılık kımıldamamalıdır.

Orantısal yöntem oranın ölçeğinden bağımsızdır, yani bu değişmezi sağlar. **Shin ve güç
yöntemleri sağlamaz** — ve bu onların kusuru değil, tanımı: ikisi de marjın büyüklüğünü
*bilgi* sayar. Bir **seviye** ölçerken (tek fiyat → olasılık) bu istenen davranıştır. Bir
**fark** ölçerken felakettir: A1 fikir değişimi yerine bahisçinin fiyatlama politikasını
ölçmeye başlardı.

Aynı gerekçe A2 için de geçerli: B365 ile Pinnacle'ın marjları farklıdır, ölçek duyarlı
bir arındırmada o marj farkı "anlaşmazlık" diye okunurdu. Nitekim çevrim, A2'nin ham
tablosunun yönünü de ters çevirmişti.

Kural bu yüzden ikiye ayrıldı (`egitim.FARK_ARINDIRMASI`):

* **Seviye** ölçüleri (kupon kararı, tahmin, kalibrasyon) → varsayılanı izler (`shin`).
* **Fark** ölçüleri (`cizgi_hareketi`, `bahisci_ayrismasi`) → `orantili`ya sabit.

A1 ve A2'nin yayımlanmış sayıları bu sayede olduğu gibi geçerli kaldı.

#### A2'nin bekçisi de mutlak eşikten göreliye çevrildi

`test_favori_sabitlenince_iliski_kayboluyor` sabit bir eşik kullanıyordu (0,02 Brier).
O sayı yazıldığı gün en geniş dilimin yayılımı 0,0143'tü — payı dardı. Çevrimden sonra
Brier düzeyleri kayınca aynı dilim 0,0200'e çıktı ve eşiği geçti; **bulgu değişmeden**
test kırıldı, yani eşiğin keyfî olduğu ortaya çıktı.

A2'nin iddiası zaten görelidir: *"koşullayınca ham ilişki kayboluyor."* Ölçüt de o hâle
getirildi — koşullanmış yayılım, ham yayılımın yarısından küçük olmalı. Ölçülen: orantısalda
en fazla %22, Shin'de en fazla %30. İddia iki ölçekte de ayakta.

#### Kalan sapma izotonikle kapatılabiliyor mu? — evet, ama yeni bir şey değil

Shin sonrası dört bant hâlâ anlamlı sapıyordu. Soru şuydu: bu artık, **parametresiz
monoton** bir düzelticiyle kapanır mı? `recalibrate.IzotonikTahminci` bunun için yazıldı —
üç sembol havuzlanır, eşit sayıda noktalı kovalara bölünür, ağırlıklı PAV ile monoton
eğri uydurulur, sonra 1'e normalize edilir. Ölçüm **sezon dışarıda bırakmalı**
(`spor_toto/kalibrasyon.py`; izotonik esnek bir düzelticidir, aynı sezonda uydurulup aynı
sezonda ölçülürse kesin yanıltır — o yüzden başka bir ölçüm yolu sunulmadı).

| Girdi olasılığı | Tahminci | Brier | Fark | %95 aralık | Geçti |
|---|---|---:|---:|---|---|
| `orantili` | `piyasa` | 0,5940 | — | — | — |
| `orantili` | **`izotonik`** | **0,5936** | **−0,00036** | [−0,00067, −0,00003] | **EVET** |
| `shin` | `piyasa` | 0,5936 | — | — | — |
| `shin` | `izotonik` | 0,5936 | +0,00001 | [−0,00020, +0,00022] | hayır |

**Okuma — ve bu satır önemli.** İzotonik, orantısal arındırmanın üstünde piyasayı geçiyor;
ama Shin'in üstünde **hiçbir şey eklemiyor**. Yani ikisi aynı olguyu ölçüyor, ikisi
toplanmıyor. Kazanç 0,0004'tür ve iki kez sayılamaz.

Pratik sonuç: **düzeltme izotonikle değil arındırmayla yapılmalı.** Shin tek parametreli,
kapalı formda ve fiyatın kendi yapısından türeyen bir düzeltme; izotonik ~90 kovalı,
veriden uydurulan bir eğri. Aynı kazanç için basit olan tercih edilir. İzotonik kademe
kodda **ölçüm aracı olarak** kalır — "arındırma değiştiğinde artık kaldı mı" sorusunun
cevabını veren şey odur.

#### Yan bulgu: geçme kuralı yuvarlanmış sayıdan karar veriyordu

İzotonik ilk koşumda `geçmedi` yazdı. Ham üst sınır **−0,000031** idi — yani aralığın
tamamı sıfırın altındaydı ve kural gereği **geçmeliydi**. Sebep `evaluate.bootstrap_farki`:
üst sınır önce 4 basamağa yuvarlanıyor, sonra karşılaştırılıyordu. `round(-0,000031; 4)`
Python'da `-0.0` verir ve `-0.0 < 0` **`False`**'tur.

Hata sessizdi ve tam da **kararın zorlaştığı yerde** — aralık daraldıkça — ortaya
çıkıyordu. Yayımlanmış hiçbir bulgu bundan etkilenmiyor (A1–A3 aralıkları sıfırı açıkça
kesiyor, A2'nin Pinnacle üst sınırı −0,0002). Düzeltildi: `fark` bloğu artık `ham_fark`,
`ham_alt`, `ham_ust` alanlarını da taşır ve `gecti` **yalnızca** ham değeri okur; yuvarlama
gösterime kaldı. `tests/test_evaluate.py::test_cok_dar_aralik_gecmis_sayilir` bekçisi.

#### Sınır — bu bir "piyasayı geçtik" bulgusu DEĞİLDİR

Ölçülen şey piyasanın hatası değil, **piyasa fiyatını okuma biçimimizin** hatasıydı.
Bahisçi zaten marjı sürprizlere yüklüyor; biz onu düz dağıttığımız için favoriyi eksik
okuyorduk. A4'ün "arayış kapandı" hükmü **yerinde duruyor**: bu satır yeni bir tahmin
kaynağı bulmuyor, mevcut kaynağı daha az bozarak okuyor.

Pratik karşılığı yine de küçük değil. 2026/27 2. haftasında (iddaa, %17,8 marj, eşik
0,68/0,38) aynı kuralın ürettiği kupon — hafta verisi PR #14 dalında
(`data/super_toto/2026_27/hafta_02.json`), bu daldan koşulunca birebir üretilir:

| Arındırma | Banko | Çifte | Üçlü | Seçim uzayı | Küme-içi |
|---|---:|---:|---:|---:|---:|
| `orantili` | 0 | 14 | 1 | 49.152 | %2,778 |
| `shin` | 1 | 13 | 1 | **24.576** | **%2,862** |

Kupon yarı fiyata düşerken tutma olasılığı **artıyor** — iki eksende birden. Sebep, 1. maçın
(Galatasaray 1.26) favori olasılığının %67,4 → %71,8 çıkması ve banko eşiğini artık
aşması. 2. haftanın kupon dosyasına düşülen *"eşiği 0,6 puanla kaçırdı"* notu, bu
yanlılığın ta kendisiydi.

#### Sonradan: aracın kendisi kronolojiye sokulabilir hâle getirildi

Dış bir geliştirme planı (bkz. [`BENZER_PLANI_ESLEMESI.md`](BENZER_PLANI_ESLEMESI.md))
üç yerde gerçek kusura parmak bastı ve üçü de koddaydı.

**En önemlisi:** `benzer_maclar` süzgeci yalnızca `lig` ve `sezon`du. `tarih`
her satırda yüklüydü ama hiç okunmuyordu, yani 2022 tarihli bir fiyat
sorulduğunda 2024–2025 maçları da "geçmişte ne oldu" cevabına giriyordu. Bu
canlı tahmine sızıntı değil — korpus güncel sezonu içermiyor — ama araç o
hâliyle **hiçbir kronolojik ölçümün içine konulamıyordu.** §6.6'nın ileri
yürüyüş bulgusu (kronoloji zorlandığında piyasanın artığını öğrenen aileler
2–3 kat kötüleşiyor) tam da bu aracın hiç geçmediği sınavdır.

`tarih=` isteğe bağlı eklendi; varsayılan davranış birebir korundu (`n` = 241
shin, 710 orantılı). Karşılaştırma katı küçüktür, yani sorulan maç kendi
cevabına giremez. Ölçüldü: `2023-08-01` kesmesiyle evren 31.103 → 15.640 ve
uyarlanan yarıçap %2,0'dan **%3,0'a** genişliyor — yarım korpusta hedef
örnekleme ulaşmak zorlaşıyor. Bu, ileri yürüyüş koşumunun kendi örneklem
sorusudur ve koşum henüz yapılmadı (eşleme belgesi §6.1).

`benzer` ayrıca sızıntı sözleşmesinde (`tests/test_sizinti.py`) hiç
geçmiyordu; üç denetimle bağlandı.

**İkinci kusur:** `inf` oran kabul ediliyordu. `inf <= 1.0` yanlıştır, yani
kapıdan geçiyor ve `implied_probs` ona %0 olasılık verdiği için üç anahtar
dönüyordu — alt kattaki `len(hedef) != 3` kontrolü de yakalamıyordu. Sorgu
koşup bir sembolü olmayan hedef vektörle korpusu tarıyordu.

**Üçüncüsü:** tolerans üç kapıda üç farklı sınırdaydı ve HTTP kapısı sınır
dışı değeri **reddetmek yerine kırpıyordu** — `?tolerans=0.9` sessizce başka
bir sorguya dönüşüyordu. Kural tek yere alındı; tavan uyarlanan aramanın
zaten durduğu yer (`EN_COK_TOLERANS`).

Rapora `mesafe` bloğu da eklendi, çünkü `tolerans_genisledi` bir boolean'dı.
Niçin karara girdiği ölçüldü — aynı oran, iki yarıçap:

| tolerans | ortanca mesafe / tavan | piyasa |
|---|---|---|
| 0,02 | %1,58 / %2 | her sembolde GA içinde |
| 0,05 | %3,88 / %5 | iki sembolde GA **dışında** |

İkinci satır bir bulgu gibi görünüyor (3.596 maçta beraberlik piyasanın
4,3 puan üstünde, aralık piyasayı dışarıda bırakıyor) ama ortancası tavanın
dörtte üçünde: o küme "aynı fiyat" değil, yarıçapın kenarı. Eski çıktıda bu
ayrımı yapacak sayı yoktu.

### 3.19 Karar katmanı: seçim artık hedefe göre kuruluyor (B0)

A1–A5 tahmin eksenini ölçtü ve kapattı. Bu iş **tahmin değil karar** katmanına
bakıyor ve önce şu soruyu sordu: *tahmin iyileşmesi zaten neyi satın alıyor?*

#### Önce ölçü: tahmin becerisinin dönüşüm oranı

Piyasa olasılığı gerçek sonuca doğru yapay olarak kaydırılıp (uydurma beceri)
hem Brier hem `P(en iyi kolon ≥ 12)` izlendi (36 tam hafta):

| yapay beceri | Brier | ΔBrier | P(≥12) | ΔP(≥12) |
|---|---:|---:|---:|---:|
| yok | 0,5740 | — | %33,5 | — |
| +1 puan | 0,5562 | −0,0178 | %34,7 | +1,17 |
| +5 puan | 0,4881 | −0,0859 | %38,1 | +4,61 |
| +10 puan | 0,4099 | −0,1641 | %41,6 | +8,09 |

**0,01 Brier ≈ +0,6 puan P(≥12).** A1–A5'te aranan/bulunan mertebe 0,0005
Brier; karşılığı **+0,03 puan**. Yani tahmin ekseni, ürünün asıl sayısı için
çok zayıf bir kaldıraç — bu, "tahmin geliştirmeyelim" değil, "tahmin
geliştirerek kupon sonucunu değiştiremeyiz" demektir.

#### Hedefin tam tanımı

`k` maç seçim kümesinin dışında kalırsa o `k` maç her kolonda yanlıştır; kalan
`15−k` içeridedir ve Hamming bloğu en fazla 1 hata bırakır. Yani en iyi kolon
≥ `14−k`, dolayısıyla **P(en iyi kolon ≥ 12) ≥ P(k ≤ 2)**. Eşitlik değil **alt
sınır**: hedef temkinlidir, optimize edilmesi güvenlidir.

Yapı üç olguyla sadeleşiyor: banko `q = 1−p₁`, çifte `q = p₃`, **üçlü `q = 0`
(asla kaçmaz)**; bedel yalnızca sayılara bağlı (`2^a·3^b·16/2⁷`).

#### Bugünkü kural hiçbir yerde bu hedefi optimize etmiyordu

`backtest.secim_uret` yalnızca favorinin olasılığına bakıyor: ikincinin
olasılığını okumuyor, haftanın şeklini görmüyor, bütçeyi ve kaplama bedelini
bilmiyor, maç maç bağımsız çalışıyor. `p_kume_ici`, Markov zinciri ve Monte
Carlo **sonradan raporlama**; hiçbiri seçime geri beslenmiyor.
`butce_danismani` planları `p_kume_ici`'ye göre sıralıyor ama yalnızca bütçe
kısılırken — ve `p_kume_ici` **P(0 kaçak)** demek, oysa garanti iki kaçağa
kadar 12 veriyor.

#### Ölçüm — aynı bütçe, 36 hafta

`spor_toto/secim.py`, bütçe içinde `P(k ≤ 2)`'yi enbüyüklüyor. Arama **kesin**:
gelecekteki her evrişim kümülatiflerin pozitif doğrusal birleşimi olduğu için
`(cum₀, cum₁, cum₂)` üzerinde Pareto baskınlığı gelecekte de korunur, yani
budama yaklaşıklık değil. `tests/test_secim.py::test_optimizasyon_gercekten_optimal`
bunu dört bütçede kaba kuvvetle karşılaştırarak çiviliyor.

| kural | kolon/hafta | P(k≤2) | en iyi kolon ort. | ≥14 | ≥13 | ≥12 |
|---|---:|---:|---:|---:|---:|---:|
| eşik (0,68/0,38) | 1.987 | %33,50 | 11,50 | 3 | 7 | 21 |
| **hedefe göre** | **1.461** | **%39,52** | **11,81** | 2 | **13** | **24** |

**+6,02 puan hedef ve %26 daha az kolon.** Eşik kuralı 36 haftanın **35'inde**
optimalin altında kalıyor.

**Aşırı uyum yok ve bunu söylemek önemli.** Optimizasyon sonucu GÖRMEZ;
piyasanın kendi olasılığına göre ex-ante bir hedefi enbüyükler. `esik_taramasi`
sonuçlara bakıp eşik seçtiği için hold-out gerektiriyordu; burada seçilen bir
parametre yok, dolayısıyla o risk de yok.

**Okunmayacak satır:** ≥14 sayısının 3'ten 2'ye inmesi. 36 haftada 14+ tek
olaydır ve iki yönde de gürültüdür. Sağlam olan iki sayı **hedef** ve
**maliyet**tir. Gerçekleşenin modelin dediğinden yüksek çıkması (%39,5 ↔ 24/36)
beklenendir: `P(k≤2)` alt sınırdır, kaplama bir kolonu tesadüfen daha iyi
tutturabilir.

#### Varsayılan kural DEĞİŞMEDİ

`VARSAYILAN_BANKO/UCLU` ve `secim_uret` yerinde duruyor; `secim.py` ölçüm ve
kıyas aracı olarak eklendi. Ürün davranışını çevirmek ayrı bir karardır ve
A5'in arındırma çevriminde olduğu gibi açıkça alınmalıdır — çevrildiğinde
dondurulmuş kuponların hangi kuralla kurulduğu da kayda yazılmalıdır.

### 3.20 Asya handikabı + alt/üst → türetilmiş 1X2 (A6) — **geçmedi**

A4 "mevcut veriden türetilebilir bir özellik piyasayı geçemiyor" demişti.
Ama elde olup **hiç bakılmamış** bir veri kaynağı vardı: `build_egitim.py`'nin
zaten indirdiği ana lig dosyaları iki fiyat daha taşıyor.

| Pazar | Kapsam (22 lig × 4 sezon, 31.132 maç) | O güne kadar kullanan kod |
|---|---:|---|
| Alt/üst 2.5 (`AvgC>2.5` / `AvgC<2.5`) | **%99,9** | yok |
| Asya handikabı (`AvgCAHH/AHA` + çizgi `AHCh`) | **%99,9** | yok |

**Bu, A1–A3'ün dokuz özelliğinden farklı bir şey.** Onlar 1X2 fiyatının
*üstüne* eklenen özelliklerdi; bunlar aynı maça verilmiş **bağımsız** iki
fiyat: alt/üst beklenen toplam golü, handikap beklenen gol farkını çiviler.

#### Türetme

İki pazar da marj arındırılır → `P(toplam ≥ 3)` ile Poisson ortalaması μ,
handikap kapama olasılığıyla supremacy δ çözülür (ikisi de tek köklü, ikiye
bölme). `λ_ev, λ_dep = (μ±δ)/2` ve `D`'nin dağılımından 1X2.

**Çeyrek çizgiler ihmal edilemezdi:** arşivdeki çizgilerin **%53'ü** çeyrek
(−0,25 / +0,25 / −0,75 …). `spor_toto/skor.py:ah_kapama` bunları iki yarım
bahse böler ve tam sayı çizgide iadeyi ayrı tutar.

#### Ölçüm

Ham türetme piyasadan **kötü** çıktı (+0,00104 Brier). Teşhis, bağımsız
Poisson'un bilinen kusuru: **beraberliği eksik tahmin ediyor** — model
%24,23, gerçek %26,09. İki parametre (beraberlik şişirme ρ, sıcaklık β)
eklenip **sezon dışarıda bırakmalı** uyduruldu:

| Tutulan | ρ | β | piyasa | türet+d | fark |
|---|---:|---:|---:|---:|---:|
| 2122 | 0,166 | 1,15 | 0,5943 | 0,5941 | −0,00021 |
| 2223 | 0,179 | 1,15 | 0,5929 | 0,5928 | −0,00014 |
| 2324 | 0,156 | 1,15 | 0,5921 | 0,5920 | −0,00015 |
| 2425 | 0,168 | 1,16 | 0,5954 | 0,5956 | +0,00025 |

Toplam (31.101 maç · 183 hafta), hafta düzeyinde eşleştirilmiş bootstrap:

| Aday | Fark | %95 aralık | Geçti |
|---|---:|---|---|
| `türet+düzeltme` | −0,000063 | [−0,000287, **+0,000155**] | hayır |
| `50/50 karışım` | −0,000107 | [−0,000223, **+0,0000038**] | hayır |

#### Yöntem notu — bir kez yanlış okundu ve düzeltildi

İlk koşumda karışımın üst sınırı sıfırın hemen altında göründü ve "geçti"
sanıldı. **İki hata vardı:** bootstrap *maç* düzeyindeydi (proje kuralı
*hafta* — aynı hafta sonu oynanan maçlar bağımsız değil) ve verdict tek bir
bootstrap kuantiline dayanıyordu. Hafta düzeyine geçilip **on ayrı tohumla**
koşulunca **onunda da geçmedi**; üst sınır her tohumda pozitif çıktı.

Sınırdaki bir aralığı tek tohumla okumak, aralığın kendisini görmezden
gelmektir. A5'teki yuvarlama hatasıyla aynı aile: karar, ölçünün
belirsizliğinden daha ince bir ayrıntıya dayanmamalı.

**Sonradan ölçüldü — birim seçimi gerçekten belirleyiciydi.** İki etken
(birim ve tohum) ayrıştırıldı; gerçek hold-out ölçümünde, on tohumun kaçında
"geçti" çıktığı:

| Ölçüm | Birim | Ortalama üst sınır | Geçen tohum |
|---|---|---:|---:|
| **hold-out** (gerçek) | maç | −0,0000029 | **9 / 10** |
| **hold-out** (gerçek) | hafta | +0,0000069 | **0 / 10** |
| sabit parametre | maç | −0,0000227 | 10 / 10 |
| sabit parametre | hafta | −0,0000130 | 10 / 10 |

Birim tek başına verdict'i çeviriyor (9/10 ↔ 0/10). Oysa hafta düzeyinin
maç düzeyine göre **tasarım etkisi yalnızca 1,11×** (Brier seviyesinde
1,16×; hafta başına ortalama 170 maç). Ders bu ikisinin birlikte
okunmasında: **küçük bir tasarım etkisi, sınırdaki bir bulguyu çevirmeye
yeter.** Aralık sıfıra ne kadar yakınsa, birim seçimi o kadar belirleyici
olur — ve bir bulgu tam da o zaman "sadece bir ayrıntı" diye savunulur.

> Not: sabit parametreli kıyasta iki birim de "geçti" der. Bu satır, birimi
> **gerçek ölçüm dışında** sınayan bir koşumun neden yanıltıcı olduğunu
> gösterdiği için tabloda duruyor.

#### Sonuç

Handikap ve alt/üst fiyatları, 1X2 fiyatının **ötesinde** ölçülebilir bilgi
taşımıyor — üç pazar aynı görüşün üç yüzü. **Korpus genişletilmedi:** ölü bir
uç için 31 bin satıra on sütun eklemenin karşılığı yok. Türetme ve matematiği
`spor_toto/skor.py`'de duruyor, 21 testle korunuyor; yeni bir veri kaynağı
gelirse hesap hazır.

A4'ün hükmü, elde olup bakılmamış **son** kaynakla da sınandı ve ayakta kaldı.

### 3.21 Beraberliğe özel düzeltme (Ö3) — **şekil gerçek, büyüklük yok**

Kalibrasyon eğrisi toplamda temiz (§3.18). Ama maçlar **favorinin gücüne**
göre bölününce beraberlikte düzenli bir şekil çıkıyor:

| favori olasılığı | n | piyasa "0" | gerçek "0" | fark |
|---|---:|---:|---:|---:|
| %30–40 | 6.350 | %29,55 | %30,25 | +0,70 |
| **%40–50** | **11.837** | **%27,95** | **%28,86** | **+0,91** ← Wilson aralığı dışı |
| %50–60 | 6.720 | %25,22 | %24,94 | −0,28 |
| %60–70 | 3.446 | %21,22 | %20,63 | −0,59 |
| %70+ | 2.750 | %14,69 | %14,22 | −0,47 |

Sapma bantlar arasında **tek yönde ilerliyor** — rastgele beş sapma bu
sırayla dizilmez. Hipotez: piyasa denk maçlarda beraberliği eksik, açık
maçlarda fazla fiyatlıyor.

#### Önce iki uyarı — ikisi de sonucu önceden haber veriyordu

**(1) Çok kıyas.** Beş bant bakıldı; birinin %95 aralığının dışına düşmesi
tek başına bulgu değil. Bonferroni ile eşik ~%99'a çıkar ve +0,91 orada kalır.

**(2) Sezon sezon işaret tutmuyor.** %40–50 bandındaki fark: **+0,44 ·
−0,70 · +1,77 · +2,14**. Dört sezonun biri ters işaretli. Havuzlanmış
"anlamlı" sonuç, dört sezonun ikisinin taşıdığı bir şey.

#### Neden karar kuralı değil, olasılık düzeltmesi

Plan bunu "beraberliğe özel **karar kuralı**" diye yazmıştı. **Ö1'den sonra o
biçim yanlış.** Eski eşik kuralı üç sembole simetrik davranıyor ve beraberliği
mekanik olarak atıyordu; `secim.en_iyi_secim` öyle bir kural taşımıyor,
verilen olasılıklara göre `P(k≤2)`'yi enbüyüklüyor. Seçim katmanına
"beraberliği koru" istisnası eklemek, doğru olan optimizasyonu bozup üstüne
yama koymak olurdu. Hipotez zaten olasılıkla ilgili → düzeltme olasılıkta
yapılır, seçim katmanı kendiliğinden doğru şeyi yapar.

#### Model: iki parametre, **iki ayrı iddia**

    z₀ = log p₀ + a + b·(f − c)      f = max(p),  c = eğitim setinin ortalama f'i

`a` beraberliği topluca kaydırır — **yeni değil**, `kalibre_bias` olarak
ölçülüp geçmişti (§3.11). `b` sapmanın favori gücüyle değişmesi — Ö3'ün asıl
iddiası. Bu yüzden asıl kıyas `bant − piyasa` değil **`bant − sabit`**.

#### Ölçüm (sezon dışarıda bırakmalı, 31.103 maç · 183 hafta)

| Tutulan | a | b | c |
|---|---:|---:|---:|
| 2122 | +0,0157 | **−0,1924** | 0,5051 |
| 2223 | +0,0236 | **−0,2949** | 0,5059 |
| 2324 | +0,0029 | **−0,2207** | 0,5029 |
| 2425 | +0,0091 | **−0,3180** | 0,5035 |

**`b` dört katlamanın dördünde de negatif** — şekil gerçek, sezon sezon
tutarlı. Ama Brier'e yansıması yok:

| Kıyas | Fark | %95 aralık | Geçen tohum |
|---|---:|---|---:|
| `sabit − piyasa` | +0,000027 | [−0,000021, +0,000079] | — |
| `bant − piyasa` | −0,000031 | [−0,000126, +0,000061] | **0 / 10** |
| **`bant − sabit`** | **−0,000057** | [−0,000137, **+0,000021**] | **0 / 10** |

A6'nın dersi uygulandı: on tohum, hafta düzeyi. Aralık her tohumda sıfırı
içeriyor.

#### Aşağı akış: kuponda ne değişiyor

Düzeltici korpusta eğitilip 36 kupon haftasına uygulandı (kupon haftaları
korpusta yok — temiz out-of-sample):

- İşareti değişen maç: **30/540 (%5,6)**, en az bir işareti değişen hafta 17/36.
- Beraberlik içeren işaret: 292 → **309 (+17)** — düzeltme gerçekten
  beraberliği daha çok koruyor, yani hipotezin öngördüğü şeyi yapıyor.

| Plan | **piyasa** olasılığı altında `P(k≤2)` | **düzeltilmiş** altında |
|---|---:|---:|
| piyasa planı | **%39,52** | %39,61 |
| düzeltilmiş plan | %39,48 | **%39,67** |

**Her plan kendi cetveli altında kazanıyor, ~0,05 puanla.** Bu, bilgi
olmadığının imzasıdır: fark gerçek bir kazanç değil, "hangi cetvelle
ölçtüğün". Kıyas için: Ö1'in karar katmanı aynı sayıda **+6,02 puan**
getirmişti — yüz kat.

#### Sonuç

Şekil gerçek (dört sezonda da aynı işaret), büyüklük ölçülemez. Piyasa
beraberliği favori gücüne göre biraz kaydırıyor olabilir, ama kayma
Brier'de de kupon kararında da gürültünün altında kalıyor. **Kural
değişmedi.** `spor_toto/beraberlik.py` ve 19 testi duruyor: iddaa arşivi
(Ö4) olgunlaşınca aynı soru **oynanan** piyasaya sorulacak ve hesap hazır
olacak — marjı %18 olan bir piyasada aynı sapmanın büyük çıkması makul.

> Ö3, planın "geçmezse yazılır ve bırakılır" maddesinin uygulanmasıdır.

### 3.22 İddaa ekseni (Ö4) — durma kuralı yazıldı, ölçüm bekliyor

**Ölçtüğümüz piyasa, oynadığımız piyasa değil.** Projenin bütün
kalibrasyonu football-data üzerinde; kupon iddaa'da oynanıyor:

| Piyasa | Marj | Nerede kullanılıyor |
|---|---:|---|
| football-data (`AvgC*`) | **%7,26** | A1–A6, kalibrasyon, geri test, eşikler |
| iddaa — bayi (`odd`) | **%16,93** | kuponun gerçekten oynandığı yer |
| iddaa — web (`wodd`) | **%21,32** | aynı bülten, ayrı fiyat |

Oran **2,6 kat** ve bu önemsiz bir ayrıntı değil: marj, arındırma
yönteminin ne kadar önemli olduğunu doğrudan belirleyen sayı. A5'in
bulgusu (`orantili` → `shin`) düşük marjlı bir piyasada ölçüldü; yüksek
marjlı bir piyasada aynı sorunun cevabı **aynı olmak zorunda değil**.

#### Bugün elde ne var

| Kaynak | Oran | Sonuç | Ölçüme girer mi |
|---|---|---|---|
| Bülten arşivi (`data/iddaa/*.csv`) | ✅ 469 maç | ❌ | hayır — kalibrasyon sonuç ister |
| Kupon haftaları (`data/super_toto/2026_27/`) | ✅ iddaa | ✅ | **evet — 1 hafta, 15 maç** |

Yani ölçümün yakıtı haftada **15 maç** ve bugün **bir hafta** var.

#### Durma kuralı — sayı önceden yazıldı

Standart iki taraflı güç hesabı (%80 güç, %5 anlamlılık). **sd
uydurulmadı, ölçüldü:** aynı maçlarda iki arındırma yöntemi arasındaki
hafta başına Brier farkının gerçek standart sapması, 38 haftada
**0,00358**.

| Aranan etki (Brier) | Gerekli hafta | Sezon |
|---:|---:|---:|
| 0,0050 | 5 | 0,1 |
| 0,0030 | 12 | 0,3 |
| **0,0015** | **45** | **1,1** |
| 0,0010 | 101 | 2,5 |
| 0,0005 | 403 | 9,8 |

**Aranan etki 0,0015 seçildi ve gerekçesi ölçümden bağımsız:** A5'te
arındırma seçimi football-data'da hafta başına 0,00059 Brier değiştirdi;
Shin düzeltmesinin büyüklüğü marjla ölçeklenir, marj 2,6 kat, dolayısıyla
beklenen etki ~0,0015. Bu sayı **önceden** yazılıyor ki sonuç görüldükten
sonra "aslında daha küçüğü de sayılır" denemesin.

> **Kural: 45 kupon haftası (iddaa oranı + sonuç) birikmeden kalibrasyon
> koşulmaz.** Erken koşulup "fark yok" denmesi, gücün yetmediği bir ölçümü
> bulgu sanmaktır. `tests/test_iddaa_hazirlik.py::test_elde_olan_veri_yetmiyor`
> bilerek konmuş bir **tetiktir**: kırıldığı gün veri gelmiş demektir.

#### Bugün ölçülebilen tek parça: bayi ↔ web

Alt sorulardan biri sonuç gerektirmiyor — iki fiyatın **ayrışıp
ayrışmadığı** yalnızca bülten arşivinden okunur (469 maç):

- Marj ayrı: bayi %16,93 ↔ web %21,32 (**web daha büyük pay alıyor**).
- Ama arındırmadan sonra en büyük sembol farkı ortalama **0,53 puan**,
  ortanca 0,47 puan; 1 puandan çok ayrışan yalnızca **52/469 (%11,1)**.

**Marj ayrı, görüş aynı.** İki fiyat aynı bültenin iki vitrini; fark
büyük ölçüde komisyon, bilgi değil. "`odd`–`wodd` farkı sonucu öngörüyor
mu" sorusunun ölçülecek tarafı maçların ancak %11'inde var — bu da o alt
soruyu, ötekiler beklerken **düşük öncelikli** yapıyor.

#### Neden bu eksen yine de tek gerçek uzun vadeli yatırım

Geçmiş iddaa oranı **hiçbir kaynakta yayınlanmıyor**. Arşiv yalnızca
ileriye doğru büyür ve kaçan hafta geri gelmez. `snapshot-iddaa.yml`
haftalık koşuyor; bu iş, sonucu bir sezon sonra alınacak olsa bile
**bugün doğru iş**.

    python scripts/iddaa_hazirlik.py            # elde ne var, ne eksik
    python scripts/iddaa_hazirlik.py --guc      # kac hafta gerekir
    python scripts/iddaa_hazirlik.py --bayi-web # odd vs wodd

### 3.23 Brier'in ayrışımı (AlphaPy incelemesinin çıktısı) — **ölçüldü**

Brier bugüne kadar **tek bir sayı** olarak raporlandı ve o sayı iki ayrı
kusuru aynı torbaya koyuyordu:

* olasılığın **yanlış ayarlı** olması — piyasa %30 diyor, gerçek %35;
  yeniden kalibrasyonla geri alınabilir;
* olasılığın **ayırt edememesi** — her maça benzer sayı veriyor; geri
  alınamaz, yeni bilgi ister.

T2, T3 ve A5'in tamamı birinci kusurun üstünde çalıştı ve hiçbiri geçmedi.
Ama *neden* geçmediği ölçülmemişti: kademe mi yetersizdi, yoksa alınacak
yol mu kalmamıştı? Murphy (1973) ayrışımı bu ikisini ayırır.

`ortak.brier_ayrisimi` sembol başına dört terim veriyor:

    BS_s = REL_s − RES_s + UNC_s + ICI_s

    REL_s = Σ_k (n_k/N)(p̄_k − ō_k)²             güvenilirlik  ↓ iyi
    RES_s = Σ_k (n_k/N)(ō_k − ō_s)²             çözünürlük    ↑ iyi
    UNC_s = ō_s(1 − ō_s)                         belirsizlik   indirgenemez
    ICI_s = Σ_k (n_k/N)[Var_k(p) − 2Cov_k(p,o)]  bant içi artık

`Σ_s BS_s` tam olarak `ortak.brier`in maç ortalamasıdır — ayrışım projenin
**kendi ölçeğinde** kapanır, yeni bir ölçek uydurulmadı.

#### Ölçülen — 31.103 maç · 183 hafta · sezon dışarıda bırakmalı · `shin`

| tahminci · sembol | Brier | güvenilirlik | çözünürlük | belirsizlik | bant içi | taban |
|---|---:|---:|---:|---:|---:|---:|
| **piyasa** · 1 | 0,2163 | 0,00012 | **0,02922** | 0,24560 | −0,00022 | 0,434 |
| **piyasa** · 0 | 0,1901 | 0,00008 | **0,00257** | 0,19284 | −0,00020 | 0,261 |
| **piyasa** · 2 | 0,1872 | 0,00022 | **0,02478** | 0,21215 | −0,00036 | 0,305 |
| **piyasa** · TOPLAM | **0,5936** | **0,00042** | **0,05657** | 0,65058 | −0,00079 | — |
| izotonik · TOPLAM | 0,5936 | 0,00022 | 0,05660 | 0,65058 | −0,00056 | — |

Sapma payı 0,00021 (aşağıda). Özdeşlik artığı her satırda `0,0e+00`.

#### Birinci okuma — kalibrasyon ekseninin tavanı bir sayıdır: **0,00042**

`REL`, *herhangi bir* yeniden kalibrasyon basamağının kazanabileceğinin
**üst sınırıdır**. Piyasa için 0,00042.

T2/T3'te ölçülen etkiler 0,0005–0,0015 aralığındaydı; yani **bu tavanın
üstünde.** O basamakların geçmemesi model kapasitesinden değil,
**kalibrasyon tarafında alınacak yolun kalmamış olmasındanmış.** §5.1
*"yön doğru, miktar yetersiz"* diyordu — ayrışım şimdi *niçin* yetersiz
olduğunu söylüyor.

Aynı koşum bunu doğrudan gösteriyor: `izotonik` `REL`i **yarıya indiriyor**
(0,00042 → 0,00022) ama toplam Brier 0,5936'da **kımıldamıyor** —
kazandığını bant içi terimde geri veriyor (−0,00079 → −0,00056). A5'in
*"`shin` üzerinde izotonik hiçbir şey eklemiyor"* bulgusunun mekanizması
budur.

#### İkinci okuma — beraberlik: eksik kalibre değil, **görünmez**

Piyasanın çözünürlüğü sembole göre on kat ayrışıyor:

    1 → 0,02922      2 → 0,02478      0 → 0,00257

Beraberlikte piyasa maçları birbirinden neredeyse **hiç ayırt edemiyor**.
Karışıklık paneli aynı şeyi karar tarafından söylüyor:

| | isabet | dengeli isabet | duyarlılık 1 | duyarlılık 0 | duyarlılık 2 |
|---|---:|---:|---:|---:|---:|
| korpus (31.103) | 0,511 | 0,443 | 0,819 | **0,003** | 0,508 |
| kupon (540) | 0,556 | 0,487 | — | **0,000** | — |

**Piyasanın argmax'ı hiçbir maça beraberlik demiyor.** Dış çalışmanın
merkezi negatif bulgusuydu (`DIS_INCELEME.md` §5) ve bizim tahmincimiz
için hiç ölçülmemişti.

Bu, Ö3'ün sonucunu yeniden okutuyor. Ö3 beraberliğe özel bir **kalibrasyon**
düzeltmesi denedi ve şekil gerçek çıktı ama büyüklük yoktu. Ayrışım sebebini
veriyor: beraberliğin sorunu `REL` (0,00008 — üç sembolün en küçüğü) değil
`RES`. **Kalibre edilecek bir şey yoktu; eksik olan ayırt etme gücü.**

#### `sapma_payi` — sayıyı okumadan önce bakılacak alan

`REL` ve `RES` sonlu örneklemde **yukarı yanlıdır**: bir bandın gözlenen
oranı gürültü taşır ve `(p̄_k − ō_k)²` o gürültünün karesini de toplar.
Büyüklüğü tahmin edilebilir ve `sapma_payi` alanı olarak yan yana basılır:

| kesit | REL | sapma payı | okunur mu |
|---|---:|---:|---|
| korpus · 31.103 maç | 0,00042 | 0,00021 | **evet** — tahmin payın iki katı |
| kupon · 540 maç | 0,00907 | **0,01085** | **hayır** — gürültü tabanı tahminin üstünde |

Yani kupon setinde `REL` **okunamaz**; yukarıdaki bütün okuma korpus
kesitine aittir. Kesit büyüklüğü burada bir ayrıntı değil **ön koşuldur**,
ve sayı bunu kendi yanında söylüyor. Yanlılık `RES`i de yaklaşık aynı
miktarda şişirdiği için farkta büyük ölçüde sadeleşir; `RES − REL` tek tek
terimlerden dayanıklıdır.

#### Ne yapıldı, ne yapılmadı

**Bu yeni bir tahminci değildir.** Hiçbir tahmin değişmedi, hiçbir sayı
arayüzde farklılaşmadı; değişen şey **cetvel**. A4'ün durma kuralına
girmez: aynı veriyle yeni bir model denenmedi, var olan tahminci daha ince
ölçüldü.

Bekçiler:

* `tests/test_ortak.py` (yeni, 18 test) — özdeşliğin **tam** kapanması
  (1e-12), düzgün tahminci için kapalı form, ve terimlerin **yönü**:
  `REL` ile `RES` yer değiştirseydi özdeşlik yine kapanırdı ama okuma
  tersine dönerdi;
* `health.tahmin_referanslari` — aynı özdeşliği **canlı veride** koşuyor ve
  çözünürlük sıralamasını denetliyor: `piyasa > sezon_sabiti > duzgun = 0`.
  Bu, Brier sıralamasından daha keskindir; Brier belirsizlik terimini de
  taşır, çözünürlük yalnızca "ayırt edebiliyor mu" der.

    python -m spor_toto.kalibrasyon --ayrisim
    python -m spor_toto.evaluate

Kaynak ve gerekçe: [`DIS_INCELEME_ALPHAPY.md`](DIS_INCELEME_ALPHAPY.md) §5.

### 3.24 Öğrenme eğrisi — *"daha çok veri işe yarar mı?"* **ölçüldü**

Projenin en pahalı açık sorusu buydu ve bugüne kadar yalnızca **güç
analiziyle** cevaplanıyordu: `scripts/faz_b.py` ≈71 ikramiyeli hafta diyor,
`scripts/iddaa_hazirlik.py` 45 kupon haftası. İkisi de *"bu etkiyi görmek
için kaç gözlem gerekir"* sorusunu, **etkinin var olduğunu varsayarak**
cevaplıyor.

Öğrenme eğrisi varsayım yapmaz ve başka bir şey sorar: *elimizdeki veriyle
model hâlâ öğreniyor mu, yoksa doymuş mu?*

`evaluate.ogrenme_egrisi` dış halkayı `hafta_disarida_birak` ile **aynı**
tutar (sezon dışarıda bırakmalı); tek fark, eğitim setinin tamamı yerine
tohumlu bir alt kümesi verilir. Alt örnekleme **hafta düzeyindedir**, maç
düzeyinde değil — aynı haftanın 15 maçı bağımsız değildir ve maç düzeyinde
örneklemek eğriyi olduğundan iyimser gösterirdi.

#### Ölçülen — 31.103 maç · 183 hafta · 4 sezon, sezon dışarıda bırakmalı

| eğitim maçı | `piyasa` | `sezon_sabiti` | `kalibre_bant` |
|---:|---:|---:|---:|
| 2.216 | 0,59364 | 0,65113 | 0,59721 |
| 5.934 | 0,59364 | 0,65079 | 0,59483 |
| 11.516 | 0,59364 | 0,65065 | 0,59409 |
| 17.593 | 0,59364 | 0,65062 | 0,59379 |
| **23.327** | **0,59364** | 0,65063 | **0,59373** |
| **toplam iniş** | **+0,00000** | +0,00050 | +0,00348 |
| **son adım** | +0,00000 | −0,00001 | **+0,00006** |

`piyasa` sütunu bir sonuç değil **sağlamadır**: hiçbir şey öğrenmeyen bir
tahmincinin eğrisi düz çıkmalıdır ve çıkıyor. Düz çıkmasaydı alt örnekleme
ölçüm setine dokunuyor, yani eğitim/test ayrımı sızdırıyor olurdu
(`test_ogrenmeyen_tahmincide_egri_duz` bunu bekçiliyor).

#### Okuma — **eğri düzleşti, ve gap kapanmadan düzleşti**

Kademe gerçekten öğreniyor: 2.216 maçtan 23.327'ye Brier 0,00348 iniyor.
Ama **son adım 0,00006**: 17.593 → 23.327 maç (+5.734 maç, eğitim setinin
üçte biri kadar) yalnızca bu kadar getirdi.

Ve iniş **piyasaya yetişmeden durdu.** Bütün korpusla eğitilmiş
`kalibre_bant` 0,59373; `piyasa` 0,59364. Kalan fark **0,00009** ve son
5.734 maç 0,00006 kazandırdı — üstelik öğrenme eğrileri düzleşerek gider,
yani sonraki maçların getirisi bundan **daha az** olacak.

**Aynı türden veri toplamak bu farkı kapatmıyor.** Bu, A4'ün *"tahmin
ekseni yeni bir veri KAYNAĞI ister"* cümlesini bir kanaatten bir **ölçüme**
çeviriyor: sorun satır sayısı değil, sütun.

`sezon_sabiti` aynı şeyi daha erken gösteriyor — ~5.900 maçta doymuş, son
adımda **yukarı** dönüyor (−0,00001). Taşıdığı tek bilgi lig taban oranı ve
o bilgi 6 bin maçta zaten öğrenilmiş.

#### Ne yapıldı, ne yapılmadı

§3.23 gibi bu da **yeni bir tahminci değildir** — cetvelin bir parçasıdır ve
A4'ün durma kuralına girmez. Ama §3.23'ten farklı bir şey söylüyor: §3.23
kalibrasyon ekseninde alınacak yolun **0,00042** olduğunu ölçtü; §3.24 o
yolun **daha çok veriyle de alınamayacağını** ölçüyor.

    python -m spor_toto.evaluate --egri --korpus
    python -m spor_toto.evaluate --egri            # kupon setinde

### 3.25 Hafta içi sıralama — Brier'in göremediği yetenek, **ölçüldü**

Brier ve log kaybı her maçı **tek tek** cezalandırır. İkisi de bir haftanın
maçlarını **birbirine göre** sıralamayı ölçmez — oysa kuponun sorduğu şey
tam olarak budur: *"bu 15 maçın hangilerine banko koyayım?"*

İki tahminci aynı Brier'i verip farklı sıralayabilir. Sıralaması iyi olan
`secim.en_iyi_secim`e daha kullanışlı bir girdi verir, çünkü `secim` bütçeyi
en güvenilir maçlara harcar ve o liste yanlış sıralanmışsa bütçe yanlış yere
gider. `ortak.siralama_olculeri` bu yeteneği ayrı ölçüyor.

Maçlar `max(p)` azalan sırada dizilir; bir maç **isabetli** sayılır en olası
sembol gerçekleşmişse. `ndcg` isabetlilerin listenin başına ne kadar
toplandığını, `isabet_k` en güvenilen `k` maçın isabetini söyler.

#### Ölçülen — korpus · 31.103 maç · 183 sözde-hafta (ort. 170 maç/hafta)

| | NDCG | taban | en emin 1 | en emin 3 | en emin 5 |
|---|---:|---:|---:|---:|---:|
| **piyasa** | **0,8971** | 0,5109 | **0,8634** | **0,8342** | **0,8230** |
| | | [0,5054, 0,5165] | [0,8061, 0,9057] | [0,8008, 0,8630] | [0,7969, 0,8463] |
| | | n=31.103 | n=183 | n=549 | n=915 |
| sezon_sabiti · duzgun | 0,7896 | 0,4337 | 0,4536 | 0,4426 | 0,4295 |

#### Ölçülen — kupon seti · 540 maç · 36 hafta (15 maç/hafta)

| | NDCG | taban | en emin 1 | en emin 3 | en emin 5 |
|---|---:|---:|---:|---:|---:|
| **piyasa** | **0,8550** | 0,5556 | 0,6944 | **0,7407** | **0,6722** |
| | | [0,513, 0,597] | [0,531, 0,820] | [0,651, 0,814] | [0,601, 0,737] |
| | | n=540 | n=36 | n=108 | n=180 |
| sezon_sabiti · duzgun | 0,7324 | 0,4407 | 0,5278 | 0,3889 | 0,4056 |

> **İki tablo doğrudan karşılaştırılamaz.** Korpusta "en emin 5", 170 maçın
> en üst **%3**'ü; kuponda 15 maçın en üst **üçte biri**. Aynı `k`, çok
> farklı seçicilik. Her tablo kendi kesitinde okunur.
>
> Kupon setinde `isabet_1` (%69,4) ile `isabet_3` (%74,1) arasındaki
> tersine dönüş **gürültüdür** — aralıklar fazlasıyla örtüşüyor ve `k=1`
> yalnızca 36 gözlem taşıyor. Wilson aralıkları tam bu yüzden yüzdenin
> yanında duruyor.

#### Okuma — **piyasanın sıralaması, Brier'inin ima ettiğinden çok daha güçlü**

Brier tarafından bakınca piyasa zayıf görünür: 0,5936, eşit dağıtımın
karşılığı 0,6667. §3.23 bunu ayrıştırdı — çözünürlük 0,05657, belirsizliğin
yalnızca **%8,7**'si.

Sıralama tarafından bakınca aynı piyasa çok farklı görünüyor: korpusta taban
isabet %51,1 iken en emin 5 maçın isabeti **%82,3**, ve aralıklar birbirine
yaklaşmıyor bile. **Piyasa hangi maçlarda haklı olduğunu biliyor** — mutlak
olasılıkları belirsiz olsa da.

Bu, B0'ın (§3.19) neden bu kadar kazandığını açıklıyor. Karar katmanı eşik
kuralından hedef kuralına geçince `P(k ≤ 2)` **+6,02 puan** kazanmıştı ve
tahmin tarafında aynı kazanç için ~0,10 Brier gerekirdi. Sebebi şu:
`en_iyi_secim` Brier'i değil **sıralamayı** kullanıyor, ve sıralama zaten
güçlüydü. Ölçülmemişti, o kadar.

**Pratik sonucu:** bir aday tahminci artık iki eksende değerlendirilir.
Brier'i piyasayı geçmeyen ama sıralaması geçen bir tahminci kupon için yine
de değerlidir — ve bu ayrım bugüne kadar yapılamıyordu.

`sezon_sabiti` ile `duzgun`un birebir aynı çıkması sağlamadır: ikisi de her
maça aynı olasılığı verir, dolayısıyla `max(p)` sabittir ve sıralama
girdinin kendi sırasıdır. O satır **bilgisiz sıralamanın zeminidir**
(NDCG 0,79) — bir tahminci onun altına inemiyorsa sıralama bilgisi taşımıyor
demektir.

    python -m spor_toto.evaluate --korpus
    python -m spor_toto.evaluate

### 3.26 Etkileşim kademeleri (Faz 2.1) — **geçmedi**, ve kapasite ceza yazdı

`DIS_INCELEME.md` §3 bir itirazı açık bırakmıştı:

> *"Piyasayı geçen özellik yok demediniz — sizin **doğrusal kademeniz** o
> özelliği kullanamadı demiş oldunuz."*

İtiraz haklı bir yere basıyordu: dokuz denemenin **hepsi** `ln p` üzerinde
doğrusal, Newton ile uydurulan tek bir softmax ailesiyle yapılmıştı.
Etkileşim yakalayan bir sınıf hiç denenmemişti. Bu bölüm o itirazı **bizim
kesitimizde** ölçüyor.

`KADEMELER`e iki basamak eklendi — iki ayrı soru olduğu için iki basamak:

| basamak | soru | sütun |
|---|---|---|
| `etkilesim` | yön özellikleri **birbiriyle** etkileşiyor mu (yorgunluk formu bastırıyor mu) | C(6,2) = **15** |
| `etkilesim_favori` | yön özellikleri **maçın açıklığıyla** etkileşiyor mu (form denk maçlarda daha mı önemli) | **+6** |

İkincisi teorik olarak daha güçlü bir adaydı: Ö3 (§3.21) beraberlik
sapmasının favori gücüne bağlı olduğunu *ölçmüştü* — şekil gerçek, büyüklük
yok. Aynı bağımlılık yön özelliklerinde de olabilirdi.

Ölçekler **veriye bakılmadan**, her özelliğin kendi tanımından alındı
(`dinlenme_farki` ±14, `sezon_sonu_pay_farki` ±1 …). Ölçeklenmeden aynı L2
cezasına sokmak büyük ölçekli özelliklerin katsayısını yapay olarak kısardı.

#### Ölçülen — 31.103 maç · 183 hafta · sezon dışarıda bırakmalı

| tahminci | Brier | fark | %95 aralık | geçti |
|---|---:|---:|---|---|
| piyasa | 0,593600 | — | — | referans |
| `kalibre_sezon_sonu` | 0,593700 | +0,000076 | [−0,000240, +0,000408] | hayır |
| `kalibre_etkilesim` | 0,593800 | **+0,000150** | [−0,000189, +0,000505] | hayır |
| `kalibre_etkilesim_favori` | 0,593800 | **+0,000165** | [−0,000180, +0,000520] | hayır |

#### Okuma — etkileşim yalnızca yardım etmiyor değil, **bedel yazıyor**

Hiçbiri anlamlı değil (üç aralık da sıfırı kesiyor), ama nokta tahmini
kapasiteyle birlikte **tek yönde** ilerliyor: 21 sütun eklemek dışarıdaki
skoru 0,000076'dan 0,000165'e taşıyor. Aşırı uyumun imzası, ve 31 bin maçta
bile görünüyor.

**İtiraz daraldı, kapanmadı — ve bu ayrım yazılır.** Ölçülen şey şudur:
*genelleştirilmiş doğrusal bir modele açık etkileşim terimleri eklemek bir
şey getirmiyor.* Ölçülmeyen şey: ağaç toplulukları gibi keyfî doğrusal
olmama. Bu ikisi aynı cümle değildir. Dış kanıt aynı yöne işaret ediyor
(`DIS_INCELEME.md` §3: RF/XGB/SVM aynı tavan; `DIS_INCELEME_ALPHAPY.md` §3:
AlphaPy'ın kendi spor öğreticisi %52–54) ama teyit ölçüm değildir.

#### Bir hata bulundu ve bekçi yakaladı

Basamaklar eklenirken `_gruplari_belirle` **elle yazılmış** bir kademe
listesi tutuyordu ve yeni basamaklar o listede olmadığı için **lig ve bant
sütunları tamamen düşüyordu**: etkileşim kademesi sessizce `bias`
seviyesine geriliyor, ölçüm sakat bir model üzerinde koşuyordu.

İlk ölçüm bu hâliyle alındı ve *"−0,0001, geçmedi"* diyordu — yani **yanlış
bir sayı, doğru görünen bir sonuç veriyordu.** Onu yakalayan şey yeni bir
test değil, zaten duran
`test_gercek_veride_egitim_ici_kapasiteyle_iyilesiyor` oldu: eğitim-içi
skor kapasiteyle **kötüleşemez** ve kötüleşti.

Sıra artık `KADEMELER`in kendisinden okunuyor; listenin iki kopyası yok.

#### Bekçiler

* `test_etkilesim_sutunu_gercekten_calisiyor` — **yokluk iddiasının
  bekçisi**. "Etkileşim bir şey eklemiyor" ancak sütunlar gerçekten
  bağlıysa bir ölçümdür. Hafta seçimi rastgele değil: son sütun
  `sezon_sonu_pay_farki` taşır ve o pay sezonun son %20'si dışında sıfırdır
  — yanlış hafta seçilirse sütun **haklı olarak** ölü görünür ve test
  yanlış sebeple yeşil kalırdı;
* `test_etkilesim_sutunu_yon_ozelligi_gibi_davranir` — çarpım simetrik
  kaymalı, beraberliğe dokunmamalı;
* `test_kupon_haftasinda_etkilesim_notr` — kupon haftaları yön özelliği
  taşımaz, yeni sütunların **tamamı** orada sıfır olmalı.

    python -m spor_toto.recalibrate

### 3.27 Elo (Faz 3.2) — **güçlü sinyal, sıfır katkı**

`DIS_INCELEME.md` §8 Elo'yu *"denenebilir ama denenmedi"* diye kayda
geçirmişti ve gerekçesi bir **tahsis kararıydı**, bir imkânsızlık değil.
Faz 1'in iki ölçümü o kararı tersine çevirdi:

* **§3.23** kalibrasyon ekseninin tavanının 0,00042 olduğunu ölçtü —
  yeniden kalibrasyon tarafında alınacak yol kalmadı;
* **§3.24** öğrenme eğrisinin piyasaya **yetişmeden** düzleştiğini ölçtü —
  aynı türden daha çok satır bu farkı kapatmıyor.

İkisi birlikte tek bir şey söylüyor: eksik olan **sütun**. Ve Elo, projenin
kendi belgelerinde en çok işaret edilen eksik sütundu:

> *"`kalibre_form` **ham** formdu, rakip gücüne göre düzeltilmemişti — Elo
> tam o eksiği kapatan standart sinyaldir. Yani 'form denendi' demek 'Elo
> denendi' demek değildir."*

#### Kurulum — ve gol sütunlarının ilk kez kullanılması

`spor_toto/elo.py`: 1500 başlangıç, K=20, ev avantajı 65 puan, 400'lük
lojistik ölçek, sezonlar arası 0,75 taşıma, gol farkı çarpanı World
Football Elo Ratings formülünden. **Hiçbir parametre veriden ölçülmedi** —
hepsi yayınlanmış futbol Elo değerleri. Elo'nun bu projedeki avantajı tam
buydu: parametrelerini uydurmaya gerek yok, dolayısıyla hold-out'a
bakılarak seçilme riski de yok (`recalibrate.L2` ile aynı gerekçe).

Kayda değer bir yan etki: korpus `hg`/`ag` sütunlarını CSV'de hep taşıyordu
ama `korpus_yukle` onları satıra hiç koymuyordu — `kod` türetiliyor, goller
atılıyordu. **Elo, gol farkını kullanan ilk özellik**, ve o sütunlar artık
taşınıyor.

Sızıntı disiplini `egitim._form_tablosu` ile birebir aynı: kronolojik gez,
farkı **önce oku, sonra** maçı işle. Elo'da bu daha kritiktir çünkü form
bir pencereyken Elo bütün geçmişi taşır.

Kapsama: 31.103 maçın **%95,6**'sı (`elo_var`; iki tarafın da en az 5 maçı
olması şartı). Farkın ortalaması **+65,4** — yani tam olarak ev avantajının
kendisi, puanlar sıfır toplamlı olduğu için. Bu bir sağlamadır.

#### Ham sinyal — devasa

| Elo farkı | maç | gerçek ev galibiyeti | piyasanın beklediği | artık |
|---|---:|---:|---:|---:|
| −∞ … −100 | 1.850 | %16,8 | %17,2 | −0,4 |
| −100 … −25 | 3.513 | %27,8 | %28,3 | −0,5 |
| −25 … 25 | 4.573 | %35,4 | %35,2 | +0,1 |
| 25 … 100 | 9.207 | %42,1 | %42,5 | −0,4 |
| 100 … 175 | 6.495 | %51,6 | %51,7 | −0,1 |
| 175 … +∞ | 4.090 | **%68,1** | %67,0 | +1,1 |

Ev galibiyeti oranı %16,8'den %68,1'e çıkıyor — **51 puanlık** bir yayılım.
Elo maç sonucunu güçlü biçimde ayırt ediyor.

#### Artık — sıfır

Sağdaki iki sütun aynı tabloyu ikinci kez okutuyor: **piyasa her bantta
zaten orada.** Artıkların hepsi ±1,1 puanın içinde ve piyasanın söylediği
sayı **her bantta Wilson %95 aralığının içinde** kalıyor — en büyük sapmada
bile (üst bant, n=4.090) piyasa %67,0 diyor, gerçek %68,1 [%66,6, %69,5].

Kademe ölçümü aynı şeyi söylüyor:

| tahminci | Brier | fark | %95 aralık | geçti |
|---|---:|---:|---|---|
| piyasa | 0,593600 | — | — | referans |
| `kalibre_form` | 0,593700 | +0,000039 | [−0,000275, +0,000351] | hayır |
| `kalibre_sezon_sonu` | 0,593700 | +0,000076 | [−0,000240, +0,000408] | hayır |
| **`kalibre_elo`** | 0,593700 | **+0,000086** | [−0,000242, +0,000429] | **hayır** |

Ve uydurulan katsayı **negatif** (−0,0597): model Elo'nun etkisini
büyütmek değil **kısmak** istiyor. `form`un katsayısı da negatifti
(−0,0316). Yani piyasa Elo'yu fiyatlamakla kalmıyor, eğer bir şey varsa
biraz **fazla** fiyatlıyor.

#### Okuma — A3'ün iç/dış form satırının aynısı

> **Güçlü sinyal, sıfır katkı.** Ham fark 51 puan, artığı sıfır.

Bu, §3.16'da iç/dış form için ölçülen şeyin birebir tekrarı (ham fark
+0,247, artığı onda biri) ve A4'ün on birinci denemesidir. Elo'yu özel
kılan şey, projenin kendi belgelerinin onu **en umutlu aday** olarak
işaretlemiş olmasıydı — o umut artık ölçülmüş bir sayıya bağlandı.

`DIS_INCELEME.md` §8'in *"denenmedi, gerekçesiyle"* satırı böylece
kapanıyor. H2H hâlâ açık ve aynı statüde duruyor.

#### İki hata bulundu, ikisi de bekçiye bağlandı

1. **Elo sütunu alt basamaklara sızdı.** A3 döngüsündeki `break`
   fonksiyondan çıkmaz, yalnızca döngüden çıkar; kapıya bağlanmayan Elo
   bloğu `dinlenme`den itibaren **bütün** alt basamaklara girdi ve
   `kalibre_elo` ile `kalibre_sezon_sonu` birebir aynı sayıyı verdi.
   Şüphe uyandıran şey sayının kendisi oldu: iki farklı model aynı altı
   haneyi vermez.
2. Bunu yapısal olarak imkânsızlaştıran test yazıldı:
   **`test_kademe_tam_bir_sutun_ekler`** — her basamak bir öncekine tam
   olarak bir sütun eklemeli (etkileşim basamakları bilinçli istisna).
   Kademenin bütün anlamı budur; bozulduğunda iki özelliğin katkısı
   birbirine karışır ve ölçüm sessizce yanlış olur.
   **`test_elo_sutunu_alt_basamaklara_sizmaz`** aynı sızıntıyı doğrudan
   kovalıyor.

    python -m spor_toto.recalibrate

### 3.28 Dixon-Coles (Faz 3.1) — piyasadan **bağımsız** ilk görüş, ve o da geçmedi

Projede takım gücünü **sonuçlardan** türeten hiçbir şey yoktu. `skor.py`
(A6) gol parametrelerini *fiyattan* çıkarıyordu ve tam bu yüzden geçmemişti:
*"üç pazar aynı görüşün üç yüzü."* Elo (§3.27) bir sonuç modelidir ama tek
bir sayı taşır ve gol üretimini hiç bilmez.

Dixon-Coles her takıma **iki** sayı verir — hücum ve savunma — ve bir skor
dağılımı üretir. Bunun projedeki değeri şudur: **piyasadan bağımsız ilk
görüş.** Yığınlamanın anlamlı olabilmesi için en az iki bağımsız görüş
gerekir ve bugüne kadar hepsi aynı fiyatın türevleriydi.

#### Kurulum

`λ_ev = α_h·β_a·γ`, `λ_dep = α_a·β_h`; ağırlıklı Poisson olabilirlik
**kapalı biçimde** güncellenir (IPF / koordinat yükselişi), `scipy.optimize`
kullanılmadı — `recalibrate._uydur` ile aynı gerekçe. Düşük skor düzeltmesi
Dixon & Coles'un `τ` parametrizasyonu; `ρ` tek skalerdir ve üçe bölmeyle
aranır.

Zaman sönümü `exp(−0,0045·gün)` ≈ **154 günlük yarı ömür**, veriye
bakılmadan seçildi. Sızıntı disiplini `elo.elo_tablosu` ile aynı, tek
farkla: Elo maç maç güncellenirken DC **tur tur yeniden uydurulur** (ISO
hafta). Bir turun maçları birbirinin sonucunu görmez.

Uydurulan tanı sayıları (31.103 maç, 477 takım): **γ = 1,2297** (ev sahibi
%23 daha çok gol atıyor) ve **ρ = −0,0330**. Bu parametrizasyonda negatif
`ρ`, 0-0 ve 1-1'i yukarı iter — yani bağımsız Poisson'un beraberliği eksik
tahmin etme kusurunu düzeltir. Dixon & Coles'un kendi bulgusuyla **aynı
yönde**, daha küçük büyüklükte.

#### Ölçülen — tek başına

| | Brier | REL | RES |
|---|---:|---:|---:|
| Dixon-Coles | **0,6153** | 0,00348 | 0,03817 |
| piyasa | 0,5933 | 0,00042 | 0,05669 |

DC piyasadan **belirgin biçimde kötü** (+0,0221) ve ayrışım nedenini
söylüyor: kalibrasyon borcu **sekiz katı**, çözünürlüğü **üçte iki**.
Gerçek ama zayıf bir görüş — beklenen de buydu, çünkü yalnızca golleri
görüyor.

#### Ölçülen — piyasanın üstüne eklenince

| tahminci | Brier | fark | %95 aralık | geçti |
|---|---:|---:|---|---|
| piyasa | 0,593600 | — | — | referans |
| `kalibre_sezon_sonu` | 0,593700 | +0,000076 | [−0,000240, +0,000408] | hayır |
| `kalibre_elo` | 0,593700 | +0,000086 | [−0,000242, +0,000429] | hayır |
| **`kalibre_dc`** | 0,593700 | **+0,000100** | [−0,000261, +0,000472] | **hayır** |

Ve katsayı yine **negatif** (−0,0492): model DC'nin görüşünü eklemek değil
**çıkarmak** istiyor.

#### Artık taraması — altı bandın altısında da piyasa aralığın içinde

| DC'nin dediği P(ev) | maç | gerçek | piyasa | artık | %95 aralık |
|---|---:|---:|---:|---:|---|
| %0–25 | 4.746 | %22,3 | %23,2 | −0,9 | [21,1 · 23,5] |
| %25–35 | 5.552 | %33,7 | %33,7 | +0,0 | [32,5 · 34,9] |
| %35–45 | 7.243 | %41,8 | %41,3 | +0,5 | [40,7 · 42,9] |
| %45–55 | 5.827 | %47,1 | %48,4 | −1,3 | [45,9 · 48,4] |
| %55–70 | 4.874 | %58,5 | %57,5 | +1,1 | [57,1 · 59,9] |
| %70+ | 2.412 | %73,1 | %72,5 | +0,6 | [71,3 · 74,8] |

DC bir bandı işaretlediğinde piyasa zaten oradadır. Hiçbir bantta anlamlı
sapma yok.

#### Okuma — bu, serinin **en sert** sonucu

A1 piyasanın kendi hareketinin kapanışı yenemediğini ölçtü. A3 türetilebilir
özelliklerin fiyatlandığını. §3.27 Elo'nun fiyatlandığını. Hepsinin ortak
zayıflığı aynıydı: **denenen şey piyasanın kendi bilgisinin bir
türeviydi.**

Dixon-Coles o itiraza kapalıdır. Fiyata hiç bakmaz; yalnızca atılan golleri
görür ve kendi görüşünü kurar. **O görüş de kapanış fiyatının içinde
çıktı.**

Bunun Faz 2.4 (yığınlama) için sonucu doğrudan: yığınlamanın ön koşulu iki
bağımsız görüştü, o görüş kuruldu ve **piyasadan bağımsız olması onu
yararlı yapmadı.** Katsayının negatif olması, üst-öğrenicinin de aynı şeyi
söyleyeceğini gösteriyor.

#### Bir iddia ölçüme çekildi

İlk sürümde skor ızgarası 10'da kesiliyordu ve docstring *"kesilen kuyruk
milyonda bir"* diyordu. Test bunu düşürdü: `λ = 3` için gerçek kayıp
**2,9·10⁻⁴** (on binde üç). Izgara 18'e çıkarıldı ve docstring'e kaybın
**ölçülmüş tablosu** yazıldı. Küçük bir olay ama projenin kuralının
kendisi: yazılan sayı ölçülmüş sayı olmalı.

    python -m spor_toto.recalibrate

### 3.29 H2H ve seriler (Faz 3.3) — aynı kalıp, üçüncü ve dördüncü kez

İki özellik, iki ayrı gerekçe ve ikisi de kayıtlı bir açık uçtu:

* **H2H** — `DIS_INCELEME.md` §8'de Elo'nun yanında *"denenebilir ama
  denenmedi"* diye duruyordu. Elo denendi ve geçmedi (§3.27); H2H açık
  kaldı. Taşıdığı iddia şudur: *bazı eşleşmeler genel güç sıralamasının
  söylemediği bir şey taşır.* Elo ve Dixon-Coles bunu **tanım gereği
  göremez** — ikisi de her takıma **tek** bir güç atar ve eşleşmeye özel
  bir terim taşımaz.
* **Seriler** — `DIS_INCELEME_ALPHAPY.md` §7'nin *"türetilebilir,
  denenmedi"* satırı; AlphaPy `sport_flow.get_streak`'in karşılığı.
  Formdan farkı incedir ama gerçektir: form son 5 maçın **puan
  ortalamasıdır**, seri **ardışıklığı** ölçer. 3 galibiyet + 2 mağlubiyet
  ile 5 beraberlik aynı ortalamayı verebilir; aynı seriyi veremez.

#### Ham sinyal — ikisi de güçlü

| `h2h_farki` | maç | gerçek ev | piyasa | artık |
|---|---:|---:|---:|---:|
| −1,00 … −0,50 | 2.128 | %30,5 | %30,0 | +0,4 |
| −0,50 … −0,15 | 3.280 | %37,4 | %38,9 | −1,5 |
| −0,15 … +0,15 | 2.409 | %43,4 | %43,9 | −0,5 |
| +0,15 … +0,50 | 2.759 | %49,7 | %48,8 | +0,8 |
| +0,50 … +1,00 | 2.175 | **%58,5** | %58,0 | +0,5 |

| `seri_farki` | maç | gerçek ev | piyasa | artık |
|---|---:|---:|---:|---:|
| −1,00 … −0,25 | 1.290 | %28,8 | %28,2 | +0,5 |
| −0,25 … −0,06 | 12.658 | %39,4 | %39,2 | +0,2 |
| −0,06 … +0,06 | 5.872 | %43,7 | %44,0 | −0,3 |
| +0,06 … +0,25 | 9.363 | %47,3 | %47,9 | −0,6 |
| +0,25 … +1,00 | 1.920 | **%59,1** | %58,9 | +0,2 |

H2H'de 28 puanlık, seride 30 puanlık yayılım. İkisi de gerçek.

#### Artık — ve bu kez **on bandın onunda da** piyasa aralığın içinde

Sağdaki sütun aynı hikâyeyi dördüncü kez yazıyor. En büyük sapma H2H'nin
ikinci bandında (−1,5) ve orada bile piyasanın söylediği sayı Wilson
aralığının içinde kalıyor.

| tahminci | Brier | fark | %95 aralık | geçti |
|---|---:|---:|---|---|
| piyasa | 0,593600 | — | — | referans |
| `kalibre_dc` | 0,593700 | +0,000100 | [−0,000261, +0,000472] | hayır |
| `kalibre_h2h` | 0,593800 | +0,000146 | [−0,000208, +0,000517] | hayır |
| `kalibre_seri` | 0,593800 | +0,000145 | [−0,000203, +0,000518] | hayır |

Katsayılar: `h2h` **+0,0050** (sıfıra yapışık), `seri` **−0,0385** (model
seriyi **söndürmek** istiyor — momentum iddiasının tam tersi).

#### Ve bir şey daha: kapasite artık **ölçülebilir biçimde** zararlı

Dokuz yön özelliğiyle etkileşim kademeleri şuraya geldi:

| tahminci | fark | %95 aralık |
|---|---:|---|
| `kalibre_etkilesim` | +0,000359 | [−0,000016, +0,000764] |
| **`kalibre_etkilesim_favori`** | **+0,000380** | **[+0,000009, +0,000782]** |

Son satırın aralığı **tamamen sıfırın üstünde.** Bu, projenin "geçti"
ölçütünün ayna görüntüsüdür: aynı kural, ters yönde. §3.26 *"kapasite bedel
yazıyor ama anlamlı değil"* diyordu; dokuz özellik ve 45+9 sütunla bedel
**anlamlı** hâle geldi.

Yani model sınıfı itirazının cevabı sertleşti: doğrusal kademeye etkileşim
eklemek yalnızca yardım etmiyor değil, **ölçülebilir biçimde zarar veriyor.**

#### Bir tanım hatası bulundu ve test yakaladı

H2H'nin ilk sürümü lig tablosu puanlamasını (3/1/0) kullanıyordu.
`test_h2h_hep_beraberlikte_sifir` onu düşürdü: o ölçekte bir beraberlik
`[−1, 1]` aralığına **−1/3** olarak düşüyor, yani *"berabere kaldılar"*
cümlesi *"ev sahibi geride"* diye okunuyordu. 3/1/0 bir **sıralama**
geleneğidir ve galibiyeti beraberliğe göre kasten fazla ödüllendirir;
H2H'nin sorduğu şey sıralama değil **üstünlük**. Kodlama ±1/0'a çevrildi.

Sayı ölçümü değiştirmedi (katsayı zaten sıfıra yapışıktı) ama **özelliğin
ne ölçtüğünü** değiştirdi — ve yanlış tanımlı bir özelliğin "geçmedi"
sonucu bir ölçüm değildir.

#### Kayıtlı sınır — H2H'nin kapsaması düşük

`h2h_var` maçların yalnızca **%41**'inde açık: dört sezonluk ve 22 ligli bir
korpusta çoğu eşleşme `H2H_EN_AZ = 3` karşılaşmayı bulamıyor. Ölçümün gücü
okunurken bu hatırlanmalı — "geçmedi" burada "%41'lik kesitte geçmedi"
demektir.

    python -m spor_toto.recalibrate

### 3.30 Gradyan artırmalı ağaçlar (Faz 2.2) — **model sınıfı itirazı kapandı**

`DIS_INCELEME.md` §3'ün itirazı §3.26'da daraltılmıştı ama kapanmamıştı:
açık etkileşim terimi ile **keyfî doğrusal olmama** aynı şey değildir. Bir
ağaç topluluğu eşik kurabilir, bölgesel davranabilir ve hiçbir çarpım
terimiyle yazılamayan şekiller öğrenebilir. Bu bölüm o sınıfı **bizim
kesitimizde** ölçüyor.

#### Kritik tasarım — ağaç **artığı** öğrenir, sıfırdan değil

Naif kurulum ağaca bütün özellikleri verip 1X2'yi doğrudan tahmin
ettirmektir. **O ölçüm işe yaramaz**: ağacın piyasa fiyatını yeniden
keşfetmesi gerekir ve daha kötü keşfeder; sonuç *"ağaçlar kötü"* olur, oysa
sorulan soru bu değildir.

Doğru kurulum LightGBM'in `init_score`udur: başlangıç ham skoru
**piyasanın log-olasılığına** sabitlenir, ağaçlar yalnızca sapmayı öğrenir.
Bu, kademenin `sicaklik`/`bias` basamaklarının `β·log p`'den başlamasıyla
aynı çerçevedir — yani ağaç ile kademe artık **aynı soruyu** cevaplıyor.

Özellik kümesi de kademeninkiyle **aynı** (`test_ozellik_kumesi_kademeyle_ayni`);
aksi halde "ağaç mı kademe mi" sorusu model sınıfını değil özellik farkını
ölçerdi.

#### İç içe CV — hiperparametre kısıtı kalktı, dürüstlük kalmadı

Proje ayarı reddediyordu ve gerekçesi doğruydu: **tek halka vardı.**
`arama.SezonKatlayici` iki halka kuruyor — dış halka sezon dışarıda
bırakmalı (dokunulmaz), iç halka eğitim sezonlarının içinde. Bekçi:
`test_ic_halka_dis_sezonu_gormez`.

İç halkanın seçtiği **en küçük model** oldu ve kapasite monoton zarar
verdi:

| yaprak | iç halka skoru |
|---:|---:|
| **4** | **0,594010** ← seçilen |
| 8 | 0,595784 |
| 16 | 0,600629 |
| 31 | 0,612048 |

#### Ölçülen — 31.103 maç · 183 hafta · sezon dışarıda bırakmalı

| tahminci | Brier | fark | %95 aralık | geçti |
|---|---:|---:|---|---|
| piyasa | 0,593600 | — | — | referans |
| `agac` | 0,594000 | +0,000368 | [−0,000009, +0,000750] | hayır |
| `agac_ham` | 0,594300 | **+0,000667** | **[+0,000282, +0,001068]** | hayır |

`agac_ham`ın aralığı **tamamen sıfırın üstünde**: piyasayı fiyat olarak
değil özellik olarak gören bir ağaç, ondan anlamlı biçimde kötü.

#### Ayrışım **mekanizmayı** söylüyor — ve bu Faz 1'in karşılığı

| | Brier | REL | RES | NDCG | beraberlik duyarlılığı |
|---|---:|---:|---:|---:|---:|
| piyasa | 0,593600 | 0,00042 | **0,05657** | **0,8971** | 0,003 |
| `agac` | 0,594000 | **0,00015** | 0,05597 | 0,8963 | 0,012 |
| `agac_ham` | 0,594300 | 0,00012 | 0,05581 | 0,8955 | 0,006 |

*(sapma payı üçünde de 0,00021)*

Ağaç piyasanın **kalibrasyonunu iyileştiriyor** — güvenilirlik borcunu
0,00042'den 0,00015'e indiriyor, yani üçte birine. Ama **çözünürlük
kaybediyor**: 0,05657 → 0,05597. Net sonuç kötü.

Bu cümle §3.23'ün ayrışımı olmasa kurulamazdı. Tek bir Brier sayısıyla
bakınca "ağaç biraz daha kötü" denirdi; ayrışımla bakınca **ne yaptığı**
görünüyor: elindeki bilgiyi daha düzgün paketliyor ama yeni bilgi
üretmiyor — ve zaten paketlemede alınacak yol §3.23'te 0,00042 olarak
ölçülmüştü.

Ağacın beraberlik duyarlılığı piyasanınkinin **dört katı** (0,012 ↔ 0,003),
ama ikisi de sıfıra yakın; beraberliği görmek 31 binde de öğrenilmiyor.

#### Okuma — itiraz kapandı

| Denenen sınıf | Nerede | Sonuç |
|---|---|---|
| Doğrusal kademe (11 basamak) | T2–A3, §3.27–3.29 | Geçmedi |
| + açık etkileşim terimleri | §3.26, §3.29 | Geçmedi; §3.29'da **anlamlı biçimde kötü** |
| **Ağaç toplulukları** (keyfî doğrusal olmama) | **§3.30** | **Geçmedi** |

`DIS_INCELEME.md` §3'ün *"sizin doğrusal kademeniz o özelliği
kullanamadı"* itirazının cevabı artık bir teyit değil bir **ölçüm**:
itirazın adını verdiği model sınıfı bizim kesitimizde, bizim kapımızdan,
bizim özelliklerimizle koşturuldu ve geçmedi. Dış kanıtlar
(`zakariae-boui`, AlphaPy'ın kendi NCAA öğreticisi) artık teyit olarak
duruyor, dayanak olarak değil.

#### Bağımlılık kararı

`scikit-learn` ve `lightgbm` `model` **ekstrasına** girdi — üretim
bağımlılığı değil. Servis bunları taşımaz (`scripts/run_prod.sh`), ölçüm
katmanı ister; `scripts/setup.sh` ve CI kurar. `spor_toto.agac` yokluğu
`HAS_LIGHTGBM` ile denetler ve modül yine içe aktarılabilir —
`core.HAS_SCIPY` deseninin aynısı.

**`alphapy-pro`'nun kendisi kurulmadı**: Python ≥ 3.12 istiyor, bizim
`.replit` 3.10 koşuyor. Yalnızca işaret ettiği kütüphaneler alındı ve her
biri **kendi katlayıcımıza** bağlandı — AlphaPy Pro'nun yarım bıraktığı yer
tam olarak orası (`DIS_INCELEME_ALPHAPY.md` §4.1).

    python -m spor_toto.agac --rapor

### 3.31 1X2 dışı pazarlar (Faz 4.1) — kısıt kalktı, kural kalmadı

§7 uzun süre şunu yazıyordu:

> *"Diğer pazarların arayüze çıkması — ürün kararı: 1X2 dışındakiler analiz
> içindir, arşivde kalır."*

Bu bir **ürün kararıydı**, bir ölçüm sonucu değil. Kısıtlar kalkarken o da
kalktı. Kalkmayan kural sayfanın kuruluşunu belirledi: **hiçbir sayı
ölçülmüş isabeti olmadan görünmez.**

#### İki pazar, iki farklı ölçüm — ve fark bir tanım

**Alt/üst 2,5 temiz bir ikili olaydır.** 2,5 yarım çizgidir, iade yoktur.
Brier, kalibrasyon eğrisi ve Wilson aralığı 1X2 için ne yapılıyorsa aynen
uygulanır.

**Asya handikabı değildir.** Arşivdeki çizgilerin **%53'ü çeyrektir** ve
öyle bir bahis iki yarım bahse bölünür: sonuç `{0, ¼, ½, ¾, 1}` kümesinden
bir **getiri**dir, ikili bir olay değil. Tam sayı çizgide ayrıca iade var.

Bu yüzden AH için Brier **hesaplanmıyor** ve gövde bunu `brier: null` +
`brier_yok_sebep` ile açıkça söylüyor. Kesirli bir sonuca karşı Brier düzgün
bir puanlama kuralı değildir; hesaplansaydı sayı bir şeye benzerdi ama
hiçbir şey ölçmezdi. Yerine **beklenen getiri kalibrasyonu** ölçülüyor.

#### Ölçülen — kupon oran arşivi · 615 maç · `shin`

**Alt/üst 2,5** (n = 539, kapsama %87,6, marj **%7,14**, Brier **0,4656**,
üst gelen %55,3):

| olasılık bandı | maç | piyasa | gerçek üst | fark | %95 aralık |
|---|---:|---:|---:|---:|---|
| %35–45 | 68 | %42,3 | %39,7 | −2,6 | [28,9 · 51,6] |
| %45–55 | 213 | %50,0 | %48,4 | −1,6 | [41,7 · 55,0] |
| %55–65 | 163 | %59,4 | %59,5 | +0,1 | [51,8 · 66,7] |
| %65+ | 87 | %69,8 | %78,2 | +8,3 | [68,4 · 85,5] |

**Sapan bant 0/4.** En büyük sapma üst bantta (+8,3) ve orada bile piyasanın
söylediği sayı aralığın içinde — dar kesitte aralıklar geniş.

**Asya handikabı** (n = 539, marj **%7,38**, ortalama getiri **0,4833**;
çizgiler: 286 çeyrek · 137 yarım · 116 tam):

| çizgi | maç | piyasa | gerçek getiri | fark |
|---|---:|---:|---:|---:|
| \|h\| 0,00–0,30 | 211 | %49,7 | %49,3 | −0,4 |
| \|h\| 0,30–0,60 | 111 | %49,8 | %48,6 | −1,1 |
| \|h\| 0,60–1,10 | 123 | %49,9 | %44,7 | −5,2 |
| \|h\| 1,10+ | 94 | %50,2 | %50,5 | +0,3 |

**Sapan bant 0/4.**

#### Bantlar neden **çizgiye** göre — ölçülmüş bir tasarım kararı

İlk sürüm handikabı da olasılığa göre dilimledi ve eğri boş çıktı: 539 maçın
**531'i** tek banda düştü. Sebep pazarın **tanımı**dır — Asya handikabının
bütün amacı iki tarafı eşitlemektir, yani olasılık kasten %50'ye çivilenir.
Yukarıdaki tabloda dört bandın dördünde de piyasa %49,7–%50,2 arasında;
bu bir bulgu değil, pazarın kendisi.

Çizgi ise gerçekten değişiyor (0'dan ±2,5'e) ve *"piyasa büyük handikaplarda
da haklı mı"* sorusu ancak öyle sorulabilir. Cevap: evet, dört dilimde de.

Bekçi: `test_handikap_bantlari_cizgiye_gore` ve
`test_handikap_olasiligi_yariya_civili`.

#### Kayıtlı sınır

Kesit **bir sezon** (kupon oran arşivi, 615 maç), 31 binlik eğitim korpusu
değil — korpus bu iki fiyatı taşımıyor (`build_egitim.py` yalnızca 1X2
çekiyor). Bantlar bu yüzden kaba ve aralıklar 1X2 ölçümlerinden geniş.
Sınır gövdenin `sinir` alanında yazılı ve **sayfada katlanmadan** duruyor.

#### Yüzey

    pazar.py → payloads.pazar_payload → /api/pazar → /pazarlar

Sözleşme `scripts/api_sozlesme.py` ve `frontend/scripts/check.mjs`
eşlemesine kayıtlı: `GET /api/pazar → PazarResponse`. Arayüz denetimi 49'dan
**50**'ye çıktı.

### 3.32 Yığınlama (Faz 2.4) — serinin **ilk negatif nokta tahmini**, ve niçin yetmiyor

Tek tek her görüş ölçüldü ve hiçbiri geçmedi. Ama *"birleştirilseler bir şey
çıkar mıydı"* ayrı bir sorudur ve tek tek denemeler onu cevaplayamaz.

`spor_toto/yigin.py` dört tabanı bir multinom logit üst-öğreniciyle
birleştiriyor. Tasarım `recalibrate`in `sicaklik` basamağıyla aynı: taban
başına **tek** katsayı, yani ağırlık doğrudan okunabiliyor.

#### AlphaPy'ın hatası burada düzeltiliyor

`DIS_INCELEME_ALPHAPY.md` §4 madde 4: klasik AlphaPy'ın `predict_blend`i
harman matrisini `model.probas[(algo, Partition.train)]`den — **örneklem
içi** olasılıklardan — kuruyor. En çok ezberleyen model kendi eğitim
setinde en iyi görünür ve üst-öğrenici ona en büyük ağırlığı verir. Pro
bunu kat dışına çevirmiş ama katları **rastgele**; zaman sıralı veride o da
sızdırır.

Buradaki yığın iki şartı birden sağlıyor: üst-öğrenici **kat dışı**
olasılıklarla eğitilir ve katlar `arama.SezonKatlayici`dan gelir, yani
sezon sınırlarıdır.

Bekçi doğrudan bu hatayı kovalıyor: `test_ust_ogrenici_kat_disi_olasilik_goruyor`
eğitim setini ezberleyip dışarısında bilgisiz olan bir taban kuruyor ve
üst-öğrenicinin ona ağırlık **vermediğini** doğruluyor. Örneklem içi
görseydi ağırlık patlardı.

#### Ölçülen — 31.103 maç · 183 hafta · kat dışı 31.103 maç

| tahminci | Brier | fark | %95 aralık | geçti |
|---|---:|---:|---|---|
| **`yigin`** | **0,593500** | **−0,000137** | [−0,000402, +0,000148] | **hayır** |
| piyasa | 0,593600 | — | — | referans |

**Serinin ilk negatif nokta tahmini.** Faz 1–3'te ölçülen her aday pozitif
taraftaydı (piyasadan kötü); yığın ilk kez sıfırın altına düşüyor. Ama
aralık sıfırı kesiyor, yani **geçmiyor** — ve projenin kuralı ortalama
değil aralıktır.

#### Ağırlıklar sebebini söylüyor

| taban | ağırlık |
|---|---:|
| piyasa | **+0,5307** |
| kademe | +0,3242 |
| agac | +0,2347 |
| **dixon_coles** | **−0,0693** |

Okuma: ilk üç taban **hepsi piyasa çıpalı**dır — `kademe` `β·log p`'den
başlar, `agac` piyasanın log-olasılığını `init_score` alır. Ağırlıkları
toplandığında **1,09** ediyor, yani yığın piyasanın kendi sinyalini üç
parçaya bölüp geri topluyor.

Piyasadan **bağımsız** olan tek taban Dixon-Coles ve ağırlığı **negatif**.
Bu §3.28'in bulgusunun yığın tarafındaki tekrarı: orada `kalibre_dc`
katsayısı −0,0492 çıkmıştı, burada −0,0693.

Yani −0,000137'lik iyileşme yeni bilgiden değil, **aynı bilginin biraz
farklı paketlenmesinden** geliyor — ve §3.23'te ölçülen paketleme tavanı
(0,00042) bunun neden bu büyüklükte kaldığını da açıklıyor.

#### Faz 2 kapanıyor

| Alt adım | Sonuç |
|---|---|
| 2.1 Etkileşim kademesi | Geçmedi; §3.29'da anlamlı biçimde kötü |
| 2.2 Ağaç toplulukları | Geçmedi (§3.30) |
| **2.4 Yığınlama** | **Geçmedi** — ilk negatif nokta tahmini, aralık sıfırı kesiyor |

    python -m spor_toto.yigin --rapor

### 3.33 LOFO ve Venn-Abers (Faz 2.5 + 2.3) — Faz 2'nin son iki adımı

#### LOFO — bir özelliği çıkarınca ne oluyor

Tekil önem ölçüleri (ağaç bölünme sayısı, permütasyon) **korelasyonlu**
özelliklerde yanıltır: `elo_farki`, `form_puan_farki` ve `h2h_farki` üçü de
takım gücünü ölçüyor ve biri düştüğünde ötekiler açığı kapatıyor. LOFO tam
bunu ölçer — *"bu özelliği tamamen çıkarsam skor ne kadar kötüleşir?"*

Katlar `arama.SezonKatlayici`dan gelir. AlphaPy Pro'nun
`select_features_lofo`u aynı işi **rastgele** katlarla yapıyor.

**Ölçülen — 31.103 maç · 4 sezon katı · taban Brier 0,594005:**

| özellik | Brier (çıkarınca) | zarar |
|---|---:|---:|
| `form_isabet_farki` | 0,594147 | **+0,000142** |
| `sezon_sonu_pay_farki` | 0,594048 | +0,000043 |
| `ic_dis_form_farki` | 0,594029 | +0,000025 |
| `sikisiklik_farki` | 0,594024 | +0,000019 |
| `seri_farki` | 0,594024 | +0,000019 |
| `dinlenme_farki` | 0,593967 | **−0,000038** |
| `elo_farki` | 0,593963 | **−0,000042** |
| `form_puan_farki` | 0,593939 | **−0,000065** |
| `h2h_farki` | 0,593939 | **−0,000065** |
| `ayrisma` | 0,593846 | **−0,000159** |

**Onun beşi negatif**: o özellikleri çıkarmak skoru **iyileştiriyor**.

İki okuma öne çıkıyor. Birincisi `ayrisma` (bahisçi anlaşmazlığı) en zararlı
sütun — A2'nin *"ham sinyalin kendisi bir görüntüydü"* bulgusunun ortak
modeldeki karşılığı. İkincisi `elo_farki` ve `h2h_farki`, yani projenin
kendi belgelerinde **en umutlu** diye işaretlenmiş iki sütun, net negatif.

LOFO'nun değeri bu tabloda tek tek ölçümlerin veremediği şeyi vermesi:
özellikler **birlikte** de bir şey taşımıyor.

#### Venn-Abers — nokta tahmininde bir şey yok, **aralık yeni**

AlphaPy Pro'nun en dikkat çeken parçasıydı. Üç sapmayla alındı ve üçü de
gerekçeli:

1. **Paket alınmadı, algoritma yazıldı.** `pip install venn-abers` bu
   ortamda **derlenmiyor**. `recalibrate._pav` zaten elimizdeydi:
   Venn-Abers iki PAV uydurmasıdır. `_uydur`un *"sessizce kaybolabilecek
   bir isteğe bağlı bağımlılık, kendi çözücünü yazmaktan kötüdür"*
   gerekçesi burada teorik değil **ölçülmüş** bir gerçek çıktı.
2. **Kalibrasyon bölmesi sezon bazlı.** Pro'nun `cal_size=0.2`si rastgele
   bir dilim alır ve zaman sıralı veride aynı sezonu hem uydurmaya hem
   kalibrasyona koyar. Burada **son sezon** ayrılıyor.
3. **Üç sınıf için bire-karşı-hepsi** — ve bu bir ödünç: geçerlilik
   garantisi her sembol için ayrı ayrı geçerlidir, normalize edilmiş üçlü
   için değil. Yazılı duruyor.

**Ölçülen:**

| tahminci | Brier | fark | %95 aralık | geçti |
|---|---:|---:|---|---|
| piyasa | 0,593600 | — | — | referans |
| `venn_abers` | 0,593900 | +0,000264 | [−0,000081, +0,000584] | hayır |

Beklenen sonuç buydu ve **koşumdan önce yazılmıştı**: §3.23 kalibrasyon
tavanını 0,00042 ölçmüştü, izotonik `shin` üzerinde zaten hiçbir şey
eklemiyordu.

**Asıl çıktı aralığın kendisi** ve o projede daha önce hiç ölçülmedi:

| | değer |
|---|---:|
| ortalama `p1 − p0` | **0,00472** |
| en geniş | 0,64179 |
| nokta (maç × sembol) | 93.309 |

Ortalama genişlik 0,0047 — kalibrasyon kümesi tipik bir olasılığı ±0,0024
içine hapsediyor. Bu, §3.23'ün `REL = 0,00042`sinin bağımsız bir teyidi:
piyasanın olasılıkları **sıkı biçimde destekleniyor**, oynatılacak yer yok.

En geniş aralık (0,64) kalibrasyon kümesinin desteği dışına düşen
skorlarda; orada model *"bilmiyorum"* diyor ve bunu artık **söyleyebiliyor**.

#### Faz 2 kapandı

| Alt adım | Sonuç |
|---|---|
| 2.1 Etkileşim kademesi | Geçmedi; §3.29'da anlamlı biçimde kötü |
| 2.2 Ağaç toplulukları | Geçmedi (§3.30) |
| **2.3 Venn-Abers** | **Geçmedi** — tavan koşumdan önce biliniyordu |
| 2.4 Yığınlama | Geçmedi; ilk negatif nokta tahmini (§3.32) |
| **2.5 LOFO** | **Hiçbir özellik taşımıyor**; onun beşi net negatif |

    python -m spor_toto.kalibre --rapor

### 3.34 Müşterek beklenen değer (Faz 4.2) — kaldırılan son kısıt

`README.md` §1.6 uzun süre şunu yazıyordu: *"İkramiye / beklenen değer
hesabı yapmaz"*. O bir **ürün kararıydı** ve kısıtlar kalkarken o da kalktı.
Kalkmayan şey **ölçülmemiş bir sayının arayüze çıkmaması**: `getiri.py`
hesabı yapar, sayıyı yazar ve **arayüze çıkmaz**.

#### Neden bu eksen ötekilerden farklı

Faz 1–3 on bir kez aynı şeyi ölçtü: kapanış fiyatını geçen bir görüş yok.
Sabit oranlı bahiste bu kapanan bir kapıdır, çünkü orada kenar
`p_model − p_piyasa`'dır. Müşterek bahiste kapanmaz (`DIS_INCELEME.md` §7):

    Sabit oranlı :  edge = p_model  − p_piyasa
    Müşterek     :  edge = p_piyasa − oynanma_payı

Yani piyasa olasılığını **olduğu gibi** kullanıp yalnızca kalabalığın ondan
saptığı yeri işaretlemek yeter. Projenin bütün ölçüm serisi bu eksene
dokunmuyor.

#### Payın kapalı formu

Bizimle birlikte kazanan rakip **kolon** sayısı `W ~ Binom(N, q)` ise:

    E[1/(1+W)] = (1 − (1−q)^(N+1)) / ((N+1)·q)

Monte Carlo yok; sayı kesin ve deterministik. Kod bunu doğrudan değil
`−expm1(n·log1p(−q))/(n·q)` olarak yazıyor: doğrudan yazım `q = 1e-12`'de
anlamlı basamak kaybından **üçüncü hanede** yanlış çıkıyordu.

**Havuz oyuncu başına değil, kazanan kolon başına bölünür.** Bu ayrım
büyüklüğü tamamen belirler: tek bir oyuncu on binlerce kolon oynar. Bu
yüzden nüfus `rakip_kolon`, `q` ise **bir kolonun** tutturma olasılığıdır.

#### İki sessiz hata, ikisi de bekçili

**(1) Kupon ile tek kolon karıştırılamaz.** İlk sürümde CLI, tek kolonun
`P(14+) ≈ 0,0009`'unu 2.228 kolonluk bir bedelle topluyordu — iki sayı iki
farklı şeyin sayısıydı. Doğrusu garantinin aritmetiğinden gelir
(`secim` modül başlığı): `P(en iyi = 14−k) = P(k)`, `k`'nın dağılımı
Poisson-binom. `kupon_kademeleri()` bunu yapar; bekçisi
`test_kupon_kademeleri_garanti_aritmetigiyle_uyumlu`.

**(2) `p = q` alınırsa hesap çöker.** İkinci sürüm kalabalığın
olasılığını bizimkine eşitliyordu. O özel durumda, `N·q ≫ 1` iken:

    p_k = q_k  ⇒  E[kazanç] = havuz·(1−c)/(N+1)

yani havuzun kademelere nasıl bölündüğünden de, bizim ne oynadığımızdan da
**bağımsız** bir sayı. Çıktı çalışır görünüyordu ve **boştu**. Bekçisi
`test_ortalama_kolonsak_pay_bolusumu_hicbir_sey_degistirmez`.
Düzeltmesi `kalabalik_kademeleri()`: kalabalığın kolonu modellenir.

#### Hesaplanan — 51. hafta · bütçe 4.096 · 3.888 kolon · bedel 5.832

Başlık bilerek *"ölçülen"* değil: aşağıdaki sayılar bir gözlemden değil, yazılı varsayımlardan çıkıyor.

Havuz 50.000.000 · komisyon %50 · rakip kolon havuzdan türetiliyor
(50.000.000 / 1,5 − 3.888 = 33.329.445):

| kalabalık modeli | q(14) | bekl. kazanç | beklenen getiri | **oran** |
|---|---:|---:|---:|---:|
| `orneklem` — rakip piyasadan çekiyor | 3,6e-05 | 910 | −4.922 | **0,156** |
| `favori` — rakip hep favoriyi işaretliyor | 9,0e-04 | 40 | −5.792 | **0,007** |

**Bu hesabın asıl sonucu tek bir sayı değil, iki sayının arasındaki 22 kattır.**
Kalabalığın nasıl işaretlediğine dair varsayım, sonucu tahmin modelinin
kendisinden **çok daha fazla** belirliyor. Bu, projenin bu eksende neye
ihtiyacı olduğunu tam olarak söylüyor: daha iyi bir tahminci değil,
**oynanma paylarının ölçümü** (§6.3b, `super_toto_hafta.kamuoyu`).

#### Havuz büyüklüğü getiriyi belirlemiyor

İki duyarlılık eğrisi ayrı sorular sorar ve karıştırılırsa yanlış okunur:

| çarpan | havuz **sabit** | havuz **da ölçekli** |
|---|---:|---:|
| ×0,25 | 0,624 | 0,156 |
| ×1 | 0,156 | 0,156 |
| ×4 | 0,039 | 0,156 |

İkinci sütun **tam olarak düz** — ve tesadüf değil: `N·q ≫ 1` iken pay
`havuz(1−c)·w/(N·q)`'ya iner, havuz ve `N` aynı çarpanla ölçeklenince
birbirlerini götürürler. Müşterek bahsin en önemli sezgisi budur:
**getiriyi havuzun büyüklüğü değil, `p_k/q_k` oranı belirler.**

#### Sonuç ve sınır

Her iki modelde de oran 1'in çok altında — yani bu varsayımlarla kupon
pozitif beklenen değerli değil. Ama bu **bir ölçüm değildir**: havuz payı
(%55/25/20), komisyon (%50) ve kalabalık modeli varsayımdır ve gövde bunu
`uyari` alanında taşımak zorundadır (bekçi:
`test_uyari_ve_varsayimlar_govdede_duruyor`). §6.3b bağıntıyı görebilmek
için ≈71 ikramiyeli hafta gerektiğini ölçtü; elde **1** var.

    python -m spor_toto.getiri
    python -m spor_toto.getiri --kalabalik favori

### 3.35 Takım bazlı istatistik (Faz 4.3) — yasak yerine bir katsayı

§7 uzun süre şunu yazıyordu:

> *"Takım bazlı istatistik | 216 takım, Süper Lig takımları bile 32 maç.
> Çıkacak sayı güvenilir görünür ama gürültüdür"*

**Teşhis doğruydu, çare yanlıştı.** Az örnekli bir ortalamanın gürültülü
olması onu yasaklamayı değil, *ne kadarının gürültü olduğunu göstermeyi*
gerektirir. Ampirik Bayes küçültmesi (James–Stein) tam bunu yapar:

    x̂_t = μ_L + B_t · (x_t − μ_L),      B_t = τ² / (τ² + σ²/n_t)

`B_t` sayının **ne kadarının takımın kendi verisi** olduğudur. Yasak
yerine bir katsayı — ve o katsayı arayüzde bir çubukla **görünür**.

#### Üç karar, üçü de gerekçeli

**Küçültme lig içinde.** 22 lig aynı havuza konsaydı Süper Lig'in bir
takımı Belçika ikinci liginin ortalamasına çekilir, ligler arası gerçek
güç farkı gürültü sayılıp silinirdi. `τ²` de lig içinde kestirilir:
takımlar arası yayılım liglere göre değişir.

**`τ̂² = max(0, Var(x_t) − ort(σ²/n_t))`.** `max(0, …)` şart: gözlenen
yayılım gürültünün altına düşerse *"gerçek takım farkı yok"* demektir ve
her takım lig ortalamasıdır. Negatif bir `τ²` küçültmeyi **tersine**
çevirirdi — tahmin ortalamanın öbür yanına geçerdi. Bekçisi
`test_gercek_fark_yoksa_hepsi_lig_ortalamasi`.

**Puan ölçeği 3/1/0.** `takim._PUAN` bilerek ±1/0 kullanıyor çünkü orada
soru *üstünlük*tü (§3.29). Burada soru **başarı** ve okurun beklediği ölçek
lig tablosununkidir. Aynı projede iki ölçek olması bir tutarsızlık değil,
iki ayrı sorunun iki ayrı cevabı.

#### Ölçülen — 31.103 maç · 22 lig · 604 takım

| | değer |
|---|---:|
| medyan maç sayısı | 108 |
| ortalama küçültme `B` | **0,854** |
| ortalama %95 aralık genişliği (puan) | 0,509 |

Küçültmenin en çok konuştuğu satırlar — hepsi az maçlı takımlar:

| lig | takım | n | ham | küçültülmüş | B |
|---|---|---:|---:|---:|---:|
| E3 | Scunthorpe | 46 | 0,565 | **0,875** | 0,61 |
| SC3 | Kelty Hearts | 36 | 2,250 | **1,945** | 0,65 |
| I2 | Pordenone | 38 | 0,474 | **0,738** | 0,69 |

Scunthorpe'un ham 0,565'i, 46 maçta güvenilir bir sayı değil; küçültme onu
lig ortalamasına doğru 0,875'e çekiyor ve aralığı [0,58, 1,17] yazıyor.
**Yasak bu satırı hiç göstermezdi; küçültme onu ne kadar bilmediğimizle
birlikte gösteriyor.**

`?sezon=` verildiğinde `n` düşer ve sistem **kendiliğinden temkinli
olur**: tek sezonda (2024-25, 397 takım) ortalama `B` 0,854'ten **0,697**'e
iner, ortalama aralık 0,509'dan **0,690**'a genişler. Bu, doğru davranışın
kod hâlidir — daha az veriye daha az güven, elle ayarlanmadan.

#### Sınır, kayda geçiyor

`τ²` momentler yöntemiyle kestiriliyor ve **kendi belirsizliği aralığa
dahil değil**; az takımlı liglerde gerçek aralık buradakinden geniştir.
Tam Bayesçi bir hiyerarşi bunu kapatırdı ama bir MCMC bağımlılığı getirir
ve gösterilen sayının okunuşunu değiştirmezdi.

İkinci sınır: sezonlar varsayılan olarak **havuzlanır**, yani sayı *"bu
kulüp korpus dönemi boyunca ne yaptı"*dır, bugünkü formu değil. Anlık
gidişat zaten `elo` ve `takim.seri_tablosu` tarafından taşınıyor — ve ikisi
de piyasayı geçmedi (§3.27, §3.29). Buradaki soru başka: *"az maçlı bir
takımın sayısına ne kadar güvenilir?"*

    python -m spor_toto.takim_gucu --lig T1
    python -m spor_toto.takim_gucu --lig T1 --sezon 2425

### 3.36 Yeni veri (Faz 3.4) — planın en yüksek beklenen değerli maddesi

Plan bunu açıkça yazmıştı: *"En yüksek beklenen değer Faz 3.4'ün yeni veri
kaynaklarında, Faz 2'nin yeni modellerinde değil."* Dört kaynak sıralanmıştı;
ikisi **açıldı**, ikisi **arandı ve kapalı çıktı**.

#### Neden bu madde ötekilerden farklıydı

§3.16 (A3) bir şey ölçmüş ve açıklayamamıştı: deplasman "dinlenmiş"
göründüğünde ev sahibi piyasayı aşıyordu, ve etki Avrupa liglerinde kat
kat güçlüydü. `egitim._takvim_tablosu`ın kendi belgesi sebebi yazıyordu:

> *"Korpus 22 lig taşıyor; kupa ve Avrupa maçları içinde yok. Dolayısıyla
> dinlenme günü olduğundan **uzun** ölçülür — ve hata rastgele değil,
> Avrupa oynayan takımlarda yoğunlaşır."*

Yani bulgu bir **sinyal** değil bir **ölçüm hatası** olabilirdi. İkisini
ayırt etmenin tek yolu eksik maçları korpusa katmaktı.

#### (1) UEFA fikstürü — ve anomalinin yarısı buharlaştı

`openfootball/champions-league` (kamu malı) ŞL + AL + Konferans maçlarını
veriyor. `scripts/build_avrupa.py` 4 sezonun **768 maçını** çekiyor ve
korpusun takım adlarına bağlıyor; ad eşleşmesi **%100** (2.222 ad ifadesi).

Ad eşleme bu işin asıl zorluğuydu ve iki kural onu çözdü: **ülke kodu bir
kısıttır** (`(GER)` yalnızca `D1`/`D2` içinde aranır) ve **bulanık eşleme
yoktur** (alt dize eşlemesi denendi, "Rangers" ile "Cove Rangers"ı
karıştırdı ve **%68**'de kaldı). Kalan istisnalar elle yazılmış, gözden
geçirilmiş bir tabloda.

**Tasarımın can alıcı yeri:** UEFA günleri ayrı bir sütun olarak
eklenmedi, `dinlenme` ve `sikisiklik` hesaplarına **enjekte edildi**. Ayrı
sütun olsaydı `dinlenme_farki` yanlış kalmaya devam eder, model iki
çelişkili girdiyi uzlaştırmak zorunda kalırdı. Sayı artık *doğru*.

**Kontrollü ölçüm — aynı korpus, tek değişken:**

| Lig katmanı | Ev dinlenmiş | Dengeli | **Dep dinlenmiş** |
|---|---:|---:|---:|
| Avrupa ligi — **UEFA yok** | −0,0018 (511) | −0,0072 (11.746) | **+0,0613** (445) |
| Avrupa ligi — **UEFA var** | −0,0058 (887) | −0,0075 (10.959) | **+0,0325** (835) |
| Diğer lig — UEFA yok | +0,0027 (1.014) | +0,0002 (14.105) | +0,0114 (1.136) |
| Diğer lig — UEFA var | +0,0027 (1.014) | +0,0002 (14.105) | +0,0114 (1.136) |

Üç şey birden söylüyor:

1. **Anomali neredeyse yarıya indi** (+0,0613 → +0,0325). Yani o sayının
   yarısı bir sinyal değil, **görünmeyen bir maçtı**.
2. **Hücre büyüdü** (445 → 835): korpus 390 maçı yanlış sınıflandırıyormuş.
3. **Kontrol katmanı bit bit aynı.** Avrupa'ya takım vermeyen liglerde
   hiçbir sayı kıpırdamadı — değişikliğin tam olarak dokunması gereken
   yere dokunduğunun kanıtı.

**Ama düzeltilmiş özellik de piyasayı geçmiyor.** `kalibre_avrupa`
+0,000028 [−0,000277, +0,000352] — hayır. Kalan yarı da fiyatlanmış.

#### (2) Şehir tablosu — `TURETILEMEYEN` listesinden bir madde düştü

`disari.TURETILEMEYEN` şunu yazıyordu: *"derbi: şehir eşlemesi ya da
rekabet tablosu yok; **elle liste yazmak türetme değil kuratörlük
olurdu**."* Cümle doğruydu ve kapıyı kapatmıyordu: elle liste yazmak
kuratörlüktür, **kaynaktan şehir okumak türetmedir**.

`openfootball/clubs` (CC0) kulüp–şehir tablosu veriyor. Kapsama **%98,0**
(604 takımın 592'si); kalan 12'sinin şehri kaynakta **hiç yazmıyor** ve
uydurulmuyor — o maçlarda derbi sorusu **cevapsız** kalıyor.

Derbi bir **yön** değil **sıcaklık** değişkeni olarak girdi (`ayrisma` ile
aynı biçim): aynı şehirde oynanan maç iki tarafa da aynı şeyi yapar; iddia
"kim avantajlı" değil "belirsizlik farklı mı".

**Ölçülen:** 30.187 maçta (%97,1) soru cevaplanabiliyor, bunların
**667'si** (%2,21) derbi. `kalibre_derbi` +0,000176 [−0,000172, +0,000539]
— `kalibre_seri`nin +0,000148'inden **kötü**. Geçmedi.

**Bir sessiz hata yakalandı ve bekçiye bağlandı.** `recalibrate._mac_ozellikleri`
bir **beyaz listedir**; `derbi` ilk koşumda ona eklenmemişti. Sütun tasarım
matrisinde vardı, her satırda sıfırdı, katsayı **tam 0,000000** çıktı ve
ölçüm *"derbi bir şey söylemiyor"* diye okunacaktı. Düzeltince katsayı
**+0,0992** oldu — yani "hiçbir şey" değil, **ölçülmemiş** bir şeydi.
Bekçi: `test_sehir.py::test_derbi_korpustan_tasarima_ulasiyor`.

#### (3) ve (4) Arandı, kapalı çıktı — ve ikisi de teknik değil ilkesel

| Kaynak | Neden kapalı |
|---|---|
| **xG** (Understat / fbref) | Understat `robots.txt`: `User-agent: * / Disallow: /` — otomatik erişime **tamamen kapalı**. fbref Cloudflare sorgusu arkasında. Ayrıca ikisi de Süper Lig'i ve korpusun çoğunluğunu oluşturan alt İngiliz liglerini kapsamıyor |
| **Kadro / sakatlık** | Kaynak teknik olarak açık (transfermarkt `Allow: /`) ama özellik **ileriye dönük kullanılamaz**: gerçek kadro ancak ilk vuruşta bellidir. Korpusta kullanıp `/tahmin`de kullanamamak **eğitim/servis ayrışmasıdır** ve ölçümü anlamsız kılar. Gereken şey maç öncesi haber akışının **tarihsel anlık görüntüleridir**; arşivde yok ve geriye dönük kurulamaz |

İkincisi kayda değer: bu, *"kaynak bulunamadı"* değil **"özellik bu ürün
için geçersiz"** demektir. `/tahmin` oynanmamış maça olasılık verir; ölçümde
kullanılan bir bilgiyi tahmin anında bulamıyorsak ölçüm ürünü tarif etmez.

> **Düzeltme (2026-08-29) — xG satırının ilk yarısı geçersiz.** Yukarıdaki
> tablo xG'yi *erişim* gerekçesiyle kapatıyordu ve o gerekçe artık ayakta
> değil: `hudl/open-data` (eski adıyla `statsbomb/open-data`) olay düzeyi
> veriyi serbestçe yayımlıyor, her şutta `shot.statsbomb_xg` var, ne
> `robots.txt` engeli ne Cloudflare var.
>
> **Ama satırın ikinci yarısı ayakta ve tek başına yetiyor.** Depo lig-sezon
> lig-sezon sayıldı: Süper Lig yok, alt İngiliz ligleri (E1/E2/E3/EC) yok,
> korpus penceresiyle kesişim 31.103 maçta **92 maç** ve o 92'nin hepsi tek
> takıma yanlı. Üstelik canlı akış yok — veri maçlardan yıllar sonra
> yayımlanıyor, yani `/tahmin` onu ilkesel olarak da göremezdi.
>
> Bu yüzden `disari.TURETILEMEYEN["xg"]` **yerinde kaldı ve gerekçesi
> değişti**. Bir kaynağın açılması sorunun çözülmesi demek değildi ve bu
> ayrımı yazmak, "artık var" deyip kapsamayı sessizce görmezden gelmekten
> iyidir. Açılan şey başkaydı ve ayrı bir anahtarla yazıldı — `xg_vekili`:
> depo xG'yi *korpusun kendi şut sayımıyla aynı maçta* verdiği 1.517 maçlık
> bir kesit sunuyor, yani bir **girdi** değil bir **kalibrasyon referansı**.
> Ölçümü §3.42.

#### Faz 3.4 kapandı — ve söylediği şey

Serinin en güçlü tek cümlesi burada: **eksik veri gerçekten eksikti,
bulundu, eklendi, ölçüm hatasını düzelttiği doğrulandı — ve düzeltilmiş
özellik de piyasayı geçmedi.**

Bu, on bir ölçümün on ikincisi değil; **niteliksel olarak farklı** bir
kapanış. Önceki ölçümler *"elimizdeki veriden çıkarılabilecek her şey
fiyatlanmış"* diyordu. Bu ölçüm bir adım daha ileri gidiyor: *"elimizde
olmayan ve bulunabilen veri de fiyatlanmış."* Kalan iki kaynak ise
bulunamıyor değil, **kullanılamıyor**.

    python scripts/build_avrupa.py
    python scripts/build_sehir.py
    python -m spor_toto.avrupa
    python -m spor_toto.sehir
    python -m spor_toto.disari

### 3.37 2. Tahmin — aynı hafta, birikmiş aletlerin tamamıyla

2. haftanın kuponu 2026-08-18'de donduruldu. O tarihten sonra projede dört
şey değişti ve **dördü de aynı haftada başka bir cevap üretiyor**. Soru
şuydu: birikmiş değişiklikler kâğıt üzerinde mi kaldı, yoksa gerçekten
başka bir kupon mu kuruyor?

Cevap ölçüldü ve kayda geçti: `hafta_02_tahmin2.json`. **1. Tahmin'in
kaydı yerinde duruyor ve yeniden hesaplanmadı** — ikinci kayıt onun yanına
eklendi, üstüne değil. Arayüzde iki sekme (`1. Tahmin` / `2. Tahmin`)
aralarında geçiş yapar.

#### Kıyas — ve niçin aynı ölçekte yapılmak zorunda

İki kuponun kendi `p_hedef`i doğrudan karşılaştırılamaz: biri `orantili`,
öteki `shin` ölçeğinde hesaplandı. Bu yüzden **eski işaretler bugünkü
olasılıklarla yeniden ölçüldü** (yeniden *seçilmedi* — `picks` olduğu gibi
alındı):

| Ölçü | 1. Tahmin (`esik` · `orantili`) | 2. Tahmin (`hedef` · `shin`) |
|---|---:|---:|
| P(en iyi kolon ≥ 12) | %34,87 | **%38,39** |
| Kolon | 4.096 | **1.296** |
| Kalabalık oranı | 0,72 | **0,81** |
| İşaret farkı | — | 11 / 15 maç |

**Hem daha iyi hem 3,2 kat ucuz.** Kazancın çoğu kural değişiminden
geliyor: aynı ölçekte eşik kuralı %30,61 verirken hedef kuralı %39,79
veriyor ve bunu 1.296 kolonda yapıyor.

#### Yeni olan tek şey: kalabalık ekseni işaretlere girdi

§3.34 müşterek beklenen değeri hesaplamıştı ama kuponu kuran kural
kalabalığı **hiç görmüyordu**. `secim.kalabalik_ayari` bu boşluğu kapatıyor
ve tasarımı tek cümlede özetlenir: **işaret sayıları sabit, hangi sembol
sorusu yeniden soruluyor.**

Sayılar sabit kaldığı için ayar **bedavadır** — aynı kolon, aynı satır,
aynı motor. Değişen yalnızca bölüşme:

| | hedef kuralı | + kalabalık ayarı |
|---|---:|---:|
| P(en iyi kolon ≥ 12) | %39,79 | %38,39 |
| kalabalık oranı | 0,59 | **0,81** |
| kazanınca rakip yoğunluğu | ×9,2 | **×7,7** |

Üç maçta sembol değişti (7, 13, 14) ve üçü de aynı kalıpta: olasılıktan
1–2 puan verip oynanmadan 7–13 puan kazanıyor.

**Amaç oran, kalabalık değil — ve ilk sürüm burada yanlıştı.** Yalnızca
kalabalık-içini küçültmek, kalabalık piyasayla birebir aynı olduğunda bile
daralmayı ödüllendiriyordu: hiçbir şey kazandırmayan bir kayıp. Bekçi
`test_ayar_kalabalik_ayrismiyorsa_tabanda_kalir`. Enbüyüklenen sayı artık
sayfada **raporlanan** sayıyla aynı: `küme-içi / kalabalık-içi`.

Arama `en_iyi_secim`in Pareto tekniğinin bir boyut fazlasıdır (kümülatifler
**ve** kalabalık skoru). Kaba kuvvet denendi ve yetmedi — maç başına üç
aday, on beş maçta 14 milyon bileşim; budamayla aynı sonuç birkaç yüz
durumda çıkıyor.

**Harcama sınırı bir ölçüm değil, karardır** ve öyle etiketlenir:
`VARSAYILAN_KAYIP_ORANI = 0,05`. Sıfır yazılırsa ayar hedefi bir puan bile
harcamaz.

#### `getiri`nin sayısı bu ekseni niçin göremiyor

Kayıtta müşterek beklenen değer bloğu var ve **arayüze çıkmıyor** (§6.3b:
bağıntıyı görmek için ≈71 ikramiyeli hafta gerekiyor, elde 1 var). Ama
ölçüm sırasında yapısal bir şey görüldü ve yazılması gerekiyor:

`getiri.kalabalik_kademeleri` rakibin isabetini **koşulsuz** hesaplar —
rastgele bir sonuç, rastgele bir rakip kolon. O sayı bizim ne
işaretlediğimize hiç bakmaz, dolayısıyla kalabalık ayarının kazancını
**tanım gereği göremez** ve iki plan için birebir aynı çıkar.

Oysa havuz, biz kazandığımızda bölünür. Doğru soru koşulludur ve kapalı
formda yazılır:

    q_koşullu = Π_i  ( Σ_{s∈sec_i} p_i(s)·o_i(s) ) / ( Σ_{s∈sec_i} p_i(s) )

Bu sayı (`kupon.<plan>.kosullu_rakip`) ayarın kazancını görüyor: ×9,2 →
×7,7. **Yalnızca aynı şekildeki planlar arasında okunur** — üçlü
işaretlenen maçın çarpanı tam 1'dir, banko işaretlenenin çarpanı büyüktür,
yani sayı "kalabalıktan kaçtım mı"nın yanı sıra "ne kadar daraldım"ı da
taşır. Farklı bütçedeki iki kuponu bu sayıyla karşılaştırmak iki ayrı şeyi
tek rakama sıkıştırırdı.

Aynı ölçüm `getiri`ye üçüncü bir kalabalık modeli kazandırdı: `oynanma`.
İlk ikisi kalabalığı **piyasadan** türetir (varsayım); üçüncüsü gerçekten
kaydedilmiş oynanma paylarını kullanır (`r = Σ_s o(s)·p(s)`, kare değil
çapraz terim). Modül başlığı uzun süre *"eksik olan yeni bir model değil,
oynanma paylarının ölçümüdür"* yazıyordu — o ölçüm 2026/27 hafta
dosyalarında var. `orneklem`, yeni modelin `o = p` özel hâlidir ve bekçisi
bunu doğruluyor.

#### Bağımsız görüş — ve niçin hiçbir işareti değiştirmiyor

2. haftanın ilk analizinde piyasadan başka bir görüş **yoktu**.
`spor_toto.gorus` bunu kapatıyor: Dixon-Coles + Elo, 31.670 maçlık
tarihçeyle (korpus 2021/22–2024/25 **artı** 2025/26 arşivi; son maç
2026-07-27) ve **oranlara hiç bakmadan**.

Ad eşleme bu işin asıl zorluğuydu ve `build_avrupa`nın iki kuralı aynen
geçerli: **lig bir kısıttır** (T1 adı yalnızca T1 havuzunda aranır) ve
**bulanık eşleme yoktur**. Kapsama 12/15; kalan üçünün (Erzurumspor FK,
Çorum FK, Amed Sportif) korpusta karşılığı **yok** ve uydurulmuyor.

Sonuç okunmaya değer:

| # | Maç | piyasa | Dixon-Coles | sapma |
|---:|---|---|---|---:|
| 4 | Fenerbahçe – Konyaspor | 66/7/27 | 73/16/11 | 16 puan |
| 5 | Eyüpspor – Gaziantep | 33/28/39 | 48/26/26 | 15 puan — **favori ayrışıyor** |
| 12 | Newcastle – Liverpool | 26/23/51 | 38/24/38 | 13 puan |
| 2 | Rizespor – Samsunspor | 44/27/29 | 36/25/39 | 10 puan — **favori ayrışıyor** |

**Ve hiçbiri işaret değiştirmiyor.** Dixon-Coles kupon setinde piyasanın
gerisinde ölçüldü (§3.28), Elo bir 1X2 olasılığı değil beklenen **skor**
verir (§3.27). İkisi de kayda geçer, karar yoluna girmez — bekçisi
`test_gorus_isaret_degistirmez`. Ayrışma bir üstünlük iddiası değil bir
**kırılganlık işaretidir**: §3.25 ölçtü, piyasa hangi maçta haklı olduğunu
biliyor.

#### Kuşkulu marj: sonuç ona duyarlı değil

4. maçın marjı %45,8; bültenin ortancası %17,7. Uyarıyı insan yazmış, kod
da bağımsız yakalamıştı. **Veri düzeltilmedi** (belirsiz veri uydurulmaz)
ama sonucun ona duyarlılığı ölçüldü: oranlar ortanca marja ölçeklenip
kupon yeniden kurulduğunda **işaretlerin hiçbiri değişmiyor**
(P(en iyi kolon ≥ 12) %38,39 → %37,70). Yani haftanın en kuşkulu satırı
kuponu belirlemiyor.

#### Yan üründe bir sessiz hata yakalandı

`super_toto_sezon.haftalari_bul` hafta dosyalarını `hafta_*.json` ile
buluyor ve yalnızca `_kupon` sonekini eliyordu — yani **ek çıkardıkça
sessizce bozulan** bir listeydi. `hafta_02_tahmin2.json` eklenince 2. hafta
iki kez sayıldı ve arayüz beslemesi "3 hafta" yazdı. Beyaz liste yerine
kapalı bir kalıp kondu (`^hafta_(\d{2})$`); bekçi
`test_yan_kayit_hafta_sanilmaz`.

    python scripts/super_toto_tahmin2.py --hafta 2
    python scripts/super_toto_tahmin2.py --hafta 2 --yaz
    python -m spor_toto.gorus --sezon 2026_27 --hafta 2

### 3.38 2. haftanın sonucu — iki kayıt, aynı 12, üç kat ucuz

Sonuç dizisi girildi: **2 2 2 1 2 1 1 2 1 2 1 0 1 0 2** (1/0/2 = 6/2/7,
yalnızca iki beraberlik). Skor ve ikramiye ekranı bu hafta GİRİLMEDİ; ikisinin
yokluğu aşağıda kendi başlığında duruyor, çünkü ölçülemeyen şeyi ölçülmüş gibi
yazmamak bu defterin tek kuralı.

#### Ne oldu

| Kayıt | Kural · ölçek | Kolon | En iyi kolon | Kaçak |
|---|---|---:|---:|---|
| 1. Tahmin — ana | eşik · orantılı | 4.096 | **12**/15 | 7, 8, 12 |
| 1. Tahmin — bütçeli | eşik · orantılı | 2.048 | 12/15 | 7, 8, 12 |
| 1. Tahmin — kısıtlı | eşik · orantılı | 1.024 | 12/15 | 7, 8, 12 |
| 2. Tahmin — taban | hedef · shin | 1.296 | 12/15 | 7, 8, 12 |
| 2. Tahmin — **ayarlı** | hedef · shin + kalabalık | **1.296** | **12**/15 | 8, 12, 14 |
| 2. Tahmin — eşik | eşik · shin | 2.048 | 12/15 | 7, 8, 12 |

Altı planın altısı da **12**'de, yani ikramiyenin başladığı kademede kapandı.
Aralarındaki tek gerçek fark bedel: 2. Tahmin aynı sonucu **3,2 kat daha az
kolonla** aldı. §3.37 sonuçları görmeden "hem daha iyi hem 3,2 kat ucuz"
demişti; sonucun söylediği, ucuzluğun **bu hafta bedava** olduğu.

Kaçan üç maçın ikisi (8 ve 12) her planda ortak. İki kaydın **birleşimi** —
"ikisini birden oynasaydık" — 13/15 veriyor: bu hafta 14, hiçbir işaret
bileşiminde yoktu.

#### 1. ders — 12 beklenen sonuçtur, başarı değil

Bugünkü kural (hedef · shin) geçen sezonun tamamında yeniden koşuldu:

| Kural | Ort. en iyi kolon | 12+ | 13+ | 14+ | Hafta başına kolon |
|---|---:|---:|---:|---:|---:|
| **hedef** (bugünkü) | **11,81** | %67 (24/36) | %36 (13/36) | %6 (2/36) | 1.461 |
| eşik (1. Tahmin'inki) | 11,50 | %58 (21/36) | %19 (7/36) | %8 (3/36) | 1.987 |

Yani 12, bu kuralın **modal çıktısıdır**. 2. haftanın 12'si kuralın iyi
çalıştığını göstermez; kuralın normalini gösterir. Aynı tablo 1. haftanın 9'unu
da yerine oturtuyor: 9 ve altı 36 haftada 2 kez görülüyor (%6), yani alt kuyruk.
**İki hafta arasındaki 9 → 12 sıçraması bir gelişme değil, dağılımın kendisidir.**

Not: hedef kuralı bu arşiv üzerinde tasarlandı, dolayısıyla eşik kuralını burada
geçmesi **beklenen** bir sonuçtur ve kanıt sayılmaz. Okunacak sayı isabet değil,
hafta başına kolon: %26 daha ucuz.

#### 2. ders — hafta kolaydı; payı doğru yere yazmak gerekiyor

| | 1. hafta | 2. hafta | arşiv ortalaması |
|---|---:|---:|---:|
| Piyasa Brier'i | 0,6873 | **0,5526** | 0,579 |
| Favori isabeti | 6/15 (bekl. 7,77) | **9**/15 (bekl. 7,91) | — |
| En iyi kolon | 9 | 12 | 11,81 (bugünkü kural) |

2. hafta arşiv ortalamasından **daha tahmin edilebilir** geçti ve favori
beklenenden bir fazla tuttu. 12'nin bir kısmı kuponun değil, haftanın eseri.
Kural değişikliklerine fatura kesmeden önce bu satıra bakmak gerekiyor —
tersi, projenin en kolay hatası olurdu.

#### 3. ders — ölçek değişimi haftanın skorunda görünmüyor

Kupon 1. haftada `orantılı`, 2. haftada `shin` ölçeğinde donduruldu. Aynı
oranlar üç ölçekte yeniden puanlandı:

| Ölçek | 1. hafta | 2. hafta | **Birikimli (30 maç)** |
|---|---:|---:|---:|
| orantılı | 0,6777 | 0,5617 | **0,6197** |
| güç | 0,6941 | 0,5453 | 0,6197 |
| shin | 0,6873 | 0,5526 | **0,6199** |

Hafta düzeyinde sıralama **işaret değiştiriyor** (1. haftada orantılı, 2. haftada
güç önde), birikimli farksa dördüncü basamakta. A5 zaten arşivde ölçüp
"fark küçük" demişti; canlı sezon bunu doğruluyor. **2. haftanın iyi geçmesi
`shin`e yazılamaz** — ve bu, yazılması en cazip yanlıştı.

#### 4. ders — kalabalık ayarı bu hafta sıfır; karar için erken

Ayar üç maçta sembolü değiştirdi (işaret sayıları sabit, bedel aynı):

| Maç | Taban → yeni | Gerçek | Sonuç | Olasılık bedeli | Oynanma kazancı |
|---|---|---|---|---|---|
| 7 Alanyaspor – Beşiktaş | 02 → 12 | 1 | **kazandı** | −0,8 puan | −10 puan |
| 13 Real Betis – Real Sociedad | 10 → 12 | 1 | değişmedi | −2,1 puan | −13 puan |
| 14 Atlético – Villarreal | 10 → 12 | 0 | **kaybetti** | −2,3 puan | −7 puan |

Net: **+0 maç**. Ödenen 5,2 puanlık olasılık, ayarın *amacı* değil bedeliydi;
amacı bölüşme ve bölüşme bu hafta **ölçülemedi** (ikramiye ekranı yok).

Durma kuralı burada yazılıyor ki sonradan gözle seçilmesin: ayar hakkında karar,
**sembolü değişen maç sayısı 20'yi geçmeden** verilmez. Karara esas olan sayı da
ham isabet farkı değil, gözlenen isabet farkı ile olasılıklardan **beklenen**
farkın karşılaştırmasıdır (bu haftanın beklentisi −0,05 maç, gözlenen 0).

#### 5. ders — tek yanlış banko haftanın tek yapısal kaybıydı, kural yine de değişmiyor

2. Tahmin dört banko yazdı, üçü tuttu (beklenen 2,51). Batan banko 8. maçtı:
Göztepe – Gençlerbirliği, piyasa ev sahibine %60,5 veriyordu, sonuç deplasman
(%16,7). İlginç olan, bağımsız görüşün tam bu maçta piyasadan ayrışmasıydı
(DC: ev %48,8, deplasman %22,4).

Bu, bir kural fikri gibi görünüyor: *"DC piyasadan çok ayrıştığında banko
yapma."* Ölçüldü, geçmedi — DC'nin arşivdeki katkısı sıfır (§3.28), ayrışma
kademesi de öyle (§3.26). Bir maçlık acıyla kural değiştirmek, 1. haftanın
4. dersinin tekrarı olurdu. Kayıtta duruyor, kuralda durmuyor.

Aynı hafta 12. maç da (Newcastle – Liverpool, sonuç beraberlik) DC'nin
piyasadan ayrıldığı yerdeydi. Görüş karnesi yine de fark üretmiyor:

| Kaynak (DC'si olan 12 maç) | Brier | log |
|---|---:|---:|
| piyasa | 0,5839 | 0,9871 |
| Dixon-Coles | 0,5834 | 0,9874 |
| yarı yarıya harman | 0,5795 | 0,9821 |
| kalabalık | 0,6752 | 1,1462 |

12 maçta dördüncü basamak farkı hiçbir şey söylemez; satır, söylemediğini
göstermek için duruyor.

#### 6. ders — kalabalık ilk kez piyasadan ayrıldı, ve yanıldı

1. haftada halkın modal kuponu ile piyasanın favori kuponu **birebir aynıydı**.
2. haftada tek maçta ayrıştılar (5. maç, Eyüpspor – Gaziantep: halk ev,
piyasa deplasman) ve sonuç piyasayı doğruladı: halk 8/15, piyasa 9/15.
Kalabalığın Brier'i piyasadan **0,09 kötü**. Havuz ekseninin dayandığı varsayım
— *oynanma verisi yön değil, pay taşır* — iki haftada da ayakta
(bkz. `VERI_TOPLAMA_VE_ISLEME.md` §"Ölçülen ilk şey").

#### 7. ders — bu hafta ulaşılabilir değildi, ve bunun bir ölçüsü var

Bütün kolonlar olasılığa göre dizilse, gerçekleşen kolon **203.403.** sırada
(1. haftada 3.410.684.). Yani 14'ü garantilemek için ~200 bin kolon gerekirdi;
oynanan 1.296. Kalabalığa göre aynı kolon 1.657.570. sırada — halkın kuponundan
çok daha uzakta, ki ikramiyenin büyük olmasının sebebi de bu.

Bu sayı defterde kalıcı bir yer aldı (`gercegin_sirasi`), çünkü "kaçırdık mı,
yoksa ulaşılamaz mıydı" sorusunun tek dürüst cevabı bu.

#### 8. ders — atılan sembol defteri canlı sezonda da açıldı

1. haftanın 2. dersi arşivden gelmişti (567 maç: atılan beraberlik %25,8
geliyor, ev %16,0, deplasman %15,6). Canlı karşılığı artık her koşumda yazılıyor:

| Atılan sembol | Atıldı | Geldi | Gözlenen | Beklenen |
|---|---:|---:|---:|---:|
| 1 (ev) | 7 | 3 | %43 | %18 |
| 0 (beraberlik) | 13 | 5 | %38 | %23 |
| 2 (deplasman) | 10 | 1 | %10 | %19 |

30 maçta okunacak bir şey yok — kolonun varlık sebebi, birikince okunabilmesi.
Sayı **gözlenen ile beklenen arasındaki farktır**, ham oran değil.

#### Ölçülemeyenler — ve haftaya kapanacak açıklar

1. ~~**İkramiye ekranı girilmedi.**~~ **Kapandı:** tablo sonradan girildi ve
   üç ölçümü birden açtı — havuz dağılımı artık varsayım değil ölçüm, getiri
   ilk kez para birimiyle hesaplandı ve popülerlik modeli ilk sınavını verdi
   (§3.40). Kalan tek eksik, kolon bedelinin yayınlanmaması.
2. **Skorlar girilmedi.** Yalnızca 1/0/2 var; gol bazlı hiçbir ölçüm (DC'nin
   kendi kalibrasyonu dahil) bu haftadan beslenemez.
3. **Kuşkulu satır kaynağından doğrulanmadı.** 4. maçın marjı %45,8'di
   (bültenin ortancası %17,7). Duyarlılık ölçümü kaydediyor ki düzeltilmiş
   marjla **işaretler değişmiyordu** — yani bu hafta bedeli sıfır. Uyarı yine de
   açık: bedelin sıfır çıkması, verinin doğru olduğunu göstermez.
4. **Oran AÇILIŞ oranıydı.** A1 arşivde ölçtü: kapanış, açılışı 0,0025 Brier
   geçiyor ve aralık tamamen sıfırın üstünde (§3.14). Bülten snapshot'ı zaten
   haftada bir alınıyor ama **pazartesi** alınıyor; kupon cuma kapanıyor.
   Kapanışa yakın ikinci bir snapshot, bu projede ölçülmüş en ucuz iyileştirme.

#### Ne değişti, ne değişmedi

**Değişti:** sonuç dizisi girildi; `super_toto_degerlendir.py` ikinci kaydı da
puanlıyor ve altı yeni ölçü yazıyor (iki kaydın kıyası ve birleşimi, ayar
karnesi, atılan sembol defteri, görüş karnesi, ölçek karnesi, gerçeğin sırası);
sezon defteri atılan sembolleri birikimli tutuyor ve ikramiye kademesine ulaşan
haftaları sayıyor. Arayüzde 2. Tahmin paneli artık sonucu **görüyor**: maç
tablosunda gerçek sembol ve ✓/✗, ayar tablosunda maç maç "kazandı / kaybetti /
değişmedi". Panel bunu `hafta.results`ten okuyor — daha önce
`tahmin2.results_known`ten okunuyordu ve o alan tanım gereği hep `false`
olduğu için panel sonuç gelse de **"sonuç bekleniyor"** yazıyordu.

**Değişmedi:** kural. Ne eşik, ne kayıp oranı, ne banko davranışı. İki haftalık
canlı veri, aranan büyüklükteki bir farkı ayırt etmekten **286 kat** uzakta
(sezon defterinin yeterlilik notu her koşumda bunu yazıyor).

#### Yan üründe üç sessiz hata yakalandı

Sonucun girilmesi, "sonuç hiç gelmeyecek" varsayan üç yeri birden aydınlattı:

1. **Hafta raporu sayfası çöktü.** `super_toto_sayfa.py` sonucu olan haftada
   ikramiye tablosunun da olduğunu varsayıyordu (`ikramiye["tiers"]` →
   `KeyError`). Dahası, kendi başlığında *"bu dosyada elle yazılmış tek bir
   ölçüm yoktur"* yazarken üç cümlesi 1. haftaya sabitlenmişti: ikramiye
   kademesine ulaşılamadığı, kalabalığın kuponunun piyasayla **birebir aynı**
   olduğu ve 14 bilenin kişi başı ödülü (`2.153.527,18` sayı olarak gövdede).
   Üçü de 2. haftada yanlıştı. Hepsi hesaba bağlandı. Betik `check.sh`
   kapısında hiç koşmuyordu — şimdi her girilmiş hafta için koşuyor, bekçisi
   `test_sayfa_her_girilmis_haftada_uretilir`.
2. **2. Tahmin paneli "sonuç bekleniyor"da donmuştu.** Rozet
   `tahmin2.results_known`ten okunuyordu; o alan kaydın donduğu anı anlatır ve
   **tanım gereği hep `false`tur**. Panel artık `hafta.results`e bakıyor ve
   hafta kapandığında sonuç sütununu açıyor.
3. **İki bekçi haftanın hiç sonuçlanmayacağını varsayıyordu.**
   `test_diskteki_kayit_bayat_degil` taze gövdeyle diskteki kaydı birebir
   karşılaştırıyordu; sonuç girilince taze gövde doğru şekilde
   `results_known: true` demeye başladı ve **doğru davranış testi kırdı**.
   Alan kıyastan çıkarıldı, "kayıt sonuçlar görülmeden donduruldu" iddiası ise
   artık **diskteki dosyadan** doğrulanıyor (aynı düzeltme `check.sh`te de var).

Kalıp üçünde de aynı: *bugünkü durumu kalıcı sanmak.* Sonuç girmek, bu
varsayımı yapan her satırı bir kerede görünür kılıyor.

    python scripts/super_toto_degerlendir.py --hafta 2
    python scripts/super_toto_sezon.py

### 3.39 15 bilen kupon — şekil değil, altı sembol

2. haftanın 15 bilen kuponu kayda geçti (`hafta_02_kupon.json` → `referans`).
Kupon **bize ait değil**, kuralın ürünü de değil; ayrı bir başlıkta, kaynağıyla
durur. Sorusu tek: *bu kuponu bizimkinden ayıran şey neydi — bütçe mi, şekil mi,
işaret seçimi mi?*

    2  12 12 1  02 10 12 12 12 02 12 02 10 10 02      2 banko + 13 çifte

#### Önce oynanma biçimi, çünkü puanı o belirliyor

| Kupon | Sistem | Kolon | P(15) | P(≥14) | P(≥13) | P(≥12) | Kalabalık oranı | Gerçek |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **15 bilen** | tam | 8.192 | %1,13 | %7,09 | %21,64 | %43,57 | 0,81 | **15**/15 |
| 1. Tahmin ana | fix16 | 4.096 | %0,34 | %2,64 | %13,65 | %34,87 | 0,72 | 12/15 |
| 2. Tahmin ayarlı | fix16 | 1.296 | %0,34 | %2,76 | %14,85 | %38,39 | 0,81 | 12/15 |

İki sütun **sistemden** okunur ve bu ayrım kozmetik değil: 16 satırlık kaplama
seçim uzayının bir dilimini oynar, küme içinde kalmak **14** demektir; tam sistem
uzayın tamamını oynar, küme içinde kalmak **15** demektir.

Bunun doğrudan sonucu: **aynı işaretler 16 satırda 1.024 kolon eder ve 14 verirdi.**
Yani 15'i satın alan şey işaret seçimi değil, kalan 7.168 kolonluk **tam
kapsamadır**. Bu kupon 14'ü sekizde bir fiyata alabilirdi; 15 için sekiz katını
ödedi ve bu hafta karşılığını aldı.

Ölçüde ters bir yer daha var: **P(15) kolon başına** bizim planımızda daha yüksek
(2,6×10⁻⁶ ↔ 1,4×10⁻⁶). Kupon mutlak olasılığı 3,3 kat büyüttü, bedeli 6,3 kat
büyüterek. Hangisinin doğru olduğu bütçeye ve ikramiye yapısına bağlıdır —
15 devreden bir jackpot iken mutlak olasılık, 12-13 hedeflenirken kolon başına
verim okunur. **Bu bir tercih farkı, hata değil.**

#### Asıl fark: azami kapsamadan altı sapma

Mekanik referans, her maçta en olası `k` sembolü işaretlemektir; kuralımız da
tam olarak bunu yapar. Kupon bu seçimden **altı maçta** saptı ve toplam
**19,6 puan** kapsama verdi:

| # | Maç | İşaret | Azami | Gerçek | Sonuç |
|---:|---|---|---|---|---|
| 5 | Eyüpspor – Gaziantep | 02 | 12 | 2 | fark etmedi |
| 6 | Trabzonspor – Başakşehir | 10 | 12 | 1 | fark etmedi |
| 7 | Alanyaspor – Beşiktaş | 12 | 02 | 1 | **kazandı** |
| 8 | Göztepe – Gençlerbirliği | 12 | 10 | 2 | **kazandı** |
| 11 | Marsilya – Strasbourg | 12 | 10 | 1 | fark etmedi |
| 12 | Newcastle – Liverpool | 02 | 12 | 0 | **kazandı** |

Kazanan üç sapma, **bizim bütün planlarımızı bozan üç maçın ta kendisi**
(§3.38: 7, 8 ve 12).

Ve kritik karşı-olgusal: **aynı şeklin azami kapsama sürümü 12/15 alıyor** —
bizim aldığımız sayının aynısı — üstelik küme-içi olasılığı daha yüksekken
(%1,47 ↔ %1,13). Yani 8.192 kolon, 13 çifte ve tam sistem tek başına 12
veriyor. **Farkı yapan şey şekil ya da bütçe değil, altı sembol.**

#### Görüş mü, şans mı — ve niçin bir hafta ayıramaz

Defterin karar sayısı bir özdeşlikten geliyor:

> Bir sapmanın piyasa altındaki beklenen neti **tanım gereği eksi kapsama
> bedelidir** (`P(tuttuğu) − P(attığı) = −(kapsama bedeli)`).

Yani piyasanın olasılıklarına göre sapmak **her zaman** negatif beklenen
değerlidir; sapmak ancak piyasadan **başka bir görüş** varsa mantıklıdır.
Bu kuponun altı sapmasında:

| | Gözlenen | Piyasanın beklediği |
|---|---:|---:|
| Kazanç | 3 | 1,37 |
| Kayıp | **0** | 1,56 |
| Net | **+3** | −0,20 |

Piyasanın kendi olasılıklarıyla bu kadar iyi ya da daha iyi bir netin olasılığı
**%5,6** — yaklaşık 18'de 1. Küçük, ama imkânsız değil ve **tek kupon görüşü
şanstan ayıramaz**: 1. haftanın ikramiye tablosunda 12 bilen 2.859 kişiydi, yani
havuzda on binlerce kupon var; 18'de 1'lik bir olayın birilerinin başına gelmesi
beklenendir. Ayrım ancak **aynı oyuncunun** sapma defteri hafta hafta birikirse
yapılabilir; ölçü hazır (`sapma_defteri`), durma kuralı §3.38'dekiyle aynı:
**20 sapma birikmeden karar yok.**

Bağımsız görüşümüz (Dixon-Coles) bu üç sapmanın **ikisini** destekliyordu:
8. maçta deplasmana piyasadan fazla pay veriyordu (%22,4 ↔ %16,7), 7. maçta ev
sahibine (%27,5 ↔ %23,5). Üçüncüsünde (12. maç) desteklemiyordu — DC ev
sahibini piyasadan **yüksek** görüyordu (%37,9 ↔ %25,8), oysa kupon tam da onu
attı. İki-bir, n = 3: hiçbir şey.

#### Ne öğrendik, ne değişti

**Değişmedi:** kural. Bu kuponun ölçülen üstünlüğü altı sembolde ve o
üstünlüğün bilgi mi şans mı olduğu **ölçülemedi**. Bir haftanın kazananına
bakarak kural değiştirmek, geçen sezonun hold-out'unun zaten ölçtüğü hatadır.

**Değişti — ölçü tarafı.** Değerlendirme koşumu artık:

- kuponları **oynanma biçimiyle** puanlıyor (`sistem: fix16 | tam`); aynı
  işaretler iki biçimde farklı puan alır ve tablo bunu ayrı sütunda yazar,
- **oynanan kolonların** toplam olasılığını (P(15)) hesaplıyor — küme-içi
  olasılıkla karıştırılan sayı buydu,
- **azami kapsamadan sapmaları** defter tutuyor: nerede, ne pahasına, ödedi mi,
  ve piyasanın aynı sapmalara verdiği olasılık ne,
- kupon dosyasına kaydedilen **dış kuponları** (kullanıcının kendi kuponu, o
  haftanın 15 bileni) aynı gövdeyle ölçüyor ve iki karşı-olgusalı yanına
  koyuyor: *aynı işaretler öteki sistemde* ve *aynı şekil, mekanik sembollerle*.

Bu dört ölçü olmadan aynı kupon şöyle okunurdu: "8.192 kolon oynamış, 15
bilmiş." Ölçülerle okunuşu şu: *"1.024 kolonluk bir işaret setini sekiz katına
tam sistem oynamış; şekli bize göre daha zayıf (küme-içi %1,13 ↔ %2,76), farkı
altı sapmada yapmış ve o sapmaların piyasa altındaki beklentisi negatifti."*

    python scripts/super_toto_degerlendir.py --hafta 2

### 3.40 İkramiye tablosu — projenin ilk ölçülmüş parası

2. haftanın ikramiye ekranı girildi ve üç ayrı yerde "varsayım" yazan satırı
birden ölçüme çevirdi.

| Kademe | Kazanan kolon | Kolon başına | Kademe havuzu |
|---|---:|---:|---:|
| 15 | 3 | 24.330.749,43 TL | 72.992.248,29 TL |
| 14 | 121 | 202.327,59 TL | 24.481.638,39 TL |
| 13 | 2.077 | 11.787,01 TL | 24.481.619,77 TL |
| 12 | 21.272 | 1.438,60 TL | 30.601.899,20 TL |

#### 1. Havuz dağılımı artık varsayım değil

15 kademesinin havuzu 1. haftadan devreden **30.149.380,57 TL**'yi içeriyor;
haftanın kendi payı 42.842.867,72 TL. Devir çıkarıldığında iki hafta da
**kuruşuna kadar aynı** oranı veriyor:

| | 15 | 14 | 13 | 12 |
|---|---:|---:|---:|---:|
| 1. hafta | 30.149.380,57 | 17.228.217,44 | 17.228.217,30 | 21.535.245,96 |
| 2. hafta | 42.842.867,72 | 24.481.638,39 | 24.481.619,77 | 30.601.899,20 |
| 14'e oranı | **1,7500** | **1,0000** | **1,0000** | **1,2500** |

Yani dağıtılan havuzun **%35 / %20 / %20 / %25**'i. `spor_toto/getiri.py`
başlığında şu yazıyordu: *"Havuzun kademelere dağılımı. **Varsayım, ölçüm
değil**… elde henüz bir haftalık kayıt var."* Artık iki hafta var ve ikisi
aynı; sabit ölçümden türetiliyor (`OLCULEN_PAY`, `PAY_KAYNAGI`).

Değişim küçük değil: modülün kademeleri (14-13-12) için pay dağılımı
`0,55 / 0,25 / 0,20` varsayımından **`0,31 / 0,31 / 0,38` ölçümüne** geçti.
14'ün ağırlığı neredeyse yarıya indi — yani müşterek beklenen değer hesabı
bugüne kadar 14'ü sistematik olarak **fazla** ödüllendiriyordu.

**Kalkmayan varsayım:** havuzun kendisi ve komisyon. İkisi de satış cirosundan
gelir ve ciro hiçbir ekranda yayınlanmıyor.

#### 2. Gerçekleşen getiri — ilk kez ölçüm, ilk kez acı

| Kupon | Sistem | Kolon | Kazanan kolonlar | Gerçekleşen | Başabaş kolon bedeli |
|---|---|---:|---|---:|---:|
| 15 bilen | tam | 8.192 | 15:1 · 14:13 · 13:78 · 12:286 | **28.291.834,48 TL** | 3.453,59 TL |
| ↳ aynı işaret, fix16 | fix16 | 1.024 | 14:1 · 13:9 · 12:37 | 361.638,88 TL | 353,16 TL |
| 1. Tahmin ana | fix16 | 4.096 | 12:4 | 5.754,40 TL | 1,40 TL |
| 2. Tahmin ayarlı | fix16 | 1.296 | 12:1 | 1.438,60 TL | **1,11 TL** |

Kolon bedeli hiçbir ekranda yayınlanmadığı için sayı mutlak değil **başabaş
fiyat** olarak okunur: kolon 1,11 TL'nin üstündeyse 2. Tahmin bu haftayı
zararla kapattı.

Tablo aynı zamanda §3.39'un cümlesini paraya çeviriyor: aynı işaretler
kaplamada **361.638,88 TL** kazanıyordu — 15'i satın alan 7.168 fazladan
kolon, bu hafta **27,9 milyon TL** getirdi.

Ve bir yan bulgu: 15 bilen kuponun tek bileti haftanın kazanan kolonlarının
**378'ini** tek başına üretti — 14 kademesindeki 121 kolonun **13'ü** onun.
Yani kendi 14 kademesini kendi kolonlarıyla seyreltti; ve ikramiye tablosundaki
"kişi" sütunu **kişi değil kolon** sayıyor.

#### 3. Sistem seçimi getiriyi değiştirmiyor, dağılımını değiştiriyor

Aynı ödül vektörü sabit tutulup **beklenen** getiri hesaplandığında
(`E[k tutturan kolon sayısı] × ödül(k)`):

| Kupon | Sistem | Kolon başına beklenen |
|---|---|---:|
| 2. Tahmin taban | fix16 | **93,69 TL** |
| 2. Tahmin ayarlı | fix16 | 87,35 TL |
| 15 bilen kupon | tam | 46,88 TL |
| ↳ aynı işaret, fix16 | fix16 | 46,16 TL |
| 1. Tahmin ana | fix16 | 28,61 TL |

İki satır bir arada okunur: **aynı işaretler iki sistemde kolon başına aynı
beklentiyi veriyor** (46,88 ↔ 46,16). Getiri kolon başına doğrusaldır, çünkü
her kolonun beklentisi yalnız kendi olasılık profiline bağlıdır. Dolayısıyla
tam sistem **üstünlük satın almaz, varyans satın alır**: aynı beklenen getiriyi
P(15) %0,14 yerine %1,13'e taşıyarak dağıtır. "Tam sistem mi oynasak"
tartışmasının cevabı budur ve bir tercih sorusudur — jackpot devrediyorsa
mutlak olasılık, 12-13 hedefleniyorsa kolon başına verim okunur.

İkinci okuma: **bizim işaretlerimiz kolon başına iki kat verimliydi**
(93,69 ↔ 46,88). 15 bilen kupon mutlak olasılığı hacimle büyüttü, biz
seçimle. Bu hafta hacim kazandı.

#### 4. B2'nin ilk cevabı: kalabalık modeli şekli tutturuyor, seviyeyi tutturmuyor

`VERI_TOPLAMA_VE_ISLEME.md` §B2 testi şuydu: *oynanma payı + gerçekleşen sonuç,
kazanan adetlerini önceden söyleyebilmelidir.* Her kademe bir **havuz kolonu
sayısı** (`N = kazanan ÷ P(k)`) ima eder; model doğruysa dört kademe aynı `N`'i
vermelidir.

| Kademe | Kazanan | N (kalabalık modeli) | N (piyasa modeli) |
|---|---:|---:|---:|
| 15 | 3 | 43.909.132 | 4.026.700 |
| 14 | 121 | 41.576.033 | 5.940.957 |
| 13 | 2.077 | 38.869.889 | 8.294.143 |
| 12 | 21.272 | 37.813.010 | 11.582.204 |

**Kalabalık modelinin dört kademesi birbirinin %16'sı içinde**
(ortalamanın ±%8'i), üstelik üç büyüklük mertebesi boyunca. Piyasa modeli
2,9 kat sapıyor. Şekil ölçüsünde
oynanma payları açık ara önde ve bu, havuz ekseninin ilk olumlu kanıtı.

**Seviye ölçüsünde ikisi de yanlış.** 1. hafta 5,2–7,5 milyon kolon ima
ediyordu, 2. hafta 37,8–43,9 milyon: 6 kat. Oysa dağıtılan havuz
86.141.061 → 122.408.025 TL, yani **1,42 kat** büyüdü. Havuz altı kat
büyümediğine göre modelin seviyesi yanlış.

Sebebi ölçülebilir: **kazanan sayıları kişi değil kolon.** Oynanma yüzdeleri
BİLET başına ölçülüyor, havuz KOLON başına bölünüyor ve sistem kuponları
ikisini sistematik olarak ayırıyor — tek bir bilet 378 kazanan kolon üretti.
Bağımsız-kolon modeli bu yığılmayı üretemez.

Sonuç, §6.3b'nin durma kuralını değiştirmiyor ama okumasını daraltıyor:
**kalabalık oranı planlar arası göreli bir ölçüdür**, kaç kişiyle
bölüşüleceğinin tahmini değildir.

#### 5. Ne değişti

**Ölçü tarafı.** `super_toto_degerlendir.py` üç yeni gövde kazandı:
`oynanan_kolon_listesi` (kolonların kendisi), `getiri_karnesi` (gerçekleşen +
beklenen + başabaş fiyat) ve `havuz_karnesi` (kademe havuzu + iki modelin ima
ettiği `N`). `spor_toto/getiri.py` ölçülmüş pay dağılımını taşıyor.

**Kural.** Değişmedi. Kolon başına beklenen getiri bizim planımızda daha
yüksek çıktı ama bu, ödül vektörü sabit tutulmuş **tek** bir haftadır.

#### Yan üründe dördüncü sessiz varsayım

2. Tahmin kaydının havuz bloğu eski pay varsayımıyla hesaplanmıştı. Kayıt
**kendi varsayımını yazdığı** için (`varsayimlar.pay_dagilimi`) okunabilir
kalıyor; bayatlık bekçisi artık şunu yapıyor: kaydın yazdığı varsayım bugünküyle
aynı değilse blok kıyastan çıkar, ama **varsayımın yazılı olduğu** ayrıca
doğrulanır. Varsayımını yazmayan bir kayıt bayat değil, izlenemezdir.

    python scripts/super_toto_degerlendir.py --hafta 2

### 3.41 Model Arena ve ileri yürüyüş — on bir ölçüm, ilk kez tek tabloda

Bu bölümün kaynağı bir dış incelemedir
([`DIS_INCELEME_AZ_RAPORU.md`](DIS_INCELEME_AZ_RAPORU.md)). Rapor 64 bölümde
öneri sıraladı; çoğunun karşılığı zaten depodaydı, **üçü gerçekten eksikti**
ve üçü de burada ölçüldü.

#### Eksiğin kendisi: sayılar kıyaslanabilir değildi

§3.26–§3.35 arasında on bir ölçüm koşumu var ve her biri **kendi modülünde
kendi tablosunu** yazıyor. Bu tabloların sayıları doğrudan kıyaslanamıyordu:
kesitleri farklı (`cizgi` açılış+kapanış çifti ister, `bahisci` bahisçi
dörtlüsü), gruplamaları farklı, bir kısmı farklı marj arındırma çevriminde
ölçüldü — §3.18'in ölçek uyarısı tam olarak bunun izidir.

Yani *"Elo geçmedi"* ile *"Dixon-Coles geçmedi"* aynı cinsten iki cümle
değildi. `arena.py` bunu düzeltir: **aynı haftalar, aynı gruplama, aynı
bootstrap tohumu, aynı referans.**

    python -m spor_toto.arena              # sezon disarida birakmali
    python -m spor_toto.arena --ileri      # kronolojik
    python -m spor_toto.arena --kupon      # kupon setinde

#### Birinci ölçüm — arena, tam korpus

183 hafta · 31.103 maç · 10 aile · sezon dışarıda bırakmalı · referans
`piyasa`:

| tahminci | Brier | log | ΔBrier | %95 aralık | geçti |
|---|---:|---:|---:|---:|---|
| `yigin` | 0,5935 | 0,9935 | −0,0001 | [−0,0004, +0,0002] | hayır |
| **`piyasa`** | **0,5936** | **0,9938** | — | — | — |
| `izotonik` | 0,5936 | 0,9939 | +0,0000 | [−0,0002, +0,0002] | hayır |
| `beraberlik_bant` | 0,5936 | 0,9938 | −0,0000 | [−0,0001, +0,0001] | hayır |
| `venn_abers` | 0,5939 | 0,9943 | +0,0003 | [−0,0001, +0,0006] | hayır |
| `kalibre_etkilesim_favori` | 0,5941 | 0,9945 | +0,0005 | [+0,0001, +0,0009] | hayır |
| `agac` | 0,5941 | 0,9945 | +0,0005 | [+0,0001, +0,0008] | hayır |
| `dixon_coles` | 0,6160 | 1,0297 | +0,0224 | [+0,0191, +0,0262] | hayır |
| `sezon_sabiti` | 0,6506 | 1,0752 | +0,0570 | [+0,0540, +0,0601] | hayır |
| `duzgun` | 0,6667 | 1,0986 | +0,0730 | [+0,0695, +0,0768] | hayır |

**Hiçbir aile geçmedi.** En yakın olan `yigin`'in aralığı sıfırı kesiyor.
Bu, §5.1'in sonucunun tekrarı değil — ilk kez **kıyaslanabilir** hâlidir.

#### İkinci ölçüm — ileri yürüyüş, ve bu yeni

Dışarıda bırakmalı ölçüm bir şeyi ölçmüyordu: **zamanı.** 2021/22 ölçülürken
model 2022/23, 2023/24 ve 2024/25'te eğitiliyordu — geleceği gören bir
ölçüm. Bu onu geçersiz kılmaz (soru *"bu sinyal veride var mı?"* ise doğru
araç odur) ama ürünün kendi sorusunu cevapsız bırakır: *o hafta, yalnızca o
güne kadar bilinenle, ne kadar iyi tahmin edebilirdik?*

`evaluate.ileri_yuruyus` bunu sorar: gruplar kronolojik dizilir ve `k`. grup
ölçülürken eğitim yalnızca `0..k-1`dir. İlk grup ölçülemez (eğitim seti boş
olurdu) ve **adı yazılır** — 2021/22 düşer, kesit 138 haftaya iner.

Aşağıdaki iki sütun **birebir aynı 138 haftada** ölçüldü; değişen tek şey
her katın eğitim setidir. (Kesitleri eşitlemek şart: arenanın 183 haftalık
tablosuyla kıyaslamak, kronolojiyi örneklem farkıyla karıştırmak olurdu.)

| aile | dışarıda bırakmalı | ileri yürüyüş | değişim |
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
çalışır ve oranı hiç okumaz — yerinde durması bu okumayla tutarlı.

> **Bulgu.** §3.26–§3.35'te ölçülen küçük kazançların bir kısmı sinyal
> değil, **kronoloji dışı eğitimin** eseriydi. Ürünün gerçek kuralı
> uygulandığında fark kapanmıyor, **açılıyor.**

Bu §5.1'i zayıflatmıyor, sertleştiriyor. Faz A'nın (b) ile kapanışına
(§6.2 A4) üçüncü bir kanıt daha ekliyor ve bu kez kanıt bir modelin
başarısızlığı değil, **ölçüm kuralının kendisi**.

İki kipin Brier'i doğrudan kıyaslanmaz ve `arena` bunu çıktısında yazar:
ileri yürüyüşte son grup dışında hiçbir ölçüm bütün veriyi görmez, yani
Brier sistematik olarak kötüdür. Kıyaslanan şey her kipin **kendi
içindeki** aday–referans farkıdır.

#### Yan ürün — çökme tespiti

Arena kupon kesitinde koşturulunca dört satır *"ölçtük, fark yok"* gibi
görünen bir sayı yazdı (`izotonik` +0,0000, `yigin` +0,0000, `dixon_coles`
düzgünle aynı). Dördü de ölçüm değildi: tahmincilerin çoğu eğitilemediğinde
**sessizce bir tabana düşer** — `yigin` üst-öğrenici kurulamazsa ilk
tabanına, `beraberlik` yeterli nokta yoksa piyasayı olduğu gibi geçirir,
`dixon_coles` takım eşleşemezse düzgüne. Her biri kendi yerinde doğru bir
karardır (uydurma katsayı üretmektense bilinen görüşü taşımak) ama arenada
bedeli var.

`arena.cokme` bunu haftalık skor vektöründen yakalar — bir aday kesitteki
**her** haftada bir zeminle aynı Brier ve log kaybını veriyorsa o zeminin
kendisidir — ve satırı `↳piyasa` diye işaretler.

#### Üçüncü eksik — sızıntı sözleşmesi

Sızıntı denetimleri vardı (`test_arama.py`, `test_recalibrate.py`,
`test_egitim.py`, `test_elo.py`) ve hiçbiri kaldırılmadı. Eksik olan bir
**sözleşme**ydi: yeni bir tahminci eklendiğinde onu kimse otomatik
denetlemiyordu. `tests/test_sizinti.py` (14 test) ve
`health.sizinti_sozlesmesi` (26. değişmez) bunu yazıya döküyor.

Bu kontrolün kovaladığı hata **ters yönlüdür**: sızan bir model *daha iyi*
skor verir, yani hata gibi değil **başarı gibi** görünür. Sağlık katmanına
girmesinin sebebi budur.

Yazarken iki gerçek kusur çıktı:

1. **İlk kronoloji denetimi boştu** — iddiayı denetlenecek setin kendisinden
   türetiyordu ve her zaman doğruydu. Bekçilik testi yakaladı.
2. **Katman ayrımı bekçisi iki yönden de yanlıştı** — kaynakta `"egitim"`
   dizgesi aranıyordu. Yanlış pozitif: "eğitim seti" sıradan bir Türkçe
   ifadedir. Yanlış negatif: `importlib` ile ya da korpus dosyasını doğrudan
   açarak yapılan okumayı kaçırırdı. Denetim artık **import düzeyinde**
   (AST) ve gövdenin tamamını geziyor — tembel import de yakalanıyor.

#### Kesit künyesi

Koşumlar `python -m spor_toto.arena --kaydet` ile koşum defterine yazıldı:
korpus `sha256 949aee9f…`, 31.104 satır · bootstrap tohumu 20260817, 2.000
tekrar · `numpy` 2.4.6, `scipy` 1.17.1, `lightgbm` 4.7.0.

### 3.42 xG (Faz 3.5) — kaynak açıldı, soru kapanmadı

§3.36 xG'yi *erişim* gerekçesiyle kapatmıştı: Understat `robots.txt`'i
`Disallow: /` diyor, fbref Cloudflare arkasında. O gerekçe artık ayakta
değil. `hudl/open-data` (eski adıyla `statsbomb/open-data`) olay düzeyi
futbol verisini serbestçe yayımlıyor — 4.235 maç için `events/`, her şutta
`shot.statsbomb_xg`, üstüne 12 oyuncu konumlu `freeze_frame`.

Bu bölüm o kaynağın **ne verdiğini ve ne vermediğini** ölçüyor.

#### Önce kapsama — ve hayal kırıklığı

Depo 80 lig-sezon taşıyor (3.961 maç) ve her biri tek tek sayıldı. Korpus
penceresiyle (2122–2425) kesişim:

| Lig-sezon | Maç | Not |
|---|---:|---|
| Ligue 1 2021/22 | 26 | yalnız PSG |
| Ligue 1 2022/23 | 32 | yalnız PSG |
| Bundesliga 2023/24 | 34 | yalnız Leverkusen |
| **Toplam** | **92** | 31.103 maçlık korpusun **%0,3'ü** |

**Süper Lig yok. Alt İngiliz ligleri (E1/E2/E3/EC) yok** — oysa korpusun
çoğunluğu onlardan geliyor, ve kupon maçları T1'den. Üstelik canlı akış da
yok: veri maçlardan yıllar sonra yayımlanıyor.

Yani §3.36'nın satırının **ikinci yarısı tek başına yetiyor** ve
`TURETILEMEYEN["xg"]` yerinde kaldı. Bir kaynağın açılması sorunun çözülmesi
demek değildi.

#### Sonra: kaynağın gerçekten verdiği şey

Buna karşılık dört lig-sezon **eksiksiz** — tek takıma indirgenmemiş:
Premier League, La Liga, Serie A ve Ligue 1'in 2015/16'sı, toplam **1.517
maç.** Ve aynı maçların 1X2 oranı ile şut sayımı football-data.co.uk'nin
`mmz4281/1516/` klasöründe, `build_egitim.py`'nin zaten okuduğu şemayla
duruyor.

Bu kesit bir **girdi** değil ama bir **referans**: korpusun kendi
`sut`/`isabet` sayımı ile gerçek xG'yi aynı maçta yan yana veriyor.

#### Eşleme — ve beklenmedik bir sağlama

Eşleme ada göre yapılmadı (StatsBomb "Sporting Gijón" der, football-data
"Sp Gijon"); birincil anahtar **(lig, tarih ±1 gün, skor)**, ad benzerliği
yalnızca çakışma çözücü. Sonuç: **1.517/1.517 = %100**, sıfır eşleşmeyen.

Sağlama bunun yanında çıktı ve daha ilginç. İki kaynak şutları **bağımsız**
sayıyor (farklı tanımlar, farklı gözlemciler). Maç başına ortalama fark:

    StatsBomb şut sayısı − football-data (HS+AS) = −0,007

Yani maç başına yüzde birden az şut. Bu, eşlemenin doğruluğunun bağımsız bir
kanıtı: yanlış eşleşmiş maçlar olsaydı fark sıfırın etrafında toplanmazdı.

#### Kalibrasyon

    xg ≈ a·isabet + b·(sut − isabet) + c

Ev ve deplasman ayrı uydurulur; penaltılar (xG'si ~0,79 sabit) regresyona
girmez.

| Yan | isabet | isabetsiz | sabit | R² | artık ss |
|---|---:|---:|---:|---:|---:|
| ev | 0,1670 | 0,0497 | +0,0428 | 0,514 | 0,487 |
| dep | 0,1666 | 0,0558 | −0,0426 | 0,485 | 0,456 |

İki sayı okunmaya değer. **İsabetli şut, isabetsizin ~3,2 katı** — kaba
sayımı ağırlıksız toplamanın neden bilgi kaybettiğini doğrudan gösteriyor.
Ve **ev/deplasman katsayıları neredeyse aynı** (0,1670 ↔ 0,1666): ev
avantajı şutun *kalitesinde* değil *sayısında*; ayrı uydurmak gerekmiyormuş
gibi görünüyor ama bu ancak ölçüldükten sonra söylenebilirdi.

Sabitler ayrışıyor (+0,043 ↔ −0,043) ve deplasmanınki negatif — bu yüzden
`xg_vekili` sıfıra kırpar; beklenen gol tanım gereği negatif olamaz ve
kırpmanın yerinde durduğunu `health.py` `xg_kalibrasyonu` kontrolü
denetliyor.

#### Katsayı lige ne kadar duyarlı

Dört ligden her biri sırayla dışarıda bırakıldı:

| Dışarıdaki lig | ev katsayısı | dep katsayısı | dışarıda RMSE (ev / dep) |
|---|---:|---:|---:|
| E0 | 0,1738 | 0,1702 | 0,460 / 0,445 |
| F1 | 0,1596 | 0,1699 | 0,507 / 0,499 |
| I1 | 0,1736 | 0,1648 | 0,453 / 0,404 |
| SP1 | 0,1605 | 0,1617 | 0,545 / 0,488 |

İsabet katsayısı **0,160–0,174** aralığında kalıyor — %9'luk bir yayılma.
Dördün birbirine benzediğini biliyoruz; **beşinci bir ligde ne yapacağını
bilmiyoruz** ve bu sınır kayda geçmelidir. Korpus 22 lig taşıyor ve on
sekizinde bu katsayı denenmemiş bir varsayımdır.

#### Ölçüm — ve serinin on ikinci "hayır"ı

Vekil `egitim._zenginlestirilmis_korpus`a `_xg` olarak girdi ve
`recalibrate.KADEMELER`e `derbi` ile `etkilesim` arasında bir basamak
eklendi. Şekil **bilerek** `form_isabet_farki` ile aynı: aynı 5 maçlık
yuvarlanan pencere, aynı simetrik kaydırma, tek fark birim — ham isabetli
şut sayısı yerine kalibre edilmiş beklenen gol. Pencere ya da şekil de
değişseydi, aradaki farkın kalibrasyondan mı şekilden mi geldiğini
söyleyemezdik (`xg.XG_PENCERE == egitim.FORM_PENCERE`, bekçisi
`test_xg.py::test_pencere_form_penceresiyle_ayni`).

**Önce sütunun gerçekten dolu olduğu doğrulandı.** `derbi` bir kez tam bu
tuzağa düşmüştü: özellik korpusta vardı, tasarım matrisinde sütun vardı,
arada duran sözlük beyaz listesi taşımıyordu ve katsayı **tam 0,000000**
çıkıp *"derbi bir şey söylemiyor"* diye okunacaktı. Aynı tuzak burada da
kurulu (`test_xg.py::test_xg_tasarima_ulasiyor`) ve uydurulan katsayı:

| Basamak | Sütun | Uydurulan katsayı |
|---|---:|---:|
| `derbi` | 47 | +0,0990 |
| **`xg`** | **48** | **+0,0845** |

Yani model bu sütuna **yaslanmak istiyor** ve işareti beklenen yönde
(pozitif = ev lehine). Sütun düşmüş değil; ölçülen şey gerçekten xG'nin
kendisi.

**Sonra dışarıda bırakmalı ölçüm.** Arena ile aynı kesit, aynı gruplama
(sezon dışarıda bırakmalı), aynı referans — 183 hafta · 31.103 maç:

| tahminci | Brier | ΔBrier | %95 aralık | geçti |
|---|---:|---:|---:|---|
| **`piyasa`** | **0,5936** | — | — | — |
| `kalibre_form` | 0,5937 | +0,0000 | [−0,0003, +0,0004] | hayır |
| `kalibre_seri` | 0,5938 | +0,0001 | [−0,0002, +0,0005] | hayır |
| `kalibre_derbi` | 0,5938 | +0,0002 | [−0,0002, +0,0005] | hayır |
| **`kalibre_xg`** | **0,5938** | **+0,0002** | **[−0,0002, +0,0005]** | **hayır** |

`derbi` ile `xg` dört haneye kadar **aynı.** Basamak, kendinden öncekinin
üstüne ölçülebilir hiçbir şey koymuyor.

Arena tablosu da (§3.41) **rakam rakam değişmedi**: yeni sütun `kademe`
ailesinin temsilcisine (`kalibre_etkilesim_favori`) ekleniyor ve o satır
hâlâ 0,5941 · +0,0005 · [+0,0001, +0,0009]. Bir özellik eklemenin en dürüst
sonucu budur — tabloyu kıpırdatmaması.

#### Ne öğrenildi

İki cümle, ve ikincisi birincisinden daha önemli:

1. **Şut kalitesi piyasada zaten fiyatlanmış.** Katsayı sıfır değil (model
   onu istiyor) ama dışarıda bırakmalı katkısı sıfır — §3.14'ün kapanış
   çizgisi için, §3.16'nın yorgunluk vekili için söylediğinin aynısı.
2. **Bu cevap ilk kez ÖLÇÜLDÜ.** §3.36 xG'yi *"kaynak kapalı"* diye
   kaydetmişti; o cümle "denenmedi"nin kibar hâliydi. Artık denendi.
   `TURETILEMEYEN` ile `TURETILEBILIR_OLDU` arasındaki fark tam olarak
   budur ve `disari.py` ikisini ayrı anahtarlarda tutuyor: `xg` hâlâ
   türetilemez (kapsama), `xg_vekili` türetilebilir oldu (kalibrasyon).

Ve bir sınır, kayda geçmesi gereken: katsayı dört ligde uyduruldu, korpus
yirmi iki lig taşıyor. Kalan on sekizinde bu vekil **denenmemiş bir
varsayımdır** — ölçülen şey "xG işe yaramıyor" değil, *"dört Batı Avrupa
liginde uydurulmuş bir xG vekili, yirmi iki ligde piyasayı geçmiyor."*

    python scripts/build_xg.py
    python -m spor_toto.health --only xg_kalibrasyonu
    pytest -q tests/test_xg.py

### 3.43 Kupon kesiti 36 → 114 hafta: ölçüm ne değişti

§6F ve §6G kupon setini dört sezona çıkardı. Bu bölüm o veriyi ölçüm
hattına bağladıktan **sonra** çıkan sayıları taşır.

#### Önce oran, sonra ölçüm

Yeni haftalar oran taşımıyordu ve `evaluate.olculebilir_haftalar`
`usable=False` haftaları **sessizce eliyor** — yani oran gelmeden istatistik
büyür, ölçüm kesiti hiç büyümezdi. `build_odds.py` sezona parametreleştirildi
ve üç sezon için koşuldu:

| Sezon | Eşleşen maç | Tam hafta |
|---|---|---|
| 2022/23 | 255 / 255 (**%100**) | 17 / 17 |
| 2023/24 | 465 / 465 (**%100**) | 31 / 31 |
| 2024/25 | 450 / 450 (**%100**) | 30 / 30 |
| 2025/26 (eski kayıt) | 567 / 615 (%92,2) | 36 / 41 |

**Yeni sezonlarda kapsama %100** ve sebebi yapısal: §6G'nin ürettiği takım
adları *zaten football-data adlarıdır* (eşleştirme orada yapıldı), üstelik
`build_odds.py`nin eşleştiricisi skoru da ayırt edici olarak kullanıyor.

`2025_26`nın §6G kaydı ölçüme **alınmadı**: varsayılan dosyanın aynı sezonu
ikinci kez okumasıdır (§6G.5) ve iki kez saymak paired bootstrap'ı bozardı.
Bekçi: `test_olcum_sezonlari_2025_26nin_IKINCI_okumasini_disarida_birakir`.

Sonuç: ölçüm kesiti **36 → 114 hafta, 540 → 1.710 maç**.

#### Piyasa çizgisi aşağı indi

| Kesit | `piyasa` Brier |
|---|---|
| 36 hafta / 540 maç | 0,5740 |
| **114 hafta / 1.710 maç** | **0,5584** |

Bu bir iyileşme değil, **daha iyi ölçülmüş bir başlangıç çizgisidir** — ve
yenilmesi gereken sayı böylece *zorlaştı*. Eski 2025/26 dilimi piyasa için
görece kötü bir dilimmiş.

#### Asıl bulgu: küçük kesitte tahminciler eğitilemiyormuş

Aynı on aile iki kesitte koşuldu. Eski kesit hafta dışarıda bırakmalı
(tek sezon vardı, başka seçenek yoktu), yeni kesit **sezon dışarıda
bırakmalı** — yani daha *sıkı* protokol:

| Aile | Eski fark (36 hf) | Yeni fark (114 hf) |
|---|---|---|
| `agac` | −0,0 [−0,0, 0,0] | **−0,0043** [−0,0085, **0,0001**] |
| `kalibre_etkilesim_favori` | +0,0047 [−0,005, 0,0143] | **−0,0030** [−0,0066, 0,0007] |
| `yigin` | 0,0 [0,0, 0,0] | **−0,0030** [−0,006, 0,0003] |
| `venn_abers` | +0,0068 [0,0005, 0,0132] | **−0,0016** [−0,0042, 0,0009] |
| `izotonik` | 0,0 [0,0, 0,0] | +0,0024 [−0,0012, 0,0058] |

(Negatif = piyasadan iyi. `gecti` için aralığın tamamı sıfırın altında
olmalı — **hiçbiri geçmedi**.)

Eski kesitteki `−0,0` / `0,0` değerleri bir sonuç değil, bir **arıza
belirtisiydi**: `agac`, `yigin` ve `izotonik` 36 haftada eğitilemiyor ve
piyasaya çöküyordu. 114 haftada gerçekten eğitiliyorlar.

İkinci ve daha keskin nokta: `venn_abers` eski kesitte piyasadan
**anlamlı biçimde kötüydü** (aralık tamamen sıfırın üstünde) — yeni kesitte
işareti döndü. Yani küçük kesit yalnızca belirsiz değildi, **yanlış yöne
işaret ediyordu**.

#### Yine de hiçbiri geçmedi — ve bu böyle yazılır

En iyi aday `agac`: −0,0043, aralık **[−0,0085, +0,0001]**. Üst sınır
sıfırın *üstünde*, dolayısıyla `gecti = False`. Bugüne kadarki en yakın
sonuçtur ve aralık ilk kez bir şey söyleyecek kadar dardır; ama
"piyasa geçildi" **denmez**.

#### Sızıntı: kesişim gerçek, çözüm koda bağlandı

Kupon maçlarının **1.155 / 1.605'i (%72)** eğitim korpusunda da var
(2022/23 %100, 2023/24 %100, 2024/25 %97, 2025/26 %0). `arena.kesit(kupon=True)`
artık `grup=sezon_anahtari` döndürüyor — `backtest.hafta_girdileri` `sezon`
alanını yazdığı için mümkün oldu; önceden alan yoktu ve `sezon_anahtari`
her haftaya `None` derdi. Künye çakışmayı `sizinti` alanında taşıyor,
`tests/test_sizinti.py` beş bekçiyle bunu koruyor.

#### Sezonlar arası ilk bulgu

Ev sahibi kazanma oranı dört sezonda **düzenli düşüyor**:

| Sezon | 1 | 0 | 2 |
|---|---|---|---|
| 2022/23 | %48,6 | %20,4 | %31,0 |
| 2023/24 | %47,1 | %24,3 | %28,6 |
| 2024/25 | %46,2 | %25,1 | %28,7 |
| 2025/26 | %45,1 | %25,3 | %29,7 |

Tek sezonda görülemeyecek bir eğilim. **Bir bulgu değil, bir gözlem**:
sezon başına 17–31 hafta var ve güven aralıkları geniş; eğilim testi
koşulmadı.

---

## 4. Sayfada bugün ne var

**`/istatistik`** — sezon dağılımı (en sık sonuç + pay çubuğu) · 5 sayı kutusu (sembol
toplamları + son 6 hafta farkı, hafta içi ortalama en uzun seri) · haftalık seyir çizgisi
(crosshair + ipucu) · haftalık bantlar (min–maks, ±1σ, ortanca, ortalama) · haftalık adet
dağılımı · **oran kartı** (4 kutu + favori kırılımı + çapraz tablo + banko bantları + **çift
kapsaması** + **beraberlik profili** + **lig kırılımı** + kalibrasyon) · **geri test özeti**
(4 kutu + geri test sayfasına bağlantı) · maç sırasına göre ısı haritası · geçiş matrisi ·
uçlar ve seriler · hafta tablosu (**Brier sütunu + CSV**) · veri kalitesi.
Filtre `?last=N` olarak adres çubuğunda durur; sayfa paylaşılabilir.

**`/istatistik/<hafta>`** — sapma ve sıra kutuları · maç maç tablo (takım, saat, skor, sonuç,
sezon payı, kapanış oranı) · **"bu haftayı formüle gönder"** · sürprizler · ardışık bloklar ·
komşu hafta gezinmesi.

**`/tahmin`** — yaklaşan maçlara 1/0/2 olasılığı **iki tahminciyle** (manşet `piyasa` +
ölçülmüş alternatif `kalibre_bias`, farkı ve aralığıyla), **ölçülmüş isabet kartı tablonun
üstünde** (maç başına %55,6 · haftada 8,33/15 · Brier 0,5740 · 14+ tutan hafta 0/36) ·
günlere bölünmüş maç tablosu + olasılık çubuğu · katlanmayan sınırlar bloğu.

**`/super-toto`** — sezonun 41 haftalık şeridi · girilen haftada dondurulmuş kupon,
revizyon kaydı ve "bugünkü kural ne işaretlerdi" · maç maç tablo · veri uyarıları.
Kaydı olan haftada **iki sekme**: `1. Tahmin` (dondurulmuş kayıt) ve **`2. Tahmin`**
— niçin ikinci bir tahmin · aynı ölçekte kıyas · kupon · **kalabalık ayarı** ·
**bağımsız görüş** (Dixon-Coles + Elo, işaret değiştirmez) · maç maç iki ölçek ·
marj duyarlılığı · oynanacak 16 satır. Müşterek beklenen değer kayıtta var,
**sayfada yok** (§6.3b).

**`/istatistik/geri-test`** — aşırı uyum uyarısı · strateji seçici (banko/üçlü eşiği) + sezon
özeti + örnek kupon · hold-out sağlaması · 28 satırlık eşik taraması (satıra tıklayınca uygulanır)
· hafta hafta sonuç · yöntem notu.

## 5. Ölçülmüş bulgular

Bunlar hesaplanmış gerçek sayılardır ve **hepsi artık sayfada duruyor**.

**Sezon.** 41 hafta · 615 maç · 1: 270 (%43,9) · 0: 149 (%24,2) · 2: 196 (%31,9)

**Banko güvenilirliği** (sayfada var):

| Favori oranı | Maç | Tuttu | Tutmadı | ↳ beraberlik | ↳ karşı taraf |
|---|---:|---:|---:|---:|---:|
| 1.00–1.20 | 11 | %90,9 | %9,1 | %9,1 | %0,0 |
| 1.20–1.35 | 39 | %76,9 | %23,1 | %17,9 | %5,1 |
| 1.35–1.50 | 64 | %64,1 | %35,9 | %23,4 | %12,5 |
| 1.50–1.75 | 106 | %60,4 | %39,6 | %20,8 | %18,9 |
| 1.75–2.00 | 104 | %50,0 | %50,0 | %35,6 | %14,4 |
| 2.00+ | 243 | %46,9 | %53,1 | %25,5 | %27,6 |

Okuma: 1.35 pratik bir sınır. 1.75–2.00 bandı tuzak — isabet %50'ye düşerken tutmama sebebinin
çoğu beraberlik, yani orada banko yapmak aslında beraberliğe karşı bahis yapmaktır.

**Favori kırılımı** (sayfada var): 567 maçın 311'inde favori tuttu (1 → 205, 2 → 106; 0 asla).
Tutmadığı 256 maçta: 0 → 144, 2 → 69, 1 → 43. Gerçek sürpriz (karşı taraf kazandı): 112 maç
(%19,8). Favori "1" iken isabet %54,8, "2" iken %54,9 — piyasa iki yönde de aynı doğrulukta.

**Kalibrasyon** (sayfada var): 8 kova; ör. %20–30 kovasında model %25,6 → gerçek %24,4.
Ortalama marj %7,26.

**Çift kapsama** (sayfada var):

| İlk-iki olasılık toplamı | Maç | Gerçek sonuç küme içinde |
|---|---:|---:|
| 0,70–0,80 | 372 | %77,4 |
| 0,80–0,90 | 149 | %86,6 |
| 0,90+ | 32 | %96,9 |

**Beraberlik profili** (sayfada var): favori ile ikincinin olasılık farkı 0–0,05 iken
beraberlik %32,7; fark 0,50+ iken %14,3. Sinyal var ama zayıf ve tam monoton değil.

**Lig kırılımı** (sayfada var): Süper Lig (285 maç) beraberlik %29,8 / favori isabet %53;
Premier Lig (71 maç) %19,7 / %47,9. Kupon başına ortalama 7 maç Süper Lig'den geliyor, bu fark
"0" bütçesinin nereye harcanacağını değiştirir.

---

**Geri test** (sayfada var): varsayılan eşiklerle 36 haftanın 3'ünde 14+ (%8,3; %95 aralık
%2,9–%21,8), hafta başına ort. **1.987 kolon**, bir 14 için 23.840 kolon. Küme içi hafta 0.
**Hold-out 1 hafta** (%2,8; %95 aralık %0,5–14,2), 2.228 kolon/hafta. Hold-out'un seçtiği eşik
36 haftanın 34'ünde varsayılanın kendisi (0,68/0,38); orantısal ölçekte 31 hafta boyunca
0,68/0,42'ye kayıyordu (§3.18). Hold-out'taki 0→1 farkı **tek bir olaydır**, aralıklar
fazlasıyla örtüşür — okunacak sayı maliyettir.

**Piyasanın yanılması** (sayfada var): sezon ortalaması Brier **0,579** (oranı olan 567 maç,
38 hafta); eşit olasılık vermenin karşılığı 0,667. Piyasa bilgi taşıyor ama az. En sürprizli
haftalar 33 (0,759, kısmi), 7 (0,741), 37 (0,706); en tahmin edilebilir 3. hafta (0,339).

**Marj karşılaştırması** (F5 ölçümü): iddaa açık bülteninde ortalama marj **%17,2**, piyasa
oranlarında **%7,26**. İki kaynağın seviyesi bu yüzden tutmaz; favori sıralaması ve marj
arındırılmış yapı tutar.

### 5.1 Tahmin katmanının bulguları (sayfada **yok**)

**Ölçek.** A5 satırlarına kadar olan bütün ölçümler `orantili` arındırmayla yapıldı ve o
hâlleriyle bırakıldı — bir ölçüm kaydı sonradan yeniden yazılmaz. Bugünkü varsayılan `shin`
ve karşılıkları: kupon seti 0,5747 → **0,5740**, korpus 0,5940 → **0,5936**.

> **Kesit büyüdü (2026-08-23).** Yukarıdaki tablonun "540 kupon maçı" sütunu
> **36 hafta**lık bir kesittir. Kupon seti o ölçümden bu yana **41 hafta /
> 615 maça** çıktı ve aynı `piyasa` çizgisi bu kesitte **0,5856** veriyor.
> Aradaki fark bir gerileme değil, **örneklem farkıdır**: yeni haftalar
> ortalamadan daha sürprizli geldi. Tablodaki sayılar kendi kesitlerinde
> doğrudur ve öyle kalır; **bugünkü** referans çizgisi arandığında
> `evaluate.degerlendir` çıktısına bakılır, bu tabloya değil. Tabloların
> hepsi aynı 540 maçlık kesitte ölçüldüğü için birbirleriyle
> karşılaştırılabilirlikleri de bozulmuş değildir.

| Ölçüm | Kesit | Sonuç |
|---|---|---|
| Piyasa çizgisi | 540 kupon maçı | Brier **0,5747** · log 0,9660 *(orantısal)* |
| Piyasa çizgisi | 31.103 korpus maçı | Brier **0,5940** — kupon maçları ortalama maçtan daha tahmin edilebilir |
| Kademe, kupon üzerinde eğitilmiş | 540 maç | Dört basamak da piyasadan **kötü** (+0,0009…+0,0133) |
| Kademe, korpus içi sezon dışarıda | 31.103 maç | `sicaklik` −0,0004 ve `bias` −0,0005 **geçti** |
| Kademe, korpusta eğit → kuponda ölç | 540 maç | Dört basamak da **iyi** (−0,0010…−0,0015), hiçbiri geçmedi |
| Takım formu (T5) | 31.103 maç | `kalibre_form` −0,0003 [−0,0007, +0,0001] — **geçmedi**; ham sinyal güçlü, piyasa fiyatlamış |
| **Kapanış vs açılış (A1)** | 31.099 maç | Kapanış **0,5940**, açılış 0,5964 · +0,0025 [+0,0019, +0,0030] — **piyasa bilgiyi soğuruyor** |
| **Çizgi hareketi (A1)** | 31.099 maç | `kalibre_hareket` = `kalibre_form`, uzatma **%1,01** — **kapanış verimli** |
| **Pinnacle vs kolektif (A2)** | 31.100 maç | `ps` **0,5936** · −0,0004 [−0,0006, −0,0002] — **geçti**; `b365` geçmedi |
| **Bahisçi anlaşmazlığı (A2)** | 31.100 maç | Ham ilişki favori gücüyle karışık; sabitlenince **kayboluyor**. Güven kısma %0,02 |
| **Dinlenme + sıkışıklık (A3)** | 31.103 maç | Geçmedi. Korpus kupa/Avrupa maçlarını görmüyor — ölçülen, yorgunluğun **vekili** |
| **İç/dış form + sezon sonu (A3)** | 31.103 maç | Geçmedi. İç/dış form ham farkı **+0,247**, artığı onda biri — güçlü sinyal, sıfır katkı |
| **Marj arındırma (A5)** | 31.103 maç | `orantili` 15 bandın **10'unda** anlamlı sapıyor; `shin`/`guc` Brier **0,5936** (−0,00042) ve sapan bant **4'e** iniyor |
| **Favori–sürpriz yanlılığı (A5)** | 31.103 maç | Piyasanın %70–80 dediği maçlar gerçekte **%78,9** (n=1.702) — sapma tek yönlü ve düzenli |
| **İzotonik kalibrasyon (A5)** | 31.103 maç | `orantili` üzerinde **geçti** (−0,00036 [−0,00067, −0,00003]); `shin` üzerinde **hiçbir şey eklemiyor** — aynı olgu, iki kez sayılamaz |
| **Arındırma çevrimi (A5)** | 31.103 maç · 36 hafta | Varsayılan `shin` oldu. Kupon seti Brier 0,5747→**0,5740**; geri test hold-out kolon/hafta 6.897→**2.228**, seçilen eşik 31 hafta 0,68/0,42 → **34 hafta 0,68/0,38** (varsayılanın kendisi) |
| **Karar katmanı (B0)** | 36 hafta | Seçim `P(k≤2)`'ye göre kurulunca **+6,02 puan** hedef ve **%26 daha az kolon**; eşik kuralı 35/36 haftada optimalin altında. Tahmin tarafında aynı kazanç için ~0,10 Brier gerekirdi |
| **Handikap + alt/üst (A6)** | 31.101 maç · 183 hafta | Türetilmiş 1X2 **geçmedi**: −0,000063 [−0,000287, +0,000155]; 50/50 karışım da −0,000107 [−0,000223, +0,0000038]. Üç pazar aynı görüşün üç yüzü |
| **Beraberlik düzeltmesi (Ö3)** | 31.103 maç · 183 hafta | Şekil gerçek (`b` dört katlamada da negatif), büyüklük yok: `bant − sabit` −0,000057 [−0,000137, +0,000021], **0/10 tohum**. Kuponda 30/540 işaret değişiyor, `P(k≤2)` her plan kendi cetveli altında ~0,05 puan kazanıyor — bilgisizliğin imzası |
| **İddaa ekseni (Ö4)** | 469 bülten maçı · 1 kupon haftası | **Ölçülmedi, kural yazıldı.** Marj football-data %7,26 ↔ iddaa %16,93 (bayi) / %21,32 (web). Kalibrasyon için **45 kupon haftası** gerekiyor (ölçülen sd 0,00358, aranan etki 0,0015). Bugün ölçülebilen tek parça: bayi–web arındırmadan sonra ort. **0,53 puan** ayrışıyor — marj ayrı, görüş aynı |
| **Brier ayrışımı (§3.23)** | 31.103 maç · 183 hafta | Kalibrasyon ekseninin tavanı **ölçüldü**: piyasanın toplam güvenilirlik borcu **0,00042** (sapma payı 0,00021), çözünürlüğü 0,05657. T2/T3'ün 0,0005–0,0015'lik etkileri bu tavanın **üstünde** — geçmemeleri kapasiteden değil, alınacak yolun kalmamasından. Beraberlik çözünürlüğü 0,00257 (1 → 0,02922, 2 → 0,02478) ve duyarlılığı **0,003**: argmax neredeyse hiç beraberlik demiyor |
| **Öğrenme eğrisi (§3.24)** | 31.103 maç · 183 hafta | **Eğri düzleşti, gap kapanmadan.** `kalibre_bant` 2.216 → 23.327 maçta 0,00348 iniyor ama **son adım 0,00006** ve 0,59373'te duruyor — `piyasa` 0,59364. Aynı türden veri toplamak bu farkı kapatmıyor; sorun satır sayısı değil sütun. `piyasa` eğrisi tam düz (sağlama) |
| **Hafta içi sıralama (§3.25)** | 31.103 maç · 183 hafta | **Piyasanın sıralaması Brier'inin ima ettiğinden çok güçlü.** Taban isabet %51,1 iken en emin 5 maç **%82,3** [%79,7, %84,6]; NDCG 0,8971, bilgisiz zemin 0,7896. B0'ın +6,02 puanının sebebi bu — `en_iyi_secim` Brier'i değil sıralamayı kullanıyor |
| **Etkileşim kademeleri (§3.26)** | 31.103 maç · 183 hafta | **Geçmedi ve kapasite bedel yazdı**: `etkilesim` +0,000150 [−0,000189, +0,000505], `etkilesim_favori` +0,000165 [−0,000180, +0,000520] — `sezon_sonu`nun +0,000076'sından kötü. Model sınıfı itirazı **daraldı, kapanmadı**: GLM'e açık etkileşim terimi eklemek bir şey getirmiyor; keyfî doğrusal olmama ölçülmedi |
| **Elo (§3.27)** | 31.103 maç · 183 hafta · %95,6 kapsama | **Güçlü sinyal, sıfır katkı.** Ham fark devasa: ev galibiyeti %16,8 → %68,1 (51 puan). Artık sıfır: piyasa her bantta Wilson aralığının içinde. `kalibre_elo` +0,000086 [−0,000242, +0,000429] — geçmedi, ve katsayı **negatif** (−0,0597): piyasa Elo'yu eğer bir şey varsa fazla fiyatlıyor |
| **Dixon-Coles (§3.28)** | 30.654 maç · %98,6 kapsama | **Piyasadan bağımsız ilk görüş, ve o da geçmedi.** Tek başına Brier 0,6153 (piyasa 0,5933): REL sekiz katı, RES üçte iki. Piyasanın üstüne eklenince `kalibre_dc` +0,000100 [−0,000261, +0,000472], katsayı **negatif** (−0,0492). Artık taramasında altı bandın altısında da piyasa Wilson aralığının içinde. γ=1,2297 · ρ=−0,0330 |
| **H2H + seriler (§3.29)** | 31.103 maç · H2H %41 kapsama | **Aynı kalıp, üçüncü ve dördüncü kez.** Ham yayılım H2H'de 28, seride 30 puan; **on bandın onunda da** piyasa Wilson aralığının içinde. `kalibre_h2h` +0,000146, `kalibre_seri` +0,000145 — ikisi de geçmedi; `seri` katsayısı **−0,0385** (model seriyi söndürmek istiyor). Ayrıca `etkilesim_favori` artık **anlamlı biçimde kötü**: +0,000380 [+0,000009, +0,000782] |
| **Ağaç toplulukları (§3.30)** | 31.103 maç · 183 hafta | **Model sınıfı itirazı kapandı.** `agac` +0,000368 [−0,000009, +0,000750], `agac_ham` +0,000667 [+0,000282, +0,001068] — ikincisi anlamlı biçimde kötü. Ayrışım mekanizmayı veriyor: ağaç **kalibrasyonu iyileştiriyor** (REL 0,00042 → 0,00015) ama **çözünürlük kaybediyor** (0,05657 → 0,05597). İç halka en küçük modeli seçti; kapasite monoton zararlı (yaprak 4 → 31: 0,5940 → 0,6120) |
| **1X2 dışı pazarlar (§3.31)** | 539 maç · kupon oran arşivi | **Kısıt kalktı, kural kalmadı.** Alt/üst 2,5: Brier 0,4656, marj %7,14, sapan bant **0/4**. Asya handikabı: ortalama getiri 0,4833, marj %7,38, sapan bant **0/4** — Brier **tanım gereği yok** (çizgilerin %53'ü çeyrek, sonuç kesirli). Handikap bantları **çizgiye** göre: olasılığa göre dilimlendiğinde 539 maçın 531'i tek banda düşüyor, çünkü pazarın amacı olasılığı %50'ye çivilemek |
| **Yığınlama (§3.32)** | 31.103 maç · kat dışı 31.103 | **Serinin ilk negatif nokta tahmini** ama geçmedi: −0,000137 [−0,000402, +0,000148]. Ağırlıklar sebebini söylüyor — piyasa +0,5307, kademe +0,3242, agac +0,2347 (**üçü de piyasa çıpalı**, toplamları 1,09) ve piyasadan bağımsız tek taban Dixon-Coles **−0,0693**. Yeni bilgi değil, aynı bilginin farklı paketlenmesi |
| **LOFO + Venn-Abers (§3.33)** | 31.103 maç · 4 sezon katı | **LOFO: hiçbir özellik taşımıyor**, onun beşi net negatif — en zararlısı `ayrisma` (−0,000159), ve `elo_farki` (−0,000042) ile `h2h_farki` (−0,000065) de negatif. **Venn-Abers geçmedi** (+0,000264) ama aralık yeni bir sayı verdi: ortalama genişlik **0,00472** — piyasanın olasılıkları sıkı destekleniyor, §3.23'ün bağımsız teyidi |
| **Müşterek beklenen değer (§3.34)** | 51. hafta · 3.888 kolon · havuz varsayımı | **Ölçüm değil, hesap** — ve sonucu belirleyen tahminci değil kalabalık varsayımı: `orneklem` modelinde getiri oranı **0,156**, `favori` modelinde **0,007** — arada **22 kat**. Havuz büyüklüğü getiriyi hiç belirlemiyor (havuz ve rakip kolon birlikte ölçeklendiğinde eğri tam düz); belirleyen `p_k/q_k` oranı. Bu eksenin ihtiyacı yeni model değil, **oynanma paylarının ölçümü** |
| **Takım bazlı istatistik (§3.35)** | 31.103 maç · 22 lig · 604 takım | **Yasak kalktı, kural kalmadı.** Ampirik Bayes küçültmesi: ortalama `B` **0,854**, ortalama %95 aralık 0,509. Tek sezona inildiğinde sistem **kendiliğinden temkinli oluyor** — `B` 0,697'ye düşüyor, aralık 0,690'a genişliyor. En çok konuşan satır Scunthorpe: 46 maçta ham 0,565 → küçültülmüş **0,875** [0,58, 1,17] |
| **Yeni veri (§3.36)** | 768 UEFA maçı · 592 takım şehri · 31.103 maç | **Serinin niteliksel olarak farklı kapanışı.** Eksik veri gerçekten eksikti: UEFA fikstürü eklenince §3.16'nın açıklanamayan anomalisi **+0,0613 → +0,0325**'e indi (kontrol katmanı bit bit aynı kaldı). Ama düzeltilmiş özellik de geçmedi — `kalibre_avrupa` +0,000028 [−0,000277, +0,000352]. Derbi de türetilebilir oldu (667 maç) ve geçmedi (+0,000176). xG ve kadro **kapalı**: biri `robots.txt`, öteki eğitim/servis ayrışması |

**Okuma.** Aşırı uyum modelin kapasitesinden değil örneklem küçüklüğünden geliyordu; büyük
korpus onu kaldırdı. Ama kalan etki 0,0005–0,0015 Brier — 31 binde anlamlı, 540'ta değil ve
%17,2'lik iddaa marjının yanında hiç. **Yön doğru, miktar yetersiz.**

**A1'in eklediği okuma daha serttir.** Piyasanın *kendi hareketi* — ham haliyle güçlü ve
monoton bir sinyal — kapanışın ötesinde hiçbir şey söylemiyor. Bu, "iyi model bulamadık"
demekten farklı bir cümledir: piyasanın kendi bilgisi bile kendini yenemiyorsa, aynı veriyle
aramaya devam etmenin karşılığı yoktur.

**A2 tabloya iki farklı şey ekledi.** Biri ilk "geçti": Pinnacle kolektifi geçiyor — ama
bu bir model değil, referansın yumuşaklığı (§6.2 A4). Diğeri **yeni bir null türü**:
anlaşmazlıkta ham sinyal *hiç yok*, yalnızca favori gücüyle karışmış bir görüntü var.
Üç ölçümün üçü de aynı yere bakıyor: piyasa fiyatı, elimizdeki veriden çıkarılabilecek
her şeyi zaten içeriyor.

### 5.2 Havuz ekseninin ilk bulguları — ölçüldü, belgeye girmedi

PR #14, 2026/27'nin ilk iki haftasında **altı ölçülmüş bulgu** üretti ve
bunların tamamı bugün yalnızca **commit mesajlarında** duruyor. Bu belgenin
kuralı ölçülen her şeyin §3'e gerekçesiyle yazılmasıdır; PR #14 `main`'e
girdi ama o yazımı yapmadı — **borç duruyor**.

Kaybolmasınlar diye başlıkları ve commit'leri:

| # | Bulgu | Commit |
|---|---|---|
| 1 | **Hedef yanlıştı.** Aynı kuralın 36 haftalık en-iyi-kolon dağılımı 14→3, 13→6, 12→12, 11→9, 10→3, 9→3. 14 hiçbir zaman ulaşılabilir hedef değildi; doğru ölçü **P(en iyi kolon ≥ 12)** — ikramiye 12'den başlıyor | `bb4a274` |
| 2 | **Atılan sembolün bedeli simetrik değil.** Çiftede atılan beraberlikse %25,8 geliyor, ev sahibiyse %16,0, deplasmansa %15,6 (567 maç). Beraberlik atmak 1,6 kat pahalı | `bb4a274` |
| 3 | **Korumak daha pahalı.** Beraberliği korumanın maliyeti kolon/14 başına 32.235 → 80.520. Yedi alternatif kural koşuldu; kullanılan kural en verimlisi çıktı | `bb4a274` |
| 4 | **Kural değiştirilmedi.** Bir haftalık veriyle eşik oynatmak, geçen sezonun hold-out'unun (%0) zaten ölçtüğü hatadır | `bb4a274` |
| 5 | **Oynanma verisi yön taşımıyor.** Halkın modal kuponu ile piyasanın favori kuponu birebir aynı — sinyal yalnızca **pay** için | `bb4a274` |
| 6 | **İsabet kalabalıkla birlikte geliyor.** 13+ haftalarda ort. 9,00 favori, 11 ve altı haftalarda 7,47 — ikramiyenin küçüldüğü haftalarda tutturuluyor | `bb4a274` |
| + | **Açılış ↔ kapanış, kupon zamanlamasıyla.** Kupon ilk maçtan önce kapanır, oranlar her maçın saatine kadar oynar: son maçlarda **kapanış fiyatı kupon verilirken yoktur**. Bedeli isabet değil **kolon: %22 artış** (2.686 → 3.290). Hareket 4 puanı aştığında kapanış gerçeği neredeyse birebir tutturuyor, açılış sapıyor | `14650a7` |

Sonuncusu **A1'i daraltıyor, çürütmüyor.** A1 hareketin *kapanışın ötesinde*
bilgi taşımadığını ölçmüştü (uzatma %1,01); bu ölçüm kapanışın açılışa göre
üstünlüğünün **nerede yoğunlaştığını** gösteriyor — hareketsiz bantta (n=407)
ikisi aynı, hareketli bantta (n=171) kapanış açık ara doğru. İkisi tutarlı:
piyasa hareketi kapanış fiyatına soğuruyor.

Pratik sonucu ise yeni ve ürünü ilgilendiriyor: **ölçümlerimizin dayandığı
kapanış fiyatı, kupon verilirken haftanın son maçları için elimizde yok.**

---

## 6. Yol planı — proje ne zaman biter

Bu bölüm **sonlanan** bir plandır: bitirildiğinde yapacak iş kalmaz.

Böyle bir şey ancak plan **özellikler** yerine **sorular** etrafında kurulursa mümkündür.
Özellik listesi sonsuzdur — her karta bir kart daha eklenebilir. Soru listesi sonludur:
hedefe ulaşılıp ulaşılamayacağını belirleyen soruların sayısı bellidir.

Bu yüzden buradaki her fazın bir **durma kuralı** vardır ve bir kısmı şudur: *"cevap hayır
çıktı, bu eksen kapandı."* Yalnızca başarıyla bitebilen bir plan, plan değil temennidir.

### 6.1 Hedefin ayrışması — planın neden sonlu olduğu

Amaç "kazanma oranını artırmak" tek bir şey değil, **çarpımsal üç etkendir**:

```
Beklenen getiri  =  P(tutturma)  ×  Pay(tutturunca)  −  Bedel
                    ─────────────    ───────────────     ──────
                    tahmin ekseni    havuz ekseni        kaplama ekseni
```

| Eksen | Ne belirler | Durum |
|---|---|---|
| **Tahmin** | 14+ tutturma olasılığı | İki bağımsız denemede ~sıfır artık (§5.1) |
| **Havuz** | Tutturunca ikramiyenin kaçta kaçını aldığın | **Motor hazır, veri geldi, ölçüm yok** (§3.34, §6.3, §6.3b). Beklenen değer artık kapalı formda hesaplanıyor; oynanma 2 hafta, ikramiye kaydı 1 hafta |
| **Kaplama** | Aynı garanti için ödenen kolon | **Çözüldü** — Hamming, kanıtlanmış optimal |

Plan sonludur çünkü **etken sayısı üçtür.** Kaplama ekseninde iş yok ve olmayacak: bir
optimum yenilemez, oraya harcanacak her saat cevabı önceden bilinen bir soruya gider.

### 6.2 Faz A — tahmin eksenini kapat ya da aç

Hepsi **mevcut korpusla** yapılır; yeni kaynak gerekmez.

#### A1 — Kapanış çizgisi verimliliği · **bitti** (§3.14)

Sorulan iki şey de ölçüldü, 31.099 maçta, sezon dışarıda bırakmalı:

> **Kapanış açılışı geçiyor** — +0,0025 Brier, aralık [+0,0019, +0,0030], tamamen sıfırın
> üstünde. Piyasa maç öncesinde gelen bilgiyi fiyata **soğuruyor.**
>
> **Hareket kapanışın ötesinde bilgi taşımıyor** — model hareketi kapanışın ötesine yalnızca
> **%1,01** uzatmak istiyor. Ham sinyal güçlü (en büyük harekette çizginin lehine oynadığı
> sembol %47,2'ye karşı %30,2 tutuyor) ve **tamamı zaten kapanış fiyatında.**

Bu sonuç A4'ün (b) şıkkına giden **en güçlü tek kanıttır** ve "iyi bir model bulamadık"
demekten farklıdır: piyasanın kendi hareketi bile kendini yenemiyorsa, sorun modelde değil
veridedir.

#### A2 — Bahisçi anlaşmazlığı · **bitti** (§3.15)

İki soru sorulmuştu, ikisi de ölçüldü — ve **cevapları farklı çıktı:**

> **Kolektifin içinde daha iyi bir üye var** — `ps` (Pinnacle) kolektif ortalamayı geçiyor:
> −0,0004 Brier, aralık [−0,0006, −0,0002]. Projede referansı geçen ilk tahminci. Bulgu
> `PS`'e özgü; `B365` kolektiften kötü.
>
> **Anlaşmazlığın kendisi bilgi taşımıyor** — ham ilişki favori gücüyle karışıktı; favori
> sabitlenince tamamen kayboluyor. Model ortalama anlaşmazlıkta güvenini **%0,02**
> değiştiriyor.

İkinci bulgu **yeni bir null türü**: T5 ve A1'de ham sinyal gerçekti ve piyasa onu
fiyatlamıştı; burada ham sinyalin kendisi bir görüntüydü.

Birinci bulgu ise durma kuralının muhasebesini değiştiriyor — aşağıda.

#### A2'nin açtığı karar: referans çizgisi `Avg` mi kalmalı?

`REFERANS_AD` bugün `piyasa`, yani `Avg` kapanışı. A2 bunun **ölçülebilir biçimde yumuşak**
olduğunu gösterdi: Pinnacle 0,0004 daha iyi. Üç seçenek var ve seçim ürün kararıdır:

| Seçenek | Sonuç |
|---|---|
| **`Avg` kalsın** | Bütün geçmiş ölçümler karşılaştırılabilir kalır; referansın yumuşaklığı belgede yazılı durur |
| **`PS`'e geçilsin** | Çıta 0,0004 yükselir, gelecek ölçümler daha dürüst olur — ama T1–A2'nin tamamı yeniden koşulmadıkça geçmişle karşılaştırılamaz |
| **İkisi de raporlansın** | Bedeli yok ama her tabloda iki referans sütunu taşımak gerekir |

**Bugünkü tercih: `Avg` kalıyor.** Gerekçe: 0,0004'lük fark, ölçülen hiçbir sonucun işaretini
değiştirmiyor (geçen tek şey `ps`'in kendisi), ve karşılaştırılabilirliği kaybetmenin bedeli
kazancından büyük. Karar bilinçlidir ve burada yazılıdır — sessizce bırakılmış değil.

#### A3 — Piyasa dışı ama türetilebilir özellikler · **bitti** (§3.16)

Altı özellik listelenmişti. **İkisi türetilemedi** ve gerekçesi kayda geçti (seyahat: şehir
yok ve bir maçın iki takımı hep aynı ligde; derbi: rekabet tablosu yok — elle liste yazmak
küratörlük olurdu). Kalan dördü türetildi ve dördü de **geçmedi:**

> Dinlenme günü, fikstür sıkışıklığı, iç/dış saha ayrı formu ve sezon sonu payı kademeye
> üstüste eklendiğinde taban çizgisi **hiç kımıldamadı** — dördü de −0,0003 [−0,0007, +0,0001].

En öğretici olanı iç/dış form: ham farkı devasa (+0,247 ev galibiyeti oranı), artığı ham
farkın onda birinden küçük. **Güçlü sinyal, sıfır katkı.**

**Bir sınır ölçüldü ve A4'e taşındı.** Korpus kupa ve Avrupa maçlarını görmüyor; dolayısıyla
ölçülen şey yorgunluk değil, *korpustan türetilebilen yorgunluk vekili*. Kör nokta taraması
bunu doğruladı — deplasman "dinlenmiş" göründüğünde ev takımı piyasayı +0,0655 aşıyor ve etki
Avrupa liglerinde dört kat güçlü. Bulgu değil (n=445, dışarıda bırakmalı katkısı sıfır), ama
A4(b)'nin yeniden açılma koşulunu somutlaştırıyor: eksik olan **fikstür verisi**.

#### A4 — Arayışın durma kuralı · **işletildi**, ve neyi kapatmadığı

> **Bu bölüm bir kez yanlış yazıldı ve düzeltildi (2026-08-18).** İlk sürüm ölçümü
> *"tahmin ekseni kapalıdır"* diye özetliyordu. Ölçüm bunu söylemedi. Söylediği şey
> **"denenen dokuz özellikten hiçbiri piyasayı geçmedi"** idi — ve bu ikisi aynı cümle
> değil. Aradaki farkı yutmak, projenin kendi amacını (README §1: *maç sonucu tahmini
> yapmak*) bir ölçüm sonucuyla iptal etmek olurdu. **Tahmin ekseni açıktır ve kapatılmaz.**

**Durma kuralı bir SORUYA aittir, eksene değil.** Kapanan soru şudur:

> *"Elimizdeki veriden türetilen bir özellik, piyasa fiyatını out-of-sample geçebilir mi?"*
>
> **Cevap: hayır.** Dokuz özellik denendi, 31.100 maçlık korpusta, sezon dışarıda bırakmalı,
> hafta üzerinden eşleştirilmiş bootstrap ile; "geçti" ölçütü güven aralığının tamamen
> sıfırın altında kalmasıdır. Bu bir kanaat değil ölçümdür.

| # | Denenen | Kesit | Sonuç |
|---|---|---|---|
| 1–4 | Yeniden kalibrasyon kademesi (T2–T3) | 31.103 | Yön doğru, miktar yetersiz |
| 5 | Takım formu (T5) | 31.103 | Geçmedi; piyasa fiyatlamış |
| 6 | Çizgi hareketi (A1) | 31.099 | Geçmedi; uzatma %1,01 |
| 7 | Bahisçi anlaşmazlığı (A2) | 31.100 | Geçmedi; ham sinyalin kendisi yok |
| 8 | Dinlenme + fikstür sıkışıklığı (A3) | 31.103 | Geçmedi |
| 9 | İç/dış form + sezon sonu payı (A3) | 31.103 | Geçmedi |

İki bağımsız doğrulama aynı yöne işaret ediyor: **açılış çizgisi kapanışın altında**
(+0,0025, aralık tamamen sıfırın üstünde) — piyasa bilgiyi soğuruyor; ve **piyasanın kendi
hareketi bile kapanışı yenemiyor.**

#### Kapanan ile açık kalan

| | Durum |
|---|---|
| **Piyasayı geçen özellik arayışı** | **Kapandı.** Aynı veriyle yeni model denemek, aynı soruyu daha yüksek sesle sormaktır |
| **Tahmin üretmek** | **Açık ve kalıcı.** Projenin amacı bu; bir ölçüm sonucu onu iptal etmez |

Aradaki fark pratikte şudur: elimizde **kalibre, ölçülmüş bir tahminci var** ve o piyasanın
kendisidir. Bunu "yenemedik" diye rafa kaldırmak, çalışan bir aracı sırf daha iyisini
bulamadık diye atmak olur. Ölçülen isabetiyle birlikte sunulduğu sürece bu tahmin
**dürüsttür** — projenin karşı çıktığı şey ölçülmemiş bir üstünlük iddiasıydı, tahminin
kendisi değil.

Tahmincinin ölçülmüş hâli (kupon seti, 36 hafta · 540 maç):

| Ölçü | Değer |
|---|---|
| Maç başına en olası seçim | **%55,6** |
| Haftada ortalama doğru | **8,3 / 15** · en iyi hafta 12/15 |
| Brier · log kaybı | 0,5747 · 0,9660 |
| Tek kolonla 14+ | **0 / 36 hafta** |

Son satır modelin kusuru değil **aritmetiktir** ve piyasanın kendi olasılıklarından çıkar:
tek kolonla P(14+) ≈ 8,6·10⁻⁴, yani ~1/1.161 hafta. 36 haftada beklenen 14+ sayısı **0,031**;
gözlenen **0**. Tahminci tam olması gerektiği kadar iyi çalışıyor — kalibre.

**14+'a kaplama motoru taşır, tahminci değil.** Tek kolon yerine garanti veren bir sistem
oynanır (haftada ort. 1,6 banko · 12,2 çift · 1,1 üçlü → 2.686 kolon). Sezon içi 3/36 hafta
14 tuttu; **hold-out'ta 0/36** — aşırı uyum, ve bu da kayıtlı.

#### Piyasayı geçmeyi yeniden mümkün kılacak kaynaklar

Arayış kapandı ama "hiçbir zaman" demiyor: **yeni veri kaynağı** diyor. A1–A3 o kaynakları
belirsiz bırakmadı, üçünü de somutlaştırdı:

| Kaynak | Hangi ölçüm işaret etti |
|---|---|
| ~~**Fikstür verisi** (kupa + Avrupa)~~ | ✅ **YAPILDI (§3.36).** UEFA maçları geldi (768 maç, ad eşlemesi %100) ve takvime enjekte edildi. Kör nokta taraması **+0,0613 → +0,0325**: anomalinin yarısı ölçüm hatasıymış. Kalan yarı da fiyatlanmış — `kalibre_avrupa` geçmedi. **İç kupalar hâlâ yok**, yani sınır küçüldü ama kaybolmadı |
| ~~**Kadro / sakatlık**~~ | ❌ **ARANDI, KAPALI (§3.36).** Kaynak teknik olarak açık (transfermarkt `Allow: /`) ama özellik **ileriye dönük kullanılamaz**: gerçek kadro ancak ilk vuruşta bellidir. Korpusta kullanıp `/tahmin`de kullanamamak eğitim/servis ayrışmasıdır. Bu "kaynak yok" değil, **"özellik bu ürün için geçersiz"** demektir |
| ~~**Şehir / rekabet tablosu**~~ | ✅ **YAPILDI (§3.36).** `openfootball/clubs` (CC0) kulüp–şehir tablosu verdi: kapsama **%98,0**, 667 derbi. `derbi` bir sıcaklık değişkeni olarak girdi ve **geçmedi** (+0,000176). `seyahat` hâlâ kapalı ama gerekçesi değişti: artık "şehir yok" değil **"koordinat yok"** |
| ~~**xG (Understat)**~~ | ❌ **Kaynak değil — ölçülmüş negatif, ve ayrıca erişime kapalı.** Dış bir çalışma 14 xG özelliğiyle denedi ve piyasayı geçemedi ([`DIS_INCELEME.md`](DIS_INCELEME.md) §4); üstelik Understat **Süper Lig'i kapsamıyor**. Faz 3.4 bir de erişimi denetledi: `robots.txt` `User-agent: * / Disallow: /` — otomatik erişime **tamamen kapalı**, fbref ise Cloudflare sorgusu arkasında (§3.36) |

> **Dört madde de kapandı (Faz 3.4, §3.36).** İkisi geldi ve ölçüldü, ikisi arandı ve
> kapalı çıktı. Bu tablonun okunuşu artık şudur: *"eksik veri gerçekten eksikti, bulundu,
> eklendi, ölçüm hatasını düzelttiği doğrulandı — ve düzeltilmiş özellik de piyasayı
> geçmedi."* Kalan iki kaynak bulunamıyor değil, **kullanılamıyor**.

Yeni bir kaynak geldiğinde açılacak soru bellidir ve altyapı hazır:
`cizgi.py`/`bahisci.py`/`disari.py` deseni aynen kullanılır — ve `build_avrupa.py` ile
`build_sehir.py` artık *"dış bir kaynağı korpusa nasıl bağlarız"* sorusunun iki çalışan
örneğidir (ülke kısıtı + bulanık eşleme yok + kapsama kapısı).

#### Model sınıfı — dokuz denemenin ortak kör noktası ve dışarıdan gelen kontrol

Yukarıdaki dokuz denemenin **hepsi tek bir model ailesiyle** yapıldı:
`recalibrate.py`'ın kademesi, `ln p` üzerinde doğrusal, Newton ile uydurulan bir
softmax. Etkileşim yakalayan ya da doğrusal olmayan eşik kuran bir sınıf hiç
denenmedi. Bu, A4'ün bugüne kadar cevaplamadığı bir itiraz bırakıyor:

> *"Piyasayı geçen özellik yok demediniz — sizin doğrusal kademeniz o özelliği
> kullanamadı demiş oldunuz."*

Dış bir çalışma (`zakariae-boui/football-prediction-ml`) tam o sınıfı deniyor —
Random Forest, XGBoost ve SVM ile, 52–62 özellik üzerinde, 6.080 Premier Lig ve
La Liga maçında — ve **aynı tavana çarpıyor**: en iyi model %54,2, bahisçi
favorisi %54,7, bütün stratejilerde ROI negatif (−%2,9 … −%8,4).

**Bu bir teyittir, ölçüm değil.** Farklı ligler, farklı dönem, farklı ölçüt
(isabet + ROI; bizim güven aralığı ölçütümüz değil) ve bizden bağımsız bir ekip.
İtirazı ortadan kaldırmaz — o sınıfın **bizim kesitimizde** ne yapacağı hâlâ
ölçülmedi — ama itirazın beklenen getirisini düşürür. Künye ve sınırlar:
[`DIS_INCELEME.md`](DIS_INCELEME.md) §3.

#### Denenmedi, gerekçesiyle

A3 *"denenmedi"* ile *"denenemez"*i ayırmayı kural hâline getirmişti (seyahat,
derbi). Aynı disiplin iki özelliğe daha uygulanır — bunlar **denenebilir ama
denenmedi**, ve bu bilinçli bir tahsis kararıdır:

| Özellik | Türetilebilir mi | Neden şimdi denenmiyor |
|---|---|---|
| **Elo** (rakip gücüne göre düzeltilmiş takım gücü) | **Evet**, korpustan; yeni kaynak gerekmez | Durma kuralı (aynı veri) · A1'in null'ı — piyasanın kendi çizgi hareketi bile kapanışı yenemedi · **fırsat maliyeti**: havuz ekseni veri taşıyor ve hiç ölçülmedi |
| **H2H** (son 5 karşılaşma) | **Evet**, aynı şekilde | Aynı üç gerekçe |

Elo'nun ayrıca kaydedilmesi gereken bir yanı var: `kalibre_form` **ham** formdu,
rakip gücüne göre düzeltilmemişti — Elo tam o eksiği kapatan standart sinyaldir.
Yani "form denendi" demek "Elo denendi" demek değildir.

**Yeniden açılma koşulu:** havuz ekseni ölçülüp kapanırsa (§6.3 B4/b), ya da
yukarıdaki üç kaynaktan biri gelirse. Ayrıntı: [`DIS_INCELEME.md`](DIS_INCELEME.md) §8.

#### `ps` geçti — arayışı yeniden açar mı? Hayır

`ps` (Pinnacle) kolektifi geçti: −0,0004 [−0,0006, −0,0002]. Ama bir özellik değil, model
bile değil — **aynı piyasanın başka bir okuması**. Yeni bilgi üretmiyor; müşterek bahiste
Pinnacle fiyatından oynanmadığı için ürüne çevrilemez; büyüklüğü yine 0,0004. Söylediği şey
**"referans çizgimiz 0,0004 kadar yumuşakmış"** — bir referans kararı (yukarıda), arayışın
sonucu değil.

#### Faz A'nın asıl çıktısı

Dokuz özellik, dört bağımsız açı, 31 bin maç — ve tek bir "geçti" yok. **Bu bir başarısızlık
değil, projenin cevaplamak için kurulduğu sorunun cevabı.** Bu alandaki araçların neredeyse
tamamı üstünlük *iddia eder*; hiçbiri üstünlüğün yokluğunu **ölçmez**.

Pratik sonuç iki yönlü ve ikisi de eyleme dönük:

1. **Tahmin ürünleşir.** Elimizdeki kalibre tahminci, ölçülmüş isabetiyle birlikte arayüze
   çıkar (Faz C — artık koşulsuz, aşağıya bakınız).
2. **Kazanç havuz ekseninden aranır.** Piyasayı tahminde yenmek gerekmiyor; kalabalığın
   gitmediği yeri işaretlemek yetiyor (Faz B).

### 6.3 Faz B — havuz eksenini aç ve ölç

Muhtemelen **tek gerçek kaldıraç** — çünkü piyasayı tahminde yenmeyi gerektirmez.

**B1'in ön koşulu artık sağlanmış durumda.** Bu bölüm uzun süre *"veri yok,
kaynak araştırılmadı"* diyordu; 2026/27 sezonunun ilk iki haftası için üç veri
birden elle girildi (`backend/data/super_toto/2026_27/hafta_NN.json`):

| Veri | 1. haftada ölçülen |
|---|---|
| **İkramiye tablosu** | 15 bilen **0 kişi** (30.149.380,57 TL devretti) · 14 bilen 8 kişi × 2.153.527,18 TL · 13 bilen 210 kişi × 82.039,13 TL · 12 bilen 2.859 kişi × 7.532,44 TL |
| **Oynanma yüzdesi** | Maç başına 1/0/2 tercih payı — **tek platformun kendi kullanıcıları**, Spor Toto havuzunun tamamı değil |
| **Gerçek iddaa oranı** | Piyasa vekili değil, oynanan fiyatın kendisi |

**Ve ilk iki ölçüm çoktan yapılmış** (`super_toto_hafta.py`, `super_toto_degerlendir.py`):

- **Havuz kenarı ölçülebiliyor.** `crowd_ratio` = kuponun küme-içi olasılığının,
  rastgele bir halk kuponununkine oranı. 1. haftada 0,451 (%2,31 ↔ %5,12) — yani
  kupon, kalabalığın seyrek olduğu yere düşüyor. B3'ün amaç fonksiyonunun çekirdeği budur.
- **Ama iki bulgu tezi zayıflatıyor.** (1) Halkın modal kuponu ile piyasanın favori
  kuponu **birebir aynı** çıktı: oynanma verisi **yön için sinyal taşımıyor, yalnızca
  pay için**. (2) Daha ağırı: strateji, en iyi kolonu 13+ olan haftalarda ortalama
  **9,00** favori, 11 ve altı haftalarda **7,47** favori görüyor — **isabet kalabalıkla
  birlikte geliyor**, yani tam da ikramiyenin küçüldüğü haftalarda.

İkinci bulgu Faz B için elimizdeki en önemli tek sayıdır ve B4'ün *(b)* şıkkını
somutlaştırır: havuz avantajı, onu kazandığın haftaların aynı zamanda payın
küçüldüğü haftalar olmasıyla kısmen kendini yiyor. **Ölçülmesi gereken şey artık
"avantaj var mı" değil, "net mi".**

**n = 2 hafta.** Hiçbiri "geçti" statüsünde değil; hepsi betimleyicidir.

Spor Toto müşterek bahistir: ikramiye havuzdan kazananlara bölünür. Sonuç: *aynı olasılığa
sahip iki sonuçtan **daha az oynananı** işaretlemek, tutturma olasılığını değiştirmeden
beklenen getiriyi artırır.* Ve kalabalık öngörülebilir davranır — favoriye yığılır. Projenin
kendi verisi bunu söylüyor: favori 567 maçın 311'inde tuttu (%54,9), yani kalabalığın gittiği
yer maçların **yarısında yanlış**.

| # | İş | Not |
|---|---|---|
| **B1** | İkramiye / kazanan verisi | **Ön koşul sağlandı** (PR #14, yukarıdaki blok). Fizibilite sorusu kapandı: kaynak Spor Toto'nun resmî ikramiye ekranı, veri **elle** giriliyor. Kalan iş biriktirme — n = 2 |
| **B2** | Popülerlik modeli | **Vekile gerek kalmadı** — gerçek oynanma payı var. Ama kendisi de vekil: tek platformun kullanıcıları, havuzun tamamı değil. **Sıradaki ölçüm bu yanlılıktır**: ikramiye tablosunun kat başına kazanan adetleri, oynanma payı + gerçek sonuçtan önceden söylenebilmeli; söylenemiyorsa platform havuzu temsil etmiyor |
| **B3** | Beklenen getiriye göre kupon kurma | **Kaplamanın ve havuzun buluştuğu yer; projenin en özgün işi.** "Hangi maça kaç işaret" sorusu ilk kez ölçülmüş bir amaç fonksiyonuyla cevaplanır. Tahmin değil, **kalabalık davranışı** modellenir |
| **B4** | Durma kuralı | *(a)* pozitif beklenen getiri ölçüldü → Faz C · *(b)* veri yok, ya da %17,2 marj + havuz seyrelmesi avantajı yutuyor → eksen kapanır |

### 6.3b Faz B'nin ölçülebilir hâli — soru, ölçü ve durma kuralı

Faz B "muhtemelen tek gerçek kaldıraç" diye yazılmıştı ama **sorusu ölçülebilir
biçimde kurulmamıştı**. Altyapı bu arada hazır oldu: `super_toto_hafta.kamuoyu`
oynanma yüzdesini taşıyor, `kupon_kur` `crowd_in_set_p` ve `crowd_ratio`
hesaplıyor, `super_toto_sezon.py` haftaları biriktiriyor. Eksik olan soruydu.

#### Soru

> Aynı tutturma olasılığında, **az oynanan** sembolü işaretlemek kişi başı
> ikramiyeyi ölçülebilir biçimde büyütüyor mu?

Tahmin ekseninden farkı ve önemi şu: bu soru **piyasayı geçmeyi gerektirmiyor.**
Piyasa fiyatı doğru olsa bile, aynı olasılıktaki iki sonuçtan az oynananı seçmek
tutturma olasılığını değiştirmeden payı büyütür. A1–A3'ün kapattığı arayış bu
ekseni kapatmaz.

#### Ölçü

`crowd_ratio = p_küme_içi / p_kalabalık_içi`. 1'in üstü, seçim kümesinin
olasılığına göre **az** oynandığı anlamına gelir. Ölçülecek bağıntı:

    tutturulan haftalarda   kişi başı ikramiye  ↔  o haftanın crowd_ratio'su

#### Durma kuralı — şimdiden yazıldı

Faz B, aşağıdaki üç şıktan biri gerçekleştiğinde kapanır:

1. **B1 verisi bulunamazsa** (kazanan sayısı ve kişi başı ikramiye, hafta
   bazında, geçmişe dönük): eksen *"ölçülemez"* diye kapanır. Bugün elde
   yalnızca **1 haftalık** ikramiye kaydı var (2026/27 1. hafta: 14 bilen 8
   kişi, kişi başı 2.153.527,18 TL). Bir gözlemle bağıntı ölçülmez.
2. **Veri bulunur ve bağıntı ölçülür**: bootstrap %95 aralığı sıfırı
   kesmiyorsa eksen **açık**, kesiyorsa **kapalı**. Ölçüt projenin geri
   kalanıyla aynıdır.
3. **Yeterli hafta birikmezse**: kaç hafta gerektiği **şimdiden** yazılır ve
   o sayıya ulaşılana kadar eksen "açık ama ölçülmemiş" kalır.

#### Kaç hafta gerekir — ölçüldü, tahmin edilmedi

`scripts/faz_b.py --guc` sorunun istatistiksel gücünü hesaplar. Kişi başı
ikramiye haftalar arası **çok** oynak (kazanan sayısına bölünür ve kazanan
sayısı 0 ile binler arasında gezer), bu yüzden orta büyüklükte bir etkiyi
(log ölçekte 0,5) %80 güçle ayırt etmek **≈71 ikramiyeli hafta ≈ 3,5 sezon**
ister. Elde **1** hafta var.

Sayı bir tahmin değil, koşum çıktısıdır — ve varsayılan standart sapma (1,5)
muhafazakâr bir tahmindir; gerçek veri biriktikçe **ölçülen** sd yerine
konmalıdır.

Bu, ekseni şimdiden kapatmaz ama **beklentiyi bugünden düzeltir**: Faz B'nin
cevabı bu sezon gelmeyecek. Gelecek olan şey, verinin **biriktirilmeye
başlanmasıdır** — ve toplanmamış veri hiçbir zaman ölçülemez.

#### Motor hazır, ölçüm değil (§3.34)

Faz 4.2 bu eksenin **hesabını** kurdu: `getiri.py` müşterek beklenen değeri
kapalı formda veriyor. Bu, durma kuralını değiştirmiyor — hesap ölçüm değildir
— ama bir şeyi netleştirdi: kalabalık modeli `orneklem`den `favori`ye
çevrildiğinde getiri oranı **0,156'dan 0,007'ye**, yani 22 kat düşüyor.

**Yani bu eksende belirsizliğin kaynağı tahminci değil, kalabalık.** Yukarıdaki
"≈71 hafta" hedefinin ölçtüğü şey de tam olarak budur; motorun varlığı hedefi
küçültmez, yalnızca ölçüm geldiğinde takılacağı yeri hazır eder.

#### Bilinen sınır — kaldırılmamalı

Oynanma yüzdeleri **tek bir platformun kendi kullanıcılarıdır**, Spor Toto
havuzunun tamamı değildir. Bütün `crowd_*` ölçüleri bu vekile dayanır ve
vekilin havuzu ne kadar temsil ettiği **ölçülmemiştir**. B1 verisi gelirse ilk
iş bu vekili doğrulamak olmalı: gerçekleşen kazanan sayısı, kalabalık
modelinin öngördüğüyle uyuşuyor mu?

### 6.4 Faz C — karar katmanı ve ürün

> **Koşul kaldırıldı (2026-08-18).** Bu bölüm önce *"yalnızca A4(a) ya da B4(a) çıkarsa
> açılır"* diyordu. O koşul yanlış yere kondu: derdi **ölçülmemiş bir üstünlüğü** arayüze
> koymamaktı, tahminin kendisini engellemek değil. Elimizde kalibre ve **ölçülmüş** bir
> tahminci var; onu ölçülen isabetiyle birlikte göstermek doktrinin yasakladığı şey değil,
> tam olarak istediği şeydir. **C2 koşulsuzdur.**

Tek kural yerinde duruyor ve sertleşti: **hiçbir sayı ölçülmüş isabeti olmadan arayüze
çıkmaz.** Bir tahmin gösterilecekse yanında "bu tahminci 540 maçta %55,6 tutturdu, tek
kolonla 14+ hiç gelmedi" yazacak. Süslenmiş bir olasılık, süslenmemiş bir yalandır.

| # | İş | Koşul |
|---|---|---|
| **C1** | Sentez katmanı (`insights.py`) | §6.6 G2'nin dört kuralı geçerli |
| **C2** | **Tahmin arayüzü** | ✅ **BİTTİ** (§3.17) — `/tahmin`, `/api/tahmin` |
| **C3** | Sayfayı soruya göre bölme | ✅ **BİTTİ** (Faz 4.4) — `/istatistik` · `/istatistik/oranlar` · `/istatistik/geri-test`, ortak sekme şeridi; beş sayfanın beşi de 3.500 px bütçesinin altında (ölçüldü) |
| **C4** | Dilim dürüstlüğü, gezinme, mobil | = eski **G3–G5** |

#### C2'nin üç parçası — sırayla

> **Bu bölüm C2 yapılMADAN önceki durumu anlatır ve tarihçe olarak duruyor.**
> C2 bitti (aynı belgede §6.2'deki tabloda "✅ BİTTİ" işaretli): `web_app.py`
> tahmin katmanını import ediyor, `/api/tahmin` yayında ve `/tahmin` sayfası
> var. Aşağıdaki "yok" cümleleri o günün fotoğrafıdır.

Bugün *(C2 öncesi)* tahmin katmanı **ürüne hiç bağlı değildi**: `web_app.py` onu
import etmiyordu, API uçlarının hiçbiri tahmin döndürmüyordu, `/tahmin` diye bir
sayfa yoktu. Ölçüm aracı olarak yaşıyordu, ürün olarak değil. Eksik olan üç şey:

| | İş | Neden gerekli |
|---|---|---|
| **C2a** | ✅ Canlı oran (`build_fixtures.py`) | football-data `fixtures.csv` — **ölçümün yapıldığı kaynağın kendisi**; iddaa bülteni yedek |
| **C2b** | ✅ `/api/tahmin` | Olasılık + ölçülmüş isabet + sınırlar, tek gövdede ve **ayrılamaz** |
| **C2c** | ✅ `/tahmin` sayfası | İsabet tablonun **üstünde**; sınırlar katlanmaz |

Üçü de bitti ve hiçbiri Faz B'yi beklemedi.

### 6.5 Faz D — sonlanma

Proje şu **dört sorunun tamamı** ölçülmüş cevaba bağlandığında biter:

| # | Soru | Bugün | Nasıl kapanır |
|---|---|---|---|
| 1 | Kapanış çizgisini **yenebiliyor** muyuz? | **hayır, ölçüldü** | A1–A4 (§6.2 A4) — arayış kapandı, tahmin ekseni açık kaldı |
| 2 | Kalabalığı yenebiliyor muyuz? | **bilinmiyor — ama artık "veri yok" diye değil, "veri geldi, ölçülmedi" diye** (§6.3) | B2–B4 |
| 3 | Pozitif beklenen getirili kupon kurulabiliyor mu? | bilinmiyor | B3 |
| 4 | Garanti hâlâ optimal mi? | **evet, kanıtlı** | kapandı |

Faz D'nin tek çıktısı README'ye yazılacak **"Bu proje ne buldu"** bölümüdür: her soru için
ölçülen sayı, örneklem, güven aralığı ve "evet"/"hayır"; her "hayır"ın yanında onu tekrar
açacak koşul. Bu bölüm yazıldığında **yapacak iş kalmaz.**

**İki bitiş de meşrudur:** ölçülmüş bir üstünlük bulunup ürüne çevrilir — ya da her eksende
üstünlük olmadığı **kanıtlanır** ve proje bunu belgeleyerek biter. İkincisi başarısızlık
değildir: bu alandaki araçların neredeyse tamamı birinciyi *iddia eder*, hiçbiri ikinciyi
ölçmez.

### 6.6 Sıra ve eski etiketlerin karşılığı

```
A1 ─┐  ✔ bitti (§3.14)
A2 ─┼─► A4  ✔ arayış kapandı · TAHMİN EKSENİ AÇIK, kapatılmaz
A3 ─┘  ✔ bitti (§3.16)
        B1 ─► B2 ─► B3 ─► B4  (havuz ekseni; B1 paralel başlayabilir)
C3 (bağımsız, her an)
                          └─► C1 (koşullu) · C2 (KOŞULSUZ, sırada)  ─► C4 ─► D
```

**Faz A bitti ve (b) ile kapandı** (§6.2 A4). **B1'in araştırma kısmı da kapandı** — veri geldi (§6.3, PR #14); açık kol artık **B2'nin yanlılık ölçümü**.
**C3 hiçbir şeyi beklemez** (ölçülmüş kusur: 7.210 px, ilk ekranda 3/11 başlık).

**Faz A'nın kapanışı §3.41'de üçüncü kez sınandı ve kapanış yerinde
kaldı.** Dış inceleme (86/100) planın dışından üç eksik gösterdi — Model
Arena, ileri yürüyüş, sızıntı sözleşmesi — üçü de uygulandı ve ilk ikisi
ölçüm üretti. Arena on bir ayrı koşumu ilk kez tek kesitte topladı:
**hiçbir aile piyasayı geçmedi.** İleri yürüyüş bundan fazlasını söyledi:
kronoloji zorlandığında piyasanın artığını öğrenen aileler **2–3 kat
kötüleşiyor**, yani §3.26–§3.35'in küçük kazançlarının bir kısmı kronoloji
dışı eğitimin eseriydi. Bu, A4'ün (b) şıkkını **güçlendiren** dördüncü
kanıttır. Ayrıntı: [`DIS_INCELEME_AZ_RAPORU.md`](DIS_INCELEME_AZ_RAPORU.md).

Eski etiketler kayıp değil, yerleşti:

| Eski | Yeni | Durum |
|---|---|---|
| T1–T5 | Faz A'nın yapılmış kısmı (§3.10–3.13) | bitti |
| — | **A1** (§3.14) | **bitti** |
| — | **A2** (§3.15) | **bitti** |
| — | **A3** (§3.16) | **bitti** |
| — | **A4** (§6.2) | **arayış kapandı; eksen açık** |
| G2 | **C2** — tahmin arayüzü | **bitti** (§3.17) |
| G1 | C3 | **bitti** (§6.8 G1, Faz 4.4) |
| G2 | C1 | koşullu |
| G3–G5 | C4 | bekliyor |
| S1 (korpus ayağı) | Faz A girdisi (§3.12) | bitti |
| S1 (kupon ayağı) | §6.7 — kapalı | bloke |
| S2 | §6.8 | hazır, ek veri gerekmez |
| S3 | Faz A/B girdisi | birikmeyi bekliyor |
| İkramiye verisi | **B1** | **veri geldi** (§6.3, PR #14); ölçüm B2'ye devrolmuş durumda |

### 6.7 S1'in kupon ayağı neden kapalı

İki bağımsız engel ölçüldü:

1. **Sonuç kaynağı sezon parametresi taşımıyor.** `/spor-toto/{week}-hafta-tahminleri/`
   mevcut sezonu döndürür; 2. hafta sorgusu `"2025/2026"` verdi.
2. **`robots.txt` kısıtı.** `User-agent: ClaudeBot → Disallow: /` ve
   `Content-Signal: ai-train=no`. Genel `User-agent: *` bloğu `/spor-toto/` yolunu
   kapatmıyor — kısıt otomatik aracıya özel.

`build_odds.py` da `st_history_2025_26.json`'a bağlı olduğundan kupon tarafı **bir bütün
olarak** bekliyor. Veri geldiğinde altyapı hazır: `evaluate.capraz_olc` ve `sezon_anahtari`
kupon setinde de çalışır.

### 6.8 Faz C ayrıntısı — sayfanın kendisi (eski G kolu)

#### Ölçülen durum

`/istatistik`, 1400 px genişlikte, tüm sezon seçiliyken:

| Ölçüm | Değer |
|---|---:|
| Sayfa boyu | **7.210 px** |
| ↳ "Oranlar ne diyordu?" kartı (6 alt bölüm) | 2.482 px · **%34** |
| ↳ Hafta tablosu (41 satır) | 2.098 px · **%29** |
| ↳ Kalan 9 kart | toplam **%37** |
| İlk ekranda görünen başlık | **3 / 11** |
| Telefonda (390 px) sayfa boyu | 11.250 px |
| ↳ Yatay kaydırma gerektiren tablo | **9'un 8'i** |
| Filtre satırı | `position: static` — kaydırınca kaybolur |
| Sayfa yükünde istek | 2 (`/api/stats` + `/api/backtest`) |

**Kök sorun: sayfa veri kaynağına göre kurulmuş, soruya göre değil.** Kartlar
"`history.py`'dan gelenler" ve "`odds.py`'dan gelenler" diye ayrılmış; kullanıcının soruları
ise başka eksende duruyor ve her birinin cevabı sayfaya dağılmış:

| Kullanıcının sorusu | Cevabın bugün bulunduğu yer |
|---|---|
| "Bu hafta kaç `0` beklemeliyim?" | Bantlar + adet dağılımı + son 6 hafta kutusu — 3 ayrı kart |
| "Hangi maça banko koyabilirim?" | Banko bantları + çift kapsaması — 2.482 px'in içine gömülü |
| "Kaç kolona çıkmalıyım?" | Çift kapsaması + geri test — iki ayrı kart, arası ~800 px |
| "Bu sayılara ne kadar güvenebilirim?" | Kalibrasyon + Brier + veri kalitesi + "az örnek" işaretleri — 4 ayrı yer |

Sayfa bütün parçalara sahip; eksik olan **sentez**. İkinci eksik: sayfa tarif ediyor ama karar
desteklemiyor — "1.35 pratik bir sınır", "1.75–2.00 tuzak bandı" gibi ölçülmüş okumalar bu
belgede yazılı, sayfada okurun kendi çıkarması gerekiyor.

#### G1 — Sayfayı soruya göre böl

**Soru:** 7.210 px'lik tek akışta kullanıcı aradığı cevaba nasıl ulaşacak?

- `/istatistik` → **Sezon**: dağılım, seyir, bantlar, adet, ısı haritası, geçiş, uçlar, hafta
  tablosu, veri kalitesi
- `/istatistik/oranlar` → **Piyasa**: favori kırılımı, banko bantları, çift kapsaması,
  beraberlik profili, lig kırılımı, kalibrasyon, Brier
- `/istatistik/geri-test` → mevcut (§3.5)

Üç sayfada ortak sekme şeridi; `?last=N` href'lerde taşınır.

> **Değişmez kural 3 bozulmuyor, genişliyor.** "Tek filtre satırı" → **"tek dilim"**: aynı anda
> görünen her blok aynı `?last` üzerinden hesaplanır ve sekme geçişinde dilim korunur. F4'te
> filtreyi URL'e taşımak (§3.8) bölmeyi ücretsiz hale getirdi.

Hafta tablosu varsayılan olarak son 12 satır + "41 haftanın tamamı" düğmesi. Kural 2 ("her
görselin tablo karşılığı vardır") bozulmaz: veri kaybolmuyor, bir tık uzağa gidiyor; CSV zaten
tamamını veriyor.

- **Yeniden kullan:** `RangeFilter`, `aralikUrldenOku` / `aralikUrleYaz`, mevcut kart bileşenleri
- **Yeni:** `app/istatistik/oranlar/page.tsx`, ortak sekme şeridi bileşeni
- **Kabul kriteri:** her sayfa < 3.500 px (masaüstü, tüm sezon) · sekme geçişinde dilim korunur
  · `/istatistik` artık `/api/backtest` istemez · hiçbir görsel kaybolmaz
- **Büyüklük:** orta

> **✅ Yapıldı (Faz 4.4).** Dört kriterin dördü de **tarayıcıda ölçüldü** (Chromium,
> 1440×900, tüm sezon):
>
> | sayfa | yükseklik | |
> |---|---:|---|
> | `/istatistik` | 3.225 px | ✅ |
> | `/istatistik/oranlar` | 2.900 px | ✅ |
> | `/istatistik/geri-test` | 3.018 px | ✅ |
> | `/pazarlar` | 1.481 px | ✅ |
> | `/takimlar` | 1.399 px | ✅ |
>
> Ölçüm iki gerçek kusur buldu ve ikisi de düzeltildi. **(1)** `/takimlar`
> 22 ligi birden basıyordu: **26.287 px**, bütçenin yedi katı. Katlanabilir
> kartlar yetmedi (3.569 px — 22 başlık tek başına 1,5 ekran); çözüm lig
> **seçici** oldu, tek tablo basılıyor. **(2)** `/istatistik/geri-test`
> 3.510 px'te kaldı — 28 satırlık eşik taraması tek başına 1.190 px.
> Tarama `BacktestWeeks` ile aynı deseni aldı: ilk 12 satır + *"tamamı"*
> düğmesi, ve **seçili ile en iyi satır her zaman listede** — kısaltma bir
> kararı gizlemiyor.
>
> Öteki üç kriter de ölçüldü: `/istatistik?last=12` yalnızca
> `/api/stats?last=12` istiyor (`/api/backtest` yok), üç sekmenin üçünde de
> `last=12` korunuyor, ve oran bloklarının tamamı `/istatistik/oranlar`a
> **olduğu gibi** taşındı. Dilim taşınması artık kalıcı bir bekçiye bağlı:
> `sekmeAdresi` saf bir modüle (`lib/sekmeler.ts`) alındı ve
> `frontend/scripts/check.mjs` onu tarayıcısız sınıyor.

#### G2 — Sentez katmanı

**Soru:** sayfa tarif ediyor; okurun çıkarması gereken sonucu neden kendisi söylemiyor?

Her sayfanın tepesinde, **veriden türetilen** (elle yazılmayan) kesit okumaları. Prototipin tüm
sezon üzerinde ürettikleri:

> - Favori oranı 1.20–1.35 bandında isabet %77 (39 maç)
> - 1.75–2.00 bandında isabet %50; tutmamanın %71'i beraberlik (104 maç)
> - İlk-iki toplamı %90+ olan maçlarda banko tek başına %84 tutuyor; ikinci işaret 12,5 puan
>   ekliyor (32 maç)
> - Piyasa Brier 0,579 (eşit dağılım 0,667) — 567 maç

**Vaka: naif cümle üretici gürültüyü iddiaya çevirir.** Prototip "isabeti %65'in üstünde olan
en yüksek bandı seç" kuralıyla çalıştırıldığında, son 12 hafta diliminde şu cümleyi üretti:
*"Favori oranı 1.75–2.00 altındayken isabet %67 (39 maç)."* Bu cümle 2.00'a kadar banko
yapılabileceğini ima ediyor — sezon boyu gerçeğin tam tersi. Sebep, o dilimde bantların
tersine dönmesi:

| Favori oranı | Tüm sezon | Son 12 hafta |
|---|---:|---:|
| 1.00–1.20 | %90,9 (11) | %100,0 (2) |
| 1.20–1.35 | %76,9 (39) | %55,6 (9) |
| 1.35–1.50 | %64,1 (64) | %50,0 (16) |
| 1.50–1.75 | %60,4 (106) | %58,1 (31) |
| 1.75–2.00 | %50,0 (104) | **%66,7 (39)** |
| 2.00+ | %46,9 (243) | %42,5 (80) |

**Ders:** tablodaki bir sayı kendi örneklemini yanında taşır ve okur onu iskonto eder; cümle
ise *iddia eder*. Bu yüzden sentez katmanının eşiği tablonunkinden katı olmak zorundadır.

**Dört zorunlu kural:**

1. **Öneri ancak ölçülmüş isabetiyle birlikte çıkar.** Amaç tahmin olduğu için "şu maça
   banko koy" biçiminde bir cümle artık meşrudur — ama yalnızca o önerinin geçmişte ne
   yaptığı (isabet, hold-out, örneklem) cümlenin yanında duruyorsa. Çıplak buyruk hâlâ
   yasak: ölçüsüz öneri, projenin kaçındığı "kazanma hissi satma" davranışının ta kendisidir.
2. **Her cümle bir ölçüme bağlıdır** ve örneklemini yanında taşır.
3. **Eşik cümlesi ancak bantlar monoton ise çıkar** — seçilen bandın altındaki her bant da
   barajı geçmeli. Yukarıdaki son-12 diliminde bu kural cümlelerin *hepsini* susturur; doğru
   davranış budur.
4. **Örneklem yetmiyorsa cümle hiç çıkmaz.** Zayıflatılmış bir cümle değil, sessizlik.

**Nerede üretilecek:** backend. Gerekçe: test edilebilir, `?last` ile zaten hesaplanmış
bloklardan türer, sağlık denetimine bağlanabilir. Arayüz yalnızca basar — ikinci bir doğruluk
kopyası oluşmaz.

- **Yeniden kullan:** `season_1x2_summary` blokları, `history_analytics`, `_wilson`
- **Yeni:** `backend/spor_toto/insights.py`, `/api/stats` içinde `insights` bloğu, 1 arayüz
  bileşeni
- **Kabul kriteri:** `?last=N` değişince cümleler değişir (sabit metin yok) · **monotonluk
  kuralı testle bekçiye bağlı: son-12 dilimi eşik cümlesi üretmemeli** · hiçbir cümle buyurgan
  değil · her cümle örneklemini taşır
- **Büyüklük:** orta-büyük (~200 satır backend + testler + 1 bileşen)

#### G3 — Dilim dürüstlüğü

`?last=6` seçilince 90 maç kalıyor; lig kırılımının ve banko bantlarının çoğu satırı
anlamsızlaşıyor. Satır satır "az örnek" deniyor ama sayfa üst düzeyde susuyor.

Blok başına minimum örneklem eşiği; eşik altındaki blok kart başlığında rozet alır ve kesit
notu toplu uyarı verir: "bu kesitte lig kırılımı ve banko bantları anlamlı değil".

- **Kabul kriteri:** eşik `AZ_ORNEK` ile tek kaynaktan gelir · uyarı `?last` değişince güncellenir
- **Büyüklük:** küçük

#### G4 — Gezinme cilası

Yapışkan filtre + sekme şeridi (7.210 px'lik sayfada filtreyi değiştirmek için başa dönmek
gerekiyor) · bölüm bağlantıları · kart başına iskelet.
**Büyüklük:** küçük

#### G5 — Mobil

9 tablodan 8'i telefonda yatay kayıyor. Hedef "kusursuz" değil **"okunabilir"**: kritik tablolar
dar ekranda kart görünümüne düşer. Kullanım ağırlıkla masaüstü olduğu için sona bırakıldı.
**Büyüklük:** orta

---

### 6.9 Veri tarafı ayrıntısı (eski S kolu)

#### S1 — Örneklem büyütme

Sayıların önündeki en derin darboğaz. 41 hafta üzerinde ölçülen her şey — kalibrasyon, banko
bantları, geri testin eşikleri — dar bir güven aralığıyla geliyor ve hold-out'un 0 çıkması da
bundan bağımsız değil. 2024/2025 sezonu aynı iki boru hattıyla çekilebilirse hafta sayısı
~80'e çıkar. G2'nin monotonluk kuralının kaç dilimde cümle üretebildiği de doğrudan buna bağlı.

- **Önce kontrol:** kaynak sitenin geçmiş sezon payload'ları duruyor mu; football-data
  `mmz4281/2425/` zaten var
- **Yeniden kullan:** `build_history.py`, `build_odds.py` — ikisi de sezon parametreli hale
  gelmeli
- **Kabul kriteri:** iki sezon yan yana sorgulanabiliyor; `data_quality` ikisinde de temiz;
  geri test sezon ayrımı yapabiliyor (birinde eşik seç, ötekinde ölç — gerçek out-of-sample)
- **Büyüklük:** orta

#### S2 — Geri testi zenginleştir

- Sabit kolon bütçesi kipi: "haftada en fazla N kolon" kısıtıyla eşik seçimi
- İkinci strateji ailesi: eşik yerine "en belirsiz k maçı çifte yap" (kolon bedelini
  doğrudan sabitler)
- `butce_danismani` ile bağ: geri testin ürettiği kupon bütçeye sığmıyorsa hangi maç kısılır
- **Büyüklük:** orta

#### S3 — İddaa arşivi olgunlaşınca

Snapshot boru hattı ve haftalık tetik çalışıyor (§3.9). ~10 snapshot biriktikten sonra:

- Snapshot'ları kupon maçlarıyla eşleştir (`build_odds.py`'daki isim normalizasyonu yeniden
  kullanılır)
- İddaa oranı ile piyasa oranını yan yana koy: favori sıralaması ne kadar örtüşüyor, marj
  arındırıldıktan sonra olasılıklar ne kadar yakın
- Geri testi iddaa oranıyla tekrarla — vekil değil, gerçek fiyatla
- **Büyüklük:** küçük (veri geldikten sonra); değeri zamanla birikir

#### S4 — Küçük işler

Geri test sayfasında eşik çiftini URL'e yazmak (`?banko=0.68&uclu=0.38` paylaşılabilir olur) ·
tarama tablosunu CSV'ye çıkarmak · hafta detayında Brier'i göstermek.
**Büyüklük:** küçük

---

#### Masada duran, sırada olmayan

**"Bu hafta" kartı.** Sayfa tamamen geçmişe bakıyor; oysa kullanıcının asıl işi bu haftanın
kuponu. Veri setinde 52./53. hafta açık duruyor ve F5 arşivi (§3.9) tam da bunu besleyebilir —
"bu haftanın maçlarına kesitteki bulguları uygula" kartı sayfayı referanstan araca çevirir.
S3'e bağımlı olduğu için bugün planlanamaz; arşiv birikince yeniden değerlendirilmeli.

## 7. Yapılmayacaklar

Bu bölüm bir kez **yeniden yazıldı** (Faz 0–4). Listedeki beş maddenin
dördü artık üstü çizili ve sebebi tek bir cümlede toplanıyor: **bunların
hiçbiri ölçüm sonucu değildi, hepsi ürün kararıydı.** Kısıtlar
kaldırılınca dördü de yapıldı — ve dördü de yapıldıktan sonra
ölçülüp *"geçmedi"* diye yazıldı. Kısıtı kaldırmak sonucu değiştirmedi;
**bilinebilir olanı** değiştirdi.

Kalan iki madde farklı türden: biri ürünün kendisi (ölçüsüz sayı
çıkmaz), öteki hukuki (`robots.txt`). İkisi de bir sonraki fazda
kalkmayacak.

| Fikir | Neden hayır |
|---|---|
| ~~Takım bazlı istatistik~~ | **Kalktı (§3.35).** Teşhis doğruydu, çare yanlıştı: az örnekli bir ortalamanın gürültülü olması onu yasaklamayı değil, **ne kadarının gürültü olduğunu göstermeyi** gerektirir. Ampirik Bayes küçültmesi az maçlı takımı otomatik olarak lig ortalamasına çeker ve `kucultme` alanı sayının ne kadarının takımın kendi verisi olduğunu söyler. Değişmeyen kural yerinde: `n`, `kucultme` ve %95 aralık sayıdan ayrılamaz |
| Ölçülmemiş tahmincinin arayüze çıkması | Amaç tahmin olsa da isabeti hold-out ile ölçülmemiş hiçbir tahminci sayfaya çıkmaz. Beraberlik profili buna örnektir: sinyal var (%14 → %33) ama zayıf ve tam monoton değil (§3.6) — girdi olarak kullanılır, tek başına tahminci olarak sunulmaz |
| ~~Diğer pazarların arayüze çıkması~~ | **Kalktı (§3.31).** Bu bir ürün kararıydı, bir ölçüm sonucu değil. Alt/üst 2,5 ve Asya handikabı artık `/api/pazar` ve `/pazarlar`da — **ölçülmüş kalibrasyonlarıyla birlikte**. Değişmeyen kural yerinde: ölçüsüz sayı çıkmaz |
| ~~İkramiye / beklenen değer hesabı~~ | **Kalktı (§3.34).** `getiri.py` müşterek beklenen değeri kapalı formda hesaplıyor. Kalkan şey *hesabın yapılmaması*ydı; kalkmayan şey **sayının arayüze çıkmaması** — havuz payı, komisyon ve kalabalık modeli varsayım, ölçüm için ≈71 ikramiyeli hafta gerekiyor ve elde 1 var (§6.3b) |
| Otomatik erişime kapalı kaynaktan veri çekme | **Hukuki, teknik değil — ve tek tek denetlendi.** Maçkolik: `robots.txt` `/api/` yolunu herkese, `anthropic-ai`'yi tamamen kapatıyor (eski açık uç ayrıca ölü). Understat: `User-agent: * / Disallow: /` — **tamamen kapalı** (§3.36). fbref: Cloudflare sorgusu arkasında, `robots.txt` bile JavaScriptsiz servis edilmiyor. Kullanılan üç kaynağın üçü de açık: football-data.co.uk (`Disallow:` boş), `openfootball/*` (kamu malı / CC0) |
| Maç öncesi bilinmeyen bir bilgiyi özellik yapmak | **Eğitim/servis ayrışması.** Kadro ve sakatlık verisi tam bu yüzden alınmadı (§3.36): gerçek kadro ancak ilk vuruşta bellidir, korpusta kullanıp `/tahmin`de kullanamamak ölçümü ürünün tarifi olmaktan çıkarır. Kural kaynak hakkında değil **zamanlama** hakkındadır ve yeni bir kaynak gelse de geçerlidir |

---

## 8. Riskler

**Küçük örneklem.** 41 hafta. Geri testte aşırı uyum ölçüldü ve büyüklüğü belli: taramanın en
iyisi 4 hafta, hold-out 0. Güven aralıkları ve "bu geçmişin en iyisidir, geleceğin garantisi
değildir" uyarısı sayfada görünür durumda; **kaldırılmamalı**. Bu riski gerçekten küçültecek tek
şey daha çok hafta (S1), daha iyi bir eşik değil.

**Geri testin kendi sınırları.** Strateji oranlardan mekanik üretiliyor: sakatlık, motivasyon,
kadro gibi hiçbir dış bilgi yok. Ayrıca gerçek bir oyuncunun 2.686 kolonluk kuponu her hafta
oynamayacağı açık — tablo bir davranışı değil, bir kuralın bedelini ölçüyor.

**Üçüncü parti kaynak.** Hem hafta payload'ları hem oran arşivi dış kaynaklı. Silinir ya da
biçim değiştirirse yeniden çekim gerekir; iki üretim scripti bunun için var.

**Piyasa oranı ≠ iddaa oranı.** Seviye tutmaz, yapı tutar. Sayfada bu not her yerde görünür
durumda; kaldırılmamalı.

**Milli maç haftaları.** 5., 10. ve 15. haftalarda oran yok; oran blokları bu haftalarda boş
gelir ve kapsama hiçbir zaman %100 olmaz.

---

## 9. Çalıştırma ve doğrulama

```bash
# Veri üretimi (ikisi de doğrulamadan dosya yazmaz)
cd backend
python scripts/build_history.py            # tarihsel 1/0/2 setini yeniden üret
python scripts/build_history.py --dry-run  # yazmadan farkı gör
python scripts/build_odds.py               # oranları çek ve eşleştir
python scripts/build_odds.py --dry-run     # yalnızca kapsama raporu
python scripts/snapshot_iddaa.py           # iddaa açık bültenini arşivle
python scripts/snapshot_iddaa.py --dry-run # yazmadan özet
python scripts/build_egitim.py             # eğitim korpusu (iki çizgi birden)
python scripts/build_egitim.py --dry-run   # yazmadan özet
python scripts/build_fixtures.py            # yaklaşan maçlar + oranları

# Tahmin katmanının ölçümleri (korpus gerekir; ~30 sn)
python -m spor_toto.recalibrate            # yeniden kalibrasyon kademesi
python -m spor_toto.cizgi                  # A1: kapanış çizgisi verimliliği
python -m spor_toto.bahisci                # A2: bahisçi anlaşmazlığı
python -m spor_toto.disari                 # A3: piyasa dışı özellikler
python -m spor_toto.tahmin                 # ÜRÜN: yaklaşan maçlara olasılık
python -m spor_toto.avrupa                 # UEFA fikstürünün korpusa değmesi
python -m spor_toto.sehir                  # şehir tablosu ve derbi kapsaması
python scripts/build_xg.py                 # xG kalibrasyonu (§3.42; ağlı, ~25 dk)
python -m spor_toto.takim_gucu --lig T1    # küçültülmüş takım gücü

# Model Arena — bütün aileler TEK kesitte, TEK tabloda (§3.41; ~10 dk)
python -m spor_toto.arena                  # sezon dışarıda bırakmalı
python -m spor_toto.arena --ileri          # kronolojik (ileri yürüyüş)
python -m spor_toto.arena --kupon          # kupon setinde (tek sezon; uyarılı)

# Her ölçüm CLI'sı koşumunu deftere yazabilir (§2.6)
python -m spor_toto.disari --kaydet
python -m spor_toto.kosum                  # kayıtlı koşumlar
python -m spor_toto.kosum --son disari     # son koşumun ortamı

# Denetim
pytest -q                                  # 1.829 test (85'i bu katman, 567'si tahmin)
pytest -n0 -q tests/test_cizgi.py          # tek çekirdek (süit varsayılan `-n auto`)
pytest -q tests/test_history.py            # veri setinin kendi denetimi
pytest -q tests/test_backtest.py           # strateji, skorlama, hold-out
pytest -q tests/test_cizgi.py              # A1 ölçümü ve korpus bütünlüğü
pytest -q tests/test_bahisci.py            # A2 ölçümü ve kaynak seçimi
pytest -q tests/test_disari.py             # A3 ölçümü ve sızıntı bekçileri
pytest -q tests/test_arena.py              # arena kaydı, kesit, çökme tespiti
pytest -q tests/test_sizinti.py            # sızıntı sözleşmesi (§3.41)
pytest -q tests/test_xg.py                 # xG vekili: sızıntı, beyaz liste, kalibrasyon
python -m spor_toto.health                 # 27 değişmez
python -m spor_toto.health --only sizinti_sozlesmesi
python -m spor_toto.health --help          # tek kontrol: ?only=geri_test

# Arayüz
cd frontend && npx tsc --noEmit && npm run build

# İkisi birlikte
bash scripts/run_next_dev.sh               # UI :3000, API :8080
```

**Oran arşivini sorgulamak** (SQLite, uzun biçim):

```sql
SELECT m.week, m.no, m.home, m.away, o.secim, o.deger
FROM oran o JOIN mac m USING (week, no)
WHERE o.pazar = '1X2' AND o.donem = 'kapanis' AND o.kaynak = 'Avg';
```

```python
from spor_toto.odds import load_odds, market_odds, implied_probs
r = load_odds()[0]
implied_probs(market_odds(r, "1X2", "Avg"))   # {"1": .., "0": .., "2": ..}
```

---

## 10. Sözlük

| Terim | Anlamı |
|---|---|
| **Banko** | Bir maça tek sembol işaretlemek |
| **Çift / üçlü** | Bir maça iki / üç sembol işaretlemek; kolon bedelini çarpar |
| **Küme içi** | Gerçek sonucun, işaretlenen sembollerin içinde kalması |
| **14-garanti** | Tahmin küme içindeyse en fazla 1 hatayla en az 14 doğruyu garanti eden kaplama |
| **Kolon bedeli** | Ödenecek tutar. Satır sayısıyla karıştırılmamalı |
| **Marj (overround)** | Bahisçi payı; ham olasılık toplamının 1'i aşan kısmı |
| **Kalibrasyon** | Modelin verdiği olasılığın gerçekleşme sıklığıyla örtüşmesi |
| **Favori** | Oranı en düşük sembol |
| **Underdog galibiyeti** | Favorinin karşı tarafının kazanması (beraberlik değil) |
| **Kapanış oranı** | Maç başlarken geçerli son oran; açılıştan daha bilgilidir |
| **Dilim** | `?last=N` ile seçilen son N hafta |
| **Geri test** | Bir stratejiyi geçmiş haftalarda çalıştırıp sonucunu ölçmek |
| **Aşırı uyum** | Geçmişe o kadar iyi uyan bir seçim ki geleceğe taşınmaz |
| **Hold-out** | Eşiği o haftayı görmeden seçip yine o haftada ölçmek |
| **Brier skoru** | Σ(olasılık − gerçekleşme)². 0 kusursuz, 0,667 eşit dağıtım |
| **Wilson aralığı** | Küçük örneklemde oran için güven aralığı; kenarlarda taşmaz |
