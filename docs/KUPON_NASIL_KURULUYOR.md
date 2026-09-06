# Kupon nasıl kuruluyor — girdiden oynanacak satıra, her adım

> **Bu belge yeni bir iddia getirmez.** Var olan boru hattını, girdinin
> kodda hangi eli değdiği sırayla anlatır: hangi sabit nereden geliyor,
> hangisi **ölçüm** hangisi **varsayım**, hangi adım kararı değiştiriyor
> hangisi yalnızca kayda geçiyor.
>
> Somut örnek olarak **2026/27 4. hafta** kullanılır ve bütün sayılar o
> haftanın gerçek dosyasından, koşturularak alınmıştır (2026-09-05).
> Yeniden üretim komutları §16'da.

---

## 0. Bir bakışta akış

```
SEN VERİYORSUN                     data/super_toto/<sezon>/hafta_NN.json
  15 maç · takım adları · lig            {meta, matches[15]}
  açılış oranları  (bahisçi × 1/0/2)
  kapanış oranları (bahisçi × 1/0/2)
  oynanma yüzdeleri (% tercih)
        │
        ▼
  ① KAPI — dogrula()                     uyarı üretir, VERİYİ DÜZELTMEZ
        │                                marj sapması · bayat kapanış · delikli bahisçi
        ▼
  ② ANA FİYAT SEÇİMİ                     odds_from — bu bir İNSAN kararı,
        │                                kod yalnızca denetler
        ▼
  ③ ORAN → OLASILIK                      implied_probs(), shin marj arındırma
        │                                p = (√(z²+4(1−z)q²/Σq) − z) / (2(1−z))
        ▼
  ④ OYNANMA → KALABALIK PAYI             100'e normalize, o(s)
        │
        ├─────────────► ⑦ HAVUZ KATMANI (E[TL], crowd_ratio) — RAPOR
        │
        ▼
  ⑤ SEÇİM — Pareto DP                    P(k ≤ eşik)'i BÜTÇE içinde enbüyükler
        │                                girdisi YALNIZCA olasılıklar + fiyat tablosu
        ▼
  ⑥ BEDEL — satıcı fiyat tablosu         84 şekil × 3 garanti, ₺10/kolon
        │
        ▼
  ⑧ KAPLAMA — Hamming(7,4) / tablo       16 satır → oynanacak kolonlar
        │
        ▼
  ⑨ DONDURULAN KAYIT                     hafta_NN_kupon.json (+ varyantlar)
```

**Tek cümlelik özet:** oynanan kuponun işaretleri **yalnızca oranlardan**
gelir. Oynanma yüzdeleri kuponu bugün *kurmuyor*; ölçülüyor, raporlanıyor
ve alternatif olarak kayda geçiyor — sebebi §7.4'te, ve o sebep bir tercih
değil bir **ölçüm sonucudur**.

---

## 1. Girdi — tam olarak ne veriyorsun

Verdiğin şey `backend/data/super_toto/<sezon>/hafta_NN.json` dosyasına
düşer. Maç başına şema:

```json
{
  "no": 1, "date": "", "kickoff": "", "league": "T1",
  "home": "Erzurumspor FK", "away": "Konyaspor",

  "odds":       {"1": 2.28, "0": 3.41, "2": 3.14},   ← ANA FİYAT (tek üçlü)
  "odds_from":  "pinnacle_kapanis",                   ← künyesi
  "odds_books": {                                     ← bütün kayıtlar
    "pinnacle_acilis":  {"1": 2.29, "0": 3.38, "2": 3.15},
    "pinnacle_kapanis": {"1": 2.28, "0": 3.41, "2": 3.14},
    "nesine_acilis":    {"1": 2.06, "0": 3.06, "2": 2.75},
    "nesine_kapanis":   {"1": 2.06, "0": 3.06, "2": 2.75}
  },
  "play_pct":   {"1": 32.0, "0": 27.0, "2": 41.0}     ← oynanma yüzdesi
}
```

Dört alanın **rolleri farklıdır** ve karıştırılmaz:

| Alan | Rolü | Kupona etkisi |
|---|---|---|
| `odds` | tek ana fiyat; olasılığın tek kaynağı | **belirleyici** |
| `odds_books` | bütün bahisçi × an kayıtları | denetim + duyarlılık; işarete girmez |
| `odds_from` | ana fiyatın hangi kayıttan geldiği | künye; ölçek uyarısı üretir |
| `play_pct` | tek platformun kullanıcı tercih payı | rapor + alternatif; varsayılanda işarete girmez |

`meta` bloğu ise haftanın künyesini taşır: `odds_kind` (ana fiyatın ilan
edilen ailesi), `odds_source`, `play_source`, `entered_at` (kuponun
donduğu an), `results` (sonuç girilene kadar `null`), `payout` (resmî
ikramiye tablosu, hafta bitince).

**Önemli:** `play_source` her hafta şunu yazar — *"yüzdeler tek bir
platformun kendi kullanıcılarıdır; Spor Toto havuzunun tamamı
DEĞİLDİR."* Bu cümle süs değil, §7'deki bütün havuz hesabının sınırıdır.

---

## 2. ① Kapı — `dogrula()`: kod veriyi düzeltmez, işaretler

`scripts/super_toto_hafta.py::dogrula` elle girilen dosyayı yedi ayrı
denetimden geçirir. Hepsi `assert` değil **liste** döndürür; koşum
durmaz, şüphe görünür olur. Kural doktrinden gelir: *belirsiz veri atılır
ya da işaretlenir, uydurulmaz.*

| # | Denetim | Eşik / kural | Neden bu eşik |
|---|---|---|---|
| 1 | Marj bültenin ortancasından sapıyor mu | `MARJ_SAPMA_ESIGI = 5.0` puan | Bültenler kendi içinde 1 puanın altında oynar, gerçek giriş hataları on puanlarla sapar; eşik aradaki boşluğa kondu |
| 2 | Marj kendi başına saçma mı | `0.0 < marj < 0.60` | Altı arbitraj verirdi (bülten öyle bir şey yayımlamaz), üstü hiçbir bültende yok |
| 3 | `1.00`'den küçük oran | var / yok | Fiyat değil, giriş hatası |
| 4 | Oynanma yüzdesi tam mı, toplamı makul mü | 3 sembol · `90 ≤ Σ ≤ 110` | Yuvarlamaya izin, kayıp satıra izin yok |
| 5 | Ana fiyatın **açılış eşi** var mı | `odds_kind` kapanışsa aynı ailenin açılışı da olmalı | Yoksa çizgi hareketi ölçülemez |
| 6 | **Bayat kapanış** | kapanış == açılış birebir | Bu bir fiyat değil, **tazelenmemiş kayıttır**; o satırda "bahisçi ayrışması" görüş farkı değil kayıt farkıdır |
| 7 | **Delikli bahisçi** | bir kitap bazı maçlarda yok | O satırlarda ana fiyat başka kayıttan gelmek zorunda; ayrıca o bahisçinin ortalama marjı eksik satırlar üzerinden hesaplanmaz |

Ayrıca: lig etiketi olmayan maç, ve sonuç dizisi bozuksa (15 ≠ uzunluk ya
da geçersiz sembol) uyarı.

