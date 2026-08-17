# İstatistik Katmanı — Durum ve Yol Haritası

**Kapsam:** `/istatistik` sayfası ve onu besleyen veri + oran altyapısı
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
| Tahmin | `backend/spor_toto/egitim.py` | — | Eğitim korpusu okuyucusu (**istatistiğe girmez**) |
| Üretim | `backend/scripts/build_egitim.py` | — | Korpus üretimi (football-data, 4 sezon) |
| Test | `backend/tests/test_predict.py` · `test_evaluate.py` · `test_recalibrate.py` · `test_egitim.py` | — | Tahmin katmanı ve **ayrım bekçisi** (104) |

Backend istatistik/oran/geri test katmanı ~2.434 satır, frontend ~3.585 satır. Backend test
paketi toplam **700 test**; **82'si** istatistik katmanına, **104'ü** tahmin katmanına ait.
`python -m spor_toto.health` **22 değişmez** çalıştırır — ikisi (`oran_arsivi`, `geri_test`)
istatistik katmanını korur; tahmin katmanının henüz değişmezi **yok** (T4).

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

**Okuma.** Aşırı uyum modelin kapasitesinden değil örneklem küçüklüğünden geliyordu; büyük
korpus onu kaldırdı. Ama kalan etki 0,0005–0,0015 Brier — 31 binde anlamlı, 540'ta değil ve
%17,2'lik iddaa marjının yanında hiç. **Yön doğru, miktar yetersiz.**

## 6. Yol haritası

**F1–F5'in tamamı uygulandı** (bkz. §3.5–3.9). Amaç tahmine döndükten sonra **T1–T3
uygulandı** (§3.10–3.12). Bundan sonrası üç koldan gider:

| Kol | Neyi iyileştirir | Durum |
|---|---|---|
| **G1–G5** | **Sayfanın kendisi** — bilgi mimarisi, sentez, kullanım | hiçbiri başlamadı |
| **S1–S4** | **Verinin ve analizin derinliği** — örneklem, strateji, kaynak | S1 kısmen (§6.1) |
| **T1–T6** | **Tahmin katmanı** — ölçüm, model, girdi | T1–T3 bitti |

**Sıra: T4 → G1 → G2 → T5 → G3 → G4 → T6 → S2 → G5 → S3.**

Gerekçe değişti. Önceki sıralamada G kolu başta geliyordu çünkü "var olan gerçeği daha iyi
teslim etmek" en ucuz kazançtı. Amaç tahmine dönünce **teslim edilecek gerçeğin kendisi
değişti**: bugün sayfada gösterilmeyen bir tahmin katmanı var ve ölçülmüş sonucu net. T4
(sağlık değişmezi) öne alındı çünkü küçük ve tahmin katmanının bütün ölçümlerini bekçiye
bağlıyor; G1–G2 hemen arkasından geliyor çünkü sayfa hâlâ mevcut bulguları taşımakta
zorlanıyor.

### 6.1 S1'in durumu — yarısı yapıldı, yarısı kapalı

S1 "örneklem büyütme" idi ve **ikiye ayrıldı**:

| Ayak | Durum |
|---|---|
| **Tahmin ölçümü için örneklem** | **Yapıldı.** Eğitim korpusu: 31.103 maç, 4 sezon, 22 lig (§3.12) |
| **Kupon seti için ikinci sezon** | **Kapalı** — aşağıdaki iki engel |

Kupon ayağının engelleri ölçüldü:

1. **Sonuç kaynağı sezon parametresi taşımıyor.** `/spor-toto/{week}-hafta-tahminleri/`
   mevcut sezonu döndürüyor (2. hafta sorgusu `"2025/2026"` verdi). Geçmiş sezonun
   adreslenebildiğine dair işaret yok.
2. **`robots.txt` otomatik erişimi kısıtlıyor.** `User-agent: ClaudeBot → Disallow: /`,
   ayrıca `Content-Signal: ai-train=no`. Genel `User-agent: *` bloğu `/spor-toto/` yolunu
   kapatmıyor; yani kısıt aracıya özel, kaynağa değil.

