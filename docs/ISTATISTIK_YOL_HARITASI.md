# İstatistik Katmanı — Durum ve Yol Haritası

**Kapsam:** `/istatistik` sayfası ve onu besleyen veri + oran altyapısı
**Güncellendi:** 2026-08-16
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
GET /api/stats/<week>   ─────────────► /istatistik/<hafta>
        ▲
        │  spor_toto/odds.py          (1X2 özeti, banko bantları, kalibrasyon)
data/odds/odds_2025_26.csv            567 maç · 108 oran sütunu
        ▲
        │  scripts/build_odds.py      (tarih ±1 gün + birebir skor + bulanık ad)
football-data.co.uk arşivi (38 dosya)
```

### 2.2 Dosya haritası

| Katman | Dosya | Satır | Rol |
|---|---|---:|---|
| Üretim | `backend/scripts/build_history.py` | 284 | Veri setini kaynağından üretir, doğrulamadan yazmaz |
| Üretim | `backend/scripts/build_odds.py` | 441 | Oranları kupon maçlarına eşleştirir, CSV + SQLite yazar |
| Okuma | `backend/spor_toto/history.py` | 423 | 6 analiz bloğu, `last=N` dilimleme, veri kalitesi denetimi |
| Okuma | `backend/spor_toto/odds.py` | 292 | 1X2 seçimi, favori kırılımı, banko bantları, kalibrasyon |
| API | `backend/web_app.py` | — | `api_stats`, `api_stats_week` |
| UI | `frontend/app/istatistik/page.tsx` | 425 | Sayfa |
| UI | `frontend/app/istatistik/[week]/page.tsx` | 332 | Hafta detayı |
| UI | `frontend/components/istatistik/charts.tsx` | 969 | 9 görsel + ipucu bileşeni |
| UI | `frontend/components/istatistik/parts.tsx` | 246 | Filtre, kesit notu, sayı kutusu, veri kalitesi paneli |
| UI | `frontend/components/istatistik/weeks-table.tsx` | 155 | Sıralanabilir/aranabilir hafta tablosu |
| UI | `frontend/components/istatistik/viz.ts` | 69 | Renk sözleşmesi, sequential ramp, sütun yolu |
| Test | `backend/tests/test_history.py` | 229 | Veri seti denetimi ve analiz blokları |
| Test | `backend/tests/test_api_stats.py` | 118 | Uç sözleşmesi, dilim, oran alanları |
| Test | `backend/tests/test_odds.py` | 82 | Arşivin geçmiş veriyle hizası |

Backend istatistik/oran katmanı ~1.869 satır, frontend ~2.196 satır. Backend test paketi
toplam **545 test**; bunların **38'i** istatistik/oran katmanına ait.

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
| `weeks` | `normalized_weeks` | hafta satırları (`counts`, `max_streak`, `matches`, …) |

`GET /api/stats/<week>` — `history_week_detail` + `week_1x2`: komşu haftalar, sezon
ortalamasına sapma, sıra, ardışık bloklar, sıra-sıra sezon bağlamı, maç listesi ve maç
numarasına göre 1X2 oranı (`odds`, `odds_hit`).

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
doğruymuş, bozuk olan hafta *içindeki* sıraymış. 51. hafta, `VERI_TOPLAMA_VE_ISLEME.md` §2.4'te
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

## 4. Sayfada bugün ne var

**`/istatistik`** — sezon dağılımı (en sık sonuç + pay çubuğu) · 5 sayı kutusu (sembol
toplamları + son 6 hafta farkı, hafta içi ortalama en uzun seri) · haftalık seyir çizgisi
(crosshair + ipucu) · haftalık bantlar (min–maks, ±1σ, ortanca, ortalama) · haftalık adet
dağılımı · **oran kartı** (4 kutu + favori kırılımı + çapraz tablo + banko bantları +
kalibrasyon) · maç sırasına göre ısı haritası · geçiş matrisi · uçlar ve seriler · hafta
tablosu · veri kalitesi.

**`/istatistik/<hafta>`** — sapma ve sıra kutuları · maç maç tablo (takım, saat, skor, sonuç,
sezon payı, kapanış oranı) · sürprizler · ardışık bloklar · komşu hafta gezinmesi.

---

## 5. Ölçülmüş bulgular

Bunlar hesaplanmış gerçek sayılardır. Bir kısmı sayfada duruyor, bir kısmı henüz durmuyor
(bkz. F3).

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

**Çift kapsama** (sayfada YOK → F3):

| İlk-iki olasılık toplamı | Maç | Gerçek sonuç küme içinde |
|---|---:|---:|
| 0,70–0,80 | 372 | %77,4 |
| 0,80–0,90 | 149 | %86,6 |
| 0,90+ | 32 | %96,9 |

**Beraberlik profili** (sayfada YOK → F3): favori ile ikincinin olasılık farkı 0–0,05 iken
beraberlik %32,7; fark 0,50+ iken %14,3. Sinyal var ama zayıf ve tam monoton değil.

**Lig kırılımı** (sayfada YOK → F3): Süper Lig (285 maç) beraberlik %29,8 / favori isabet %53;
Premier Lig (71 maç) %19,7 / %47,9. Kupon başına ortalama 7 maç Süper Lig'den geliyor, bu fark
"0" bütçesinin nereye harcanacağını değiştirir.

---

## 6. Yol haritası

Önerilen sıra: **F1 → F3 → F2 → F4 → F5.** Gerekçe: F1 diğer her şeyin değerini ölçer.

### F1 — Geri test (en yüksek değer)

**Soru:** "Bu strateji geçen sezon ne yapardı?" 41 haftanın her biri için oranlardan seçim üret
(eşiklerle banko/çift/üçlü), motoru çalıştır, kaç haftada 14 tutardı ve kaça mal olurdu ölç.

- **Veri hazır mı:** evet — 567 maçta 1X2 olasılığı ve gerçek sonuç var
- **Yeniden kullan:** `core.parse_picks`, `core.Encoder`, `core.solve_fix16`,
  `core.merge_rows`, `core.row_cost`, `core.dogrula_kaplama`, `odds.market_odds`,
  `odds.implied_probs`
- **Yeni:** `backend/spor_toto/backtest.py` · `GET /api/backtest` · sayfada bir kart
- **Kabul kriteri:** 41 hafta < 5 sn; eşik taraması tablo halinde; aşırı uyum uyarısı görünür
- **Büyüklük:** orta-büyük (backend ~250 satır, UI 1 kart)

### F2 — Oranlardan `probs` → formül sayfası

**Soru:** motor zaten `probs` alıyor ama kullanıcı 15 maçın olasılığını elle yazıyor.

- **Veri hazır mı:** evet — `match_1x2` marj arındırılmış olasılığı zaten döndürüyor
- **Yeniden kullan:** `frontend/components/formul/prob-grid.tsx`, `lib/api.ts:solve`,
  `SolveRequest.probs`, `lib/utils.ts:normalize`
- **Yeni:** hafta → formül sayfası devri (URL parametresi ya da `sessionStorage`) ve hafta
  detayında "bu haftayı formüle gönder" düğmesi
- **Kabul kriteri:** düğmeye basınca formül sayfası 15 maçın olasılığı dolu açılır
- **Büyüklük:** küçük-orta

### F3 — Karar destek kartları

Bölüm 5'te ölçülmüş üç bulgu sayfaya çıkmıyor: **çift/üçlü kapsama tablosu**, **beraberlik
profili**, **lig kırılımı** (lig etiketi `90d0102` ile düzeldi, `odds.py` üzerinden okunabilir).

- **Yeniden kullan:** `odds.season_1x2_summary` deseni, `charts.tsx:FavouriteBands` tablo düzeni
- **Kabul kriteri:** üçü de `?last=N` dilimine uyar; az örneklemli satırlar işaretli
- **Büyüklük:** küçük (her biri ~1 backend fonksiyonu + 1 tablo)

### F4 — Kullanım cilası

Filtre durumu URL'de (`/istatistik?last=12` paylaşılabilir olur) · hafta tablosundan CSV dışa
aktarma · haftalık Brier skoru ("piyasa hangi hafta yanıldı" — sürpriz haftaları işaretler).
**Büyüklük:** küçük.

### F5 — İddaa bülten arşivi (ileriye dönük)

Geçmiş iddaa oranı alınamıyor. Ama haftalık snapshot alınırsa bir sezonda kendi arşivimiz olur;
bugün başlamanın maliyeti bir cron job.

- **Yeni:** `backend/scripts/snapshot_iddaa.py` + haftalık tetik;
  `sportsbookv2.iddaa.com/sportsbook/events` (411 etkinlik, 410'unda 1X2 pazarı)
- **Büyüklük:** küçük; değeri zamanla birikir

---

## 7. Yapılmayacaklar

| Fikir | Neden hayır |
|---|---|
| Takım bazlı istatistik | 216 takım, Süper Lig takımları bile 32 maç. Çıkacak sayı güvenilir görünür ama gürültüdür |
| "Beraberlik tahmincisi" | Sinyal var (%14 → %33) ama zayıf ve tam monoton değil. Gösterge olarak sunmak dürüst, tahminci diye sunmak değil |
| Diğer pazarların arayüze çıkması | Ürün kararı: 1X2 dışındakiler analiz içindir, arşivde kalır |
| Maçkolik'ten veri çekme | `robots.txt` `/api/` yolunu herkese, `anthropic-ai`'yi tamamen kapatıyor; ayrıca eski açık uç ölü |

---

## 8. Riskler

**Küçük örneklem.** 41 hafta. F1'de eşik taraması yapılırsa aşırı uyum kaçınılmazdır: 41 hafta
üzerinde en iyi görünen eşik gelecek sezon aynısını yapmaz. Sonuçlar güven aralığıyla verilmeli
ve "bu geçmişin en iyisidir, geleceğin garantisi değildir" notu görünür kalmalı — araç zaten
"maç sonucu tahmin etmez" diyor.

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

# Denetim
pytest -q                                  # 545 test (38'i istatistik/oran)
pytest -q tests/test_history.py            # veri setinin kendi denetimi
python -m spor_toto.health                 # 14 invariant

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