Kitap listesi **bütün maçların birleşimidir**. Önceden yalnızca 1. maçın
kitaplarına bakılıyordu; 1. maçta olmayıp başka maçta olan bir bahisçi
hiç denetlenmezdi.

**4. haftanın gerçek çıktısı** (`[kod]` = otomatik, `[elle]` = insan notu):

```
[kod] 2. maç: marj %17.7, bültenin ortancası %4.9 — 12.8 puan sapma, KUŞKULU
[kod] pinnacle_acilis : 1 maçta kayıt YOK (maç 2)
[kod] pinnacle_kapanis: 2 maçta kayıt YOK (maç 2, 13)
[kod] nesine_kapanis  : 8 maçta kapanış açılışla BİREBİR aynı (1,2,3,4,7,8,9,14)
[kod] pinnacle_kapanis: 1 maçta kapanış açılışla BİREBİR aynı (maç 9)
```

Bu haftanın dersi kayda geçmiş durumda: **bayatlık ilk kez ana fiyat
kaynağının kendisinde göründü** (9. maç, Pinnacle). Ve 2. maçtaki 12,8
puanlık sapma bir giriş hatası **değil**, ölçek farkıdır — Pinnacle o maçı
hiç fiyatlamadığı için ana fiyat %17,7 marjlı Nesine'den gelmiştir. Kapı
"KUŞKULU" der, kod düzeltmez, insan gerekçeyi `data_warnings`'e yazar.

---

## 3. ② Ana fiyat seçimi — **kodun yapmadığı** tek şey

`odds` alanına hangi bahisçinin hangi anı yazılacağı **veri girişinde
verilen bir karardır**. Kod bu kararı vermez; denetler (§2), künyesini
taşır ve haftalar arası kıyasta ölçek uyarısı basar.

4. haftanın kararı ve gerekçesi kayıtta duruyor:

* **13 maçta** `pinnacle_kapanis`,
* **13. maçta** (Inter–Napoli) `pinnacle_acilis` — kapanışı bültende yok;
  *aynı bahisçi, bir önceki an*: ölçek korunur, kaybolan yalnızca o maçın
  çizgi hareketidir,
* **2. maçta** (Kasımpaşa–Amed) `nesine_kapanis` — Pinnacle o maçı hiç
  fiyatlamamış; *başka bahisçi, başka marj ölçeği* (%17,7 ↔ Pinnacle
  bandı %4,6).

İki ikame **aynı ağırlıkta değildir** ve kayıt bunu adıyla söyler.
Seçenek Nesine ya da `1/3–1/3–1/3` idi; ikincisi elde olan bilgiyi atmak
olurdu.

**Oranı hiç olmayan maç** için kural nettir: `probs = 1/3, 1/3, 1/3`,
`margin = 0`, `fav = None`. Bu bir tahmin değil, **bilgi yokluğunun
ilanıdır** — ve böyle bir maç eşik kuralının üçlü eşiğinin (0,38) altında
kalıp otomatik olarak kapatılır (`102`).

---

## 4. ③ Oran → olasılık: marj arındırma

### 4.1 Marj (overround)

```
marj = Σ(1/o) − 1
```

Adil bir bültende sıfır. `odds.margin()` sıfır/negatif oranı **eler**
(`1/0` sonsuza giderdi).

4. hafta ana fiyatın ortalama marjı **%5,44**. Bu sayı saf Pinnacle
değildir: 2. maçın Nesine'den gelmesi ortalamayı %4,62'den %5,44'e
çıkarıyor. Pinnacle satırlarının kendi ortalaması **%4,62** kapanış (13
maç) / **%4,65** açılış (14 maç). Geçen sezon arşivi (football-data `Avg`)
**%7,26**, iddaa açık bülteni **%17,2–18,9**.

Ölçekler aynı değildir ve rapor bunu her hafta yazar: *"iki ölçek aynı
değildir ve arındırılmış olasılıklar birebir kıyaslanamaz."*

### 4.2 Üç arındırma yöntemi — ve hangisinin seçildiği sonucu değiştirir

| Yöntem | Formül | Davranış |
|---|---|---|
| `orantili` | `p = (1/o) / Σ(1/o)` | Marjı her sonuca **eşit** dağıtır; basit ve tersine çevrilebilir |
| `guc` | `p ∝ (1/o)^k`, `k` ikiye bölmeyle | `k > 1` çıkar; küçük olasılıkları daha çok kısar |
| **`shin`** | `p = (√(z² + 4(1−z)q²/Σq) − z) / (2(1−z))` | **Varsayılan.** Marjı bilgili bahisçi payı `z` ile açıklar |

**Neden `orantili` bırakıldı (A5).** Bahisçi marjı sürprizlere ağır
yükler; eşit dağıtmak favoriyi **sistematik olarak eksik fiyatlar**.
31.103 maçlık korpusta ölçüldü: piyasanın %70–80 dediği maçlar gerçekte
**%78,9** oluyor (n=1.702, +4,4 puan, %95 aralığın dışında) ve 15 banttan
**10'u** anlamlı sapıyor.

`shin`e çevrildikten sonra: Brier 0,5940 → **0,5936**, fark −0,00035
[−0,00049, −0,00021] — aralığın tamamı sıfırın altında, yani projenin
geçme kuralını sağlıyor. Anlamlı sapan bant **10 → 4**.

Marj sıfıra giderken üç yöntem de aynı sonuca yakınsar; ayrıştıkları yer
yüksek marjdır — iddaa bülteni (~%18) tam olarak orası.

**İki ölçüm bilerek `orantili`da bırakıldı:** açılış↔kapanış hareketi ve
bahisçi anlaşmazlığı. İkisi de bir **fark** ölçer ve orantısal yöntem
oranın ölçeğinden bağımsız olan tek yöntemdir; Shin'de bahisçinin yalnızca
marjını büyütmesi "hareket" ya da "anlaşmazlık" gibi okunurdu.

### 4.3 Hesabın mühendisliği

`_arindirilmis` **saf ve önbelleklidir** (`lru_cache`). Shin kök bulucusu
çağrı başına 60 ikiye bölme adımı koşuyor ve korpus profillendiğinde
sürenin **%92'si** buradaydı (217.685 çağrı, 39,7 sn); aynı oran üçlüsü
%42 oranında tekrar ediyordu. Önbellek sonucu **bit birebir** korur —
yayımlanmış ölçümlerin arkasındaki sayılar oynamasın diye adım sayısı
düşürülmedi.

### 4.4 4. haftanın çıktısı

```
 # Maç                              oran 1/0/2        olasılık (shin)  fav
 1 Erzurumspor – Konyaspor          2.28/3.41/3.14    42/28/30          1
 3 Çorum FK – Eyüpspor              1.69/3.86/4.85    57/24/19          1
 5 Başakşehir – Galatasaray         5.06/4.53/1.59    18/21/61          2
 7 Trabzonspor – Gençlerbirliği     1.57/4.19/5.54    61/22/16          1
12 Athletic Bilbao – Atl. Madrid    3.13/3.53/2.32    31/27/42          2
```

