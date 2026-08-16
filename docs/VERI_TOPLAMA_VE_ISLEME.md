# Veri Katmanı — Toplama, İşleme ve Doğrulama

**Kapsam:** projedeki iki veri setinin tamamı — tarihsel 1/0/2 sonuçları ve oran arşivi
**Sürüm:** v2 (sıra hatası kapatıldı, veri maç düzeyine indi, oran arşivi eklendi)
**İlgili belgeler:** [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) (katmanın
durumu ve yol haritası) · [`ARCHITECTURE_NEXT.md`](ARCHITECTURE_NEXT.md) (API sözleşmesi)

| | Tarihsel sonuçlar | Oran arşivi |
|---|---|---|
| **Dosya** | `backend/data/st_history_2025_26.json` | `backend/data/odds/odds_2025_26.csv` |
| **Üreten** | `backend/scripts/build_history.py` | `backend/scripts/build_odds.py` |
| **Okuyan** | `backend/spor_toto/history.py` | `backend/spor_toto/odds.py` |
| **Bekçi** | `backend/tests/test_history.py` | `backend/tests/test_odds.py` |

---

## 1. Veri doktrini

Bu yedi ilke, aşağıdaki her kararın gerekçesidir. Yeni bir veri kaynağı eklerken de bunlar
geçerlidir.

**1. Tek doğruluk kaynağı vardır ve zinciri bellidir.**
Maç listesi → sonuç dizisi → sayımlar. Dizi listeden üretilir, sayımlar diziden sayılır. Üç
temsil de dosyada durur ama biri diğerinden türer; hiçbiri bağımsız yazılmaz.

**2. Kesin olmayan veri elenir, tahmin edilmez.**
15 maçı tam kapanmamış hafta analize hiç girmez. Bir eksik sonuç bile o haftanın 1/0/2
vektörünü bozar. Eksiği doldurmak, ortalamayla tamamlamak, "yaklaşık" saymak yok.

**3. Sıra kaynağın kendi sırasıdır.**
Kupon sırası tahmin edilmez, tarihe göre sıralanmaz, isimden çıkarılmaz. Kaynağın haftaya ait
kendi listesinden okunur. Bu ilke v1'de ihlal edildiği için 41 haftanın 15'i bozuldu (§6.4).

**4. Çelişki gizlenmez, raporlanır.**
Dosyadaki hazır sayım ile diziden türeyen sayım çelişirse fark yutulmaz; `data_quality`
bloğunda listelenir ve **arayüzde gösterilir**. "Sessizce doğru olanı seç" yaklaşımı, hatanın
bir sonraki sefere kadar saklanması demektir.

**5. Doğrulanmadan yazılmaz.**
Üretim scriptleri çıkmadan önce iç tutarlılığı `assert` ile kontrol eder; tutmuyorsa dosya
yazılmaz. Yazıldıktan sonra testler aynı şeyi bağımsız olarak tekrar denetler.

**6. Türetilmiş veri sürümlenir, ham veri sürümlenmez.**
İnsan tarafından okunabilen ve üzerinde konuşulan çıktılar git'e girer. İndirilen ham dosyalar
ve üretilen ikili kopyalar `.gitignore`'dadır — tek komutla yeniden üretilirler.

**7. Kaynak dürüstlüğü.**
Verinin ne OLMADIĞI, ne olduğu kadar önemlidir. Oranlar piyasa oranıdır, iddaa oranı değildir
ve bu her yerde yazar. Bir kaynak otomatik erişime kapalıysa oradan veri çekilmez.

---

## 2. Elimizde ne var

### 2.1 Tarihsel sonuçlar

| Alan | Değer |
|---|---|
| Sezon | 2025/2026 |
| Tarih aralığı | 2025-08-18 → 2026-07-27 |
| Hafta | **41** (2.–51. haftalar arası, tamamı 15/15) |
| Maç | **615** |
| 1 / 0 / 2 | 270 (%43,90) · 149 (%24,23) · 196 (%31,87) |
| Haftalık ortalama | 6,59 / 3,63 / 4,78 |
| Maç düzeyi | Her maç için takım adları, başlama saati, skor, kod |

Bant özeti (haftalık adet serisinin dağılımı):

