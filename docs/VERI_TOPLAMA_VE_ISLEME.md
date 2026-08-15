# Spor Toto Tarihsel 1 / 0 / 2 Veri Toplama ve İşleme Raporu

**Dosya:** `backend/data/st_history_2025_26.json`  
**Üretici:** `backend/scripts/build_history.py`  
**Modül:** `backend/spor_toto/history.py`  
**Üretim tarihi:** 2026-08-15 (v1) · 2026-08-16 (v2 — yeniden üretim)  
**Sezon:** 2025 / 2026  

> **v2 notu.** İlk üretimde sonuç dizisinin **sırası** 41 haftanın 15'inde,
> **sayımı** ise 6'sında hatalıydı. Sebep §6.10'da; düzeltme artık tek komutla
> tekrarlanabilir (`python scripts/build_history.py`). Sezon toplamları
> değişmedi (270 / 149 / 196) çünkü dosyadaki `n1/n0/n2` alanları baştan
> doğruydu — bozuk olan `results` dizisiydi. Veri seti artık her hafta için
> **maç listesini** (takım adları, başlama saati, skor) da taşır.

Bu belge, tarihsel 1 / 0 / 2 istatistik setinin **nasıl elde edildiğini**, **nasıl işlendiğini** ve işlerken **nelere dikkat edildiğini** eksiksiz kaydeder. Amaç: aynı yöntemle tekrar üretilebilirlik ve şeffaflık.

---

## 1. Amaç

Sistemde kullanılmak üzere şu sorulara **kesin (15/15 dolu haftalarla)** cevap üretilmesi:

1. Hangi tarih aralığı kapsanıyor?
2. Toplam kaç hafta ve kaç maç var?
3. Kaç maç **1** (ev), kaç **0** (beraberlik), kaç **2** (deplasman) bitti?
4. Yüzdesel dağılım nedir?
5. Haftalık ortalama (15 maç üzerinden) nedir?
6. Ortalama **üstünde** / **altında** kapatan hafta sayıları nedir?
7. Üstünde / altında kapatan haftaların kendi ortalaması ve ortalamadan sapması nedir?

**Kural (kullanıcı kararı):** %100 kesin olmayan veri **elenir**. Sadece tam 15 sonucu olan haftalar analize girer.

---

## 2. Kaynak seçimi ve sınırlar

### 2.1 Hedef mimari (plan)

```
Resmi / arşiv bülten (15 maç listesi)
        ↓
Her maçın skoru (mümkünse Maçkolik)
        ↓
1 / 0 / 2 dizisi
        ↓
Sadece 15/15 haftalar → özet istatistik
```

### 2.2 Maçkolik

- Tarihsel ve açık kaynak scraper’larda bilinen endpoint:  
  `http://goapi.mackolik.com/livedata?date=dd/mm/yyyy`
- Bu çalışma ortamında endpoint **DNS çözülemedi** (`Name or service not known`).
- Sonuç: Maçkolik üzerinden canlı skor çekimi **yapılamadı**.

**2026-08-16 tekrar kontrolü.** `www.mackolik.com` ayakta (302), ancak
`goapi.mackolik.com` hâlâ ölü. Sitenin `robots.txt` dosyası `/api/` yolunu
**herkese** kapatıyor; ayrıca `GPTBot`, `CCBot`, `Google-Extended` ve
`anthropic-ai` için sitenin tamamı yasak. Yani Maçkolik bu proje için
otomatik bir veri kaynağı değildir — teknik engelin yanında açık bir politika
sınırı da var. Oran kaynakları için bkz. §12.

### 2.3 Kullanılan birincil kaynak