---

## 5. ④ Açılış ↔ kapanış — kupona **girmez**, üç işe yarar

Bu, verdiğin girdiler içinde en çok yanlış anlaşılmaya açık olanı, o
yüzden ayrı bölüm.

### 5.1 Ölçüm ne dedi (A1)

31.099 / 31.103 maçlık kesitte, sezon dışarıda bırakmalı:

| Tahminci | Brier | Fark | %95 aralık |
|---|---:|---:|---|
| **kapanış** | **0,5940** | — | referans |
| açılış | 0,5964 | +0,0025 | [+0,0019, +0,0030] |

**Soru 1 — piyasa bilgiyi soğuruyor mu? Evet.** Aralık tamamen sıfırın
üstünde: açılışla kapanış arasında gelen bilgi (kadro, sakatlık, hava,
para) fiyata işleniyor.

**Soru 2 — hareket kapanışın ötesinde bilgi taşıyor mu? Hayır.**
`z_s = β·ln p_kapanış + γ·(ln p_kapanış − ln p_açılış)` kurulduğunda
γ/β = **%1,01** (β = 1,094, γ = 0,0111). Model harekete baktı ve kapanışın
ötesine uzatmak için kayda değer sebep bulamadı.

**Ham sinyal ise gerçek** — ve bu ayrım kritik:

| Hareket büyüklüğü | Lehine tuttu | Aleyhine | n |
|---|---:|---:|---:|
| <0,05 | %33,4 | %33,5 | 4.577 |
| <0,15 | %36,2 | %33,2 | 12.861 |
| <0,30 | %41,1 | %32,0 | 9.221 |
| ≥0,30 | **%47,2** | %30,2 | 4.440 |

Çizgi ne kadar oynarsa yönü o kadar tutuyor — güçlü, monoton bir sinyal.
**Ama tamamı zaten kapanış fiyatında.** "Hareket bilgi taşımıyor" bir
yokluk iddiasıdır ve hareketin *hiç* bilgi taşımamasından da gelebilirdi;
gelmiyor.

### 5.2 O hâlde açılış oranı ne işe yarıyor

1. **Bayatlık denetimi** (§2, denetim 6) — kapanış açılışa birebir eşitse
   o satır bir fiyat değil, tazelenmemiş kayıt. 4. haftada Nesine'de 8,
   Pinnacle'da 1 satır.
2. **Künye denetimi** (denetim 5) — ana fiyat kapanışsa açılış eşi
   olmalı; yoksa "kupon anında hangi fiyat elimizdeydi" doğrulanamaz.
3. **Duyarlılık kuponu** — aynı kural, ana fiyat yerine **açılış** ile
   yeniden koşulur. Sebebi dürüst: *Spor Toto kuponu ilk maçtan önce
   kapanır; haftanın son maçlarının gerçek kapanış çizgisi o anda henüz
   yoktur.* Kayıttaki "kapanış", **kupon donarken elde olan en geç
   kayıttır** (3. haftanın 3. dersi).

**4. haftada bu farkın pratik ağırlığı sıfır çıktı:** Pinnacle açılış
fiyatıyla kurulan kupon **15 maçın 15'inde birebir aynı** işaretleri
verdi.

---

## 6. ⑤ Oynanma yüzdesi → kalabalık payı

### 6.1 Normalizasyon

```python
t = sum(m["play_pct"].values()) or 100
m["play"] = {s: m["play_pct"][s] / t for s in ("1", "0", "2")}
```

100'e normalize edilir ki oranla **aynı ölçekte** kıyaslanabilsin. Sonra
maç maç `prob`, `play`, `diff = play − prob` ve `ratio = play / prob`
tablosu çıkar.

### 6.2 4. haftanın kamuoyu tablosu (seçilmiş satırlar)

```
 # Maç                          oynanma   piyasa    fark (puan)
 7 Trabzonspor – Gençlerbirliği 81/11/8   61/22/16  +20/-11/-8
 9 Göztepe – Gaziantep          73/17/10  51/25/24  +22/-8/-14
 1 Erzurumspor – Konyaspor      32/27/41  42/28/30  -10/-1/+11   ← AYRIŞMA
12 Athletic Bilbao – Atl.Madrid 21/27/52  31/27/42  -10/-0/+10

Favoriye ortalama fazla oynanma : +4,9 puan
%70+ mutabakat olan maç         : 2
Kamuoyu ile piyasanın AYRIŞTIĞI : [1]  (halkın favorisi ≠ piyasanın favorisi)
```

Okuma: kalabalık favoriye piyasadan **daha keskin** yığılıyor — ki bu
zaten ölçülmüş bir olgudur (§6.3).

### 6.3 Kalabalık modeli — `λ = 1,7608`

Tek platformun yüzdeleri elde olmadığında (ya da kıyas gerektiğinde)
kalabalık modelden üretilir:

```
o_i(s)  ∝  p_i(s)^λ · (1 + δ·[s = "0"]) · (1 + h·[s = "1"])
```

* `λ = 1` → kalabalık piyasa olasılığından çekiyor (`orneklem`)
* `λ → ∞` → herkes favoriyi işaretliyor (`favori`)

**Ölçüldü:** `λ = 1,7608`, hafta düzeyinde bootstrap %95 aralığı
**[1,669, 1,865]** — aralık 1'i içermiyor. Uyum **112 hafta × 4 kademe =
448 gözlem** üzerinde, kademeler arası **oranlarla** kuruldu (haftalık
toplam kolon sayısı `N` bilinmiyor ve gerekmiyor). 15. kademe bilerek
dışarıda: 14/13/12 **kolon** sayar, 15 **kupon** sayar.

`δ` ve `h` **sıfır** çünkü kazanmadılar: sezon sezon kestirildiğinde işaret
değiştiriyorlar (gürültü) ve sezon dışarıda bırakmalı kıyasta tek
parametreli model üç parametreliden ayırt edilemiyor.

**`favori` modeli iki kez birden çürüdü:** hafta başına ~4 kat kötü uyuyor
**ve** haftada 10¹⁷ kolonluk fiziksel olarak imkânsız bir havuz ima
ediyor. Bunun sonucu doğrudandır — daha önce 22 kat genişlikte olan
belirsizlik aralığının `favori` ucu **kapanır**.

---

## 7. ⑥ Kuponun aritmetiği ve seçim

### 7.1 Garanti → kaçak → kademe: üç satırlık aritmetik

`G`-garanti şu demektir: *doğru sonuç seçim kümesinin içindeyse en az bir
kolon en fazla `15 − G` hatalıdır.* `k` maç kümenin **dışında** kalırsa o
`k` maç **her** kolonda yanlıştır ve kalan `15 − k` için garanti işler:

```
en iyi kolon  ≥  (15 − k) − (15 − G)  =  G − k
```

Buradan doğrudan:

| Garanti | `P(en iyi kolon ≥ 12)` için izin | Kaynağı |
|---|---|---|
| 14 | `k ≤ 2` | `sistem.kacak_esigi(14)` |
| **13** | **`k ≤ 1`** | **varsayılan** (kullanıcı 13-garantili oynuyor) |
| 12 | `k ≤ 0` | |

