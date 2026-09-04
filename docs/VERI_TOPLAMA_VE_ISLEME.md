# Veri Katmanı — Toplama, İşleme ve Doğrulama

**Kapsam:** projedeki dört veri setinin tamamı — tarihsel 1/0/2 sonuçları, piyasa oranı
arşivi, iddaa bülten arşivi ve (ayrı katman) eğitim korpusu
**Sürüm:** v9 (beşinci veri seti: yaklaşan maçlar — tahmin ürününün girdisi)
**İlgili belgeler:** [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) (katmanın
durumu ve yol haritası) · [`ARCHITECTURE_NEXT.md`](ARCHITECTURE_NEXT.md) (API sözleşmesi)

> **Amaç değişikliği (2026-08-17).** Projenin amacı artık **veriyi analiz ederek kazanma
> oranını artıracak sonuçlar üretmek ve maç sonucu tahmini yapmaktır**
> ([`../README.md`](../README.md) §1). Bu belgenin **doktrini değişmedi** — yedi ilkenin
> tamamı aynen geçerlidir ve tahmin hedefiyle birlikte daha da bağlayıcı hale gelmiştir:
> bir tahmin modeli, altındaki verinin bütün kusurlarını devralır ve onları güvenilir
> görünen bir sayıya çevirir. Değişen tek şey **önceliklerdir** (§10) ve amaçla birlikte
> ortaya çıkan **yeni bir veri ihtiyacıdır** (§10.1).

| | Tarihsel sonuçlar | Piyasa oranı arşivi | İddaa bülten arşivi |
|---|---|---|---|
| **Dosya** | `data/st_history_2025_26.json` | `data/odds/odds_2025_26.csv` | `data/iddaa/iddaa_<tarih>.csv` |
| **Üreten** | `scripts/build_history.py` | `scripts/build_odds.py` | `scripts/snapshot_iddaa.py` |
| **Okuyan** | `spor_toto/history.py` | `spor_toto/odds.py` | (henüz analize girmiyor) |
| **Bekçi** | `tests/test_history.py` | `tests/test_odds.py` | `tests/test_snapshot_iddaa.py` |
| **Yönü** | geriye dönük, tamam | geriye dönük, tamam | **ileriye dönük, birikiyor** |

(Yollar `backend/` altındadır.)

Bu üçü **istatistik ve kaplama katmanlarının** verisidir. Dördüncü bir veri
seti daha var ve bilerek **ayrı** tutulur:

| | Eğitim korpusu |
|---|---|
| **Dosya** | `data/egitim/egitim_korpus.csv` |
| **Üreten** | `scripts/build_egitim.py` |
| **Okuyan** | `spor_toto/egitim.py` → **yalnızca tahmin katmanı** |
| **Bekçi** | `tests/test_egitim.py` (ayrım testleri dahil) |
| **Yönü** | geriye dönük, 4 geçmiş sezon |

Ve **beşinci** bir veri seti, tahmin ürününün girdisi:

| | Yaklaşan maçlar |
|---|---|
| **Dosya** | `data/fixtures/fixtures.csv` |
| **Üreten** | `scripts/build_fixtures.py` |
| **Okuyan** | `spor_toto/tahmin.py` → `/api/tahmin`, `/tahmin` |
| **Bekçi** | `tests/test_tahmin.py` |
| **Yönü** | **ileriye dönük, yuvarlanan pencere** |

Diğer dördünden yönüyle ayrılır: hepsi geriye dönüktür, sonucu belli maçları
taşır. Bu ise **henüz oynanmamış** maçı taşır ve hafta oynandıkça boşalır.
"Yaklaşan maç yok" bu yüzden **normal bir durumdur, hata değildir.**