| Sonuç | Ort. | Ortanca | En az–en çok | σ | Üstünde | Üst ort. | Altında | Alt ort. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6,59 | 7 | 4–10 | 1,64 | 21 hf | 7,90 | 20 hf | 5,20 |
| 0 | 3,63 | 4 | 0–8 | 1,69 | 22 hf | 4,91 | 19 hf | 2,16 |
| 2 | 4,78 | 5 | 1–9 | 1,73 | 21 hf | 6,10 | 20 hf | 3,40 |

### 2.2 Oran arşivi

| Alan | Değer |
|---|---|
| Eşleşen maç | **567 / 615 (%92,2)** |
| Tam kapsanan hafta | **36 / 41** |
| Oran sütunu | **108** · toplam 51.683 değer |
| Maç istatistiği | 14 sütun (şut, korner, faul, kart, ilk yarı skoru) |
| Pazarlar | 1X2 · 2.5 alt/üst · Asya handikap — her biri açılış + kapanış |
| Kaynak | football-data.co.uk (piyasa oranları) |

---

## 3. Kaynak seçimi

### 3.1 Değerlendirilen kaynaklar

| Kaynak | Ne için | Karar | Gerekçe |
|---|---|---|---|
| **sportototahmin.com** hafta payload'ları | 15 maçlık liste + skor | **Kullanılıyor** | Maç listesi ve skor aynı kayıtta ve maç nesnesine bağlı; sıra haftanın kendi dizisinde |
| **football-data.co.uk** arşivi | Oran | **Kullanılıyor** | Ücretsiz, geçmişi tam, açılış + kapanış, çok pazarlı; kişisel kullanıma açık |
| `sportoto.gov.tr` | Resmi sonuç arşivi | Kullanılamadı | Toplu, makine dostu arşiv ucu bulunamadı |
| **Maçkolik** | Skor + iddaa oranı | **Kullanılmıyor** | Eski açık uç (`goapi.mackolik.com`) ölü; `robots.txt` `/api/` yolunu herkese, `anthropic-ai`/`GPTBot`/`CCBot`'u tamamen kapatıyor. Teknik engelin yanında açık bir politika sınırı var (§3.3) |
| **iddaa resmi API** (`sportsbookv2.iddaa.com`) | İddaa oranı | İleriye dönük (F5) | Çalışıyor — 411 etkinlik, 410'unda 1X2 — ama **yalnızca açık bülten**; ölçümde 8 günlük pencere. Geriye dönük arşiv ucu yok |
| **Nesine** bülten API'si | İddaa oranı | Aynı | Canlı bülten; geçmiş yok |
| **Misli** sonuç sayfası | Çapraz doğrulama | Nokta atışı kullanıldı | 51. haftanın sonuç satırı bağımsız doğrulama için kullanıldı (§6.2) |

### 3.2 Neden geçmiş iddaa oranı yok

Kısa cevap: **hiçbir açık kaynak yayınlamıyor.** İddaa ve bayileri (Nesine, Misli, Bilyoner)
yalnızca açık bülteni servis eder; kapanan maçın oranı API'den düşer. O veri Maçkolik gibi
sitelerin maç sayfalarında durur, ama orası otomatik erişime kapalıdır.

Sonuç: **geçmiş için piyasa oranı** kullanıyoruz. Seviye tutmaz (iddaa marjı daha yüksek),
**favori sıralaması ve marj arındırılmış olasılık yapısı** tutar — analizde kullanılan da budur.
İleriye dönük çözüm F5: haftalık bülten snapshot'ı alınırsa bir sezonda kendi iddaa arşivimiz
olur.

### 3.3 Yasal ve etik sınır

- `robots.txt` bir kaynağın otomatik erişim politikasıdır; ihlal edilmez.
- football-data.co.uk verisi kişisel kullanım için serbesttir; ham dosyalar repoya konmaz,
  yalnızca türetilmiş eşleştirme sürümlenir.
- Kaynak siteler resmi devlet arşivi değildir. Bu yüzden eksik haftalar elenir ve en az bir
  hafta bağımsız kaynakla çapraz doğrulanır. Bu belge "tam sezon resmi dump" iddiası taşımaz;
  **41 tam haftalık filtrelenmiş set** iddiası taşır.

---

## 4. Tarihsel sonuç boru hattı

### 4.1 Kaynak biçimi

`https://sportototahmin.com/spor-toto/{N}-hafta-tahminleri/_payload.json` — Nuxt dehidrasyon
dizisi. Nesneler ya düz değerdir ya da `["Reactive", index]` benzeri referanslarla başka
indekslere işaret eder; çözümleyici referansı takip ederek skalere iner (derinlik sınırı 12).