Bu **eşitlik değil alt sınırdır** — kaplama bir kolonu tesadüfen daha iyi
tutturabilir. Yani optimize edilmesi **güvenlidir**: ölçümde gerçekleşen
isabet bu sayının üstünde çıkıyor (36 haftada model %39,5 derken
gerçekleşen 24/36 oldu).

**Hedef 14 değil 12.** İkramiye kademesi 12'de başlar; 14 bir yan
üründür (1. haftanın 1. dersi). Bu bir varsayım değil ölçülmüş bir
seçim (E2): 12/13/14 adayları 114 hafta boyunca **gerçek ikramiye
tablolarına** karşı koşturuldu, eşleştirilmiş ROI farklarının üçü de
sıfırı kesti — sabit değişmedi ama gerekçesi değişti.

### 7.2 Bir maçın kaçak olasılığı

Yapı şaşırtıcı biçimde sadedir — kaçak olasılığı **yalnızca kaç sembol
işaretlendiğine** bağlıdır:

```
banko (1 sembol)   q = 1 − p₁
çifte (2 sembol)   q = p₃          (en düşük olasılıklı sembol)
üçlü  (3 sembol)   q = 0           ← üçlü ASLA kaçmaz
```

Bedel ise yalnızca **sayılara** bağlıdır (hangi maç olduğuna değil).
Bu iki olgu aramayı küçük ve **tam çözülebilir** bir probleme indirger.

4. haftanın gerçek `q` tablosu (13-garanti, ₺2.000 bütçe):

```
 #  p1/p0/p2        q(banko) q(çifte)  seçilen   q
 1  0.42/0.28/0.30    0.579    0.277     102   0.000
 2  0.44/0.28/0.28    0.561    0.279     102   0.000
 3  0.57/0.24/0.19    0.431    0.189       1   0.431
 4  0.53/0.24/0.23    0.474    0.232     102   0.000
 5  0.18/0.21/0.61    0.390    0.184       2   0.390
 6  0.36/0.32/0.32    0.638    0.317     102   0.000
 7  0.61/0.22/0.16    0.386    0.164       1   0.386
 8  0.50/0.28/0.22    0.499    0.220      10   0.220
 9  0.51/0.25/0.24    0.491    0.237     102   0.000
10  0.29/0.26/0.45    0.551    0.263     102   0.000
11  0.58/0.25/0.17    0.421    0.175       1   0.421
12  0.31/0.27/0.42    0.581    0.273     102   0.000
13  0.58/0.25/0.18    0.423    0.178       1   0.423
14  0.57/0.24/0.19    0.430    0.189       1   0.430
15  0.46/0.29/0.25    0.539    0.252     102   0.000
```

Okuma: `k ≤ 1` çok sıkı bir bütçedir. Motor sekiz maçı **kapatıyor**
(`q = 0`) ve riski yalnızca yedi maça bırakıyor — altısı banko, biri
çifte. Toplam kaçak beklentisi `Σq = 2,70` ve `P(k ≤ 1) = 0,1748`.

### 7.3 Arama — neden Pareto DP, neden açgözlü değil

Amaç bir **Poisson-binom kuyruğudur** ve maçlar arasında ayrışmaz;
açgözlü bir kural masada değer bırakır. Ama şu gözlem aramayı tamamlıyor:
ileride yapılacak her evrişim, kümülatif toplamların **pozitif doğrusal
birleşimidir**

```
son_cum₂ = Σⱼ (gelecek pⱼ) · (şimdiki cum₂₋ⱼ)
```

Dolayısıyla `(cum₀, cum₁, …)` vektöründe **baskın** olan bir durum
gelecekte de baskın kalır. Pareto sınırını taşımak **kesin** çözüm verir;
budama bir yaklaşıklık değil, yalnızca baskılanmışları atmaktır.

Durum uzayı: `(çifte sayısı, üçlü sayısı) → Pareto kümesi`. Her maçta üç
dal (banko/çifte/üçlü), her dalda kümülatif güncelleme:

```
cum_m' = cum_m·(1 − q) + cum_{m−1}·q
```

Üç kesin budama:

1. **Bütçe alt sınırı** — bir durumdan ileride çifte/üçlü yalnızca
   *artar*; ulaşılabilir şekillerin en ucuzu bütçeyi aşıyorsa dal ölüdür.
   (Alt sınır formülden değil **fiyat tablosundan** okunur.)
2. **Pareto baskınlığı** — yukarıdaki gerekçe.
3. **Eşitlikte ucuz olan kazanır** — aynı hedefe daha az kolonla ulaşmak
   her zaman tercih edilir.

Pareto sınırı `PARETO_SINIRI = 64` (kalabalık kolunda 256) — güvenlik
supabı; ölçümde en yoğun hafta 12 nokta gördü. Sınıra dayanılırsa
`kirpildi` bayrağı açılır, yani sessizce yaklaşık olunmaz.

### 7.4 Oynanma yüzdesi işaretleri neden değiştirmiyor

İki ayrı mekanizma denendi, ikisi de **ölçüldü**:

**(a) `kalabalik_ayari`** — işaret *sayılarını* koruyup "hangi sembol"
sorusunu yeniden sorar (bedel aynı kalır, bölüşme değişir). Amacı
`küme-içi / kalabalık-içi` oranını enbüyüklemek. Kayıp bütçesi
`VARSAYILAN_KAYIP_ORANI` uzun süre `0.05`ti ve başlığı dürüstçe *"bu bir
ölçüm değil, harcama kararıdır"* diyordu. Ölçüldü, **sıfır çıktı** — üç
bağımsız yoldan:

1. Ölçülen kalabalık modeliyle kayıp bütçesi 0'dan **0,70**'e taransa
   bile **tek bir maçın işareti değişmiyor**;
2. Doğrudan `E[TL]` üzerinde yerel arama: 25 haftanın 25'inde taban plan
   zaten en iyi, tek maçlık en iyi değişimin kazancı **tam 1,0000×**
   (arama dejenere değil: favoriyi bırakmak `E[TL]`'yi 0,39×'e düşürüyor);
3. Mekanizma analitik: `o(s) ∝ p(s)^λ` **monotondur**, sembol sıralamasını
   korur. Kalabalıktan sapmak ancak daha düşük olasılıklı sembole geçerek
   mümkün ve tutturma kaybı pay kazancını her bantta eziyor.

Sıfır "ayar kapalı" demek **değildir**: hedefi hiç düşürmeyen değişimler
hâlâ yapılır. Değişen şey, tutturma olasılığının **satılmamasıdır**.

**(b) `getiri_secim`** — doğrudan `E[TL]`'yi enbüyükler ve **kayıtlı**
oynanma paylarını kullanır. Gerekçesi güçlü: kayıtlı paylar monoton
*değil* — 60 maçın **21'inde** kalabalığın sıralaması piyasanınkinden
farklı, yani kenar varsa oradadır ve monoton model onu göremez.

