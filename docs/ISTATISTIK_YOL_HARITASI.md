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
tek kaynak dokümantasyonu) · [`ARCHITECTURE_NEXT.md`](ARCHITECTURE_NEXT.md) (API sözleşmesi)

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
| Analiz | `backend/scripts/super_toto_degerlendir.py` | Sonuç sonrası: kaçakların Poisson-binom dağılımı, banko karnesi, **kalabalık karnesi**, ikramiye özeti |
| Üretim | `backend/scripts/super_toto_sayfa.py` | Hafta raporu sayfası; sayfadaki hiçbir sayı elle yazılmaz, boru hattından okunur |
| Analiz | `backend/scripts/acilis_kapanis.py` | Açılış ↔ kapanış fiyatı, **kupon zamanlamasıyla** (§5.2) |
| Veri | `backend/data/super_toto/<sezon>/hafta_NN{,_kupon}.json` | Elle girilen hafta verisi ve dondurulmuş kupon — köken sınıfı ayrı ([`VERI_TOPLAMA_VE_ISLEME.md`](VERI_TOPLAMA_VE_ISLEME.md) §6B) |
| UI | `frontend/app/super-toto/page.tsx` · `components/super-toto/haftalar.tsx` · `lib/super-toto.ts` | Sezonun hafta şeridi; `?hafta=N` adreste durur |

Backend istatistik/oran/geri test katmanı ~2.434 satır, frontend ~3.585 satır. Backend test
paketi toplam **1.141 test**; **82'si** istatistik katmanına (`history` `odds` `backtest`
`api_stats` `api_backtest` `snapshot_iddaa`), **294'ü** tahmin katmanına ait (`predict`
`evaluate` `recalibrate` `egitim` `cizgi` `bahisci` `disari` `kalibrasyon` `tahmin`
`benzer`). Dosya adlarıyla sayılıdır ki tablo elle bakım gerektirmesin —
`tests/test_belgeler.py` onları gerçek koleksiyona karşı denetler.
`python -m spor_toto.health` **24 değişmez** çalıştırır — ikisi (`oran_arsivi`, `geri_test`)
istatistik katmanını, biri (`tahmin_referanslari`) tahmin katmanının ölçüm koşumunu korur.

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
| **Havuz** | Tutturunca ikramiyenin kaçta kaçını aldığın | **Veri geldi, ölçülmedi** (§6.3, §6.3b). Oynanma 2 hafta, ikramiye kaydı 1 hafta |
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
| **Fikstür verisi** (kupa + Avrupa) | A3'ün kör nokta taraması: deplasman "dinlenmiş" göründüğünde ev takımı piyasayı +0,0655 aşıyor, etki Avrupa liglerinde dört kat güçlü. Türetebildiğimiz yorgunluk vekili fiyatlanmış; **gerçek yorgunluk ölçülmedi** |
| **Kadro / sakatlık** | Hiçbir veri setinde yok. Piyasanın gördüğü, bizim görmediğimiz en büyük girdi |
| **Şehir / rekabet tablosu** | A3'te seyahat ve derbi bu yüzden elendi — hesaplanamadıkları için |
| ~~**xG (Understat)**~~ | **Kaynak değil — ölçülmüş negatif.** Listede yoktu, yani örtük olarak açık duruyordu. Dış bir çalışma 14 xG özelliğiyle denedi ve piyasayı geçemedi; üstelik Understat **Süper Lig'i kapsamıyor**. Ayrıntı: [`DIS_INCELEME.md`](DIS_INCELEME.md) §4 |

Biri geldiğinde açılacak soru bellidir ve altyapı hazır: `cizgi.py`/`bahisci.py`/`disari.py`
deseni aynen kullanılır. Gelmediği sürece **aynı veriyle yeni model denenmez.**

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
| **C3** | Sayfayı soruya göre bölme | = eski **G1**. Bağımsız, her an yapılabilir |
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

Eski etiketler kayıp değil, yerleşti:

| Eski | Yeni | Durum |
|---|---|---|
| T1–T5 | Faz A'nın yapılmış kısmı (§3.10–3.13) | bitti |
| — | **A1** (§3.14) | **bitti** |
| — | **A2** (§3.15) | **bitti** |
| — | **A3** (§3.16) | **bitti** |
| — | **A4** (§6.2) | **arayış kapandı; eksen açık** |
| G2 | **C2** — tahmin arayüzü | **bitti** (§3.17) |
| G1 | C3 | bekliyor |
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

| Fikir | Neden hayır |
|---|---|
| Takım bazlı istatistik | 216 takım, Süper Lig takımları bile 32 maç. Çıkacak sayı güvenilir görünür ama gürültüdür |
| Ölçülmemiş tahmincinin arayüze çıkması | Amaç tahmin olsa da isabeti hold-out ile ölçülmemiş hiçbir tahminci sayfaya çıkmaz. Beraberlik profili buna örnektir: sinyal var (%14 → %33) ama zayıf ve tam monoton değil (§3.6) — girdi olarak kullanılır, tek başına tahminci olarak sunulmaz |
| Diğer pazarların arayüze çıkması | Ürün kararı: 1X2 dışındakiler analiz içindir, arşivde kalır |
| Maçkolik'ten veri çekme | `robots.txt` `/api/` yolunu herkese, `anthropic-ai`'yi tamamen kapatıyor; ayrıca eski açık uç ölü |

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

# Denetim
pytest -q                                  # 1.141 test (82'si bu katman, 294'ü tahmin)
pytest -n0 -q tests/test_cizgi.py          # tek çekirdek (süit varsayılan `-n auto`)
pytest -q tests/test_history.py            # veri setinin kendi denetimi
pytest -q tests/test_backtest.py           # strateji, skorlama, hold-out
pytest -q tests/test_cizgi.py              # A1 ölçümü ve korpus bütünlüğü
pytest -q tests/test_bahisci.py            # A2 ölçümü ve kaynak seçimi
pytest -q tests/test_disari.py             # A3 ölçümü ve sızıntı bekçileri
python -m spor_toto.health                 # 24 değişmez
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