Maç kaydının zinciri:

```
{ homeTeamName: <ref>, awayTeamName: <ref>, match: <ref> }
        └─ match  → { date: <ref>, score: <ref> }
                        └─ score → { homeRegular: <ref>, awayRegular: <ref> }
```

Skorlar **maç nesnesinin kendi zinciri** üzerinden alınır. "İlk 15 isim + ilk 15 skor listesini
sırayla yapıştır" yaklaşımı denenmiş ve reddedilmiştir: skorlar farklı bloklarda tekrarlandığı
için yanlış maç–skor eşleşmesi üretir.

### 4.2 Hangi blok — doktrin 3'ün uygulanışı

Payload içinde maça benzeyen **birden fazla blok** vardır:

| Blok | İçerik | Kullanılır mı |
|---|---|---|
| `{weekNumber, matches: [...]}` | Haftanın kendi 15 maçı, kupon sırasıyla | **Evet, yalnızca bu** |
| `nearbyWeekSummaries[].featuredMatches` | Komşu haftaların 3'er öne çıkan maçı | Hayır |

**Kural:** hafta nesnesini `weekNumber` ile bul, yalnızca onun `matches` dizisini sırasıyla
çöz, başka hiçbir bloğa bakma. Diziyi baştan sona tarayıp maça benzeyen her nesneyi toplamak,
öne çıkan maç blokları araya girdiğinde sırayı bozar (§6.4).

Bunun bir yan sonucu: **tekilleştirmeye gerek yoktur.** Tek ve doğru listeden okunduğu için
mükerrer kayıt oluşmaz.

### 4.3 Hafta meta alanları

Aynı bilgi payload'da **iki farklı adla** durur:

| Nesne | Kapanış tarihi | Sezon |
|---|---|---|
| Haftanın kendi kaydı (`matches` taşıyan) | `roundCloseDate` | `year` |
| `nearbyWeekSummaries` içindeki komşu özet | `closeDate` | `season` |

Script önce haftanın kendi kaydına, bulamazsa komşu özetine bakar. (Yeniden üretimin ilk
denemesinde yalnızca `closeDate` aranıyordu ve tüm tarihler boş çıktı — hata testte değil,
üretim çıktısına bakılırken yakalandı.)

### 4.4 Maç satırı üretimi

Haftanın `matches` dizisi üzerinde, sırayı bozmadan:

1. Ev ve deplasman adını çöz
2. `match.score.homeRegular` / `awayRegular` çöz
3. Gol değerleri `int` ve `0…20` aralığında mı kontrol et — anlamsız parse reddedilir
4. `match.date` → başlama saati (`YYYY-MM-DD HH:MM`, UTC)
5. Sonuç kodu: `home > away → 1` · `home == away → 0` · `home < away → 2`

**Yalnızca normal süre.** `homeRegular` / `awayRegular` kullanılır; uzatma ve penaltı alanları
dahil edilmez — Spor Toto maç sonucu normal süre üzerinden okunur.

### 4.5 Kesinlik eşiği

| Geçerli maç sayısı | Karar |
|---|---|
| **= 15** | Analize dahil |
| **≠ 15** | Elenir |

Bu sette elenen 12 hafta:

| Hafta | Durum |
|---:|---|
| 1 | 12 geçerli maç |
| 23 | 14 |
| 34 | 14 |
| 43–49 | 0 (yaz arası) |
| 52 | 3 (henüz kapanmamış) |
| 53 | 0 (aktif) |

### 4.6 Özet ve bant hesabı

```text
N          = kabul edilen hafta sayısı
T          = N × 15
sum_r      = tüm maçlarda r ∈ {1,0,2} adedi
pct_r      = 100 × sum_r / T
avg_r      = sum_r / N                      # haftalık ortalama

above      = { n_r | n_r >  avg_r }         # ortalama üstü kapatan haftalar
below      = { n_r | n_r <= avg_r }
above_gap  = mean(above) − avg_r
below_gap  = avg_r − mean(below)
```

Ayrıca min, ortanca, maks ve **popülasyon** standart sapması kaydedilir.

> Not: bantlar `history.py` tarafından **çalışma anında haftalardan yeniden hesaplanır**;
> dosyadaki değerler bilgi amaçlıdır. Sebep: `?last=N` dilimi alındığında bantların da o dilime
> göre hesaplanması gerekir.