Ama kısıtsız hâli **ölçülüp geri alındı**: 2026/27 2. haftada `E[TL]`'yi
**3,01 kat** büyütürken `P(k≤1)`'i 0,2194 → **0,0073**'e (−%96,7)
düşürdü; gerçekleşen sonuçta kaçak 1'den 3'e çıktı ve **1.439 TL'lik ödül
sıfıra indi.** Sebep yapısal: `pay_beklentisi` çok küçük `q`'da `1/(N·q)`
gibi patlar, yani kısıtsız beklenen değer neredeyse hiç gerçekleşmeyen
ama gerçekleşirse çok büyük olan dalı seçer. **Ağır kuyruklu bir ödemede
beklenen değeri tek başına enbüyüklemek, iyi olmakla aynı şey değildir.**

Bugünkü hâli: `GETIRI_KAYIP_TAVANI = 0.05` (P tabanın %95'inin altına
inemez) ve **varsayılan yolda çağrılmaz** — ayrı bir satır olarak, "VARSAYILAN
DEĞİL" etiketiyle raporlanır.

4. haftada: değişen maç **0**, `E[TL]` katı **1,000×**.

---

## 8. ⑦ Bedel — iki fiyat modeli, aynı depoda

### 8.1 Eski model: `bedel_hesapla` (yalnızca fix16)

```
bedel = 2^çifte · 3^üçlü / 2⁷ · 16
```

Bu `core.solve_fix16`'nın bedelidir: Hamming(7,4) bloğu **en az yedi
çifte** ister, tek garanti seviyesi (14) tanır. Yanlış değil, **dar**.

### 8.2 Bugünkü model: satıcı fiyat tablosu (`sistem.py`)

Oynanan ürün o değil. Satıcının tablosu **84 şeklin tamamını** ve **üç
garanti seviyesini** (12/13/14) taşıyor: `data/sistem_fiyat/st_extra.json`.

Tablo bir fiyat listesi değil, bir **ölçümdür**: her satır o `(tek, çifte,
kapalı)` şekli için satıcının üretebildiği indirgenmiş sistemin kolon
sayısını verir — yani bizim kendi kaplama kodumuzun **bağımsız
karşılaştırma noktası**.

**Kolon bedeli ₺10 — ölçülmüş.** Üç bağımsız kökenden aynı sayı:
kupon aracı ekranları (dört 15 bilen kuponda da `bedel / kolon = 10,00`,
birinde kolon sayısı ekranda yazılı), kullanıcının bayi / resmî uygulama
beyanı, ve tablonun kendi 250 satırının 250'sinde de tutması.

Aynı şeklin üç garantideki fiyatı (`6 tek / 1 çifte / 8 kapalı`):

| Garanti | Kolon | TL |
|---|---:|---:|
| 12 | 45 | 450 |
| **13** | **162** | **1.620** |
| 14 | 972 | 9.720 |

**Şüpheli satırlar sessizce düzeltilmez.** Tabloda iki satır tekdüzeliği
bozuyor (aynı `tek` bloğunda bir çifte üçlüye dönerken fiyat *düşüyor* —
bir üçlü uzayı büyütür, ucuzlatamaz). İkisi de `supheli` listesinde adıyla
duruyor ve `bedel()` çağrıldığında **uyarır**; değerleri düzeltilmez,
çünkü hangi rakamın yanlış olduğu bilinmiyor.

### 8.3 Bütçe nereden geliyor — ve bu bir **harcama kararıdır**

Bu ayrım depoda açıkça yazılıdır: `hedef` kuralı bir bütçe **ister**;
eşik kuralı bütçeyi kendisi **üretir**. Üretimde "hangi bütçe" sorusu
veriden türetilemez.

İki yol vardır ve ikisi de canlı:

| Yol | Bütçe kaynağı | 4. haftada |
|---|---|---|
| `hafta_kos.py --oncesi` (**varsayılan**) | doğrudan TL — `VARSAYILAN_BUTCE = 2000.0` | 162 kolon = **₺1.620** |
| `super_toto_hafta.py` (profil/kıyas) | eşik kuralının aynı haftada ürettiği maliyet | 3.888 kolon = **₺38.880** |

İkisi çelişmiyor; **farklı bütçelerde farklı sorulara** cevap veriyorlar.
Bütçeyi eşik kuralına sabitlemek, kural kıyasını kuponu değil **kuralı**
ölçen bir kıyas hâline getirir ve ölçüldü: 36 haftanın 35'inde `hedef`
daha iyi, 1'inde eşit, ortalama **%26 daha ucuz**.

**Ölçülmüş bir yan gözlem:** ₺2.000 bütçede 13-garantide dört haftanın
dördünde de aynı şekil çıktı — **6 banko / 1 çifte / 8 üçlü, 162 kolon**.
Yani bütçe + garanti şekli neredeyse çiviliyor; haftanın oranları
*hangi maçın* hangi seviyeye düşeceğini ve *hangi sembollerin*
işaretleneceğini belirliyor. ₺2.000'e sığan şekil sayısı: **37**.

### 8.4 Ve bütçe kaldırılırsa? — **ölçüldü, hiçbir şey açılmıyor** (E6)

*"Bütçe bir harcama kararıdır"* cümlesi bir kaçış olabilirdi: belki de
doğru bütçe **haftaya göre** değişendi. `docs/KAZANMA_PLANI.md` §E6 bunu
ölçtü — 114 hafta, 15 basamak, 14-garantide **gerçek kolonlar** ve resmî
ikramiye tabloları:

