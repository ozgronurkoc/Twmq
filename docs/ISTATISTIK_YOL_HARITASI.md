# İstatistik Katmanı — Durum ve Yol Haritası

**Kapsam:** `/istatistik` sayfası, onu besleyen veri + oran altyapısı, tahmin katmanı ve
**projenin tamamını kapsayan yol planı** (§6). Dosya adı tarihsel; kapsam §6 ile genişledi.
**Güncellendi:** 2026-08-17 (proje amacı güncellendi — aşağıya bakınız)

> **Amaç değişikliği (2026-08-17).** Projenin amacı artık **veriyi analiz ederek
> kazanma oranını artıracak sonuçlar üretmek ve maç sonucu tahmini yapmaktır**
> (bkz. [`../README.md`](../README.md) §1). Bu belgedeki ölçüm disiplini aynen
> geçerlidir ve daha da kritik hale gelmiştir: tahmin iddiası, ölçülmemiş hiçbir
> sayının arayüze çıkmamasıyla dengelenir. Hold-out **0 hafta**, piyasa Brier
> **0,579**, iddaa marjı **%17,2** — bu üç sayı tahmin katmanının başlangıç
> çizgisidir ve ilerleme bunlara karşı ölçülür.
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
| **Ürün** | `backend/spor_toto/tahmin.py` | — | **Tahmin ürünü (C2)**: yaklaşan maça olasılık + ölçülmüş isabet |
| Üretim | `backend/scripts/build_fixtures.py` | — | Yaklaşan maçlar ve oranları (football-data `fixtures.csv`) |
| UI | `frontend/app/tahmin/page.tsx` | — | Tahmin sayfası |
| UI | `frontend/components/tahmin/parts.tsx` | — | Olasılık çubuğu, isabet kartı, sınırlar |
| Tahmin | `backend/spor_toto/egitim.py` | — | Eğitim korpusu okuyucusu (**istatistiğe girmez**) |
| Üretim | `backend/scripts/build_egitim.py` | — | Korpus üretimi (football-data, 4 sezon, **iki çizgi + bahisçi kırılımı**) |
| Test | `backend/tests/test_predict.py` · `test_evaluate.py` · `test_recalibrate.py` · `test_egitim.py` · `test_cizgi.py` · `test_bahisci.py` · `test_disari.py` · `test_tahmin.py` | — | Tahmin katmanı, **ürün** ve ayrım bekçisi (224) |

Backend istatistik/oran/geri test katmanı ~2.434 satır, frontend ~3.585 satır. Backend test
paketi toplam **906 test**; **82'si** istatistik katmanına, **224'ü** tahmin katmanına ait.
`python -m spor_toto.health` **23 değişmez** çalıştırır — ikisi (`oran_arsivi`, `geri_test`)
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

**Ölçülen.** Varsayılan eşiklerle 36 haftanın **3'ünde** 14+ tutuyor, hafta başına ortalama
**2.686 kolon**. Küme içi kalan hafta **yok** — 15 maçın tamamını işaretlerin içinde tutmak
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
etmiyordu, 11 API ucunun hiçbiri tahmin döndürmüyordu, `/tahmin` diye bir sayfa yoktu.
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

**`/tahmin`** — yaklaşan maçlara 1/0/2 olasılığı, **ölçülmüş isabet kartı tablonun
üstünde** (maç başına %55,6 · haftada 8,33/15 · Brier 0,5747 · 14+ tutan hafta 0/36) ·
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
%2,9–%21,8), hafta başına ort. 2.686 kolon, bir 14 için 32.235 kolon. Küme içi hafta 0.
Taramanın en iyisi 4 hafta (%68/%42 eşiği, 6.995 kolon/hafta), **hold-out 0 hafta** — aradaki
fark aşırı uyumun ölçüsü.

**Piyasanın yanılması** (sayfada var): sezon ortalaması Brier **0,579**; eşit olasılık
vermenin karşılığı 0,667. Piyasa bilgi taşıyor ama az. En sürprizli haftalar 33 (0,753, kısmi),
7 (0,734), 37 (0,700); en tahmin edilebilir 3. hafta (0,348).