### 4.7 Çıkış şeması

```jsonc
{
  "meta": {
    "season": "2025/2026",
    "date_from": "2025-08-18", "date_to": "2026-07-27",
    "weeks": 41, "matches": 615,
    "source": "sportototahmin week payloads (week.matches order, match-linked scores); …",
    "rule": "only weeks with exactly 15 results; match order from the week's own matches array",
    "generated_at": "2026-08-15"
  },
  "totals":     { "1": 270, "0": 149, "2": 196,
                  "pct_1": 43.9024, "pct_0": 24.2276, "pct_2": 31.8699 },
  "weekly_avg": { "1": 6.5854, "0": 3.6341, "2": 4.7805 },
  "bands": {
    "1": { "avg", "min", "max", "median", "std",
           "above_n", "below_n", "above_mean", "below_mean", "above_gap", "below_gap" },
    "0": { … }, "2": { … }
  },
  "weeks": [
    {
      "week": 51,
      "close_date": "2026-07-27",
      "season": "2025/2026",
      "n1": 7, "n0": 4, "n2": 4,
      "results": "000111122212011",        // matches'ten üretilir
      "matches": [
        { "no": 1, "home": "AGF Aarhus", "away": "Brondby",
          "kickoff": "2026-07-25 16:00", "hg": 1, "ag": 1, "code": "0" }
        // … 15 adet
      ]
    }
  ]
}
```

---

## 5. Oran boru hattı

### 5.1 Kaynak dosyalar

İki tür, toplam 38 dosya:

| Tür | Örnek | Sütun | İçerik |
|---|---|---:|---|
| Ana ligler | `mmz4281/2526/T1.csv` | 131 | 1X2 (11 bahisçi, açılış + kapanış), 2.5 alt/üst, Asya handikap, maç istatistikleri |
| Ek ülkeler | `new/POL.csv` | 25 | Yalnızca kapanış 1X2, 4 kaynaktan |

Ana ligler: İngiltere (E0–E3, EC), İskoçya (SC0–SC3), Almanya (D1, D2), İtalya (I1, I2),
İspanya (SP1, SP2), Fransa (F1, F2), Hollanda (N1), Belçika (B1), Portekiz (P1), Türkiye (T1),
Yunanistan (G1). Ek ülkeler: ARG, AUT, BRA, CHN, DNK, FIN, IRL, JPN, MEX, NOR, POL, ROU, RUS,
SWE, SWZ, USA.

### 5.2 Eşleştirme

**Anahtar: tarih (±1 gün) + BİREBİR skor + bulanık takım adı (eşik 0,55).**

Skor şartı yanlış eşleşmeye karşı en güçlü korumadır: aynı gün aynı skorla biten, adı da
benzeyen başka bir maç bulma ihtimali pratikte yoktur. Ad benzerliği ayrıca eşiği geçmek
zorundadır.

İsim normalizasyonu:
1. Türkçe karakterler sadeleştirilir, aksan atılır
2. **Sponsor ekleri** çıkarılır: `Hesap.com Antalyaspor` → `antalyaspor`,
   `Natura Dünyası Gençlerbirliği` → `gençlerbirliği`
3. Hukuki/genel ekler atılır (`a.ş.`, `fk`, `fc`, `sk`, `kulübü`, `1907`…)
4. Bilinen kısaltmalar için eş tablosu: `Buyuksehyr` → `basaksehir`, `Ath Bilbao` →
   `athletic bilbao`, `M'gladbach` → `borussia monchengladbach` …

> **Dikkat:** sponsor listesine takımın kendi adı asla girmez. Bir defasında
> `genclerbirligi` yanlışlıkla sponsor listesine düştü ve kapsama %92,2'den %87'ye indi;
> kod içinde bu uyarı yorum olarak duruyor.

### 5.3 Kapsama

| | Değer |
|---|---|
| Eşleşen | 567 / 615 (%92,2) |
| Tam kapsanan hafta | 36 / 41 |
| Eşleşmeyen | 48 maç |

Eşleşmeyenlerin dağılımı **yapısaldır**, gürültü değil:

| Neden | Maç |
|---|---:|
| Milli maç haftaları (5, 10, 15) — kaynak milli maç yayınlamıyor | 45 |
| K-League (50. hafta) — kaynakta yok | 2 |
| Tek eşleştirme kaçağı (33. hafta) | 1 |