| soru | cevap |
|---|---|
| Merdivende yukarı çıkmak geri dönüşü artırıyor mu? | **Hayır.** Basamak oranı %10,6–%37,9 arasında yönsüz zıplıyor; 320 → 4.860 TL'ye çıkmak haftalık ödülü 85 → 1.413 TL yapıyor, yani 4.540 TL fazladan harcamanın karşılığı **1.328 TL: %29** — ortalamanın aynısı |
| Haftaya göre değişen bir kural sabiti yener mi? | **Hayır.** Sınanan on iki kuralın (λ kuralı yedi eşikte, LOO'lu hâli, "en büyük", iki sabit bütçe) on ikisinde de eşleştirilmiş %95 aralık **sıfırı kesiyor** — ve o on iki kural yalnız sekiz farklı seçim deseni üretiyor |
| İyi hafta kupon kapanmadan tanınabiliyor mu? | **Hayır — iki aday da düştü.** `P(hedef)`: rho +0,1175, p 0,2117. **Devir** (havuza dışarıdan giren para, kupon öncesi ilan edilir): rho **+0,2028 [+0,0134, +0,3863]**, p 0,0319 — sıfırı kesmiyor ama iki sınav yapıldığı için Holm eşiği 0,025. Geçseydi bile tavanı ölçülü: devir çarpanı azami 1,645, gereken 1,95–2,84 |
| Öyleyse neden ayırt edilemiyor? | **Kuyruk.** Basamağa göre ödülün %42–%88'i 114 haftanın **en iyi 5'inden** geliyor |

Fiyat cinsinden tek satır: bir birim `P(hedef)` tutturunca **984 TL**
ediyor; merdiven onu uçtan uca medyan **12.002 TL**'ye satıyor (**12,2×**),
oynanan basamağın bir üstünde **92.167 TL**'ye (**93,7×**).

Bu yüzden `--oncesi` artık **merdiveni** de basıyor: bütçe hâlâ bir karar,
ama artık görünmez bir karar değil — hangi basamağın ne kadara satıldığı ve
seçili satıra göre bir puan olasılığın kaç TL ettiği ekranda duruyor.

```bash
python -m spor_toto.hafta_hakki --cephe --garanti 13   # merdivenin kendisi
python -m spor_toto.hafta_hakki --kiyas                # E6 olcumu (~20 dk)
```

---

## 9. ⑧ Kaplama kodu — 16 satır, ve neden tam olarak 1 hata

Bu katman **olasılığı hiç bilmez**. `core.py` içinde olasılık katmanına
tek bir atıf yoktur; garanti bir tahmin değil **kombinatoryal teoremdir**.

### 9.1 Fix16

`solve_fix16` yedi çifte maçı Hamming(7,4) bloğuna koyar — **16 kolon,
kanıtlanmış optimal**. Bu yedinin dışında kalan her şey (fazladan
çifteler ve bütün üçlüler) "ekstra" sayılır ve **tam sistem** olarak aynı
16 satırın içine çifte/kapama işareti şeklinde girer.

Garanti neden korunuyor: ekstra maçlarda bütün ihtimaller oynandığı için
hata payı **sıfırdır**; toplam hata bütçesi Hamming bloğunda kalır, orada
da en fazla 1 hata olur. **İki `r=1` bloğu birleştirilirse yarıçap 2 olur
ve garanti kırılır** — bu yüzden yalnızca tek blok olabilir.

Bilinen alt sınırlar (küre-kaplama: `kolon ≥ |uzay| / top_boyutu`):

| Durum | Optimal kolon |
|---|---|
| 5 çifte | 7 |
| 6 çifte | 12 |
| **7 çifte** | **16** (Hamming(7,4)) |
| 8 çifte | 32 |
| 4 üçlü | 9 |

**8 çifteyi 16 kolona sığdırmak imkânsızdır.**

### 9.2 Satır ≠ kolon

Bir maça çifte işaretlersen o satır **2 kolon** üretir ve 2 kolon bedeli
ödersin. Bu bir ürün kuralıdır: kolon bedeli hiçbir yerde satır
sayısından ayrı gösterilmez.

4. haftanın fix16 kuponu: seçim uzayı 31.104 → **3.888 kolon · 16 satır**.

### 9.3 Oynanacak satırlar

`merge_rows` 16 kolonu insan okuyacak satırlara döker (birleşmiş satırda
bir maçta birden çok sembol işaretli olabilir). 4. haftanın 16 satırı
`hafta_04_kupon.json → rows` içinde duruyor; ilk üçü:

```
 1  102 102 1  1  2  102 1  1  1  102 1  102 1  1  1
 2  102 102 1  1  2  102 1  1  1  102 0  102 1  0  0
 3  102 102 1  1  2  102 1  1  0  102 1  102 0  0  1
```

---

## 10. ⑨ Havuz katmanı — `E[TL]` ve rakip yoğunluğu

Bu katman **kuponu kurmaz**, kuponun parasal karşılığını hesaplar.

### 10.1 Havuz bölüşümü — ölçülmüş kural

222 haftada ölçüldü ve **sabit bir kuraldır**:

```
BOLUSUM = {15: 1.75, 14: 1.0, 13: 1.0, 12: 1.25}   →  %35 / %20 / %20 / %25
```

| Oran | Beklenen | Sonuç |
|---|---|---|
| 14 ÷ 13 | 1,00 | 218 haftanın **214'ünde birebir** |
| 12 ÷ 13 | 1,25 | ortanca **tam 1,2500** |
| 15 ÷ 13 | 1,75 | 176 haftanın **135'inde tam**, hiçbirinde altında değil |

**Devir 15'e özgü değildir:** kazanansız kalan *her* kademe payını ileri
taşır ve ertesi hafta aynı kademe fazlasıyla döner. Model
genelleştirilince açıklanamayan hafta **10'dan 2'ye** düştü (222 haftanın
220'si kurala birebir oturuyor) ve devir zinciri kapanıyor: devreden
haftanın ardından gelen ÷ giden oranının ortancası **1,000**, 41 haftanın
36'sında %2 içinde birebir eşit.

Bu, `getiri_secim` için kritik bir olgudur: `E[TL]`'nin argmax'ı havuzun
**ölçeğine** değil kademeler arası **oranına** bağlıdır — ve o oran kupon
kapanmadan **bilinir**.

### 10.2 Pay — "tutturmak yetmez, az kişiyle tutturmak gerekir"

```
pay_beklentisi(N, q) = E[1/(1+W)],   W ~ Binom(N, q)      (kapalı form)
```

`q` **bir rakip kolonun** o kademeyi tutturma olasılığıdır — bir
oyuncunun değil; havuz kolon başına bölünür. `N·q` on kat büyüyünce pay
altıda bire iner.

Küçük `q`'da naif form **çöker** (`(1−q)^n` bire yapışır, çıkarma anlamlı
basamakları yer) ve yanlış **aşağı** doğru: havuz payını olduğundan küçük
gösterir. Kapalı form bu yüzden var.

### 10.3 Koşullu ortak dağılım — asıl incelik

Rakibin isabetini **koşulsuz** hesaplamak yanlıştır: havuz **biz
kazandığımızda** bölünür. `kosullu_kademe_dagilimi` her maçta dört yolu
birlikte taşır:

```
sonuç kümede (p_S)     · rakip uydu   a = Σ_S p·o / Σ_S p
sonuç kümede           · uymadı
sonuç KAÇTI  (1 − p_S) · rakip uydu   b = Σ_S̄ p·o / Σ_S̄ p
sonuç kaçtı            · uymadı
```

Sonuç `dp[k][j]` — `k` kaçak **ve** rakip tam `j` doğru. İkisini ayrı
hesaplamak, kaçtığımız maçta rakibin de kaçma eğilimini görmezden gelirdi.

Sonra:

```
E[TL] = Σ_k P(k kaçak) · havuz(garanti − k) · pay_beklentisi(N, q_koşullu)
```

### 10.4 Varsayımlar — adıyla

| Sayı | Statü | Not |
|---|---|---|
| `BOLUSUM` %35/20/20/25 | **ÖLÇÜM** (222 hafta) | |
| `KOLON_BEDELI = 10 TL` | **ÖLÇÜM** (üç bağımsız köken) | |
| `λ = 1,7608` | **ÖLÇÜM** (448 gözlem, %95 [1,669, 1,865]) | |
| `RAKIP_KOLON = 15.000.000` | **VARSAYIM** | Model 10–19 milyon ima ediyor; `E[TL]` buna `1/(N·q)` mertebesinde duyarlı — **mutlak TL değil kıyas için okunur** |
| `VARSAYILAN_KOMISYON = 0.50` | **VARSAYIM** | Ciro hiçbir ekranda yayınlanmıyor |
| havuzun kendi büyüklüğü | **VARSAYIM** | aynı sebep |

### 10.5 Ve sayının kendisi

4. haftada `E[TL]` hesaplanmadı çünkü ikramiye tablosu henüz yok (hafta
kapanmamış). Sonuçlanmış üç hafta:

| hf | kolon | maliyet | P(k≤1) | E[TL] | kaçak | kademe | ödül | net |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 162 | 1.620 | 0,249 | 75 | 4 | 9 | 0 | −1.620 |
| 2 | 162 | 1.620 | 0,219 | 94 | 1 | 12 | 1.439 | −181 |
| 3 | 162 | 1.620 | 0,282 | 93 | 1 | 12 | 1.230 | −390 |
| **4** | **162** | **1.620** | **0,175** | — | — | — | — | — |

Toplam: ₺4.860 maliyet, ₺2.668 ödül, **net −₺2.192, geri dönüş %54,9**.

İki şey birlikte okunur ve motor ikisini de saklamaz:
1. **`E[TL]` maliyetin çok altında** (₺75–94 ↔ ₺1.620). Kendi
   varsayımlarıyla bu kupon negatif beklenen değerlidir ve rapor bunu
   yazar.
2. **Ödül sütunu alt sınırdır** — 162 kolonluk bir 13-garanti sistemi,
   garantinin söylediği tek kolondan fazlasını da tutturur; karne onları
   saymaz çünkü kolon listesi bizde değil (şekle biz karar veriyoruz,
   kolonları satıcı üretiyor). Gerçekleşen getiri bu tablodan büyüktür.
3. **`n` küçük.** Üç hafta bir strateji karnesi değil, bir kayıt
   başlangıcıdır.

---

## 11. Haftanın profili — geçen sezonun ölçülmüş bantları

Kupon kurulmadan önce hafta, **geçen sezonda ölçülmüş** tablolara
oturtulur. Bu bir tahmin katmanı değil, bir **bağlam** katmanıdır: kupon
işaretlerini değiştirmez, "bu hafta normal mi" sorusunu cevaplar.

**Banko güvenilirliği** (kapanış favorisinin oranına göre, 567 maç):

| Favori oranı | Maç | Tuttu | ↳ beraberlik | ↳ karşı taraf |
|---|---:|---:|---:|---:|
| 1,00–1,20 | 11 | %90,9 | %9,1 | %0,0 |
| 1,20–1,35 | 39 | %76,9 | %17,9 | %5,1 |
| 1,35–1,50 | 64 | %64,1 | %23,4 | %12,5 |
| 1,50–1,75 | 106 | %60,4 | %20,8 | %18,9 |
| **1,75–2,00** | 104 | **%50,0** | **%35,6** | %14,4 |
| 2,00+ | 243 | %46,9 | %25,5 | %27,6 |

Okuma: 1,35 pratik bir sınır; **1,75–2,00 bandı tuzaktır** — isabet
%50'ye düşerken tutmama sebebinin çoğu beraberliktir, yani orada banko
yapmak aslında beraberliğe karşı bahis yapmaktır.

**Çift kapsama** — ilk-iki olasılık toplamı 0,70–0,80 iken gerçek sonuç
küme içinde kalma oranı %77,2; 0,80–0,90 → %85,3; 0,90+ → %95,1. Aynı
bantlarda **banko** yapılsaydı: %47,8 / %65,4 / %80,5.

**4. haftanın profili:**

```
                             bu hafta      geçen sezon ort.
beklenen '1' adedi                6,91                6,59
beklenen '0' adedi                3,88                3,63
beklenen '2' adedi                4,22                4,78
favori dağılımı 1/0/2       12 / 0 / 3        %66 / 0 / %34
favori tutar (piyasa)             7,61
favori tutar (bantlar)            7,97                8,23
çift kapsar (piyasa)             11,57
marj                             %5,44               %7,26  (0,75×)

Lig: T1 9 · I1 3 · E0 2 · SP1 1
     (T1 beraberlik %29,8 ↔ E0 %19,7 — "0" bütçesi nereye harcanır)
```

---

## 12. Kuponu **etkilemeyen** ama kayda geçen katmanlar

Bunlar çalışır, raporlanır ve **işaret değiştirmez**. Sebepleri
ölçülmüştür:

| Katman | Ne yapar | Neden karara girmiyor |
|---|---|---|
| **Dixon-Coles + Elo** (`gorus.py`) | Orana hiç bakmadan bağımsız görüş | İkisi de kupon setinde piyasanın gerisinde ölçüldü; Elo zaten 1X2 değil beklenen **skor** verir |
| **Bahisçi ayrışması** (A2) | Kolektif içi dağılım bilgi mi | Değil — ve 4. haftadaki en büyük "ayrışmalar" bayat satırlardan geliyor |
| **Piyasa dışı özellikler** (A3) | Türetilebilir sütunlar | Faz A dört cepheden piyasayı geçmeye çalıştı, hiçbiri geçmedi |
| **Hakem** (E4) | Sütun arayışının son denemesi | Etki **yok** çıktı — zayıf değil, yok |
| **Benzer maç** (`benzer.py`) | "Bu oranda geçmişte ne olmuş" | Bilgi ürünü; kurala bağlanmadı |
| **Fire / Markov / Monte Carlo** | Küme dışı manzara, sıralı risk | Garantiyi değiştirmez; formül sayfasının ölçüm blokları |

4. haftada görüşün en büyük ayrışması: **14. maç Roma–Atalanta** —
piyasa 57/24/19, Dixon-Coles 33/30/37, sapma **24 puan**. Kayda geçti,
kupona girmedi.

---

## 13. Ne dondurulur — ve neden yeniden türetilebilir

`hafta_NN_kupon.json` üç şey taşır:

* **`meta.strategy`** — `arindirma` (`shin`), `kural` (`hedef`),
  `butce_kolon`, `butce_kaynagi`, `fiyat`, `marj_ort_pct`.
  Bu alanlar sabit yazılmaz, kayıttan okunur: bir dönem sabitti ve 3.
  haftada **yalan söylemeye başladı** (kayıt "ölçek değişti" diyecekti,
  oysa değişmemişti). Deponun üçüncü kez gördüğü kalıp: bugünkü durumu
  kalıcı sanmak.
* **`variants`** — aynı haftanın altı kuponu, hepsi ölçülmüş:

| Varyant | Kolon | P(≥12) | küme-içi | crowd_ratio |
|---|---:|---:|---:|---:|
| **ana — hedef kuralı, kalabalık görülmeden (DONDURULAN)** | 3.888 | %46,70 | %4,01 | 0,43 |
| hedef + kalabalık ayarı (ölçüldü, oynanmadı) | 3.888 | %44,86 | %3,69 | 0,56 |
| eşik kuralı — eski kural, aynı ölçek (kıyas) | 6.144 | %36,72 | %2,91 | 0,55 |
| bütçe kısıtlı — 864 kolon | 864 | %26,18 | %1,31 | 0,38 |
| bütçe kısıtlı — 1.296 kolon | 1.296 | %31,84 | %1,80 | 0,39 |
| 3. Kupon — SÜRPRİZ (kalabalıktan azami sapma) | 432 | %8,15 | %0,15 | **3,08** |

* **`duyarlilik`** — açılış fiyatıyla kurulan kupon (4. haftada 15/15
  aynı), ve kuşkulu marj düzeltilseydi ne olurdu (değişmiyor).

**Sızıntı yok, ama dondurulmuş da değil.** Karne, her haftanın kupon
öncesi girdilerinden **bugünkü motorla** yeniden türetilir. Girdiler
sonuç girilmeden kaydedildi (`entered_at` < `results_entered_at`) ve
kalabalık modeli 2026/27'yi hiç görmeyen 112 tarihsel haftada kestirildi
— ama motor o gün bugünkü hâlinde değildi. Karne bunu **her satırda**
söyler.

`meta.results_known` `false` olmadan `super_toto_tahmin2.py` yazmayı
**reddeder**: sonucu bilinen bir haftaya "ikinci tahmin" yazmak tahmin
değil, geriye dönük kurgu olurdu.

---

## 14. Bilinen sınırlar — hepsi ölçülmüş ya da adıyla varsayım

| Sınır | Durum |
|---|---|
| **Maç bağımsızlığı** (`kacak_dagilimi` Poisson-binom varsayar) | Ölçüldü, **kırılmadı**: hafta içi ortalama ikili artık korelasyon korpusta −0,00009 [−0,00102, +0,00080]; kupon kesitinde −0,00349 [−0,01724, +0,01020]. Kuyruğa çevrildiğinde `P(k≥14)` en fazla %5 şişiyor |
| **Seçim koşullu aşırı güven** | Ölçüldü ve **gerçek**: yüksek eşikte +%14,9 aşırı güven (§3.49). Küresel olarak iyi kalibre bir model, *seçtiği* alt kümede gürültüyü seçer |
| **`P(k ≤ eşik)` iyimser mi** | Hayır — **alt sınırdır**; gerçekleşen isabet üstünde çıkıyor |
| **Oynanma payı = havuz payı mı** | **Hayır.** Tek platformun kullanıcıları; Spor Toto havuzunun tamamı değil |
| **"Kapanış" gerçekten kapanış mı** | **Hayır.** Kupon donarken elde olan **en geç kayıt**. Ölçüldü ve etiketin fazla olduğu görüldü (3. haftanın 3. dersi) |
| **Havuz ekseni (az oynanana kayma) kâr getirir mi** | **Bugün ölçülemez.** Güç analizi ≈71 ikramiyeli hafta istiyor (≈3,5 sezon); analiz koşulduğunda elde 1, bugün 3 sonuçlanmış hafta var. Durma kuralı şimdiden yazılı |
| **Tahmin katmanı piyasayı geçiyor mu** | **Geçmiyor.** Kalan etki 0,0005–0,0015 Brier: 31 binde anlamlı, 540 kupon maçında değil, %17,2'lik iddaa marjının yanında pratik eşiğe yakın bile değil |
| **Kâr vaadi** | **Yok.** Proje kazanmayı garanti etmez; garanti ettiği tek şey kombinatoryal olandır |

---

## 15. 4. haftanın uçtan uca koşumu

```
GİRDİ    15 maç · pinnacle+nesine × açılış/kapanış · % tercih · 2026-09-04
  ①      5 otomatik uyarı (1 kuşkulu marj, 3 eksik/bayat kayıt, 1 delik)
  ②      ana fiyat: 13× pinnacle_kapanis, 1× pinnacle_acilis, 1× nesine_kapanis
  ③      shin arındırma → marj ort. %5,44 (Pinnacle satırları %4,62)
  ④      oynanma normalize; favoriye ortalama +4,9 puan fazla oynanma
  ⑤      13-garanti → k ≤ 1;  Pareto DP, ₺2.000 bütçe, 37 aday şekil
  ⑥      şekil 6 banko / 1 çifte / 8 üçlü  →  tablo: 162 kolon = ₺1.620
  ⑦      P(en iyi kolon ≥ 12) = P(k ≤ 1) = 0,1748
  ⑧      kalabalık ayarı: değişen maç 0 · E[TL] katı 1,000×
  ⑨      E[TL] hesaplanamadı (ikramiye tablosu henüz yok)

KUPON    102 102 1 102 2 102 1 10 102 102 1 102 1 1 102
         banko  : 3, 5, 7, 11, 13, 14
         çifte  : 8
         üçlü   : 1, 2, 4, 6, 9, 10, 12, 15
```

Aynı hafta ₺38.880 bütçeyle (eşik kuralının ürettiği maliyet, 14-garanti
fix16 yolu) başka bir kupon veriyor: 3 banko / 7 çifte / 5 üçlü,
**3.888 kolon**, `P(≥12) = %46,70`. İkisi çelişmiyor — **bütçe bir
harcama kararıdır ve veriden türetilemez.**

---

## 16. Yeniden üretme

```bash
cd backend

# Kupon öncesi plan (VARSAYILAN yol: TL bütçe, satıcı tablosu, 13-garanti)
python scripts/hafta_kos.py --oncesi 2026_27 4          # plan + MERDIVEN
python scripts/hafta_kos.py --oncesi 2026_27 4 --butce 5000 --garanti 14

# Bütçe ekseninin kendisi (E6)
python -m spor_toto.hafta_hakki --cephe --garanti 13     # haftanın merdiveni
python -m spor_toto.hafta_hakki --para 2026_27:3         # E[TL] cephesi
python -m spor_toto.hafta_hakki --kiyas                  # 114 hafta, ~20 dk

# Haftanın profili + kamuoyu + bütçe merdiveni (fix16 yolu, kıyas)
python scripts/super_toto_hafta.py --hafta 4
python scripts/super_toto_hafta.py --hafta 4 --json

# Aynı haftayı bugünkü aletlerin tamamıyla yeniden okuma
python scripts/super_toto_tahmin2.py --hafta 4

# Karne (sonuç + resmî ikramiye tablosu girildikten sonra)
python scripts/hafta_kos.py --sonrasi --yaz

# Katman katman
python -m spor_toto.sistem --butce 2000     # satılan şekiller ve fiyatları
python -m spor_toto.kalabalik               # λ kestirimi + çapraz doğrulama
python -m spor_toto.kalabalik --havuz       # bağımsız kolon-sayısı sınavı
python -m spor_toto.cizgi                   # açılış→kapanış (A1)
python -m spor_toto.havuz                   # bölüşüm + devir zinciri
python -m spor_toto.secim                   # geçen sezonun kural kıyası
python scripts/acilis_kapanis.py            # açılış/kapanış kupon kıyası
```

---

## 17. İlgili belgeler

* `docs/ISTATISTIK_YOL_HARITASI.md` — §3.14 (A1 çizgi), §3.18 (shin),
  §3.19 (hedef kuralı), §3.34/§3.40/§3.47/§3.48 (havuz, getiri, dersler),
  §3.49 (seçim koşullu kalibrasyon)
* `docs/KAZANMA_PLANI.md` — Faz B (havuz ekseni), Faz K (kalabalık), Faz S
* `docs/KAZANMA_KARNESI.md` — haftalık öngörülen ↔ gerçekleşen
* `docs/KADEME_OLASILIKLARI.md` — kademe aritmetiği ve durma kuralları
* `README.md` §3–§5 — kombinatoryal çekirdek, olasılık katmanı, veri