**Marj karşılaştırması** (F5 ölçümü): iddaa açık bülteninde ortalama marj **%17,2**, piyasa
oranlarında **%7,26**. İki kaynağın seviyesi bu yüzden tutmaz; favori sıralaması ve marj
arındırılmış yapı tutar.

### 5.1 Tahmin katmanının bulguları (sayfada **yok**)

| Ölçüm | Kesit | Sonuç |
|---|---|---|
| Piyasa çizgisi | 540 kupon maçı | Brier **0,5747** · log 0,9660 |
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
| **Havuz** | Tutturunca ikramiyenin kaçta kaçını aldığın | **Hiç ölçülmedi.** Veri bile yok |
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

Biri geldiğinde açılacak soru bellidir ve altyapı hazır: `cizgi.py`/`bahisci.py`/`disari.py`
deseni aynen kullanılır. Gelmediği sürece **aynı veriyle yeni model denenmez.**

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

Projenin hiç dokunmadığı eksen ve muhtemelen **tek gerçek kaldıraç** — çünkü piyasayı
tahminde yenmeyi gerektirmez.

Spor Toto müşterek bahistir: ikramiye havuzdan kazananlara bölünür. Sonuç: *aynı olasılığa
sahip iki sonuçtan **daha az oynananı** işaretlemek, tutturma olasılığını değiştirmeden
beklenen getiriyi artırır.* Ve kalabalık öngörülebilir davranır — favoriye yığılır. Projenin
kendi verisi bunu söylüyor: favori 567 maçın 311'inde tuttu (%54,9), yani kalabalığın gittiği
yer maçların **yarısında yanlış**.

| # | İş | Not |
|---|---|---|
| **B1** | İkramiye / kazanan verisi | **Faz B'nin ön koşulu.** Hafta başına 13 ve 14 doğru için kazanan adedi + tutar. Kaynak araştırılmadı; **önce fizibilite**, sonra boru hattı. Yoksa Faz B düşer ve bu da bir cevaptır |
| **B2** | Popülerlik modeli | B1 gelene kadar vekil: favori olasılığı → tahmini oynanma payı. B1 gelirse vekil **gerçek veriyle kalibre edilir** |
| **B3** | Beklenen getiriye göre kupon kurma | **Kaplamanın ve havuzun buluştuğu yer; projenin en özgün işi.** "Hangi maça kaç işaret" sorusu ilk kez ölçülmüş bir amaç fonksiyonuyla cevaplanır. Tahmin değil, **kalabalık davranışı** modellenir |
| **B4** | Durma kuralı | *(a)* pozitif beklenen getiri ölçüldü → Faz C · *(b)* veri yok, ya da %17,2 marj + havuz seyrelmesi avantajı yutuyor → eksen kapanır |

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

Bugün tahmin katmanı **ürüne hiç bağlı değil**: `web_app.py` onu import etmiyor, 11 API
ucunun hiçbiri tahmin döndürmüyor, `/tahmin` diye bir sayfa yok. Ölçüm aracı olarak yaşıyor,
ürün olarak değil. Eksik olan üç şey:

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
| 2 | Kalabalığı yenebiliyor muyuz? | bilinmiyor | B1–B4 |
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

**Faz A bitti ve (b) ile kapandı** (§6.2 A4). **B1 artık tek açık kol** — o bir araştırma, kod değil.
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
| İkramiye verisi | **B1** | araştırılmadı |

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
pytest -q                                  # 906 test (82'si bu katman, 224'ü tahmin)
pytest -q tests/test_history.py            # veri setinin kendi denetimi
pytest -q tests/test_backtest.py           # strateji, skorlama, hold-out
pytest -q tests/test_cizgi.py              # A1 ölçümü ve korpus bütünlüğü
pytest -q tests/test_bahisci.py            # A2 ölçümü ve kaynak seçimi
pytest -q tests/test_disari.py             # A3 ölçümü ve sızıntı bekçileri
python -m spor_toto.health                 # 23 değişmez
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