Kaynağı football-data'nın `fixtures.csv` dosyasıdır ve seçim kasıtlı:
**ölçümün yapıldığı kaynağın ta kendisi.** Kupon setinde ölçülen isabet aynı
fiyatlayıcıya ait olduğu için ürüne meşru biçimde taşınabilir. İddaa bülteni
yedektir ve kalibrasyonu **ölçülmemiştir** (marj %17,2'ye karşı %7,26); o
maçlar gövdede ayrı işaretlenir.

Oranlar **açılış** oranıdır ve bedeli ölçülmüştür (A1): açılış Brier 0,5964,
kapanış 0,5940 — fark +0,0025. Ürün gövdesi bu sayıyı taşır.

**Korpus `/istatistik` sayfasına girmez.** O sayfa Spor Toto kuponunun
sezonunu anlatır (41 hafta, 615 maç) ve öyle kalır. Ayrım ürün kararıdır ve
`test_ayrim_*` testleriyle korunur (§6A.4).

---

## 1. Veri doktrini

Bu yedi ilke, aşağıdaki her kararın gerekçesidir. Yeni bir veri kaynağı eklerken de bunlar
geçerlidir.

**1. Tek doğruluk kaynağı vardır ve zinciri bellidir.**
Maç listesi → sonuç dizisi → sayımlar. Dizi listeden üretilir, sayımlar diziden sayılır. Üç
temsil de dosyada durur ama biri diğerinden türer; hiçbiri bağımsız yazılmaz.

**2. Kesin olmayan veri elenir, doldurulmaz.**
15 maçı tam kapanmamış hafta analize hiç girmez. Bir eksik sonuç bile o haftanın 1/0/2
vektörünü bozar. Eksiği doldurmak, ortalamayla tamamlamak, "yaklaşık" saymak yok.

> Bu ilke **maç sonucu tahminiyle çelişmez, onun önkoşuludur.** Yasak olan şey eksik
> *girdiyi* uydurmaktır; amaç ise gelecek sonucu *tahmin etmektir*. İkisi aynı şey değil:
> imputasyonla doldurulmuş bir eğitim seti, modelin öğrendiği ilişkinin ne kadarının
> gerçek olduğunu ölçülemez hale getirir. Amaç tahmine döndüğü için bu ilke gevşemez,
> **sıkılaşır.**

**3. Sıra kaynağın kendi sırasıdır.**
Kupon sırası tahmin edilmez, tarihe göre sıralanmaz, isimden çıkarılmaz. Kaynağın haftaya ait
kendi listesinden okunur. Bu ilke v1'de ihlal edildiği için 41 haftanın 15'i bozuldu (§7.4).

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

### 2.3 İddaa bülten arşivi (ileriye dönük)

| Alan | Değer |
|---|---|
| Kaynak | `sportsbookv2.iddaa.com/sportsbook/events` — **açık bülten**, geçmiş yok |
| Toplanan | Yalnızca futbol (`sid=1`) ve yalnızca maç sonucu (1X2) |
| Ölçülen | 226 futbol etkinliği, 225'inde 1X2 pazarı; 222'si kaydedildi |
| Fiyat listesi | İki tane, ikisi de saklanır: `odd` (kupon), `wodd` (web) |
| **Ortalama marj** | **%17,2** — piyasa oranlarında %7,26 idi |
| Biriktirme | Haftalık snapshot; tarih damgalı CSV sürümlenir |

Bu arşiv **bugün analize girmiyor** çünkü tek snapshot bir şey söylemez. Değeri birikimdedir:
haftada bir çalışırsa bir sezon sonunda geçmiş iddaa oranı sorunu (§3.2) kendi verimizle
kapanır.

Marj farkı, belgenin baştan beri söylediği "seviye tutmaz, yapı tutar" cümlesinin ölçülmüş
karşılığıdır: iddaa payı piyasanın iki katından fazla.

### 2.4 Resmî Spor Toto arşivi — ikramiye ve havuz

| Alan | Değer |
|---|---|
| Kaynak | `webapi.sportoto.gov.tr` — **Spor Toto'nun kendi ucu**, kimlik doğrulamasız |
| Sezon | **6** (2021/2022 kısmi → 2026/2027) |
| Hafta | **225**, bunların **223'ünde ikramiye tablosu** (%99,1) |
| Taşıdığı | Hafta adı, kapanış tarihi, kademe başına (15/14/13/12) **kazanan adedi + kişi başı ikramiye** |
| **Taşımadığı** | **15 maçlık liste ve 1/0/2 dizisi** — resmî uçta maç listesi yalnızca bülten **görseli** olarak var |

Bu, deponun **ilk resmî kaynağıdır.** Öteki dördü üçüncü partidir: football-data
piyasa oranı, sportototahmin hafta payload'ı, iddaa bülteni, openfootball fikstür.
Burası Spor Toto'nun kendisidir ve ikramiye ile kazanan adedinde başka hiçbir
kaynak ona eşit değildir.

**Neden şimdi bulundu.** §3.1 uzun süre "toplu, makine dostu arşiv ucu bulunamadı"
yazıyordu ve bu yanlıştı. `sportoto.gov.tr` bir Next.js uygulamasıdır ve hafta
verisini ayrı bir hosttan **istemci tarafında** çeker; uçlar sayfa kaynağında
değil JS parçalarında durur. İlk aramada görünmemesinin sebebi budur, kaynağın
kapalı olması değil.

Ne çözdüğü §10.1'dedir ve tek cümleyle şudur: havuz ekseni **n = 3'ten n = 223'e**
çıktı. Ne çözmediği de aynı ölçüde nettir — kupon dizisi hâlâ bu kaynaktan gelmiyor
(§6D.3).

### 2.5 Geçmiş sezon kupon arşivi (türetilmiş)

| Alan | Değer |
|---|---|
| Kaynak | Resmî bülten **görseli** (OCR) + football-data fikstürü |
| Sezon | **4** (2022/23 → 2025/26) |
| Hafta | **112**, hepsi 15/15 (§6I'de 107'den çıktı) |
| Maç | **1.680**, kupon sırasıyla, skor ve 1/0/2 ile |
| Çapraz doğrulama | 2025/26'nın 31 ortak haftasında **30'u birebir aynı** |
| Taşımadığı | Oran ve maç istatistiği yok |

Kupon değerlendirme seti 41 haftadan **148 haftaya** çıktı (41 eski + 107
yeni; 29'u aynı sezonun iki bağımsız okuması). Ayrıntı §6F ve §6G.

## 3. Kaynak seçimi

### 3.1 Değerlendirilen kaynaklar

| Kaynak | Ne için | Karar | Gerekçe |
|---|---|---|---|
| **sportototahmin.com** hafta payload'ları | 15 maçlık liste + skor | **Kullanılıyor** | Maç listesi ve skor aynı kayıtta ve maç nesnesine bağlı; sıra haftanın kendi dizisinde |
| **football-data.co.uk** arşivi | Oran | **Kullanılıyor** | Ücretsiz, geçmişi tam, açılış + kapanış, çok pazarlı; kişisel kullanıma açık |
| **`webapi.sportoto.gov.tr`** | Resmî hafta kaydı + **ikramiye tablosu** | **Kullanılıyor** | Deponun ilk **resmî** kaynağı. 6 sezon · 225 hafta · 223 ikramiye tablosu. Kimlik doğrulamasız, sezon parametreli. Önceki "arşiv ucu bulunamadı" kaydı **yanlıştı**: site Next.js ve uçlar JS parçalarında (§2.4). **Maç listesi vermez** — o yalnızca bülten görseli |
| **Maçkolik** | Skor + iddaa oranı | **Kullanılmıyor** | Eski açık uç (`goapi.mackolik.com`) ölü; `robots.txt` `/api/` yolunu herkese, `anthropic-ai`/`GPTBot`/`CCBot`'u tamamen kapatıyor. Teknik engelin yanında açık bir politika sınırı var (§3.3) |
| **iddaa resmi API** (`sportsbookv2.iddaa.com`) | İddaa oranı | **Kullanılıyor (ileriye dönük)** | Çalışıyor ama **yalnızca açık bülten**; geriye dönük arşiv ucu yok. Haftalık snapshot ile kendi arşivimizi kuruyoruz (§6) |
| **Nesine** bülten API'si | İddaa oranı | Aynı | Canlı bülten; geçmiş yok |
| **Misli** sonuç sayfası | Çapraz doğrulama | Nokta atışı kullanıldı | 51. haftanın sonuç satırı bağımsız doğrulama için kullanıldı (§7.2) |
| **hudl/open-data** (StatsBomb Open Data) | Olay düzeyi veri, şut başına gerçek xG | **Kullanılıyor (yalnızca kalibrasyon)** | Korpusun liglerini kapsamıyor — Süper Lig ve alt İngiliz ligleri depoda yok, kesişim 92 maç. Ama kapsadığı 1.517 maçta gerçek xG ile korpusun şut sayımını yan yana veriyor; **girdi değil referans** (§6C) |

### 3.2 Neden geçmiş iddaa oranı yok

Kısa cevap: **hiçbir açık kaynak yayınlamıyor.** İddaa ve bayileri (Nesine, Misli, Bilyoner)
yalnızca açık bülteni servis eder; kapanan maçın oranı API'den düşer. O veri Maçkolik gibi
sitelerin maç sayfalarında durur, ama orası otomatik erişime kapalıdır.

Sonuç: **geçmiş için piyasa oranı** kullanıyoruz. Seviye tutmaz (iddaa marjı daha yüksek),
**favori sıralaması ve marj arındırılmış olasılık yapısı** tutar — analizde kullanılan da budur.
İleriye dönük çözüm uygulandı (§6): haftalık bülten snapshot'ı alındıkça bir sezonda kendi
iddaa arşivimiz olur. Ölçülen marj farkı (%17,2 → %7,26) vekilin neden yalnızca *yapı* için
kullanılabileceğini somutlaştırıyor.

### 3.3 Yasal ve etik sınır

- `robots.txt` bir kaynağın otomatik erişim politikasıdır; ihlal edilmez.
- football-data.co.uk verisi kişisel kullanım için serbesttir; ham dosyalar repoya konmaz,
  yalnızca türetilmiş eşleştirme sürümlenir.
- Kaynak siteler resmi devlet arşivi değildir. Bu yüzden eksik haftalar elenir ve en az bir
  hafta bağımsız kaynakla çapraz doğrulanır. Bu belge "tam sezon resmi dump" iddiası taşımaz;
  **41 tam haftalık filtrelenmiş set** iddiası taşır.
- **StatsBomb verisi iki ek yükümlülük getiriyor ve deponun ilk lisans kısıtı odur.** Diğer
  kaynaklar ya kişisel kullanıma serbest (football-data), ya CC0 (`openfootball/clubs`), ya
  kamu malı (`openfootball/champions-league`); StatsBomb değil. "StatsBomb Public Data User
  Agreement" iki maddesi doğrudan bu depoyu bağlıyor:

  | Madde | Metin | Sonuç |
  |---|---|---|
  | 1.2.1 | kullanıcı veriyi *"edit, distort, distribute, reproduce, sell or in any way provide ... to any external or third party"* edemez | `ozgronurkoc/Twmq` **public**tir; ham JSON commit edilemez. Depoya yalnızca **katsayı ve rapor** girer — maç başına xG satırı bile girmez |
  | 1.4 | *"The User is required to accredit any publication of analysis formed from StatsBomb Data with the StatsBomb brand logo"* | xG bulgusu arayüzde yayımlanırsa **StatsBomb logosu eşlik etmek zorundadır** |

  Sözleşmenin girişi karşılığında şunu açıkça serbest bırakıyor: *"Any analysis or conclusions
  that are created as a result of using this data, may be shared publicly."* `data/xg/`
  altındaki iki dosya tam olarak bu kategoridedir — ölçülmüş katsayılar ve bir kapsama raporu,
  verinin kendisi değil.

  Sözleşmede **bahis/kumar yasağı yoktur** (metin arandı: `bet`, `gambl`, `wager` geçmiyor).
  Kısıt ticari sömürüdedir (md. 1.2.2: veriyi *veya ondan türetilen analizi* ticari olarak
  sömürmek yasak). Bu proje ticari değildir; olursa bu katman sökülebilir olmalıdır ve bu,
  onu üretim tahmin yolundan uzak tutmanın ikinci gerekçesidir.

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
öne çıkan maç blokları araya girdiğinde sırayı bozar (§7.4).

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

## 6. İddaa bülten boru hattı

### 6.1 Kaynak biçimi

Tek uç, tek çağrı: `sportsbookv2.iddaa.com/sportsbook/events?st=1&type=0&version=0`. Cevap
`{isSuccess, data: {version, events}}` sarmalında gelir. Her etkinlik `m` altında onlarca pazar
taşır; **maç sonucu pazarı ölçülerek bulundu**: `t=1, st=1` ve seçenek adları birebir
`"1"/"0"/"2"`.

Lig adı ayrı uçtan gelir (`/sportsbook/competitions`) ve etkinliğin `ci` alanıyla eşleşir. Lig
adı alınamazsa snapshot yine değerlidir — kod satırda durur, ad boş kalır ve script bunu uyarı
olarak basar.

Başlama zamanı `d` alanında unix saniyedir; **UTC olarak saklanır**, çünkü oran arşivindeki
`kickoff` da UTC — iki kaynak aynı eksende olmalı.

### 6.2 Neyin elendiği

| Durum | Karar | Gerekçe |
|---|---|---|
| `sid ≠ 1` | Elenir | Futbol dışı; kupona girmez |
| 1X2 pazarı yok | Elenir | Ölçümde 226'nın 1'i |
| 1X2'nin bir ayağı eksik | Elenir | İki ayaklı bir "1X2" yanıltır |
| **Bir ayak ≤ 1.00** | **Elenir** | 1.00 fiyat değil, askıya alınmış ayağın yer tutucusu |

Son satır ölçülmüş bir vakadır: 225 maçın 3'ünde üçlü `17.95 / 8.48 / 1.00` gibi çıkıyor. Bunu
fiyatmış gibi saklamak sonraki her analizi zehirlerdi. `spor_toto.odds.match_1x2` zaten aynı
kuralı uyguluyordu (doktrin 2: kesin olmayan veri elenir); snapshot da uyguluyor ve kaç maçın
elendiğini `iddaa_rapor.json` içinde `dropped` olarak raporluyor.

### 6.3 Depolama katmanları

| Dosya | Sürümlenir | İçerik |
|---|---|---|
| `data/iddaa/iddaa_<tarih>.csv` | **evet** | Snapshot başına bir dosya, maç başına bir satır |
| `data/iddaa/iddaa_rapor.json` | **evet** | Son çalışmanın özeti + biriken snapshot listesi |
| `data/iddaa/iddaa.sqlite3` | hayır | Uzun biçim kopya, üretilir |
| `data/iddaa/_kaynak/*.json` | hayır | İndirilen ham payload |

Doktrin 6'nın uygulanışı: burada **sürümlenen şey arşivin kendisidir**, çünkü kaynak onu bir
daha vermeyecek. Oran arşivinde ham dosyalar istendiği an yeniden indirilebilirdi; kapanmış bir
iddaa bülteni indirilemez.

SQLite şeması bilerek `odds.sqlite3` ile aynı uzun biçimdedir:

```sql
mac (alinma, event_id, kickoff, home, away, lig, lig_kodu, canli)
oran(alinma, event_id, pazar, secim, donem, deger)   -- pazar: 1X2 · donem: kupon|web
```

Anahtarın `alinma`'yı içermesi kasıtlıdır: aynı maç farklı snapshot'larda **ayrı satırdır**.
Açılış–kapanış farkı ancak böyle çıkar; aynı gün ikinci kez çalıştırmak ise satırı çoğaltmaz,
üstüne yazar.

### 6.4 Zamanlama

`.github/workflows/snapshot-iddaa.yml` **açık**: her pazartesi 06:00 UTC (TR 09:00), hafta
kuponu açıktayken. Snapshot alınır, biçimi `test_snapshot_iddaa.py` ile denetlenir ve yeni veri
varsa depoya işlenir.

Botun yazma alanı dar tutuldu:

| Önlem | Ne engelliyor |
|---|---|
| `git add backend/data/iddaa` | Arşiv dışında hiçbir dosyaya dokunmaz |
| `git diff --cached --quiet` kontrolü | Değişiklik yoksa boş commit atmaz |
| `concurrency: iddaa-snapshot` | İki çalışma aynı dosyaya yazıp push yarışına girmez |
| `pull --rebase` + açık hedefe push | Dal bu arada ilerlediyse çakışmaz |
| Testin push'tan **önce** koşması | Bozuk biçimli bir snapshot depoya girmez |

**Zamanlanmış işler yalnızca varsayılan daldan çalışır.** Bu iş bir özellik dalında durduğu
sürece tetiklenmez; arşiv, dosya `main`'e geçtiği anda birikmeye başlar. Elle denemek için
Actions → bu iş → "Run workflow" (bu, `workflow_dispatch` ile her daldan çalışır).

Durdurmak: Actions → bu iş → "Disable workflow". Durdurmanın bedeli, o haftanın bülteninin bir
daha ele geçmemesidir.

---

## 6A. Eğitim korpusu boru hattı

### 6A.1 Neden dördüncü bir veri seti

Kupon değerlendirme seti 540 maç ve tek sezon. "Piyasayı geçen bir şey var mı"
sorusuna bu örneklemle verilen cevap zayıf kalıyordu: Adım 2'de yeniden
kalibrasyon kademesinin **hiçbir basamağı** geçemedi, ama kapasite arttıkça
eğitim-içi iyileşip dışarıda kötüleşmesi bunun bir *örneklem* sorunu
olabileceğini gösteriyordu.

Aynı kaynak — football-data.co.uk — kupon dışındaki maçların da **hem sonucunu
hem 1X2 oranını** taşıyor. Bir tahminciyi ölçmek için gereken üçlü budur;
kuponun hangi 15 maçtan oluştuğu bu iş için ilgisizdir. Kupon bileşimi yalnızca
**kaplama katmanı** ve kupon düzeyindeki geri test için gerekli kalır.

### 6A.2 Kaynak ve kapsam

`https://www.football-data.co.uk/mmz4281/{sezon}/{lig}.csv` — 22 lig × 4 geçmiş
sezon. `robots.txt` tüm erişime açıktır (`Disallow:` boş).

Ölçülen: **31.103 maç · 4 sezon · 22 lig · %100 kapanış oranı.** Oranı tam
olmadığı için elenen 29 maç. Sonuç dağılımı 1: %43,4 · 0: %26,1 · 2: %30,5 —
Spor Toto sezonunun dağılımıyla (%43,9 / %24,2 / %31,9) tutarlı; bağımsız bir
sağlama sayılır.

Maçların **%93,0'ı** maç istatistiği (şut, isabetli şut, korner) taşır; bunlar
maç *sonrası* veridir ve doğrudan tahminci girdisi olamazlar — tek amaçları
yuvarlanan takım formu üretmektir. **%99,99'u** açılış+kapanış çizgi çifti
taşır (§6A.6) ve **%99,99'u** bahisçi dörtlüsü (§6A.7).

### 6A.3 Varsayılan sezonlar 2025/2026'yı dışarıda bırakır

Bu bir tercih değil, **sızıntı önlemidir.** Kupon değerlendirme seti 2025/26
sezonundan gelir; korpusa o sezon katılırsa eğitim ve sınav aynı maçları
paylaşır. Varsayılan `2122 2223 2324 2425`; başka bir sezon istenirse
`--sezonlar` ile açıkça verilir ve rapor bunu yazar.
`test_varsayilan_korpus_guncel_sezonu_icermez` bekçidir.

### 6A.4 Ayrım nasıl korunuyor

Ayrım yorumla değil testle korunur:

| Test | Neyi korur |
|---|---|
| `test_ayrim_istatistik_katmani_korpusu_import_etmez` | `history`, `odds`, `payloads`, `backtest`, `core`, `health` korpusa atıf yapmaz |
| `test_ayrim_stats_govdesi_korpustan_etkilenmez` | `/api/stats` gövdesinde korpus izi yok |
| `test_ayrim_korpus_kupon_bilesimi_tasimaz` | Korpus kupon alanı (`week`, `no`) taşımaz |

### 6A.5 Doktrin bu boru hattına da uygulanır

Oranı tam olmayan maç **elenir, tamamlanmaz** (ilke 2). Üretim scripti
doğrulamadan dosya yazmaz (ilke 5): geçersiz kod, 1.00'dan küçük oran, boş
takım adı ya da mükerrer maç bulursa çıkar ve yazmaz. Türetilmiş CSV + rapor
sürümlenir, ham lig dosyaları `_kaynak/` altında git dışıdır (ilke 6). Kaynağın
ne olmadığı raporda yazar: **piyasa oranıdır, iddaa oranı değildir** (ilke 7).

### 6A.6 Açılış ve kapanış çizgisi ayrı ayrı taşınır

Korpus başta maç başına **tek** bir oran üçlüsü yazıyordu: tercih sırasındaki
ilk tam kaynak, pratikte hep kapanış (`AvgC`). Kapanış varsa açılış kayboluyordu
— ve A1'in ölçmek istediği şey tam olarak ikisinin farkı.

Sütunlar artık üç grup: `oran_*` (birincil, kapanış tercihli — `piyasa`
tahmincisinin okuduğu), `acilis_*` ve `kapanis_*`.

**Çift yalnızca aynı bahisçi ailesinden kurulur:** `Avg`↔`AvgC`, `B365`↔`B365C`,
`PS`↔`PSC`. Sebep ölçümün kendisidir — `Avg` bütün bahisçilerin ortalaması,
`B365` tek bahisçi. Açılışı `Avg`'den kapanışı `B365C`'den alsaydık aradaki
fark piyasanın fikir değiştirmesini değil, **iki farklı fiyatlayıcıyı** ölçerdi.
Bir aile ancak iki ucu da tamsa kabul edilir; hiçbir aile tam değilse çift
kurulmaz.

**Çift ya tamdır ya yoktur** (ilke 2). Yarım çift hem üretici doğrulamasında
hem okuyucuda reddedilir; sızsaydı hareket o maçta sıfır görünür, maç A1
kesitine girer ve ölçümü sessizce seyreltirdi.

**Çifti olmayan maç elenmez.** `oran_*` tamdır, maç tahminci ölçümüne girer;
yalnızca A1 kesitine giremez. Korpus 31.103 maçta kaldı (31.099'unda çift var),
böylece kesit önceki ölçümlerle karşılaştırılabilir.

**Hareket ham oran üzerinden değil, marj arındırılmış olasılık üzerinden
ölçülür.** Ham oranın hareketi iki ayrı şeyi karıştırır: piyasanın fikir
değiştirmesi ve bahisçinin marjını değiştirmesi. Bütün ayakları aynı oranda
kısan bir bahisçi fikrini değiştirmemiştir; marj arındırıldıktan sonra geriye
yalnızca fikrin yeniden dağılımı kalır.

### 6A.7 Bahisçi kırılımı — kaynak seçimi ölçümü belirler

A2 (bahisçi anlaşmazlığı) kolektifin **içine** bakar, dolayısıyla kırılım
gerekir. Ama hangi kaynakların taşınacağı burada masum bir tercih değildir.

football-data yedi tekil bahisçi veriyor; **kapsamaları sezona göre değişiyor**
(31.132 maçta ölçüldü):

| Kaynak | 2122 | 2223 | 2324 | 2425 |
|---|---:|---:|---:|---:|
| `B365C`, `PSC` | %100 | %100 | %100 | %100 |
| `BWC` | %99 | %100 | %97 | **%63** |
| `WHC` | %99 | %91 | %94 | **%76** |
| `BFC`, `1XBC`, `BFEC` | %0 | %0 | %0 | %100 |

Hepsini isteyen bir filtre 2425'in %40'ını atardı. Sezon dışarıda bırakmalı
ölçümde bu **sessiz bir yanlılıktır**: model bir sezonu diğerlerinden farklı
bir maç evreninde öğrenir. Bu yüzden yalnızca dört sezonda da ~%100 olan dört
kaynak taşınır — `B365C`, `PSC`, `MaxC`, `AvgC` — ve kesit 31.100 maç kalır.

Aynı gerekçenin ikinci yüzü türetilen özelliklerdedir. İki anlaşmazlık ölçüsü
var ve biri bilerek **ikincil**:

| Ölçü | Kaynak | 2122 | 2223 | 2324 | 2425 |
|---|---|---:|---:|---:|---:|
| `ayrisma` | sabit `B365`↔`PS` çifti | 0,0142 | 0,0122 | 0,0125 | 0,0124 |
| `en_iyi_prim` | `Max`/`Avg` açığı | 0,0712 | 0,0641 | 0,0629 | 0,0577 |

`en_iyi_prim` daha geniştir — bütün bahisçi evrenini görür — ama `Max`, kaynak
sayısı değiştikçe **mekanik olarak kayar**: %20'lik bir sürüklenme ölçüldü.
Modele yalnızca `ayrisma` verilir. Sürüklenen bir özellik modele anlaşmazlık
değil **sezon kimliği** öğretir ve sızıntı sessizdir: skor iyileşir, sebep
yanlıştır. `en_iyi_prim` betimleyici kalır ve sürüklenmesi raporlanır.

Dörtlü **ya tamdır ya yoktur** (çizgi çiftiyle aynı gerekçe): kısmi bir kaynak
kümesi anlaşmazlığı değil, o gün hangi kaynağın mevcut olduğunu ölçerdi.
Doğrulamaya ayrıca **`Max ≥ Avg`** eklendi — en iyi fiyat ortalamanın altına
inemez; inerse kaynak sütunları karışmıştır (ilke 5).

---

## 6B. Süper Toto haftası — elle girilen veri

### 6B.1 Neden ayrı bir köken sınıfı

Bu belgenin ilk beş boru hattı ortak bir varsayım üzerine kurulu: **veri
script'le üretilir, üretim anında doğrulanır ve yeniden üretilebilir**
(`build_history.py`, `build_odds.py`, `snapshot_iddaa.py`, `build_egitim.py` —
hiçbiri doğrulamadan dosya yazmaz, §7.1).

`backend/data/super_toto/<sezon>/hafta_NN.json` bu varsayımı bozar:

```
odds_source    : "iddaa taraf oranları — kullanıcı ekran görüntüsü (2026-08-18)"
play_source    : "tek platform kullanıcı oynanma yüzdesi — kullanıcı ekran görüntüsü"
results_source : "Spor Toto resmî sonuç ekranı — kullanıcı ekran görüntüsü"
payout.source  : "Spor Toto resmî ikramiye ekranı — kullanıcı ekran görüntüsü"
```

**Bu bir kusur değil, bir zorunluluktur.** §10.1'in tarif ettiği havuz verisi
otomatik erişilebilir bir kaynakta yok; ikramiye ve oynanma payı yalnızca ilan
ekranlarında yayımlanıyor. Elle girmek, veriyi hiç almamakla arasındaki tek
seçenekti.

Doktrinin 4. ilkesi (kaynak dürüstlüğü) bu yüzden burada **daha da sıkı**
uygulanır: her blok kendi kaynağını ve tarihini kendi içinde taşır.

### 6B.2 Sınıfın kuralları

| Kural | Gerekçe |
|---|---|
| **Her veri bloğu `*_source` alanı taşır** ve alan ekran görüntüsünün tarihini içerir | Yeniden üretilemeyen veride kaynak, tek doğrulama izidir |
| **Yeniden üretilemez** — `scripts/` altında bu dosyayı yazan bir üretici yoktur, yalnızca okuyanlar vardır | Bunu gizlemek, dosyayı öteki dördüyle aynı statüde gösterirdi |
| **Türetilmiş yan kayıtlar bu sınıfa GİRMEZ** — `hafta_NN_tahmin2.json` elle girilmiş veriden hesaplanır ve yeniden üretilebilir | Elle girilen ile ondan türetileni aynı sınıfta göstermek, doğrulama izini bulanıklaştırırdı |
| **`data_quality` denetiminden geçmez** | O denetim `st_history` veri setine özgüdür (§7.3) |
| **27 değişmezin hiçbiri ona bakmaz** | Sağlık katmanı vaadin canlıda geçerliliğini ölçer; bu dosya ürün vaadine girmiyor |
| **Kuşkulu satır işaretlenir, düzeltilmez** | 2. haftada 4. maçın ima ettiği marj %45,8 iken bültenin geri kalanı %17,5–17,9'du; satır **KUŞKULU** olarak işaretlendi. Doğru marjla banko, verilen oranla çifte olurdu — sessizce "doğru olanı seçmek" §1.3'ün yasakladığı şeydir |
| **Eksik oran uydurulmaz** | Oranı ilan edilmemiş maç 1/3–1/3–1/3 taşır. Bu bir tahmin değil, **bilgi yokluğunun ilanı**; kural onu otomatik olarak üçlü yapar |

### 6B.3 Ne taşıyor

| Blok | İçerik |
|---|---|
| `matches[]` | 15 maç: tarih, saat, lig, takımlar, **iddaa oranı**, **oynanma yüzdesi**, skor, sonuç |
| `meta.payout` | Kat başına (12/13/14/15) kazanan adedi, kişi başı tutar, devreden tutar |
| `meta.results` | 15 karakterlik 1/0/2 dizisi |
| `hafta_NN_kupon.json` | **Sonuç görülmeden dondurulmuş** kupon: işaretler, kolon sayısı, küme-içi olasılık, `crowd_ratio`; revize edilirse eski sürüm `superseded` altında gerekçesiyle saklanır |
| `hafta_NN_tahmin2.json` | **2. Tahmin** — aynı hafta, bugünkü ölçek ve kuralla yeniden kurulmuş İKİNCİ kayıt (§3.37). Yukarıdaki kaydı **değiştirmez**; `hafta_NN.json`in fonksiyonu olduğu için sınıfı ayrıdır: elle girilmiş değil **türetilmiştir** ve `scripts/super_toto_tahmin2.py --yaz` ile yeniden üretilebilir. `meta.frozen_at` kaydın donduğu gündür ve `--tarih` ile açıkça verilir; `meta.results_known` doluysa betik yazmayı **reddeder** |

**Oynanma yüzdesinin kendisi de vekildir** ve dosya bunu yazıyor: *"yüzdeler tek
bir platformun kendi kullanıcılarıdır; Spor Toto havuzunun tamamı DEĞİLDİR."*
Yanlılığı ölçülmedi — nasıl ölçüleceği §10.1'de.

### 6B.4 Geçmiş sezon arşivine karışmaz

`super_toto_hafta.py` geçen sezonun tablolarını **okur, yazmaz**; `/api/stats`
yolunun beslediği arşive dokunmaz. Ayrım §6A'daki korpus ayrımıyla aynı
gerekçeye dayanır: biri kapanmış kayıt, öteki işleyen sezon.

Bir uyarı dosyanın kendi içinde duruyor ve taşınmalı: **oranlar iddaa oranıdır,
geçen sezon arşivi football-data piyasa kapanışıdır.** Marj farkı (%17,2 ↔
%7,26) yüzünden marj arındırılmış olasılıklar birebir aynı ölçekte değildir.

## 6C. xG kalibrasyonu — veri değil, KATSAYI üreten boru hattı

### 6C.1 Neden bu boru hattı ötekilerden farklı

Öteki beş üretici bir **veri seti** üretir ve onu depoya koyar. Bu üretici bir **ölçüm**
üretir ve yalnızca onu koyar. Fark iki sebepten:

1. **Lisans** (§3.3): StatsBomb verisi çoğaltılamaz.
2. **Kapsama**: StatsBomb korpusun liglerini kapsamıyor, yani veri kalıcı olarak taşınsa
   bile korpusun %99,7'sinde kullanılamazdı.

`spor_toto/disari.py` xG'yi *"türetilemeyen"* diye kayda geçirmişti ve gerekçesinin ilk
yarısı artık geçersiz — kaynak açıldı. **İkinci yarısı ayakta** ve girdi `TURETILEMEYEN`
listesinde kaldı; açılan şey ayrı bir anahtarla yazıldı: `xg_vekili`. Aradaki fark bu
bölümün konusudur.

### 6C.2 Kapsama — sayılarla

Depo lig-sezon lig-sezon sayıldı (80 lig-sezon, 3.961 maç). Korpus penceresiyle (2122–2425)
kesişim:

| Lig-sezon | Maç | Not |
|---|---|---|
| Ligue 1 2021/22 | 26 | yalnız PSG'nin maçları |
| Ligue 1 2022/23 | 32 | yalnız PSG'nin maçları |
| Bundesliga 2023/24 | 34 | yalnız Leverkusen'in maçları |
| **Toplam** | **92** | 31.103 maçlık korpusun **%0,3'ü** |

**Süper Lig (T1) hiç yok. Alt İngiliz ligleri (E1/E2/E3/EC) hiç yok** — oysa korpusun
çoğunluğu onlardan geliyor. Kupon maçlarının geldiği lig de T1'dir. Yani xG üretimde bir
girdi olamaz; canlı akış da yok, veri maçlardan yıllar sonra yayımlanıyor.

### 6C.3 Kullanılabilir olan: dört tam lig-sezon

Buna karşılık şu dördü **eksiksiz** — tek takıma indirgenmemiş, bütün fikstür:

| Lig | Sezon | Maç | football-data karşılığı |
|---|---|---|---|
| Premier League | 2015/16 | 380 | `1516/E0` |
| La Liga | 2015/16 | 380 | `1516/SP1` |
| Serie A | 2015/16 | 380 | `1516/I1` |
| Ligue 1 | 2015/16 | 377 | `1516/F1` |
| | | **1.517** | |

Tek takıma indirgenmiş lig-sezonlar (Bundesliga 23/24, Ligue 1 21/22–22/23) kesite
**bilerek alınmadı**: 34 maçın 34'ünde aynı takımın oynadığı bir kesitte ölçülen katsayı o
takımın şut profilini ölçer, ligin değil.

### 6C.4 Ne ölçülüyor

Korpus zaten `ev_sut`/`dep_sut` (toplam şut) ve `ev_isabet`/`dep_isabet` (isabetli şut)
taşıyor. Onlardan bir "fakir adamın xG'si" kurulabilir ama katsayısı bugüne kadar **keyfî**
olurdu. Bu kesit tam olarak onu çözer:

```
xg ≈ a·isabet + b·(sut − isabet) + c
```

Ev ve deplasman **ayrı** uydurulur — ev sahibi şutlarının ortalama kalitesi farklıdır ve bunu
varsaymak yerine ölçmek gerekir. Çözüm 3×3'lük normal denklemlerdir; `numpy` kullanılmaz
(bkz. `scripts/__init__.py`: üretici katman hafif kalır).

Penaltılar ayrı taşınır ve regresyona **girmez**: penaltı xG'si ~0,79 sabittir ve şut
sayımıyla ilişkisi yoktur; aynı denkleme sokulsa katsayıları kirletirdi.

### 6C.5 Eşleme — ada göre değil, MAÇA göre

StatsBomb "Sporting Gijón" der, football-data "Sp Gijon". Bulanık ad eşlemesi bu depoda zaten
bir zayıf nokta (`sehir_rapor.json`: 12 takım eşleşmiyor). Burada birincil anahtar
**(lig, tarih ±1 gün, ev golü, deplasman golü)**; ad benzerliği yalnızca çakışma çözücüdür ve
bir football-data satırı en fazla bir kez eşleşir.

Böylece ad haritası küratörlük değil eşlemenin **çıktısı** olur — `xg_rapor.json` içine yazılır
ve denetlenebilir. Tarih toleransı ±1 gündür çünkü StatsBomb yerel tarihi, football-data
İngiltere tarihini yazar.

### 6C.6 Doğrulama ve lig duyarlılığı

Üretici doğrulamadan dosya yazmaz. İki kapı:

- **Kapsama** ≥ %95 (eşleşen maç oranı).
- **İşaret:** isabetli şutun katsayısı isabetsizinkinden büyük ve ikisi de pozitif olmalı.
  Değilse vekil ters uydurulmuş demektir ve o dosyayı yazmak sessiz bir yalan olurdu.
  Aynı kapı koşarken de duruyor: `health.py` `xg_kalibrasyonu` kontrolü (§7.1'in çalışma
  zamanı karşılığı) — üreticiden geçmemiş, elle düzenlenmiş bir dosyayı o yakalar.

Ayrıca **lig-dışarıda-bırak** raporlanır: dört ligden her biri sırayla dışarıda bırakılıp
diğer üçüyle uydurulur. Katsayının lige ne kadar duyarlı olduğu ölçülmeden bu vekil 22 lige
uygulanamaz. Dördün birbirine ne kadar benzediğini biliyoruz; beşinci bir ligde ne yapacağını
**bilmiyoruz** ve rapor bunu böyle yazar.

### 6C.7 Çıkış — ve neyin çıkmadığı

`backend/data/xg/` altında **iki dosya**, ikisi de commit edilir:

| Dosya | İçerik |
|---|---|
| `xg_kalibrasyon.json` | katsayılar, lig-dışarıda-bırak sonuçları, örneklem sayıları |
| `xg_rapor.json` | eşleşen/eşleşmeyen maç, türetilen ad haritası, kapsama, lisans künyesi |

**Çıkmayan:** ham olay JSON'u ve maç başına xG satırı (§3.3, md. 1.2.1).

Ham dosyalar diske hiç yazılmaz — bir olay dosyası ~3,4 MB ve 1.517 tane var, yani **~5,2
GB**. Akışta işlenir, maç başına dört sayıya indirgenir, atılır. `_kaynak/xg_ozet.jsonl`
yalnızca o özeti tutar (birkaç yüz KB) ve tek işi ~25 dakikalık sıralı indirmeyi yeniden
başlatılabilir kılmaktır; git dışıdır.

## 6D. Resmî Spor Toto arşivi — ikramiye boru hattı

### 6D.1 Neden bu boru hattı §6B'yi kapatır

§6B (elle girilen Süper Toto haftası) bir zorunluluktu ve gerekçesi şuydu:

> §10.1'in tarif ettiği havuz verisi otomatik erişilebilir bir kaynakta yok;
> ikramiye ve oynanma payı yalnızca ilan ekranlarında yayımlanıyor.

**Bu cümlenin ilk yarısı artık doğru değil.** İkramiye tablosu resmî uçta,
makine dostu biçimde, altı sezon geriye duruyor (§2.4). İkinci yarısı hâlâ
doğru: **oynanma payı** hiçbir açık uçta yok ve elle girilmeye devam edecek.

Yani §6B sınıfı kapanmıyor, **daralıyor**: ikramiye bloğu bu boru hattına
devrediyor, oynanma yüzdesi elle girişte kalıyor.

### 6D.2 Kaynak ve uçlar

```
GET /api/GameRound/GetGameRoundYears           sezon listesi
GET /api/GameRound                             TÜM haftalar (her sezon, tek çağrı)
GET /api/GameResult/GetGameResultByGameRoundId?id=<gameRoundId>
```

Üçü de kimlik doğrulamasız. `GetGameRoundNamesByYear?year=<sezon>` de var ama
`GameRound` zaten hepsini tek çağrıda verdiği için kullanılmıyor.

Sonuç ucunun parametresi **`id`**, `gameRoundId` değil — `gameRoundId` yazınca
"Kayıt bulunamadı" döner ve bu sessiz bir tuzaktır: cevap HTTP 200'dür,
`isSucceed: true` taşır ve yalnızca `object: null` verir.

### 6D.3 Ne taşıyor, ne taşımıyor

| Blok | İçerik |
|---|---|
| `weeks[].week` | Hafta numarası — `"9. Hafta"` adından okunur; desene uymayan ad **tahmin edilmez**, `null` kalır ve `data_warnings`a yazılır |
| `weeks[].close_date` | Kapanış tarihi |
| `weeks[].payout.tiers[]` | **15/14/13/12** için kazanan adedi + kişi başı ikramiye |
| `weeks[].bulletin_image` | Bülten görselinin **adresi** — görsel indirilmez |
| `weeks[].data_warnings[]` | Çelişki ve okunamayan alan kaydı |

**Taşımadığı, ve bu bir test bekçisine bağlıdır
(`test_sportoto_arsiv.py::test_yayindaki_arsivde_kupon_dizisi_YOK`):**
15 maçlık liste ve 1/0/2 dizisi. Resmî uçta maç listesi yalnızca bir JPG/PNG
olarak yayımlanıyor. Görseller de ancak **2023/2024'ten itibaren** erişilebiliyor;
2021/22 ve 2022/23 için `/image/<ad>` 404 dönüyor.

Dolayısıyla §10.2'nin kupon ayağı bu kaynakla **kapanmadı**. Kapanması için
bültenin görselden okunması (OCR) ve okunanın bağımsız olarak doğrulanması
gerekir — yolu §10.3'te.

### 6D.4 Doktrinin uygulanışı

| İlke | Uygulanışı |
|---|---|
| 2 — kesin olmayan elenir, doldurulmaz | İkramiyesi alınamayan hafta `payout: null` taşır; kademe alanı `null` ise o kademe **atlanır, sıfır sayılmaz** — "kimse bilemedi" ile "veri yok" ayrı şeylerdir |
| 4 — çelişki gizlenmez | Kapanış tarihi iki uçtan farklı gelirse biri seçilmez; ikisi de saklanır ve `data_warnings`a yazılır |
| 5 — doğrulanmadan yazılmaz | `dogrula()` mükerrer hafta/kimlik, tek dosyada iki sezon, ters sıralı kademe ve negatif değer arar; tutmuyorsa **hiçbir dosya yazılmaz** |
| 6 — türetilmiş sürümlenir, ham sürümlenmez | Sezon JSON'ları ve rapor git'e girer; `_kaynak/` git dışıdır ve tek komutla yeniden üretilir |
| 7 — kaynak dürüstlüğü | `meta.does_not_contain` alanı her dosyanın içinde sınırını yazar |

### 6D.5 `st_history` ile karışmaz

İki veri seti aynı sezonu anlatabilir ve bu **bilinçlidir**: kökenleri farklıdır.
`st_history_2025_26.json` kupon sonuç arşividir (üçüncü parti payload'dan),
`sportoto_arsiv/2025_26.json` ikramiye arşividir (resmî uçtan). Biri ötekinin
yerine geçmez ve `/api/stats` yoluna yalnızca birincisi girer.

Ayrımın ilk kazancı ölçüldü ve **§10.4**'te: 2025/26'nın 41 haftası iki bağımsız
kaynakta yan yana geldi, hepsi eşleşti ve `close_date` alanının iki kaynakta
**farklı anlama geldiği** ortaya çıktı.

---

## 6D-ek. Korpus derinliği — ölçüldü, ama varsayılan yapılmadı

`build_egitim.py` bugün 4 sezon × 22 lig çekiyor (31.103 maç). Altı sezona
çıkarmak **denendi ve ölçüldü**:

| Ölçüm | 4 sezon | 6 sezon (1920 + 2021) |
|---|---:|---:|
| Maç | 31.103 | **45.652** (+%47) |
| Kapanış oranı | %100 | **%100** |
| Açılış+kapanış çifti | %99,99 | **%100** |
| Bahisçi dörtlüsü | %99,99 | **%99,9** |
| Maç istatistiği | %93,01 | **%93,2** |

**Şema hiç bozulmuyor.** Tavan da ölçüldü: football-data'nın tam şeması
**2019/20'de başlıyor** — `mmz4281/1819/T1.csv` başlığında yalnızca
`PSCH/PSCD/PSCA` ve eski `Bb*` toplayıcıları var, `B365C`/`MaxC`/`AvgC`
yok. 1819 ve öncesi eklenirse `acilis_*`/`bahisci_*` kesitleri seyrelir ve
A1/A2 ölçümleri sezona göre dengesizleşir — §6A.7'nin BW/WH/BF'yi dışarıda
bırakma gerekçesiyle aynı gerekçe.

### Neden varsayılan yapılmadı

Korpusu büyütmek **serbest bir kazanç değildir**:

1. **Ölçüm kayıtları bu korpusa çıpalı.** Yalnız
   [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md)'de "31.103"
   **53 yerde** geçiyor ve bunların çoğu bir *ölçümün kaydıdır* ("31.103
   maçta şu çıktı"). Korpusu değiştirip o satırları olduğu gibi bırakmak
   onları yanlış yapar; sayıları değiştirmek ise **yapılmamış bir ölçümü
   yapılmış gibi göstermek** olur. İkisi de bu deponun yasakladığı şeydir.
2. **`artefakt.py`** eğitilmiş modelin korpus sha256'sını taşıyor;
   `health` bayatlık görünce **kırmızı** yanıyor.
3. **Kazanç ölçülmüş ve küçük.** README §1.1 ve §10 aynı türden daha çok
   verinin Brier'i büyütmediğini zaten ölçtü (kalan etki 0,0005–0,0015).
   Büyüyen şey **istatistiksel güçtür, sinyal değil**.

Bu yüzden derinleştirme bir **komut seçeneğidir**, varsayılan değil:

```bash
python scripts/build_egitim.py --sezonlar 1920 2021 2122 2223 2324 2425
```

Varsayılanı çevirmek isteyen **önce §3.x ölçümlerini yeniden koşmalı** ve
sayıları kaydıyla birlikte güncellemelidir. O ayrı bir iştir ve bu belgede
açık bir iş olarak durur.

---

## 6E. Havuz — ikramiye tablosundan geri hesap

### 6E.1 Ölçülen bölüşüm: 35 / 20 / 20 / 25

Havuzu hesaplanabilen **222 haftada** kademe havuzlarının birbirine oranı:

| Oran | Beklenen | Sonuç |
|---|---|---|
| 14 ÷ 13 | 1,00 | 218 haftanın **214'ünde birebir**; kalan 4'ü binde birin altında |
| 12 ÷ 13 | 1,25 | ortanca **tam 1,2500** |
| 15 ÷ 13 | 1,75 | 176 haftanın **135'inde tam**, hiçbirinde **altında değil** |

Bölüşüm sabit bir kuraldır ve `spor_toto/havuz.py::BOLUSUM`'da durur.

### 6E.2 Devir 15'e özgü değildir — model bir kez düzeltildi

İlk model yalnızca 15 kademesini devirli sayıyordu ve 222 haftanın **10'unu**
"bölüşüm bozuk" diye işaretliyordu. Veri aksini gösterdi: **kazanansız kalan
her kademe** payını ileri taşır ve ertesi hafta **aynı kademe** fazlasıyla
döner.

| Hafta | Kazanansız kademe | Ertesi hafta o kademe ÷ birim |
|---|---|---|
| 2021/22 hf 47 → 48 | 15 ve 14 | **1,58** |
| 2022/23 hf 28 → 29 | 15 ve 14 | **1,03** |
| 2025/26 hf 7 → 8   | 15 ve 14 | **1,67** |
| 2025/26 hf 45 → 46 | 15 ve 14 | **1,59** |

Model genelleştirilince açıklanamayan hafta **10'dan 2'ye** düştü.

İkinci bir düzeltme daha gerekti ve o da ölçümden geldi: devir eşiği önce
**1 TL mutlak**tı ve 176 haftanın 174'ü "devirli" görünüyordu. Sebep kuruş
yuvarlaması — kişi başı ikramiye kuruşa yuvarlanıp on binlerce kazananla
çarpılınca hata binlerce TL'ye çıkıyor. Eşik göreliye çevrildi ve ayrım
temiz: gürültünün en büyüğü birimin **1,01e-3**'ü, gerçek devrin en küçüğü
**4,82e-2**'si — arada üç mertebe boşluk var.

### 6E.3 Zincir kapanıyor — modelin bağımsız kanıtı

Bölüşüm oranları tek bir haftanın **içinden** okunur. Zincir ise **ardışık
iki haftayı** birbirine bağlar, yani bağımsız bir sınamadır:

| Ölçüm | Sonuç |
|---|---|
| Devreden haftanın ardından devir alan hafta | **41** |
| gelen ÷ giden oranı, ortanca | **1,000** |
| birebir eşit (%2 içinde) | **36 / 41** |
| oranı 1'in **altına** düşen | **0 / 41** |

Kalan 5'i ardışık devirdir (üst üste kazanansız kapanan haftalar). Oranın
1'in altına hiç inmemesi kritiktir: devir ancak **ekleyebilir**, düşüremez.

### 6E.4 Elle girilen kayıtla çapraz doğrulama

2026/27 2. hafta için hesap **42.842.867,18 TL** veriyor; elle girilen kayıt
(§6B, ekran görüntüsünden) **42.842.867,72 TL** yazıyor. Fark **0,54 TL** —
42,8 milyonda, yani milyonda 0,013 — ve bu, 14-kademesinin kendi kuruş
yuvarlaması payının (±0,61 TL) içindedir.

> **Bu satır bir kez fazla iddialı yazıldı.** Önce "kuruşuna kadar aynı"
> denmişti; o sırada birim 13-kademesiydi ve hata 33,12 TL'ydi, sıfır değil.
> Birim seçimi hassaslaştırılınca (kazananı az olan kademe daha az yuvarlama
> hatası taşır) 0,54 TL'ye indi. Ölçülen sayı ne ise o yazılır.

### 6E.5 Ne vermiyor

- **Brüt hasılat değil, DAĞITILAN havuz.** Aradaki fark Spor Toto'nun payıdır
  ve bu veriden çıkarılamaz. Modül her yerde `dagitilan` der, "hasılat" demez.
- **Kazananlar kolon sayısıdır, bilet değil** (§3.40). Bu ayrım çözülmedi.
- **Açıklanamayan 2 hafta düzeltilmez, işaretlenir** (doktrin 4): 2024/25
  hf 43 ve 2025/26 hf 10 — ikisinde de 12-kademesi beklenenin **altında**,
  yani devir değil gerçek sapma.

---

## 6F. Bülten görseli — OCR boru hattı

### 6F.1 Neden OCR, ve neden burada meşru

§6D resmî arşivi kurdu ama maç listesini vermedi: haftanın 15 maçı yalnızca
bir bülten **görseli** olarak yayımlanıyor. §10.3 bunu geçmiş kupon verisinin
önündeki tek engel olarak yazmıştı.

Görseller **makine üretimidir**: sabit şablon, yüksek kontrast, numaralı
satırlar, `EV - DEPLASMAN` biçimi. OCR burada bir umut değil, uygun bir araç.

Ayarlar denenerek seçildi, varsayılmadı:

| Ayar | Gerekçe |
|---|---|
| `--psm 4` | Sütunlu metin. `psm 6` aynı görselde 15 satırın 9'unu okudu ve adları bozdu ("BAŞAKŞEMİM FK"); `psm 11`/`12` tabloyu hiç görmedi |
| ×3 ölçek | Küçük görseller (595×756) ×1'de 9/15, ×2'de 14/15, ×3'te 15/15 |
| `-l tur` | İ, Ş, Ğ, Ç, Ö, Ü olmadan adlar kullanılamaz |

### 6F.2 Doktrin 2 burada gevşemez, sıkışır

**OCR çıktısı bir veri değil, bir arama anahtarıdır.** Betik okuduğunu
"düzeltmez", eksiği tamamlamaz, benzer isme yuvarlamaz. Harf düzeltmesi
yapılmaz — "BAŞAKŞEMİM"i "BAŞAKŞEHİR"e çevirmek tam olarak yasak olan şeydir;
o iş §6G'de fikstüre karşı yapılır ve orada tutmayan maç **düşer**.

Bir kural bir kez **ihlal edildi ve test yakaladı**: biçimsel temizlik sondaki
noktayı da kırpıyordu ve "A.Ş." → "A.Ş" oluyordu. Bu biçimsel değil içerik
değişikliğidir; kural daraltıldı, nokta artık kırpılmıyor.

### 6F.3 Sıra kilidi — §7.4'ün tekrarına karşı

En büyük risk sıradır: OCR bir satırı düşürebilir ve düşen satır sessizce
sırayı kaydırır. Ölçüldü — sol sütundaki küçük rakam görsele göre düşüyor
(2023/24 5. haftada 15 maç adının tamamı doğru okundu, numaraların yalnızca
3'ü çıktı).

Numara **konumdan kurtarılır ama uydurulmaz**, ve iki kilit bunu güvenli
kılar:

1. **Tam olarak 15 satır bulunmalı.** 14 ya da 16'da hafta elenir — hangisinin
   kaydığı bilinemez.
2. **Numarası okunabilen her satır konumuyla uyuşmalı.** Bir tanesi bile
   tutmuyorsa hafta elenir.

### 6F.4 Kapsama

| Ölçüm | Sonuç |
|---|---|
| Bülten görseli olan hafta | 224 |
| Görseli erişilebilir olan | 194 (2021/22 ve 2022/23'ün çoğu **404**) |
| **15/15 okunan** | **156** |
| Erişilebilir görsellerin okunma oranı | **%80,4** |

### 6F.5 Bağımlılık ayrı tutuldu

Bu, deponun **stdlib dışına çıkan tek** üretim betiğidir: `tesseract` (sistem
paketi) + `pillow`. Bu yüzden `pyproject.toml`da `ocr` **ekstrasıdır**,
varsayılan kuruluma girmez; `check.sh` ve CI onu kurmaz; testler bağımlılık
yoksa OCR'a dokunanları **atlar** ve saf ayrıştırma testleri her yerde koşar.
Üretilen çıktı sürümlendiği için veriyi **okumak** için kimsenin tesseract
kurması gerekmez.

## 6G. Geçmiş sezon — bülten + fikstür birleştirme

### 6G.1 Eşleştirme burada `build_odds.py`dan zordur

`build_odds.py` eşleştirirken **skoru biliyor** ve onu ayırt edici olarak
kullanıyor. Burada skor **aranan** şeydir, dolayısıyla o kilit yok. Yerine
üç kilit kondu, üçü de "şüpheliyi ele" yönünde:

1. İki taraf da eşiği geçmeli (`0,72` / ortalama `0,82`).
2. **Aday tek olmalı** — pencerede eşiği geçen ikinci bir aday varsa maç
   düşer. "En iyisini seç" demek iki benzer adlı takım arasında sessizce kura
   çekmektir.
3. 15/15 tamamlanmayan hafta düşer.

`sadelestir`/`benzerlik` yeniden yazılmadı, `build_odds.py`dan içe aktarıldı.

### 6G.2 Zaman penceresi bir AYAR değil, bir KORUMA

Eşleşmeyen maçların büyük bölümü **ertelenmiş** maçlardır ve fikstürde
haftalar/aylar sonra durur:

| Bültende | Gerçekte oynandığı |
|---|---|
| hf 33 · 2024-03-15 · Atalanta – Fiorentina | **2024-06-02** |
| hf 37 · 2024-04-12 · Monaco – Lille | 2024-04-24 |
| hf 3 · 2023-08-25 · Ad. Demirspor – Beşiktaş | 2023-09-27 |
| hf 4 · 2023-09-01 · Ath Madrid – Sevilla | **2023-12-23** |

Ertelenen maçın aylar sonraki sonucu **o haftanın kupon sonucu değildir.**
Pencereyi genişletmek bu satırları "eşleşti" gösterir ve sessizce yanlış bir
1/0/2 dizisi üretir. Bu yüzden pencere dışında kalan maç düşer, onunla
birlikte hafta düşer.

### 6G.3 Türkçe ad tablosu — ölçülerek kuruldu

Bülten yabancı kulüpler için Türkçe adlar kullanıyor (MARSILYA, BAYERN MÜNİH,
B. LEVERKUSEN, WOLVERHAMPTON). 156 haftada eşleşmeyen adlar sayıldı ve
yalnızca football-data'da karşılığı **doğrulananlar** tabloya girdi. Tablo bir
"yakınsatma" değil, doğrulanmış bir sözlüktür; tabloda olmayan ad olduğu gibi
bulanık eşleştirmeye gider.

### 6G.4 Kapsama ve yapısal tavan

| Ölçüm | Sonuç |
|---|---|
| Bülten okunan hafta | 156 |
| **15/15 eşleşen hafta** | **112** (4 sezon) |
| Kupon maçı | **1.680** |

> **Sayılar §6I'de büyüdü** (107 → 112, 1.605 → 1.680). Sebep yeni veri
> değil, eşleştirmedeki bir kusurun düzeltilmesi: Türkçe noktalı `İ`
> sözlük aramasını bozuyordu ve `BULTEN_ESLERI`nin üç satırı hiç
> çalışmamıştı. Katkı tamamen eklemeli — kaybolan hafta yok.

Elenenlerin çoğu **milli takım haftalarıdır**: football-data yalnızca kulüp
liglerini kapsıyor, milli maçları hiç taşımıyor. Bu bir eşleştirme sorunu
değil, kaynağın yapısal sınırıdır ve kapanmaz.

### 6G.5 Çapraz doğrulama — ve bulunan bir SIRA ayrışması

İki boru hattı birbirini hiç görmeden aynı sezonu üretiyor:

    eski: sportototahmin hafta payload'ı (üçüncü parti Nuxt JSON)
    yeni: resmî bülten görseli → OCR → football-data fikstürü

| Ölçüm | Sonuç |
|---|---|
| Ortak hafta (2025/26) | 29 |
| **1/0/2 dizisi birebir aynı** | **28 / 29** |

**Ayrışan tek hafta bir sonuç hatası değil, bir SIRA ayrışmasıdır.** 2025/26
30. haftada iki kaynak **aynı 15 maçı** taşıyor (skor kümeleri birebir aynı)
ama kupon sırası farklı: bültende Göztepe–Eyüpspor **6.** sırada, payload'da
**15.** sırada; aradaki dokuz maç birer kayıyor.

Bu §7.4'ün v1 vakasıyla **aynı sınıfta** bir bulgudur ve doktrin 4 gereği
düzeltilmedi: hangi kaynağın haklı olduğu ölçülmedi, fark raporlanıyor.
Bekçi: `test_gecmis_sezon.py::test_ayrisan_hafta_SIRA_farkidir_sonuc_farki_degil`
— maç kümesi de ayrışırsa sorun sırada değil eşleştirmededir ve o test bunu
ayırt eder.

> **Not:** resmî bülten görseli Spor Toto'nun kendi yayınıdır, payload üçüncü
> partidir. Doktrin 3 ("sıra kaynağın kendi sırasıdır") bu ayrışmada resmî
> kaynağı işaret eder — ama bu bir **hipotezdir**, ölçüm değil, ve öyle
> yazılmıştır.

### 6G.6 Yeni bir sızıntı riski doğdu — ve görünür kılındı

Kupon değerlendirme seti 2022/23–2025/26'yı kapsıyor. Eğitim korpusunun
varsayılan sezonları ise `2122, 2223, 2324, 2425`. **Kesişim üç sezon:**
`2223, 2324, 2425`.

Bu bugün aktif bir hata değildir — yeni set henüz hiçbir ölçüme bağlı değil.
Ama **sessiz kalırsa hataya dönüşür**: o sezonların kupon haftaları üzerinde
ölçülen bir tahminci, aynı maçlarda *eğitilmiş* olur ve isabet olduğundan iyi
görünür. §6A.3 aynı gerekçeyle 2025/26'yı korpusun dışında bırakmıştı; o
gerekçe şimdi üç sezon daha için geçerli.

Doktrin 4 gereği çelişki gizlenmedi, **veriyle birlikte taşınıyor**:
`egitim_rapor.json` artık `kupon_sezonlari`, `kesisim` ve `kesisim_notu`
alanlarını yazıyor, `build_egitim.py` da koşum sonunda ekrana uyarı basıyor.

**Kural:** kesişimdeki sezonların kupon haftalarında ölçüm yapılacaksa
`evaluate.sezon_anahtari` (sezon dışarıda bırakmalı) kullanılmalıdır; düz
`capraz_olc` sızdırır. Kesişimi tamamen boşaltmak isteyen `--sezonlar` ile o
sezonları çıkarır — ama bu korpusu 31 binden ~8 bine düşürür, yani bedeli
ağırdır ve karar ölçümü yapanındır.

### 6G.7 `st_history_2025_26.json` ile karışmaz

Üretilen dosyalar `data/st_history/<sezon>.json` altındadır; eski dosya
yerinde durur ve `/api/stats` ile 27 değişmez ona bakmaya devam eder. Yeni
dizin ayrı bir köken sınıfıdır (`origin: turetilmis`) ve meta'sında bunu
yazar.

---

## 6H. Oran arşivi artık sezonlu

§5'in oran boru hattı tek sezona çiviliydi ve **üç sabiti** vardı; üçü de
sessiz hataya açıktı:

| Sabit | Sessiz hata |
|---|---|
| `SEZON = "2526"` | başka sezon istenemezdi |
| `odds_2025_26.csv` (sabit ad) | ikinci sezon birincinin **üstüne** yazardı |
| ortak önbellek dizini | `indir()` var olan dosyayı atlar → başka sezon istendiğinde **sessizce 2025/26 CSV'leri** okunurdu |

Üçü de sezondan türetiliyor artık (`--sezon`, `sezon_dosya_adi`,
`_cache_dizini`). SQLite kopyası da ayrıldı: ortak dosyada `mac` ve `oran`
tablolarının anahtarı `(week, no)` ve sezon bileşeni yok, yani ikinci sezon
birincinin satırlarını `INSERT OR REPLACE` ile ezerdi.

**Varsayılan yol hiç oynamadı:** `--sezon 2526` ile üretilen
`odds_2025_26.csv` byte byte aynı çıktı, rapor adı da değişmedi.

### Kapsama — ve neden yeni sezonlarda %100

| Sezon | Eşleşen | Tam hafta |
|---|---|---|
| 2022/23 | 255 / 255 (**%100**) | 17 / 17 |
| 2023/24 | 465 / 465 (**%100**) | 31 / 31 |
| 2024/25 | 450 / 450 (**%100**) | 30 / 30 |
| 2025/26 (eski kayıt) | 567 / 615 (%92,2) | 36 / 41 |

Sebep yapısaldır: §6G'nin ürettiği takım adları **zaten football-data
adlarıdır** — eşleştirme orada yapıldı ve `home`/`away` alanlarına kaynağın
kendi yazımı kondu. Üstüne `build_odds.py` skoru da ayırt edici olarak
kullanıyor. Yani bu %100 bir şans değil, iki aşamalı eşleştirmenin sonucu.

### Sezonlar birleştirilmez

`odds.py`nin anahtarı `(week, no)` ve sezon bileşeni **yok**. Bu yüzden her
sezon kendi dosyasında durur ve `load_odds(sezon=…)` seçer.
`season_1x2_summary` de sezon almak zorundadır: `weeks` bir hafta *numarası*
listesidir, sezon taşımaz — sezon geçirilmezse başka bir sezonun arşivinde
aynı numaralar bulunur ve özet sessizce başka bir sezonu anlatırdı.

---

## 6I. Eşleştirme teşhisi — ve sessizce ölü bir sözlük

§6G'nin boru hattı 156 haftanın **107'sini** kabul ediyor, 49'unu eliyordu.
`georgedouzas/sports-betting` incelemesi bir eşleştirme stratejisi önerdi
(küresel bire-bir atama + artık-tek kuralı) ve soru şuydu: elenen 49
haftanın kaçına dokunabilir?

**Önce ölçüldü, sonra kod yazıldı** — ve ölçüm öneriyi reddetti.

### 6I.1 `--teshis`: "eşleştirmeyi iyileştirelim" ölçülebilir bir cümle mi

`eslestir` iki gerekçe döndürüyordu ve birincisi **iki çok farklı durumu
birleştiriyordu**: *yakın bir aday var ama eşiği geçmiyor* ile *pencerede
benzeyen hiçbir şey yok*. Ayrım yapılmadan hiçbir strateji kararı
verilemez. `teshis_sinifi` gerekçeyi üçe ayırır:

| Sınıf | Strateji değişikliği kurtarabilir mi |
|---|---|
| `ayirt_edilemedi` | **evet** — iki aday eşiği geçti, seçim yapılmadı |
| `aday_yok_esik_alti` | belki — yakın aday var, ad kusuru olabilir |
| `aday_yok_uzak` | **hayır** — ertelenmiş maç ya da kapsam dışı lig |

Ölçüm:

```
mac (elenen haftalar dahil):
     0  ayirt_edilemedi
    86  aday_yok_esik_alti
   233  aday_yok_uzak
```

**156 haftanın hiçbirinde** pencerede iki adayın birden eşiği geçtiği bir
maç yok; hiçbir fikstür iki bülten maçına atanmıyor. Önerilen strateji bu
kesitte çalışacak bir şey **bulamazdı** ve alınmadı.

`build_odds.py` tarafı da aynı biçimde reddedildi: `odds_rapor.json`un 48
eşleşmeyen maçının tamamı **milli takım haftasıdır** ve football-data o
maçları hiç taşımıyor. Kapsama sorunu, eşleştirme sorunu değil.

### 6I.2 Ama teşhis başka bir şey buldu — ve o gerçekti

`aday_yok_esik_alti` sınıfının en yüksek skorlu satırları okununca kusur
görünür oldu:

```
"MARSILYA".lower()  ->  "marsilya"                  sozlukte VAR
"MARSİLYA".lower()  ->  "marsi" + U+0307 + "lya"    sozlukte YOK
```

Türkçe noktalı `İ` (U+0130) Unicode'da `i` + **birleşen nokta**ya küçülür.
İkisi ekranda aynı görünür. `BULTEN_ESLERI`nin anahtarları düz ASCII
olduğu için, bülten yazımında `İ` geçen her satır **hiçbir zaman
çalışmadı** — `marsilya`, `sporting lizbon`, `milano`.

Bülten **büyük harfli bir görselden** OCR ile okunuyor (§6F), yani `İ`
orada kural dışı değil **normal hâldir**: kusur, sözlüğe en çok ihtiyaç
duyulan yerde vuruyordu. `build_odds.sadelestir` aynı temizliği ilk günden
yapıyor; buradaki eksiklik bir **ayrışmaydı**.

### 6I.3 Üç düzeltme, her biri ayrı ölçüldü

| Düzeltme | Kabul edilen hafta |
|---|---|
| (başlangıç) | 107 |
| Unicode birleşen işaret temizliği | **110** |
| OCR `/` sütun ayracı artığı | **112** |
| teşhiste doğrulanan 7 sözlük satırı | **112** |

`/` artığı ayrı bir sınıftır: bülten görselindeki sütun ayracı zaman zaman
adın başına düşüyor (`/ MARSILYA`). Hiçbir kulüp adı `/` ile başlamaz,
dolayısıyla bu bir "yakınsatma" değil bir **temizliktir**; iç `/`
karakterine dokunulmaz.

Eklenen 7 sözlük satırının hepsi eşik altında kalmış maçların en iyi
adayından okundu ve football-data'da **tek tek doğrulandı**. Aynı listede
duran ama karşılığı doğrulanamayanlar (Qingdao'nun ad değişikliği,
Wuhan'ın **yanlış** deplasman eşi) bilerek alınmadı — eşiğin doğru biçimde
reddettiği şeyi sözlükle geri sokmak, eşiği kaldırmakla aynı şeydir.

### 6I.4 Katkı tamamen eklemeli, çapraz doğrulama güçlendi

| | Önce | Sonra |
|---|---|---|
| Kabul edilen hafta | 107 | **112** |
| Kupon maçı | 1.605 | **1.680** |
| Kaybolan hafta | — | **0** |
| Değişen 1/0/2 dizisi | — | **0** |
| Çapraz doğrulama ortak hafta | 29 | **31** |
| Birebir aynı | 28 | **30** |
| Ayrışan | 1 | **1** (aynı bilinen kupon sırası vakası) |

Kupon × korpus kesişimi yeniden ölçüldü: **1.155/1.605 → 1.200/1.680**
(oran %72 → %71). `arena.py`, `tahmin.py` ve `test_tahmin.py`'daki sabit
sayılar güncellendi.

### 6I.5 Ölçüm kesiti KALDI, ve niçin

`evaluate.kupon_kesiti_tum` hâlâ **114 hafta** döndürüyor: yeni beş
haftanın oran kapsaması yok, dolayısıyla `usable` değiller. Büyüyen şey
`st_history` setidir; ölçüm kesiti oran arşivi genişleyince büyür. Bu bir
eksiklik değil, iki setin **ayrı kapılardan** geçtiğinin kanıtıdır.

### 6I.6 Canlı sezon sızmıyor

2026/27 bülteni okunuyor ama kabul edilen haftası **0**. `evaluate`in kupon
sezonları aynı sezonu iki kez saymamak için özenle kurulmuştu (§6G.5);
canlı sezonun bu tarihsel sete sızması o özeni boşa çıkarırdı. Bekçi:
`test_canli_sezon_gecmis_sete_SIZMAZ`.

    python scripts/build_gecmis_sezon.py --teshis
    python scripts/build_gecmis_sezon.py


## 7. Kalite güvencesi

### 7.1 Üretim anında

`build_history.py` dosyayı yazmadan önce her hafta için:

```python
assert len(results) == 15 == len(matches)
assert (n1, n0, n2) == tuple(results.count(s) for s in "102")
assert results == "".join(m["code"] for m in matches)
```

Yani liste, dizi ve sayımların üçü birbirini tutmadan çıktı üretilmez.

### 7.2 Bağımsız çapraz doğrulama

51. hafta için Misli sonuç satırı: `X X X 1 1 1 1 2 2 2 1 2 X 1 1` → `000111122212011`.
Üretim çıktısı **birebir aynı**. Bu, yalnızca kodların değil **sıranın** da en az bir haftada
bağımsız kaynakla doğrulandığı anlamına gelir.

### 7.3 Okuma anında — `data_quality` bloğu

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

### 7.4 Vaka: v1 sıra hatası

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

### 7.5 Vaka: BOM hatası

football-data ana lig dosyaları latin-1 okunuyor; UTF-8 BOM bu kodlamada `ï»¿` olarak gelip ilk
sütunun adına yapışıyor (`ï»¿Div`). Temizlik yalnızca `﻿` arıyordu, bu yüzden `Div`
anahtarı hiç bulunamıyor ve **539 maçın lig etiketi boş kalıyordu**. Düzeltildikten sonra 15
lig doğru etiketlendi — Süper Lig'de beraberlik %29,8, Premier Lig'de %19,7 gibi kırılımlar
ancak bu alanla mümkün.

**Ders.** Boş kalan bir alan hata vermez, sadece sessizce kaybolur. Üretim çıktısındaki özet
tablolar (script'in bastığı lig dağılımı) bunu yakalayan şeydi.

### 7.6 Test bekçileri

| Test | Neyi garanti eder |
|---|---|
| `test_history.py::test_veri_seti_temiz` | Yayındaki veri seti `data_quality` denetiminden geçiyor |
| `test_history.py::test_mac_listesi_diziyi_uretir` | Kod skordan, dizi maç sırasından türüyor |
| `test_history.py::test_ayni_hafta_icinde_takim_tekrar_etmez` | Aynı hafta aynı takım iki kez yok |
| `test_history.py` (analiz blokları) | Sütun toplamları sezon toplamına eşit; dilimleme tutarlı |
| `test_odds.py::test_arsiv_gecmis_veriyle_birebir_hizali` | Oran satırları kupon maçlarıyla sıra sıra aynı |
| `test_odds.py::test_favori_isabeti_gerceklikle_uyumlu` | Favori isabeti %45–70 bandında (eşleştirme kaymışsa çıkar) |
| `test_api_stats.py` | Uçların sözleşmesi; **diğer pazarların arayüze sızmadığı**; karar destek blokları ve Brier'in maçları bölüştürdüğü |
| `test_backtest.py::test_kume_ici_hafta_15_tutturur` | Skorlama doğru: küme içi hafta 14-garanti gereği en az 14 tutturur |
| `test_backtest.py::test_holdout_taramadan_iyi_olamaz` | Aşırı uyum ölçüsü tutarlı: hold-out taramanın en iyisini geçemez |
| `test_api_backtest.py::test_diger_pazarlar_geri_teste_de_sizmaz` | 1X2 kuralı geri testte de geçerli |
| `test_snapshot_iddaa.py::test_askidaki_ayak_maci_eler` | 1.00 fiyat sayılmaz |
| `test_snapshot_iddaa.py::test_farkli_snapshot_birikir` | Arşiv gerçekten birikiyor, üstüne yazmıyor |
| `test_sportoto_arsiv.py::test_yayindaki_arsivde_kupon_dizisi_YOK` | Resmî arşiv maç listesi taşımıyor — sınır sessizce kaymasın |
| `test_sportoto_arsiv.py::test_eksik_kademe_sifir_sayilmaz` | "kimse bilemedi" ile "veri yok" ayrı kalır |
| `test_sportoto_arsiv.py::test_hafta_no_tahmin_edilmez` | Hafta numarası uydurulmaz (doktrin 2) |
| `test_sportoto_arsiv.py::test_celisen_kapanis_tarihi_raporlanir` | İki uç çelişirse biri sessizce seçilmez (doktrin 4) |

Toplam 113 test bu dört veri setini korur (backend paketi 2.027 test). `python -m spor_toto.health`
27 değişmez çalıştırır; `oran_arsivi` ve `geri_test` bu katmanı, `tahmin_referanslari`
tahmin katmanının ölçüm koşumunu korur.

### 7.7 Bilinen kabuller

| Kabul | Gerekçe |
|---|---|
| Yalnızca normal süre golü | Spor Toto sonucu normal süre üzerinden okunur |
| Gol aralığı 0–20 | Anlamsız parse değerlerini reddetmek için |
| Kupon sırası = kaynağın sırası | Resmi bülten numaralandırmasıyla ayrıca karşılaştırılmadı; 51. hafta bağımsız doğrulandı (§7.2) |
| Oran = kapanış, yoksa açılış | Kapanış daha bilgilidir; kaynak sırası Avg → B365 → PS → BFE → Max |
| Lig bilgisi oran arşivinden gelir | Payload maç kaydı lig adı taşımıyor |
| İddaa bülteninde 1.00 fiyat değildir | Askıya alınmış ayağın yer tutucusu; ölçüldü (§6.2) |
| Bülten saatleri UTC saklanır | Oran arşiviyle aynı eksende olsun diye |

---

## 8. Sınırlar

1. **Tam sezon değil:** 41 / ~53 hafta. Eksik skorlu haftalar bilinçli olarak yok.

   > **Genişledi (2026-08-30).** Bültenden okunup fikstüre bağlanan set (§6F, §6G)
   > **4 sezon · 107 hafta · 1.605 maç** ekledi. Yine "tam sezon" değil ve olmayacak:
   > tavan **milli takım haftalarıdır** — football-data yalnızca kulüp liglerini
   > kapsıyor ve o haftalar bu yolla hiçbir zaman gelmeyecek. Ayrıca bültenin
   > listelediği ama **ertelenen** maçı olan hafta da bilinçli olarak düşer (§6G.2).

2. **Tek sezon değil, artık dört.** Bu madde "tek sezon: 2025/2026, 41 hafta küçük
   örneklem" diyordu. Kupon değerlendirme seti **148 haftaya** çıktı (41 eski +
   107 yeni, 29'u aynı sezonun iki bağımsız okuması). İstatistiksel güç hâlâ
   sınırlı ama sınır artık "tek sezon" değil.
3. **Milli maç haftalarında oran yok** (5, 10, 15). Oran blokları o haftalarda boş; kapsama
   hiçbir zaman %100 olmayacak.
4. **Geçmiş iddaa oranı yok** (§3.2). Piyasa oranı vekildir; ölçülen marj farkı (%17,2 → %7,26)
   bu vekilin neden yalnızca *yapı* için kullanılabileceğini gösterir. İleriye dönük arşiv
   §6 ile başladı; haftalık tetik açık ama arşiv henüz tek snapshot.
5. **Üçüncü parti kaynak riski:** üç kaynak da dış. İlk ikisi silinir ya da biçim değiştirirse
   yeniden çekim gerekir; üretim scriptleri tam olarak bunun için var. Üçüncüsünde (iddaa) bu
   kurtarma yolu **yok**: kaçırılan hafta kaçmıştır.
6. **Resmi bülten numarası doğrulanmadı:** kupon sırası kaynağın sırasıdır.

Amaç tahmine döndüğü için iki sınır daha kritik hale geldi ve ayrıca yazılmalıdır:

7. **Piyasa dışı doğrudan sinyal yok — ama türetilebilir olanlar var.** Üç veri setinin
   *doğrudan* taşıdığı her şey ya sonucun kendisi ya da piyasanın sonuç hakkındaki
   fiyatıdır: sakatlık, kadro, motivasyon kaydı yok.

   > **Düzeltme (2026-08-17).** Bu madde önce "veride piyasa dışı **hiçbir** sinyal yok"
   > diyordu; bu fazla genişti. Tarih ve takım alanlarından **türetilebilecek** birkaç
   > özellik var ve hiçbiri denenmedi: dinlenme günü, fikstür sıkışıklığı, seyahat, derbi,
   > sezon sonu bahis. T5 yalnızca **takım formunu** denedi ve piyasanın onu fiyatladığını
   > gösterdi; bu, diğerleri hakkında hiçbir şey söylemez.
   > Planı: [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §6.2 A3.

   Yine de sınır gerçektir: bu özellikler de piyasanın gördüğü bilgiden türer, yalnızca
   farklı biçimde. Ölçülen sayılar bu sınırla tutarlı — hold-out isabeti **36 haftada 1**
   (%2,8; aralık %0,5–14,2), formun artık değeri ~0.

   > **Sayı güncellendi (2026-08-23).** Burada "hold-out isabeti 0 hafta" yazıyordu; o
   > sayı `orantili` arındırma ölçeğinde ölçülmüştü ve varsayılan `shin`e çevrilince 1
   > oldu (A5). **Argüman değişmedi:** 36 haftada 1 isabet, "piyasa dışı sinyal aramanın
   > sınırı" tezini aynen destekler — tek bir olay ve güven aralığı sıfırı içeriyor.

   > **A1 bu sınıra en sert kanıtı ekledi (2026-08-17).** Korpus artık her maçın **açılış
   > ve kapanış** çizgisini ayrı ayrı taşıyor (§6A.6) ve ikisi 31.099 maçta karşılaştırıldı:
   > kapanış açılışı geçiyor (+0,0025 Brier, aralık sıfırın tamamen üstünde) — yani piyasa
   > maç öncesinde gelen bilgiyi **soğuruyor.** Ama hareketin yönü kapanışın ötesinde hiçbir
   > şey söylemiyor: model hareketi yalnızca %1,01 uzatmak istiyor. Ham sinyal güçlüyken
   > (en büyük harekette çizginin lehine oynadığı sembol %47,2'ye karşı %30,2 tutuyor)
   > artık değerin sıfır olması, **piyasanın kendi bilgisinin bile kapanışta tükendiği**
   > anlamına gelir. Ölçüm: [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.14.

   > **A2 bir uyarı ekledi (2026-08-17).** Korpus artık bahisçi kırılımı da taşıyor (§6A.7)
   > ve anlaşmazlık ölçüldü. Ham tablo güçlü bir sinyal gösteriyordu — bahisçiler ayrıştıkça
   > kolektifin Brier'i düşüyordu — ama ilişki **favori gücüyle karışıktı** ve favori
   > sabitlenince tamamen kayboldu. Bu, veri sınırlarını okurken taşınması gereken bir ders:
   > *ham bir tablo, karışmış bir değişkenle gerçek sinyal taklidi yapabilir.* §6.2 A3'ün
   > listesindeki özelliklerin çoğu (dinlenme günü, fikstür sıkışıklığı, sezon sonu
   > motivasyonu) aynı riski taşıyor ve her biri en az bir kontrol dilimiyle ölçülmelidir.
   > Ölçüm: [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.15.

   > **A3 bu maddeyi kapattı (2026-08-17).** Listedeki altı özellikten **ikisi türetilemedi**
   > — seyahat (şehir/koordinat yok; bir maçın iki takımı hep aynı ligde) ve derbi (rekabet
   > tablosu yok). Kalan dördü — dinlenme günü, fikstür sıkışıklığı, iç/dış saha ayrı formu,
   > sezon sonu payı — türetildi ve **dördü de piyasayı geçemedi.**
   >
   > **Ama bu maddeye yeni ve daha keskin bir sınır eklendi:** korpus 22 lig taşıyor, **kupa
   > ve Avrupa maçları içinde yok.** Dolayısıyla ölçülen şey yorgunluk değil, *korpustan
   > türetilebilen yorgunluk vekilidir*. Kör nokta ölçüldü: deplasman "dinlenmiş" göründüğünde
   > ev takımı piyasanın beklediğini +0,0655 aşıyor ve etki Avrupa'ya takım veren liglerde
   > **dört kat** güçlü — görünmeyen bir maç oynanmış olmasıyla tutarlı. Bir bulgu değil
   > (n=445, dışarıda bırakmalı katkısı sıfır) ama **fikstür verisi** artık somut bir veri
   > ihtiyacı olarak yazılı (§10.1 ile aynı statüde).
   > Ölçüm: [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.16 ve §6.2 A4.
9. **xG var ama kapsamıyor — ve bu, "kaynak yok"tan farklı bir sınırdır.** StatsBomb Open
   Data (`hudl/open-data`) şut başına gerçek xG'yi serbestçe veriyor, yani `disari.py`nin
   eski gerekçesi (Understat `robots.txt`, fbref Cloudflare) geçersizleşti. Ama depo **Süper
   Lig'i ve alt İngiliz liglerini kapsamıyor** ve korpus penceresiyle kesişimi 92 maç (§6C.2).
   Üstelik canlı akış yok: veri maçlardan yıllar sonra yayımlanıyor, yani `/tahmin` onu
   ilkesel olarak da göremezdi.

   Bu yüzden kaynak **girdi değil referans** olarak kullanıldı: kapsadığı 1.517 maçta korpusun
   kendi şut sayımı gerçek xG'ye karşı kalibre edildi ve kalibre edilmiş vekil korpusun
   tamamına uygulandı (§6C). Sınırın kendisi kalkmadı — vekil, gerçek xG değildir ve dört
   ligde uydurulmuş bir katsayının beşinci bir ligde ne yapacağı ölçülmedi.

   `TURETILEMEYEN` listesindeki diğer iki madde **kapalı kaldı** ve gerekçeleri denetlendi:
   `seyahat` için StatsBomb'un `stadium` nesnesinde koordinat yok (yalnız `id`, `name`,
   `country`); `kadro_sakatlik` için `lineups/` maç sonrası veridir ve itiraz zaten kaynak
   değil eğitim/servis ayrışmasıydı.
10. **İkramiye verisi: sınır kalktı. Havuz verisi: kalkmadı.** Bu madde önce "dört üretim
   veri setinin hiçbiri haftalık kazanan adedini veya ikramiye tutarını taşımıyor" diyordu,
   sonra §6B'nin elle girilen sınıfıyla n = 3'e çıkmıştı. **Artık resmî uçtan 223 hafta
   geliyor** (§2.4, §6D) — kademe başına kazanan adedi ve kişi başı ikramiye, altı sezon.

   > **Havuz da geldi — ama türetilerek, ve hasılat olarak değil.** Bu satır önce
   > "haftalık hasılat resmî uçta yok" diyordu; doğru ama eksikti. Kademe havuzu
   > `kazanan × kişi_başı`dır ve kademeler arası bölüşüm **sabit** çıkıyor
   > (**35/20/20/25**, 222 haftada ölçüldü) — yani tablo dağıtılan havuzu zaten
   > taşıyor. `spor_toto.havuz` onu geri hesaplıyor; ayrıntı §6E.
   >
   > **Kalan tek gerçek eksik: oynanma payı.** Hiçbir açık uçta yok, elle giriliyor
   > (§6B), n = 3. Faz B'nin sorusu ikramiye × oynanma payı çarpımını istiyor;
   > ikramiye tarafı 222 hafta, oynanma tarafı 3 hafta. **Darboğaz yer değiştirdi.**
   >
   > Değişmeyen iki uyarı: dağıtılan havuz **brüt hasılat değildir** (Spor Toto'nun
   > payı bu veriden çıkarılamaz), ve kazanan adedi **kolon** sayısıdır, bilet değil
   > — §3.40'ın yığılma sorunu çözülmedi, yalnızca 222 hafta üzerinde ölçülebilir
   > hale geldi.

   Spor Toto müşterek bahis olduğu için **kazanma oranı** ile **beklenen getiri** farklı
   şeylerdir; ikincisi **hâlâ ölçülmedi** ama artık örneklem darlığı bahane değil (§10.1).

---

## 9. Yeniden üretim

```bash
cd backend

python scripts/build_history.py              # tarihsel seti üret
python scripts/build_history.py --dry-run    # yazmadan farkı gör
python scripts/build_history.py --cache /tmp/p   # payload'ları sakla/oradan oku

python scripts/build_odds.py                 # oranları çek ve eşleştir
python scripts/build_odds.py --dry-run       # yalnızca kapsama raporu
python scripts/build_odds.py --no-sqlite     # yalnızca CSV + rapor

python scripts/snapshot_iddaa.py             # bültenin anlık görüntüsünü al
python scripts/snapshot_iddaa.py --dry-run   # yazmadan özet
python scripts/snapshot_iddaa.py --kaynak d.json   # kaydedilmiş ham dosyadan

python scripts/build_sportoto_arsiv.py       # RESMI arsiv: hafta + ikramiye (6 sezon, ~4 dk)
python scripts/build_sportoto_arsiv.py --dry-run          # yazmadan kapsama raporu
python scripts/build_sportoto_arsiv.py --sezon 2023/2024  # tek sezon

python scripts/build_xg.py                   # xG kalibrasyonunu olc (~25 dk, agli)
python scripts/build_xg.py --dry-run         # kapsama + katsayi ozeti, yazmadan
python scripts/build_xg.py --limit 40        # kucuk kesitle deneme

pytest -q tests/test_history.py tests/test_odds.py tests/test_snapshot_iddaa.py \
       tests/test_xg.py tests/test_sportoto_arsiv.py
```

Üç script de doğrulamadan dosya yazmaz; testler yazıldıktan sonra aynı şeyi tekrar denetler.
Ham dosyalar ve SQLite git dışıdır, bu komutlarla yeniden oluşur.

**Tek fark — ve önemli:** iddaa snapshot'ı *yeniden üretilemez*. Diğer iki set kaynağından her
an tekrar çekilebilir; kapanmış bir iddaa bülteni çekilemez. Bu yüzden orada sürümlenen şey
türetilmiş çıktı değil, **arşivin kendisidir** (§6.3). Bu dizini silmek geri alınamaz.

**Okuma tarafı:**

```python
from spor_toto.history import history_summary, history_weeks, history_analytics, history_week_detail
from spor_toto.odds import load_odds, market_odds, implied_probs, season_1x2_summary

history_summary(last=12)                      # son 12 hafta dilimi
implied_probs(market_odds(load_odds()[0], "1X2", "Avg"))

from spor_toto.backtest import backtest
backtest(sweep=False)["season"]                # 41 haftalık geri test, ~1,2 sn
```

---

## 10. Yol haritasının veri tarafı

[`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) fazlarının **tamamı uygulandı**;
veri tarafında yeni boru hattı gerektiren tek faz F5 idi ve §6'da anlatıldı.

Amaç tahmine döndüğü için sıralama değişti. Öncelik artık "sayfayı zenginleştiren veri"
değil, **tahminin ölçülebilir hale gelmesini sağlayan veridir.**

| Öncelik | İş | Veri durumu |
|---|---|---|
| **✔** | **Eğitim korpusu** (§6A) | **Yapıldı.** 31.103 maç · 4 sezon · 22 lig |
| **✔** | **T5 — Takım formu özellikleri** | **Yapıldı.** Maç istatistiği sütunları korpusa eklendi; form yuvarlanan pencereyle türetiliyor. Ham sinyal güçlü, artık değer ~0 |
| **✔** | **A1 — Açılış/kapanış çizgi çifti** (§6A.6) | **Yapıldı.** Aynı kaynaktan, yeni indirme gerekmedi. 31.099 maçta çift var |
| **✔** | **A2 — Bahisçi kırılımı** (§6A.7) | **Yapıldı.** Dört kaynak taşınıyor; kapsaması sezona göre değişenler bilerek dışarıda |
| **✔** | **A3 — Türetilebilir özellikler** | **Yapıldı.** Dördü türetildi ve geçmedi; seyahat ile derbi türetilemedi. Faz A **(b) ile kapandı** |
| **1** | **Fikstür verisi** (kupa + Avrupa) | **Hiç yok.** A3'ün kör noktası: korpus 22 ligi görüyor, kupa/Avrupa maçlarını görmüyor. Tahmin eksenini yeniden açabilecek üç kaynaktan biri |
| **✔** | **İkramiye verisi** (§10.1) | **Yapıldı.** Resmî uçtan 6 sezon · 225 hafta · **223 ikramiye tablosu** (§2.4, §6D). n = 3 → 223. Kalan iş ölçüm, veri değil |
| **2** | **Havuz + oynanma payı** (§10.1) | **Kısmen açık.** Haftalık hasılat resmî uçta yok; oynanma payı hiçbir açık uçta yok ve §6B'de elle giriliyor |
| **✔** | **S1'in kupon ayağı** | **Yapıldı** (§6F, §6G; §6I'de genişledi). 4 sezon · 112 hafta · 1.680 maç. Çapraz doğrulama 30/31 birebir. Tavan: milli takım haftaları |
| **4** | **S3 — İddaa arşivi olgunlaşınca** | **Birikmeyi bekliyor.** Boru hattı ve haftalık tetik çalışıyor (§6.4); ~10 snapshot sonra eşleştirme anlamlı olur |
| **5** | **S2 — Geri testi zenginleştir** | **Hazır.** Ek veri gerekmez |
| — | **Korpus derinliği** | **Ölçüldü, açık bırakıldı** (§6D-ek). 6 sezon 45.652 maç; varsayılan yapmak §3.x ölçümlerinin yeniden koşulmasını gerektirir |
| — | **S4 — Küçük işler** | Veri tarafı yok |

**Örneklem sorununun yarısı çözüldü.** Tahminci ölçümü için gereken büyük örneklem korpusla
geldi ve sonucu net: aşırı uyum modelin kapasitesinden değil **örneklem küçüklüğünden**
geliyormuş. Ama kalan etki 0,0005–0,0015 Brier — 31 binde anlamlı, 540 kupon maçında değil.
Daha çok **aynı türden** veri bu sayıyı büyütmez; büyütecek olan şey **piyasada olmayan bir
girdidir** (öncelik 1).

### 10.2 S1'in kupon ayağı neden kapalıydı

> **Durum değişti (2026-08-30).** Aşağıdaki iki engel hâlâ geçerli ama artık
> tek yol değiller: resmî arşiv (§6D) haftaların kendisini veriyor, eksik olan
> yalnızca **maç listesi**. Yeni durum ve yol §10.3'te.

İki bağımsız engel ölçüldü:

1. **Sonuç kaynağı sezon parametresi taşımıyor.** `/spor-toto/{week}-hafta-tahminleri/`
   mevcut sezonu döndürür; 2. hafta sorgusu `"2025/2026"` verdi. Geçmiş sezonun
   adreslenebildiğine dair işaret bulunamadı.
2. **`robots.txt` kısıtı.** `User-agent: ClaudeBot → Disallow: /` ve
   `Content-Signal: ai-train=no, use=reference`. Genel `User-agent: *` bloğu `/spor-toto/`
   yolunu kapatmıyor — kısıt otomatik aracıya özel. Doktrin 7 gereği bu sınıra uyulur.

`build_odds.py` da `st_history_2025_26.json`'a bağlı olduğundan kupon tarafı **bir bütün
olarak** bekliyor. Veri geldiğinde altyapı hazır: `evaluate.capraz_olc` "bir sette eğit,
ötekinde ölç" yapıyor ve `sezon_anahtari` kupon setinde de çalışır.

### 10.1 İkramiye ve havuz — ikramiye geldi, havuz açık

> **Durum güncellendi (2026-08-30).** Bu bölüm "veri var, ölçüm yok — n = 2"
> diye yazılmıştı ve o sayı elle girilen haftalardan geliyordu. Resmî arşiv
> boru hattı (§6D) kurulunca **n = 223** oldu: altı sezon, kademe başına
> kazanan adedi ve kişi başı ikramiye. Aşağıdaki argümanların hiçbiri
> değişmedi — yalnızca "n = 2 iken hiçbir sayı sonuç değildir" cümlesinin
> geçerliliği bitti. **B2 (popülerlik modeli) artık örneklem darlığıyla
> gerekçelendirilemez.**
>
> Değişmeyen iki eksik: **haftalık hasılat** (havuzun kendisi) resmî uçta yok,
> ve **oynanma payı** hiçbir açık uçta yok — o hâlâ §6B'nin elle girişinde.
> §3.40'ın "kazananlar kişi değil kolon" bulgusu da aynen duruyor; 223 hafta
> onu çözmüyor, ölçülebilir kılıyor.

Yeni amaç iki farklı hedefi birbirine karıştırmaya açıktır ve veri tarafı bu ayrımı
zorunlu kılar:

| Hedef | Neyi artırır | Bugün ölçülebilir mi |
|---|---|---|
| Daha iyi tahmin | 14 tutturma **olasılığını** | Evet — geri test + hold-out |
| Daha az paylaşılan kolon | Tutturunca alınan **payı** | **Veri var, ölçüm yok** — n = 2 hafta |

İkincisi Spor Toto'nun müşterek bahis olmasından gelir: ikramiye havuzdan kazananlara
bölünür, dolayısıyla aynı olasılığa sahip iki sonuçtan **daha az oynananı** işaretlemek
tutturma olasılığını değiştirmeden beklenen getiriyi artırır. Bu, piyasayı tahminde yenmeyi
gerektirmeyen tek kaldıraçtır.

**Bu bölüm uzun süre "elde hiçbir şey yok" diyordu; artık doğru değil.** İhtiyaç
duyulan iki veri de §6B'nin boru hattıyla geliyor: kat başına kazanan adedi + ödenen
tutar (`meta.payout`) ve maç başına oynanma payı (`play_pct`). Kaynak Spor Toto'nun
resmî ilan ekranlarıdır; **erişim biçimi elle giriştir** ve bunun kuralları §6B.2'de.

Doktrin bu boru hattına olduğu gibi uygulanır — özellikle ilke 2 ve 7: ikramiye verisi
bulunamayan hafta boş bırakılır, tahmin edilmez; bulunan veri hangi kaynaktan geldiğini
yanında taşır.

#### Vekil sorunu yer değiştirdi, kalkmadı

Eskiden popülerlik vekili **favori oranından türetilecekti** (oran → tahmini oynanma
payı). Artık gerçek oynanma payı var — ama **o da bir vekil**, çünkü tek platformun
kendi kullanıcılarını sayıyor, Spor Toto havuzunun tamamını değil. Dosya bunu kendi
içinde yazıyor (`play_note`).

**Yanlılığı ölçmenin yolu ikramiye tablosunun içinde.** Her hafta üç kat için kazanan
adedi veriliyor (12, 13, 14 bilen). Oynanma payı + gerçekleşen sonuç, bu adetleri
**önceden söyleyebilmelidir**:

| Söylüyorsa | Söylemiyorsa |
|---|---|
| Platform havuzu temsil ediyor; pay hesabı doğrudan kurulabilir | Platform yanlı; oynanma payı havuza çevrilmeden kullanılamaz ve yanlılığın **yönü** bu farktan okunur |

Bu, B2'nin (popülerlik modeli) asıl işidir ve **hafta biriktikçe** koşulur: her hafta
üç veri noktası verir, ama haftalar birbirinden bağımsız değildir (aynı platform, aynı
kullanıcı kitlesi). n = 2 iken hiçbir sayı sonuç değildir.

#### Ölçülen ilk şey tezi zayıflatıyor

1. haftanın değerlendirmesi (`super_toto_degerlendir.py`) iki bulgu verdi ve ikisi de
   havuz tezinin lehine değil:

- **Oynanma verisi yön taşımıyor.** Halkın en çok oynadığı kupon ile piyasanın favori
  kuponu **birebir aynı** çıktı. Kalabalık piyasadan sapmıyor; yalnızca payı belirliyor.
- **İsabet kalabalıkla birlikte geliyor.** Aynı strateji, en iyi kolonu 13+ olan
  haftalarda ortalama **9,00** favori, 11 ve altı haftalarda **7,47** favori görüyor.
  Yani tutturulan haftalar, kalabalığın da tutturduğu ve ikramiyenin küçüldüğü haftalar.

İkincisi ölçülmesi gereken soruyu değiştiriyor: artık *"havuz avantajı var mı"* değil,
**"net mi"**. Ayrıntı: [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §6.3.

**2. hafta (n = 2).** Halkın modal kuponu ile piyasanın favori kuponu bu kez **ayrıştı**
— tek maçta (5. maç: halk ev sahibi %53, piyasa deplasman %38,8) — ve sonuç piyasayı
doğruladı: halk 8/15, piyasa 9/15. Kalabalığın Brier'i o hafta 0,6752, piyasanınki 0,5839.
İki hafta da aynı yönde: **oynanma verisi yön değil, pay taşıyor.**

**İkramiye tablosu sonradan girildi ve B2 ilk cevabını verdi.** Her kademe bir *havuz
kolonu sayısı* ima eder (`N = kazanan ÷ P(k doğru)`); model doğruysa dört kademe aynı `N`'i
vermelidir. 2. haftada **kalabalık modelinin dört kademesi birbirinin %16'sı içinde** kaldı
(37,8–43,9 milyon, ortalamanın ±%8'i), piyasa modeli 2,9 kat saptı (4,0–11,6 milyon). Yani **şekil** ölçüsünde
oynanma payları açık ara önde — havuz ekseninin ilk olumlu kanıtı.

Ama **seviye** yanlış: 1. hafta 5,2–7,5 milyon kolon ima ediyordu, 2. hafta 37,8–43,9 milyon
(6 kat), oysa dağıtılan havuz yalnızca 1,42 kat büyüdü. Sebebi tam da bu belgenin uyardığı
şey: **kazanan sayıları kişi değil kolon.** Oynanma yüzdeleri BİLET başına ölçülür, havuz
KOLON başına bölünür; tek bir sistem kuponu (8.192 kolon) o hafta 378 kazanan kolon üretti.
Bağımsız-kolon modeli bu yığılmayı üretemez. Ayrıntı:
[`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.40.

**Skorlar hâlâ girilmedi** (yalnızca 1/0/2). Gol bazlı hiçbir ölçüm bu haftadan beslenemez;
ve bu açık, ikramiye tablosunun aksine sonradan kapatılamaz.

Sonuç girişi bu yüzden **üç parçalıdır** ve üçü aynı anda girilir:

| Parça | Nereden | Kaybedilirse ne ölçülemez |
|---|---|---|
| Sonuç dizisi (15 sembol) | resmî sonuç ekranı | her şey — hafta hiç ölçülemez |
| Skorlar (gol) | resmî sonuç ekranı | gol bazlı her ölçüm (Dixon-Coles kalibrasyonu) |
| İkramiye tablosu (kat başına kazanan + ödül) | resmî ikramiye ekranı | havuz ekseninin tamamı: pay dağılımı (§3.40'ta ölçüldü), kolon başına getiri, popülerlik modeli |

Bu yol pozitif getiri garanti etmez; ölçülebilir hale getirdiği şey, bu belgenin önceki
sürümünde hakkında hiçbir şey bilinmeyen bir boyuttur.

### 10.3 Kupon ayağı — KAPANDI

> **Durum (2026-08-30).** Bu bölüm "kalan tek parça maç listesi" diye
> açılmıştı. O parça §6F'de (bülten OCR) okundu, §6G'de fikstüre bağlandı ve
> ayak **kapandı**: 4 sezon · **107 hafta** · **1.605 kupon maçı**, tam 1/0/2
> dizisiyle. Aşağıdaki tablo o günün durumunu anlatıyor ve kayıt olarak
> duruyor; güncel sayılar §6G.4'te.
>
> Kapanmayan tek şey **yapısal tavan**: milli takım haftaları football-data'da
> hiç yok ve o haftalar bu yolla hiçbir zaman gelmeyecek.

Resmî arşiv (§6D) §10.2'nin denklemini değiştirdi. Geçmiş bir kupon haftası
dört parçadır ve üçü artık elde:

| Parça | Durum | Kaynak |
|---|---|---|
| (a) Hangi hafta, ne zaman kapandı | **Var** | Resmî uç, 6 sezon · 225 hafta |
| (b) İkramiye tablosu | **Var** | Resmî uç, 223 hafta |
| (c) Hangi 15 maç, kupon sırasıyla | **YOK** | Yalnızca bülten **görseli** (2023/24'ten itibaren) |
| (d) Skor ve 1/0/2 | **Türetilebilir** | (c) gelirse `build_odds.py` eşleştiricisiyle |

**(d)'nin türetilebilir olması kilit noktadır ve ölçülmüştür.** `build_odds.py`
maçları tarih ±1 gün + **birebir skor** + bulanık takım adıyla eşleştiriyor ve
2025/26'da 615 maçın 567'sini tutturdu (%92,2). Yani bir kaynağın skor vermesi
**gerekmiyor**; 15 takım çiftini doğru sırayla vermesi yetiyor.

Dolayısıyla kalan iş tek bir şeye indi: **bülten görselinden 15 maçın okunması.**

**Ama doktrin 2 burada gevşemez, sıkışır.** OCR çıktısı bir veri değil, bir
**arama anahtarıdır**: okunan ad football-data'nın o tarihteki fikstürüne
birebir oturmazsa maç düşer, 15/15 tamamlanmazsa hafta düşer. Uydurma yok,
"yakın isim" yok, elle düzeltme yok. Bu kural olmadan OCR bu depoya giremez —
çünkü sessizce yanlış bir kupon dizisi üretmek, hiç veri olmamasından kötüdür
(§7.4'ün v1 sıra hatası tam olarak buydu).

Ölçülmesi gereken sayı da bellidir ve peşin söylenmelidir: **kaç hafta 15/15
tamamlanıyor.** Görseller elle yüklenmiş, çözünürlükleri ve biçimleri tutarsız
(`whatsapp-image-2024-08-02-at-111013.jpeg`, `screenshot-2025-08-02-at-215731.png`,
`toto2.jpg`). Bu oran düşük çıkarsa iş bir kaynak sorunu değil, bir sınırdır ve
öyle yazılır.

Kapsama tavanı da şimdiden bellidir: görseller **2023/2024'ten itibaren**
erişilebiliyor, 2021/22 ve 2022/23 için 404. Yani bu yol en iyi ihtimalle
**~160 hafta** getirir; 225'in tamamını değil.

### 10.4 Ayrımın ilk kazancı: 41 haftalık çapraz doğrulama — ve ölçülen bir anlam farkı

§7.2'nin "bağımsız çapraz doğrulama"sı tek haftaydı (51. hafta, Misli). Artık
2025/26'nın **41 haftası** iki bağımsız kaynakta yan yana duruyor ve karşılaştırma
koşuldu:

| Ölçüm | Sonuç |
|---|---|
| `st_history`'nin 41 haftasının resmî arşivde karşılığı | **41 / 41** |
| Kapanış tarihi birebir aynı | **0 / 41** |
| Resmî `close_date` = haftanın **ilk** maçının günü | **41 / 41** |
| `st_history.close_date` − resmî `close_date` | **1–4 gün** (ortanca 3) |

**Bu bir çelişki değil, bir anlam farkıdır ve ikisi de doğrudur.** Resmî uçtaki
`roundCloseDate` **kupon satışının kapandığı** andır — 41 haftanın 41'inde
haftanın ilk maçının gününe eşit çıkması bunu kanıtlıyor. `st_history`'nin aynı
adlı alanı ise haftanın **son** maçına denk düşer, yani turun bittiği gün.

Doktrin 4 gereği hiçbiri "düzeltilmedi": iki dosya da kendi alanını taşıyor ve
resmî arşivin `meta.close_date_note` alanı farkı kendi içinde yazıyor. Alan adı
aynı olduğu için bu, sessizce yanlış hizalanabilecek türden bir tuzaktı —
ölçülüp yazıldı.

**Pratik değeri:** havuz modeli için doğru zaman çıpası **resmî** tarihtir.
Oynanma payı ve iddaa oranı o an donuyor; haftanın son maçı değil, satışın
kapandığı an. §3.40'ın kolon sayısı hesabı bu çıpaya oturtulmalıdır.

## 11. Sürüm geçmişi

| Sürüm | Ne değişti |
|---|---|
| **v1** (2026-08-15) | İlk üretim. 41 hafta, 615 maç. Sonuç dizisi 15 haftada yanlış sırada, 6'sında yanlış sayımda (§7.4) — o zaman fark edilmedi |
| **v2** (2026-08-16) | Sıra hatası kapatıldı; veri **maç düzeyine** indi (takım, saat, skor); üretim tek komutla tekrarlanabilir oldu; `data_quality` denetimi ve test bekçileri eklendi; **oran arşivi** kuruldu (§5) |
| **v13** (2026-08-30) | **Eşleştirme teşhis edildi; sessizce ölü bir sözlük bulundu** (§6I). Dış inceleme (`DIS_INCELEME_SPORTS_BETTING.md`) küresel bire-bir eşleştirme önerdi; `--teshis` önce ölçtü ve `ayirt_edilemedi` sınıfını **sıfır** buldu — önerilen strateji bu kesitte çalışacak bir şey bulamazdı ve **alınmadı**. Ama teşhis başka bir kusur buldu: Türkçe noktalı `İ` (U+0130) `.lower()` altında `i` + birleşen noktaya dönüşüyor ve düz ASCII sözlük anahtarıyla eşleşmiyor; `BULTEN_ESLERI`nin üç satırı (`marsilya`, `sporting lizbon`, `milano`) **hiçbir zaman çalışmadı**. Bülten büyük harfli görselden OCR edildiği için `İ` orada kural dışı değil normal hâl. Üç düzeltme ayrı ayrı ölçüldü: Unicode temizliği 107→110, OCR `/` artığı 110→112, doğrulanmış 7 sözlük satırı 111→112. Katkı tamamen **eklemeli** — kaybolan hafta yok, değişen 1/0/2 dizisi yok. Çapraz doğrulama **gerilemedi, güçlendi**: ortak hafta 29→31, birebir aynı 28→30. Kupon × korpus kesişimi yeniden ölçüldü: 1.155/1.605 → **1.200/1.680**. Ölçüm kesiti 114 haftada **kaldı** (yeni haftaların oran kapsaması yok, `usable` değiller) |
| **v12** (2026-08-30) | **Yeni veri ölçüm hattına bağlandı.** Oran arşivi sezonlu (§6H): üç sabit sezondan türetildi, yeni sezonlarda eşleşme **%100** (255/255 · 465/465 · 450/450), varsayılan dosya byte byte aynı kaldı. `history` sezon seçer (birleştirmez), `/api/stats?sezon=` ve `/api/meta.seasons` geldi. `backtest.hafta_girdileri` artık `sezon` yazıyor — bu tek alan `arena.kesit(kupon=True)`de **sezon dışarıda bırakmalı** ölçümü açtı. Ölçüm kesiti **36 → 114 hafta** (540 → 1.710 maç). Ölçülen sonuçlar: ISTATISTIK_YOL_HARITASI §3.43 |
| **v11** (2026-08-30) | **Korpus derinliği ölçüldü, varsayılan yapılmadı** (§6D-ek): 6 sezon 45.652 maç ve şema hiç bozulmuyor, ama 53 belgelenmiş ölçüm 31.103'e çıpalı — korpusu değiştirmek onları geçersiz kılar. Komut seçeneği olarak kaldı. **Yeni bir sızıntı riski görünür kılındı**: kupon seti 4 sezona çıkınca korpusla üç sezon kesişti; `egitim_rapor.json` artık `kesisim`i yazıyor, betik ekrana uyarı basıyor, üç bekçi testi çakışmanın görünür kalmasını koruyor |
| **v10** (2026-08-30) | **Geçmiş sezon kupon verisi geldi.** Resmî bülten görseli OCR ile okundu (§6F, 156 hafta) ve football-data fikstürüne bağlandı (§6G): **4 sezon · 107 hafta · 1.605 maç**, tam 1/0/2 dizisiyle. §10.2/§10.3'ün kupon ayağı **kapandı**. Çapraz doğrulama: iki bağımsız boru hattı 29 ortak haftanın **28'inde birebir aynı**; ayrışan tek hafta bir **kupon sırası** farkıdır (aynı 15 maç) ve düzeltilmeden raporlandı. Pencere bir ayar değil koruma: ertelenen maçın aylar sonraki sonucu o haftanın sonucu değildir |
| **v9** (2026-08-30) | **Resmî Spor Toto arşivi** kuruldu (§2.4, §6D): `webapi.sportoto.gov.tr` — deponun ilk **resmî** kaynağı. 6 sezon · 225 hafta · **223 ikramiye tablosu**. §10.1'in havuz ekseni n = 3'ten n = 223'e çıktı. §3.1'in "arşiv ucu bulunamadı" kaydı **düzeltildi** — kaynak kapalı değildi, uçlar JS parçalarındaydı. **Maç listesi hâlâ gelmiyor** (yalnızca bülten görseli); §10.2 kupon ayağı §10.3 olarak yeniden açıldı |
| **v5** (2026-08-17) | **Eğitim korpusu** kuruldu (§6A): football-data'dan 22 lig × 4 geçmiş sezon, 31.103 maç. Kupon değerlendirme setinin 58 katı. `/istatistik` sayfasına **girmez** — ayrım `test_ayrim_*` ile bekçiye bağlandı. Varsayılan sezonlar 2025/26'yı dışarıda bırakır (sızıntı önlemi) |
| **v6** (2026-08-17) | **Korpus artık iki çizgi taşıyor** (§6A.6): açılış ve kapanış oranı ayrı sütunlarda, yalnızca aynı bahisçi ailesinden eşleşmiş çift olarak. Maç sayısı değişmedi (31.103; 31.099'unda çift var), böylece önceki ölçümler karşılaştırılabilir kaldı. Bu değişiklik A1'i (kapanış çizgisi verimliliği) mümkün kıldı; sonucu §8 madde 7'ye işlendi |
| **v7** (2026-08-17) | **Korpus bahisçi kırılımı taşıyor** (§6A.7): `B365C`, `PSC`, `MaxC`, `AvgC`. Kaynak seçimi ölçümün parçası — kapsaması sezona göre değişen bahisçiler (`BW`, `WH`, `BF`, `1XB`) bilerek dışarıda, çünkü kesiti sezona göre dengesizleştirip sezon dışarıda bırakmalı ölçümü yanlılarlardı. Aynı gerekçeyle model yalnızca sabit kaynak çiftinden gelen `ayrisma`yı görür; sürüklenen `en_iyi_prim` betimleyici kalır. Doğrulamaya `Max ≥ Avg` eklendi |
| **v8** (2026-08-17) | **A3 özellikleri korpustan türetiliyor** (kod tarafında; yeni sütun yok): dinlenme günü, fikstür sıkışıklığı, iç/dış saha ayrı formu, sezon sonu payı. Hepsi maçtan **önceki** maçlardan hesaplanır ve her biri ayrı sızıntı bekçisine bağlıdır. §8 madde 7 kapandı: dört özellik de piyasayı geçemedi, ikisi (seyahat, derbi) türetilemedi. Yeni ve daha keskin bir sınır yazıldı — korpus **kupa ve Avrupa maçlarını görmüyor**, dolayısıyla ölçülen yorgunluk değil vekilidir |
| **v9** (2026-08-18) | **Beşinci veri seti: yaklaşan maçlar** (`build_fixtures.py`). Tahmin ürününün girdisi; diğer dördünden yönüyle ayrılır — ileriye dönük ve yuvarlanan bir penceredir, hafta oynandıkça boşalır. Kaynak football-data `fixtures.csv`, yani **ölçümün yapıldığı fiyatlayıcının kendisi**; iddaa bülteni yedek ve kalibrasyonu ölçülmemiş olarak işaretli. Oranlar açılış oranıdır ve bedeli A1'de ölçülmüştür (+0,0025 Brier) |
| **v4** (2026-08-17) | **Veri değişmedi, amaç değişti.** Proje maç sonucu tahminine ve kazanma oranını artırmaya yöneldi. Doktrinin yedi ilkesi aynen korundu; ilke 2'ye "eleme ≠ tahmin" ayrımı yazıldı. §8'e iki sınır eklendi: veride piyasa dışı sinyal yok, ikramiye/havuz verisi yok. §10 öncelikleri yeniden sıralandı ve §10.1 ile **dördüncü veri seti ihtiyacı** (ikramiye/havuz) tanımlandı |
| **v3** (2026-08-16) | **İddaa bülten arşivi** kuruldu (§6) ve haftalık tetiği açıldı — ileriye dönük, birikmeye başlıyor. Oran arşivinden türetilen üç karar destek bloğu (çift kapsama, beraberlik profili, lig kırılımı) ve haftalık Brier eklendi; geri test boru hattı bu veriyi tüketmeye başladı. İddaa boru hattı §5'in eki değil **üçüncü veri seti** olduğu için `5A` yerine kendi bölüm numarasını aldı; sonraki bölümler bir kaydı |

Sezon toplamları v1 ve v2'de aynıdır (270/149/196) — çünkü v1'de bozuk olan yalnızca diziydi,
sayımlar doğruydu.

---

Bu belge veri katmanının tek kaynak dokümantasyonudur. Sayfanın kendisi, alınan ürün kararları
ve yol haritası için: [`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md).