| Özellik | Değer |
|--------|--------|
| Site | [sportototahmin.com](https://sportototahmin.com) |
| Endpoint kalıbı | `/spor-toto/{N}-hafta-tahminleri/_payload.json` |
| Format | Nuxt / Vue serialized JSON payload (index dizisi + referanslar) |
| Sezon alanı | Payload içinde `2025/2026` |
| Neden seçildi | Haftalık **15 maç listesi** ile **skor** aynı kayıtta, **maç nesnesine bağlı** |

**Önemli:** Skorlar “ilk 15 isim + ilk 15 skor” gibi sıraya dayalı kırılgan eşleme ile değil; her maç nesnesinin kendi `match → score → homeRegular / awayRegular` zinciri çözülerek alındı.

### 2.4 Çapraz doğrulama

- **Misli** Spor Toto sonuç sayfası (ör. 51. hafta civarı) tarama sonuçlarında şu satır görünüyordu:  
  `X X X 1 1 1 1 2 2 2 1 2 X 1 1` → kod: `000111122212011`
- Aynı hafta payload çıkarımı: **`000111122212011`** — birebir uyum.
- Bu, maç–skor bağının en az bir kapalı haftada resmi sonuç satırı ile örtüştüğünü gösterir.

### 2.5 Resmi `sportoto.gov.tr`

- Toplu, makine-dostu arşiv API’si bu çalışmada kullanılabilir bulunmadı.
- Bu yüzden birincil paket kaynak sportototahmin hafta payload’ları oldu; kesin sayım için **eksik skorlu haftalar tamamen dışarıda bırakıldı**.

---

## 3. Ham veri yapısı (Nuxt payload)

Payload, tipik Nuxt dehidrasyon dizisidir:

- Büyük bir `list` / dizi.
- Nesneler ya düz değerdir ya da `["Reactive", index]` benzeri referanslarla başka indekslere işaret eder.
- Çözümleyici (resolver) referansı takip ederek son skaler değere iner.

### 3.1 Maç bağlantı şeması (kritik)

Gözlenen ve kullanılan yapı:

```
{
  "homeTeamName": <ref>,
  "awayTeamName": <ref>,
  "match": <ref>
}
```

`match` çözülünce:

```
{
  "date": <ISO datetime ref>,
  "homeTeam": ...,
  "awayTeam": ...,
  "score": <ref>
}
```

`score` çözülünce:

```
{
  "homeRegular": <gol sayısı ref>,
  "awayRegular": <gol sayısı ref>
}
```

Aynı payload içinde tam hafta için genelde:

- 15 adet `homeTeamName` + `match` nesnesi
- 15 adet skor taşıyan eş yapı
- 15 adet `homeRegular` / `awayRegular` skoru

bulunur.

### 3.1.b Maç sırası — v2'nin kritik düzeltmesi

Payload içinde maça benzeyen **birden fazla blok** vardır:

| Alan | İçerik |
|------|--------|
| `{weekNumber, matches: [...]}` | **haftanın kendi 15 maçı, kupon sırasıyla** |
| `nearbyWeekSummaries[].featuredMatches` | komşu haftaların 3'er öne çıkan maçı |

v1, diziyi baştan sona tarayıp `homeTeamName` + `match` taşıyan her nesneyi
topluyordu. Bu, öne çıkan maç blokları araya girdiğinde **sırayı bozuyor**,
bazı haftalarda da yanlış maçı sayıma sokuyordu.

v2 kuralı: **hafta nesnesini `weekNumber` ile bul, yalnızca onun `matches`
dizisini sırasıyla çöz.** Başka hiçbir bloğa bakma.

### 3.2 Hafta meta

İki ayrı yerde, **iki farklı adla** durur:

| Nesne | Kapanış | Sezon |
|-------|---------|-------|
| Haftanın kendi kaydı (`matches` taşıyan) | `roundCloseDate` | `year` |
| `nearbyWeekSummaries` içindeki komşu hafta özeti | `closeDate` | `season` |

v2 önce haftanın kendi kaydına, bulamazsa komşu özetine bakar. (v1 yalnızca
`closeDate` arıyordu; bu yüzden yeniden üretimin ilk denemesinde tüm tarihler
boş çıktı — hata testte değil, üretim çıktısında yakalandı.)

`close_date`, raporun tarih aralığı için kullanılır.

---

## 4. İşleme boru hattı (adım adım)

### Adım A — Hafta döngüsü

- `N = 1 … 53` (ve 54 → 404) için payload indirildi.
- HTTP hata / 404 → hafta atlandı, hata listesine yazıldı.

### Adım B — Referans çözümleme

```text
resolve(data, idx):
  - idx skaler ise → değeri döndür
  - ["Reactive"|"Ref"|..., target] ise → resolve(data, target)
  - derinlik sınırı (ör. 12) aşılırsa → dur
```

Bu, Nuxt proxy sarmalayıcılarını soyarak `homeRegular` / takım adı / tarih alanlarını düz değere indirir.

### Adım C — Maç satırı üretimi

Haftanın **kendi `matches` dizisi** üzerinde, **sırayı bozmadan** (§3.1.b):

1. Ev ve deplasman adını çöz.
2. `match.score.homeRegular` / `awayRegular` çöz.
3. Gol değerleri `int` ve makul aralıkta mı kontrol et (`0 … 20`).
4. `match.date` → başlama saati.
5. Sonuç kodu:

| Koşul | Kod |
|--------|-----|
| `home > away` | **1** |
| `home == away` | **0** |
| `home < away` | **2** |

Tekilleştirmeye gerek yoktur: tek ve doğru listeden okunduğu için mükerrer
kayıt oluşmaz. (v1'de tekilleştirme, birleştirilmiş bloklardaki kopyaları
temizlemek zorundaydı; bu da sıranın kaynağını belirsizleştiriyordu.)

### Adım D — 15/15 filtresi (kesinlik eşiği)

| `len(uniq_matches)` | Karar |
|---------------------|--------|
| **== 15** | Analize **dahil** |
| **≠ 15** | Analize **hariç** (eleme) |

Elenen örnekler (bu sette):

| Hafta | Durum (örnek) |
|------:|----------------|
| 1 | 12 skor (eksik) |
| 23 | 14 skor |
| 34 | 14 skor |
| 43–49 | 0 skor (yaz arşivi / boş) |
| 52 | 3 skor (henüz kapanmamış / eksik) |
| 53 | 0 skor (aktif / boş) |

### Adım E — Haftalık özet

Her kabul edilen hafta için:

- `matches`: 15 maçlık liste — `no`, `home`, `away`, `kickoff`, `hg`, `ag`, `code`
- `results`: 15 karakterlik string, **maç listesinden üretilir**, örn. `000111122212011`
- `n1`, `n0`, `n2` (15’in parçalanması; `n1+n0+n2 = 15`)
- `close_date`: `YYYY-MM-DD`
- `season`: `2025/2026`

Script çıkmadan önce her hafta için şunu doğrular (assert):
`results == "".join(m.code)` ve `(n1,n0,n2) == results.count(...)`. Yani
listenin, dizinin ve sayımların üçü de birbirini tutmadan dosya yazılmaz.

### Adım F — Sezon özeti

```text
N          = kabul edilen hafta sayısı
T          = N × 15
sum1,0,2   = tüm maçlarda 1 / 0 / 2 adedi
pct_*      = 100 * sum_* / T
avg_*      = sum_* / N          # haftalık ortalama
```

### Adım G — Ortalama üstü / altı bantları

Her sonuç tipi `r ∈ {1,0,2}` için, haftalık `n_r` serisi:

```text
above = { n | n > avg_r }
below = { n | n < avg_r }

above_n     = |above|
below_n     = |below|
above_mean  = mean(above)
below_mean  = mean(below)
above_gap   = above_mean - avg_r
below_gap   = avg_r - below_mean
```

Ayrıca min / medyan / max / popülasyon std kaydedildi.

---

## 5. Üretilen veri seti özeti

| Alan | Değer |
|------|--------|
| Sezon | 2025 / 2026 |
| Tarih aralığı | **2025-08-18 → 2026-07-27** |
| Analiz haftası | **41** |
| Toplam maç | **615** |
| 1 | **270** (**%43,90**) |
| 0 | **149** (**%24,23**) |
| 2 | **196** (**%31,87**) |
| Haftalık ort. 1 / 0 / 2 | **6,59 / 3,63 / 4,78** |

### Bant özeti

| Sonuç | Ort. | Üstünde (hf) | Üst ort. | Sapma+ | Altında (hf) | Alt ort. | Sapma− |
|--------|-----:|-------------:|---------:|-------:|-------------:|---------:|-------:|
| 1 | 6,59 | 21 | 7,90 | +1,32 | 20 | 5,20 | −1,39 |
| 0 | 3,63 | 22 | 4,91 | +1,27 | 19 | 2,16 | −1,48 |
| 2 | 4,78 | 21 | 6,10 | +1,31 | 20 | 3,40 | −1,38 |

---

## 6. Dikkat edilen noktalar (kalite kontrol)

### 6.1 Sıra ile skor eşlemesi yapılmadı

İlk denemelerde “15 isim + 15 skor listesini sırayla yapıştır” yaklaşımı denendi. Bu, payload içinde skorların farklı bloklarda tekrarlanması durumunda **yanlış maç–skor** üretebilir.  
**Nihai yöntem:** her maç kaydının kendi `match.score` referansı.

### 6.2 Sadece regular time golleri

`homeRegular` / `awayRegular` kullanıldı. Uzatma / penaltı alanları (varsa) bu Spor Toto 1-0-2 tanımına dahil edilmedi; Spor Toto maç sonucu normal süre üzerinden okunur.

### 6.3 Gol aralığı filtresi

Anlamsız parse (negatif, aşırı büyük) değerler satır olarak reddedildi (`0…20`).

### 6.4 Mükerrer kayıt temizliği

Aynı `(home, away, skor, date)` birden fazla serileşirse tek satır tutuldu; aksi halde 15’ten fazla satır “sahte tamam” görünebilirdi.

### 6.5 Eksik hafta politikası

Kısmi hafta (14/15, 12/15, 0/15) **ortalama hesaplarına karıştırılmadı**.  
Gerekçe: bir eksik sonuç bile o haftanın 1/0/2 vektörünü bozar; kullanıcı “kesin veri yoksa ele” şartı koydu.

### 6.6 Maçkolik yokluğu açıkça belgelendi

Skor kaynağı Maçkolik olamadı. Bunun yerine **bülten kaydına gömülü, maça bağlı skorlar** kullanıldı.  
51. hafta Misli satırı ile çapraz kontrol edildi.

### 6.7 Üçüncü parti kaynak riski

sportototahmin resmi devlet arşivi değildir. Bu yüzden:

- Eksik haftalar atıldı.
- En az bir hafta bağımsız sonuç satırı ile doğrulandı.
- Rapor “kesin resmi 53 haftalık tam sezon dump’ı” iddiası taşımaz; **41 tam haftalık filtrelenmiş set** iddiası taşır.

### 6.8 Tarih alanı

`close_date` katalog `closeDate` alanından ISO → `YYYY-MM-DD`.  
Aralık raporu: min / max `close_date` (dahil haftalar üzerinden).

### 6.9 Sonuç kodu string’i

`results` alanı, maç sırasına göre 15 karakter (1/0/2).  
Hem insan okuması hem de ileride formül / simülasyon geri testi için tutuldu.

### 6.10 v1'de bulunan hata ve düzeltmesi (2026-08-16)

**Belirti.** Veri seti kendi içinde çelişiyordu: 6 haftada dosyadaki
`n1/n0/n2` alanları ile `results` dizisinin sayımı tutmuyordu; ayrıca iki
farklı hafta çifti (22–25 ve 24–26) **birebir aynı** sonuç dizisini taşıyordu.

**Teşhis.** Kaynak payload'lar yeniden çekilip 9 hafta tek tek karşılaştırıldı.
Çelişkili 6 haftanın **hepsinde** dosyadaki `n1/n0/n2` kaynakla birebir
uyuştu; hatalı olan `results` dizisiydi. Sıra kontrolü daha geniş bir hasar
gösterdi: 41 haftanın **26'sında** dizi doğru, **15'inde** sıra yanlıştı
(bunların 6'sında sayım da). Sebep §3.1.b: düz tarama, `featuredMatches`
bloklarını haftanın kendi listesine karıştırıyordu.

**Etki.** Sezon toplamları ve bantlar etkilenmedi (onlar `n1/n0/n2`
üzerindendi). Ama **sıraya bağlı** her analiz — maç sırası dağılımı, geçiş
matrisi, seriler — 15 haftada kirliydi.

**Düzeltme.** `scripts/build_history.py` ile veri seti kaynağından yeniden
üretildi: 26 hafta aynı kaldı, 9 haftada sıra, 6 haftada sıra + sayım
düzeldi, mükerrer diziler ortadan kalktı. `close_date` alanlarının 41/41'i
v1 ile birebir aynı çıktı — yani hafta eşlemesi baştan doğruydu, bozuk olan
hafta *içindeki* sıraydı.

**Bekçi.** `tests/test_history.py::test_veri_seti_temiz` artık veri setinin
kendi denetiminden geçmesini şart koşuyor; sıra ya da sayım bir daha bozulursa
test kırmızıya döner.

---

## 7. Çıktı şeması (`data/st_history_2025_26.json`)

```json
{
  "meta": {
    "season": "2025/2026",
    "date_from": "YYYY-MM-DD",
    "date_to": "YYYY-MM-DD",
    "weeks": 41,
    "matches": 615,
    "source": "...",
    "rule": "only weeks with exactly 15 results",
    "generated_at": "2026-08-15"
  },
  "totals": {
    "1": 270, "0": 149, "2": 196,
    "pct_1": 43.9024, "pct_0": 24.2276, "pct_2": 31.8699
  },
  "weekly_avg": { "1": 6.5854, "0": 3.6341, "2": 4.7805 },
  "bands": {
    "1": { "avg", "min", "max", "median", "std",
           "above_n", "below_n", "above_mean", "below_mean",
           "above_gap", "below_gap" },
    "0": { "...": "..." },
    "2": { "...": "..." }
  },
  "weeks": [
    {
      "week": 51,
      "close_date": "2026-07-27",
      "season": "2025/2026",
      "n1": 7, "n0": 4, "n2": 4,
      "results": "000111122212011",
      "matches": [
        {
          "no": 1,
          "home": "AGF Aarhus",
          "away": "Brondby",
          "kickoff": "2026-07-25 16:00",
          "hg": 1, "ag": 1,
          "code": "0"
        }
      ]
    }
  ]
}
```

Uygulama tarafında yükleme: `spor_toto.history.load_history()` /
`history_summary(last)` / `history_weeks(last)` / `history_analytics(last)` /
`history_week_detail(n)`.

---

## 8. UI entegrasyonu

| Rota | Sayfa |
|------|--------|
| `/istatistik` | Sezon payı, haftalık seyir, bantlar, dağılım, maç sırası ısı haritası, geçiş matrisi, hafta tablosu, veri kalitesi |
| `/istatistik/<week>` | Maç maç sonuçlar (takım adı + skor), sezon ortalamasına sapma ve sıra, sürprizler, seriler |

Formül motoru (`/`, `/api/solve`) bu seti zorunlu kullanmaz; istatistik sayfası bağımsız okur. İleride prior / Dirichlet / Bayes için `weekly_avg` ve `bands` doğal aday girdilerdir.

---

## 9. Bilinen sınırlamalar

1. **Tam sezon değil:** 41 / ~53 hafta; eksik skorlu haftalar yok.
2. **Maçkolik doğrulaması yok:** API ölü ve robots.txt otomatik erişimi kapatıyor (§2.2).
3. **Kupon sırası kaynağın sırasıdır.** Haftanın kendi `matches` dizisi esas alınır; resmi bülten numaralandırmasıyla ayrıca karşılaştırılmamıştır. 51. hafta bağımsız sonuç satırıyla birebir tutuyor (§2.4) — bu, hem kodların hem sıranın en az bir haftada doğrulandığı anlamına gelir.
4. **Lig bilgisi yok:** payload maç kaydında lig adı taşımıyor; oran eşleştirmesi tarih + skor + takım adı üzerinden yapılır (§12).
5. **Yaz dönemi (43–49)** çoğu boş payload; lig takvimi / bülten yapısı farklı olabilir.
6. Üçüncü parti arşiv güncellenirse veya silinirse **yeniden çekim** gerekir; script bunun için vardır.

---

## 10. Yeniden üretim

```bash
cd backend
python scripts/build_history.py            # çek, doğrula, yaz
python scripts/build_history.py --dry-run  # yazmadan sonucu gör
pytest tests/test_history.py               # veri seti denetimi
```

Script her hafta için listenin, dizinin ve sayımların birbirini tuttuğunu
doğrulamadan dosya yazmaz. Yazdıktan sonra `test_veri_seti_temiz` bunu bir kez
daha bağımsız olarak kontrol eder.

---

## 11. Kısa sonuç

- Veri **uydurulmadı**; haftalık payload’lardan **maç bağlı skor** ile üretildi.
- **Kesinlik filtresi** uygulandı: 15’ten az sonuçlu hafta yok.
- Dağılım tipik futbol oranlarına yakın: ~%44 ev, ~%24 beraberlik, ~%32 deplasman.
- Ortalama üstü/altı yaklaşık yarı yarıya; tipik sapma **±1,3–1,5 maç / hafta**.
- v2 ile sıra hatası kapatıldı ve veri seti maç düzeyine indi.

---

## 12. Oran (iddaa) verisi — yapılabilirlik notu

2026-08-16 araştırması. Ayrıntılı ölçüm sohbet kaydında; özet:

| Hedef | Durum |
|-------|-------|
| Geçmiş maçlar + **iddaa'nın kendi oranı** | Yok. Resmi API (`sportsbookv2.iddaa.com`) yalnızca açık bülteni verir (ölçümde 8 günlük pencere); Nesine de aynı. Arşiv ucu bulunamadı. |
| Geçmiş maçlar + **piyasa kapanış oranı** | Var. football-data.co.uk ücretsiz CSV'leri ile 615 maçın **567'si (%92,2)** eşleşti; 41 haftanın 36'sı tam 15/15. |
| Bundan sonraki haftalar + iddaa oranı | Mümkün — haftalık bülten snapshot'ı alınırsa kendi arşivimiz oluşur. |

Eşleşmeyen 48 maç yapısal: 5., 10. ve 15. haftalar tamamen **milli maç**
(kaynak milli maç yayınlamıyor), kalanı K-League ve tek bir eşleştirme kaçağı.

Eşleşmenin sağlaması: kapanış oranındaki favori %54,9 tutmuş, favori hiçbir
maçta beraberlik çıkmamış (374 kez "1", 193 kez "2"); marj arındırılmış
olasılıklar gerçekleşmeyle kova kova örtüşüyor. Ortalama marj %7,26.

Bu setin bu belgedeki veriyle birleştirilebilmesinin **ön koşulu**, v2 ile
gelen `matches` alanıdır: eşleştirme tarih + skor + takım adı üzerinden yapılır.

Bu MD, projedeki tarihsel istatistik katmanının tek kaynak dokümantasyonudur.