### 5.4 Toplanan pazarlar

| Pazar | Dönem | Değer adedi |
|---|---|---:|
| 1X2 | kapanış | 16.179 |
| 1X2 | açılış | 15.796 |
| Asya handikap | açılış | 5.564 |
| Asya handikap | kapanış | 4.742 |
| 2.5 üst | kapanış / açılış | 2.369 / 2.332 |
| 2.5 alt | kapanış / açılış | 2.369 / 2.332 |

Ayrıca aynı satırdan bedavaya gelen 14 maç istatistiği: `HS/AS` (şut), `HST/AST` (isabetli),
`HC/AC` (korner), `HF/AF` (faul), `HY/AY` (sarı), `HR/AR` (kırmızı), `HTHG/HTAG` (ilk yarı).

### 5.5 Depolama katmanları

| Dosya | Sürümlenir | İçerik |
|---|---|---|
| `data/odds/odds_2025_26.csv` | **evet** | Maç başına bir satır, 108 oran + 14 istatistik sütunu (332 KB) |
| `data/odds/odds_rapor.json` | **evet** | Kapsama, sütun sözlüğü, eşleşmeyen maç listesi |
| `data/odds/odds.sqlite3` | hayır | Sorgulanabilir kopya, **uzun biçim** |
| `data/odds/_kaynak/*.csv` | hayır | İndirilen ham dosyalar (12 MB) |

SQLite şeması — analiz için uzun biçim, sütun adı ayrıştırılmış:

```sql
mac(week, no, kickoff, home, away, hg, ag, code,
    kaynak_dosya, kaynak_lig, kaynak_ev, kaynak_dep, guven)
oran(week, no, sutun, kaynak, pazar, secim, donem, deger)   -- pazar: 1X2|2.5U|2.5A|AH
istatistik(week, no, ad, deger)
```

`AvgCH` gibi bir sütun adı `(kaynak=Avg, pazar=1X2, secim=1, donem=kapanis)` diye çözülür;
böylece "piyasa ortalamasının kapanış 1X2'si" tek `WHERE` ile alınır.

### 5.6 Eşleştirmenin sağlaması

Eşleştirme doğruysa oranların gerçeklikle uyumlu davranması gerekir — ölçüldü:

- Kapanış favorisi **%54,9** tuttu; favori **hiçbir maçta beraberlik çıkmadı** (374 kez "1",
  193 kez "2") — futbolun bilinen tablosuyla uyumlu
- Marj arındırılmış olasılıklar gerçekleşmeyle kova kova örtüşüyor (ör. %20–30 kovası: model
  %25,6 → gerçek %24,4)
- Ortalama marj %7,26

Rastgele ya da kaymış bir eşleştirme bu tabloyu üretemez. `test_odds.py` favori isabetini
alt/üst sınırla bekçiye bağlar.

---

## 6. Kalite güvencesi

### 6.1 Üretim anında

`build_history.py` dosyayı yazmadan önce her hafta için:

```python
assert len(results) == 15 == len(matches)
assert (n1, n0, n2) == tuple(results.count(s) for s in "102")
assert results == "".join(m["code"] for m in matches)
```

Yani liste, dizi ve sayımların üçü birbirini tutmadan çıktı üretilmez.

### 6.2 Bağımsız çapraz doğrulama

51. hafta için Misli sonuç satırı: `X X X 1 1 1 1 2 2 2 1 2 X 1 1` → `000111122212011`.
Üretim çıktısı **birebir aynı**. Bu, yalnızca kodların değil **sıranın** da en az bir haftada
bağımsız kaynakla doğrulandığı anlamına gelir.

### 6.3 Okuma anında — `data_quality` bloğu

`history.py` her okumada veri setini denetler ve sonucu API'ye koyar:

| Alan | Ne yakalar |
|---|---|
| `count_conflicts` | Dosyadaki `n1/n0/n2` ile diziden türeyen sayım çelişiyor |
| `match_conflicts` | Maç listesinin kodları diziyle örtüşmüyor (sıra dahil) |
| `weeks_without_matches` | Hafta maç listesi taşımıyor |
| `incomplete_weeks` | 15 maçtan az |
| `duplicate_results` | İki hafta birebir aynı diziyi taşıyor |
| `ok` | Hepsi temizse `true` |

Bu blok **arayüzde gösterilir**. Temizse yeşil bir satır, değilse hangi haftada ne olduğu.