`build_odds.py` de `st_history_2025_26.json`'a bağlı olduğu için kupon tarafı **bir bütün
olarak** bekliyor. Veri geldiğinde altyapı hazır: `evaluate.capraz_olc` zaten "bir sette
eğit, ötekinde ölç" yapıyor.

---

### G kolu — sayfanın kendisi

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

### T kolu — tahmin katmanı

Amaç tahmine döndükten sonra kurulan kol. **Sayfaya hiçbir şey çıkmadı** ve bu bilinçli:
ölçülmemiş tahminci arayüze çıkmaz (§7).

#### Yapılanlar

| # | İş | Sonuç |
|---|---|---|
| **T1** | Tahminci sözleşmesi + değerlendirme koşumu (§3.10) | `piyasa` çizgisi 0,5747 |
| **T2** | Piyasanın yeniden kalibrasyonu, 4 basamaklı kademe (§3.11) | Kupon üzerinde eğitilince **hiçbiri geçmedi** |
| **T3** | Eğitim korpusu + çapraz ölçüm (§3.12) | Korpusta eğitilince yön döndü, **anlamlılık kurulamadı** |

#### T4 — Referans skorlarını sağlık değişmezine bağla

**Küçük, ve sıranın başında.** `duzgun` her zaman Brier 0,6667 vermeli, `piyasa` kupon
kesitinde 0,5747 ± dar bir bant. Bu sayılar kayarsa bozulan şey model değil **veri ya da
boru hattıdır** — ve bunu bugün hiçbir şey fark etmez.

- **Yeniden kullan:** `evaluate.karsilastir`, `health.py` kontrol sözleşmesi
- **Yeni:** 1 değişmez (`tahmin_referanslari`)
- **Kabul kriteri:** referans skoru bandın dışına çıkarsa sağlık kırmızıya döner · kontrol
  modelin *kalitesini* değil, ölçümün *tekrarlanabilirliğini* denetler
- **Büyüklük:** küçük

#### T5 — Piyasa dışı girdi: takım formu

Ölçülen sonuç net: piyasanın kendi olasılığını yeniden kalibre etmek yön olarak doğru ama
miktar yetersiz (§5). Sinyal ancak **piyasada olmayan** bir girdiden gelebilir.

En ucuz aday zaten korpusun kaynağında duruyor: football-data CSV'leri maç istatistiği
taşıyor (şut, isabetli şut, korner, faul, kart). Bunlar maç *sonrası* veridir, doğrudan
tahminci girdisi olamaz — ama **yuvarlanan pencereyle takım formu** üretilebilir: son N
maçın şut farkı, isabetli şut oranı, gol beklentisi vekili.

Dürüst beklenti: piyasa formu da fiyatlıyor. Sorulan soru "form bilgi taşıyor mu" değil,
**"piyasanın fiyatladığından fazlasını taşıyor mu"** — ve cevabı T1'in koşumu verecek.

- **Yeniden kullan:** `egitim.korpus_haftalari`, `recalibrate` kademe altyapısı, `capraz_olc`
- **Yeni:** korpusa istatistik sütunları, form özelliği üreteci, kademeye bir basamak
- **Kabul kriteri:** form basamağı `piyasa`'yı korpus içi sezon dışarıda bırakmalı ölçümde
  geçmeli · geçmezse sonuç **olduğu gibi raporlanır**, basamak sayfaya çıkmaz
- **Büyüklük:** orta

#### T6 — Tahmin katmanının arayüzü

Ölçülmüş bir tahminci çıkarsa nasıl gösterilecek. Bugün gösterilecek bir şey yok, o yüzden
sırada geride. Kurallar şimdiden belli:

- İsabet, örneklem ve güven aralığı cümlenin yanında durur (§6 G2 kural 1)
- Korpus sayıları `/istatistik`'e girmez — gerekirse **ayrı sayfa**
- **Büyüklük:** orta

---

### S kolu — verinin ve analizin derinliği

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

### Masada duran, sırada olmayan

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

# Denetim
pytest -q                                  # 664 test (82'si bu katman)
pytest -q tests/test_history.py            # veri setinin kendi denetimi
pytest -q tests/test_backtest.py           # strateji, skorlama, hold-out
python -m spor_toto.health                 # 17 invariant
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