### 6.4 Vaka: v1 sıra hatası

**Belirti.** Veri seti kendi içinde çelişiyordu: 6 haftada `n1/n0/n2` ile dizinin sayımı
tutmuyordu; ayrıca iki hafta çifti (22–25 ve 24–26) **birebir aynı** sonuç dizisini taşıyordu.

**Teşhis.** Kaynak payload'lar yeniden çekilip 9 hafta tek tek karşılaştırıldı. Çelişkili 6
haftanın **hepsinde** dosyadaki `n1/n0/n2` kaynakla birebir uyuştu — hatalı olan `results`
dizisiydi. Sıra kontrolü daha geniş hasar gösterdi: 41 haftanın **26'sında** dizi doğru,
**15'inde sıra yanlıştı** (bunların 6'sında sayım da).

**Sebep.** §4.2: düz tarama, `featuredMatches` bloklarını haftanın kendi listesine karıştırıyordu.

**Etki.** Sezon toplamları ve bantlar etkilenmedi (onlar `n1/n0/n2` üzerindendi). Ama **sıraya
bağlı** her analiz — maç sırası dağılımı, geçiş matrisi, seriler — 15 haftada kirliydi.

**Düzeltme.** Veri seti kaynağından yeniden üretildi: 26 hafta aynı kaldı, 9'unda sıra, 6'sında
sıra + sayım düzeldi, mükerrer diziler ortadan kalktı. `close_date` alanlarının 41/41'i v1 ile
aynı çıktı — hafta eşlemesi baştan doğruymuş, bozuk olan hafta *içindeki* sıraymış.

**Ders.** Sayım doğru olduğu için hata gözden kaçmıştı; sıra hiçbir toplamı değiştirmiyordu.
Bugün `match_conflicts` denetimi tam olarak bunu yakalar.

### 6.5 Vaka: BOM hatası

football-data ana lig dosyaları latin-1 okunuyor; UTF-8 BOM bu kodlamada `ï»¿` olarak gelip ilk
sütunun adına yapışıyor (`ï»¿Div`). Temizlik yalnızca `﻿` arıyordu, bu yüzden `Div`
anahtarı hiç bulunamıyor ve **539 maçın lig etiketi boş kalıyordu**. Düzeltildikten sonra 15
lig doğru etiketlendi — Süper Lig'de beraberlik %29,8, Premier Lig'de %19,7 gibi kırılımlar
ancak bu alanla mümkün.

**Ders.** Boş kalan bir alan hata vermez, sadece sessizce kaybolur. Üretim çıktısındaki özet
tablolar (script'in bastığı lig dağılımı) bunu yakalayan şeydi.

### 6.6 Test bekçileri

| Test | Neyi garanti eder |
|---|---|
| `test_history.py::test_veri_seti_temiz` | Yayındaki veri seti `data_quality` denetiminden geçiyor |
| `test_history.py::test_mac_listesi_diziyi_uretir` | Kod skordan, dizi maç sırasından türüyor |
| `test_history.py::test_ayni_hafta_icinde_takim_tekrar_etmez` | Aynı hafta aynı takım iki kez yok |
| `test_history.py` (analiz blokları) | Sütun toplamları sezon toplamına eşit; dilimleme tutarlı |
| `test_odds.py::test_arsiv_gecmis_veriyle_birebir_hizali` | Oran satırları kupon maçlarıyla sıra sıra aynı |
| `test_odds.py::test_favori_isabeti_gerceklikle_uyumlu` | Favori isabeti %45–70 bandında (eşleştirme kaymışsa çıkar) |
| `test_api_stats.py` | Uçların sözleşmesi; **diğer pazarların arayüze sızmadığı** |

Toplam 38 test bu iki veri setini korur (backend paketi 545 test).

### 6.7 Bilinen kabuller

| Kabul | Gerekçe |
|---|---|
| Yalnızca normal süre golü | Spor Toto sonucu normal süre üzerinden okunur |
| Gol aralığı 0–20 | Anlamsız parse değerlerini reddetmek için |
| Kupon sırası = kaynağın sırası | Resmi bülten numaralandırmasıyla ayrıca karşılaştırılmadı; 51. hafta bağımsız doğrulandı (§6.2) |
| Oran = kapanış, yoksa açılış | Kapanış daha bilgilidir; kaynak sırası Avg → B365 → PS → BFE → Max |
| Lig bilgisi oran arşivinden gelir | Payload maç kaydı lig adı taşımıyor |

---

## 7. Sınırlar

1. **Tam sezon değil:** 41 / ~53 hafta. Eksik skorlu haftalar bilinçli olarak yok.
2. **Tek sezon:** 2025/2026. İstatistiksel güç sınırlı — 41 hafta küçük örneklem.
3. **Milli maç haftalarında oran yok** (5, 10, 15). Oran blokları o haftalarda boş; kapsama
   hiçbir zaman %100 olmayacak.
4. **Geçmiş iddaa oranı yok** (§3.2). Piyasa oranı vekildir.
5. **Üçüncü parti kaynak riski:** iki kaynak da dış. Silinir ya da biçim değiştirirse yeniden
   çekim gerekir; iki üretim scripti tam olarak bunun için var.
6. **Resmi bülten numarası doğrulanmadı:** kupon sırası kaynağın sırasıdır.

---

## 8. Yeniden üretim

```bash
cd backend

python scripts/build_history.py              # tarihsel seti üret
python scripts/build_history.py --dry-run    # yazmadan farkı gör
python scripts/build_history.py --cache /tmp/p   # payload'ları sakla/oradan oku

python scripts/build_odds.py                 # oranları çek ve eşleştir
python scripts/build_odds.py --dry-run       # yalnızca kapsama raporu
python scripts/build_odds.py --no-sqlite     # yalnızca CSV + rapor

pytest -q tests/test_history.py tests/test_odds.py   # bağımsız denetim
```

Her iki script de doğrulamadan dosya yazmaz; testler yazıldıktan sonra aynı şeyi tekrar
denetler. Ham dosyalar ve SQLite git dışıdır, bu komutlarla yeniden oluşur.

**Okuma tarafı:**

```python
from spor_toto.history import history_summary, history_weeks, history_analytics, history_week_detail
from spor_toto.odds import load_odds, market_odds, implied_probs, season_1x2_summary

history_summary(last=12)                      # son 12 hafta dilimi
implied_probs(market_odds(load_odds()[0], "1X2", "Avg"))
```

---

## 9. Yol haritasının veri tarafı

[`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) fazlarının veri ihtiyacı:

| Faz | Veri durumu |
|---|---|
| **F1 — Geri test** | **Hazır.** 567 maçta olasılık + gerçek sonuç var; ek veri gerekmez |
| **F2 — Oranlardan `probs`** | **Hazır.** `match_1x2` marj arındırılmış olasılığı zaten döndürüyor |
| **F3 — Karar destek kartları** | **Hazır.** Lig etiketi §6.5 ile düzeldi; çift kapsama ve beraberlik profili mevcut alanlardan hesaplanır |
| **F4 — Kullanım cilası** | Veri tarafı yok |
| **F5 — İddaa bülten arşivi** | **Yeni boru hattı gerekir.** `snapshot_iddaa.py` haftalık çalışıp bülteni tarih damgalı saklar; şema oran arşiviyle aynı uzun biçim olmalı ki iki kaynak yan yana sorgulanabilsin |

**Örneklem büyütme (öneri, planda yok):** 2024/2025 sezonu aynı iki boru hattıyla çekilebilirse
hafta sayısı ~80'e çıkar. Geri testin aşırı uyum riskini azaltmanın en doğrudan yolu budur;
kaynak sitenin geçmiş sezon payload'larını taşıyıp taşımadığı kontrol edilmeli.

---

## 10. Sürüm geçmişi

| Sürüm | Ne değişti |
|---|---|
| **v1** (2026-08-15) | İlk üretim. 41 hafta, 615 maç. Sonuç dizisi 15 haftada yanlış sırada, 6'sında yanlış sayımda (§6.4) — o zaman fark edilmedi |
| **v2** (2026-08-16) | Sıra hatası kapatıldı; veri **maç düzeyine** indi (takım, saat, skor); üretim tek komutla tekrarlanabilir oldu; `data_quality` denetimi ve test bekçileri eklendi; **oran arşivi** kuruldu (§5) |

Sezon toplamları v1 ve v2'de aynıdır (270/149/196) — çünkü v1'de bozuk olan yalnızca diziydi,
sayımlar doğruydu.

---

Bu belge veri katmanının tek kaynak dokümantasyonudur. Sayfanın kendisi, alınan ürün kararları
ve yol haritası için: [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md).
