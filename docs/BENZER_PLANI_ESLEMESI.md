# `benzer.py` dış geliştirme planı — depoyla madde madde eşleme

**Kapsam:** Depo dışından gelen bir geliştirme planının madde madde karşılığı:
**hangisi zaten var, hangisi kısmen var, hangisi gerçekten eksikti, hangisi
bilerek reddedildi.**
**İncelenen belge:** `BENZER_PY_CLAUDE_CODE_GELISTIRME_PLANI.md` (27 bölüm, 18 faz)
**Bu belgenin tarihi:** 2026-08-30 · taban `7f16e64` (PR #25 birleştikten sonra)
**İlgili belgeler:** [`GELISTIRME_PLANI_ESLEMESI.md`](GELISTIRME_PLANI_ESLEMESI.md) ·
[`DIS_INCELEME_AZ_RAPORU.md`](DIS_INCELEME_AZ_RAPORU.md) ·
[`DIS_INCELEME.md`](DIS_INCELEME.md) · [`DIS_INCELEME_ALPHAPY.md`](DIS_INCELEME_ALPHAPY.md)
(aynı türün önceki örnekleri) ·
[`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §3.18 (A5, bu
modülün kendi bölümü) ve §6 (projenin sonlanan planı ve durma kuralları)

> **Künye — bu plan depo okunmadan yazıldı.** Projeyi bulunduğu yerden farklı
> tarif ediyor: `benzer.py` tek başına duran testsiz bir script, backtest ve
> kalibrasyon katmanı yok, metadata "mümkünse" eklenecek bir şey. Gerçekte
> modül 48 modüllük bir paketin içinde, 21 testi, bir HTTP ucu ve bir arayüz
> kartı var; korpus planın istediği metadata'nın biri hariç hepsini taşıyor.
> Bu, planı değersiz yapmaz — **üç yerde gerçek kusura parmak bastı** ve üçü
> de bugün koddaydı. Ama statüsü **dış görüştür**, teyit değil.

---

## 1. Kısa cevap

| Kova | Sayı | Örnek |
|---|---:|---|
| **Zaten var** | çoğunluk | test altyapısı, Wilson aralığı, kalibrasyon kovaları, örneklem dürüstlüğü, çoklu karşılaştırma uyarısı, raporlama, API'ye hazır mimari, regresyon fikstürleri |
| **Gerçekten eksikti → uygulandı** | 3 | `inf` oranın kabul edilmesi · toleransın üç kapıda üç farklı sınırı · zaman kesmesinin hiç olmaması |
| **Yarım kalmış → tamamlandı** | 1 | `_wilson` takma adı |
| **Reddedildi, gerekçesi ölçülmüş** | 6 | L1/L2/JS · Bonferroni/FDR · 500K benchmark · `AnalysisConfig` · dataclass katmanı · karar motoru |
| **Reddedilmedi, kaydedildi** | 3 | ileri yürüyüş ölçümü · çizgi ekseni · `cli.py`/`health.py` bağlanması |

Uygulanan üçün ürettiği sonuç, planın ana tezini **değiştirmedi**: plan
"sistem test edilmemiş" diyordu; bulunan şey testin yokluğu değil, testlerin
hiç bakmadığı üç kapıydı. Biri bugün yanlış cevap üretiyordu (`inf`), biri
sessizce başka bir sorguya çeviriyordu (`tolerans` kırpması), biri bir
yeteneğin hiç olmamasıydı (kronoloji).

---

## 2. Gerçekten eksik olan üç şey

### 2.1 `inf` oran kabul ediliyordu — `benzer.py`

Kapı tek satırdı:

```python
if any(v is None or v <= 1.0 for v in oranlar.values()):
    raise ValueError("her oran 1.00'den büyük olmalı")
```

`inf <= 1.0` yanlıştır, `nan <= 1.0` da yanlıştır. İkisi de bu kapıdan
geçiyordu. Ölçüldü (`spor_toto.odds.implied_probs`):

```
{'1': inf, '0': 3.04, '2': 2.44}  ->  {'1': 0.0, '0': 0.445…, '2': 0.554…}
{'1': nan, '0': 3.04, '2': 2.44}  ->  {'0': 0.445…, '2': 0.554…}     ← 2 anahtar
```

**`inf` üç anahtar döndürüyor**, yani bir alt kattaki `len(hedef) != 3`
kontrolüne de takılmıyordu. Sorgu koşuyor ve `1` sembolüne %0 olasılık
atanmış bir hedef vektörle korpusu tarıyordu. Çıkan sayı bir cevap gibi
görünüyordu.

`nan` yakalanıyordu ama **yanlış mesajla**: sembol arındırmadan sessizce
düşüyor, `len(hedef) != 3` devreye giriyor ve *"üç sembolün de oranı
gerekli"* deniyordu. Kullanıcı üç oranı da vermiştir; mesaj yanlış yeri
gösteriyordu.

Planın FAZ 2'deki `odds finite` maddesi haklıydı. Artık `math.isfinite`
üzerinden ve **hangi sembolün suçlu olduğu** söylenerek reddediliyor.

### 2.2 Aynı parametre üç kapıda üç farklı sınır — tolerans ve `en_az`

| Kapı | Tolerans | `en_az` |
|---|---|---|
| `benzer_maclar(…)` | **sınır yok** — `0.9` kabul, bütün korpus "benzer" | **sınır yok** — `0` ve `-5` kabul |
| CLI `--tolerans` / `--en-az` | `type=float`/`int`, sınır yok | sınır yok |
| HTTP `?tolerans=` / `?en_az=` | `_parse_esik` `[0, 1]`'e **kırpar** | `max/min` `[1, 20000]`'e **kırpar** |

Üçü de uyarlanan aramanın kendi tavanını (`EN_COK_TOLERANS = 0.05`)
tanımıyordu. Sabitin kendi yorumu o tavanı şöyle gerekçelendiriyor: *"Ötesi
'benzer maç' olmaktan çıkar."* Otomatik yol 0,05'te duruyor, elle yol 0,9'a
çıkabiliyordu — bir özellik değil, tutarsızlık.

Asıl kusur kırpmanın kendisiydi: `?tolerans=0.9` **reddedilmiyor**, sessizce
1,0'a çekilip **başka bir sorguya** çevriliyordu. Kullanıcı bunu göremiyordu.

HTTP'de iki durum ayrıldı ve ayrım korundu:

- **okunamayan** değer (`?en_az=abc`) → varsayılana düşer, 200. Eski
  sözleşme; `test_api_gecerli_ve_bozuk_ek_parametreler_cokmez` onu bekçiliyor
  ve kırılmadı.
- **okunan ama sınır dışı** değer (`?tolerans=0.9`, `?en_az=0`) → 400.

Kural artık tek yerde: `benzer._dogrula`. CLI kendi kopyasını yazmıyor,
`ValueError`'u iletiyor.

### 2.3 Zaman kesmesi yoktu — `benzer.py`

Süzgeç yalnızca `lig` ve `sezon`du. `tarih` her satırda yüklüydü
(`egitim.korpus_yukle`) ama hiç okunmuyordu. Sonuç: 2022 tarihli bir fiyat
sorulduğunda 2024–2025 maçları da "geçmişte ne oldu" cevabına giriyordu.

**Bu canlı tahmine sızıntı DEĞİL** ve öyle sunulmamalı: korpus güncel sezonu
içermiyor, `test_egitim.test_varsayilan_korpus_guncel_sezonu_icermez` bunu
bekçiliyor. Kusur başka ve daha sessizdi: modül o hâliyle **hiçbir kronolojik
ölçümün içine konulamıyordu.** Depo bunun bedelini zaten ölçtü — ileri
yürüyüşte kronoloji zorlandığında piyasanın artığını öğrenen aileler **2–3
kat kötüleşti** (`ISTATISTIK_YOL_HARITASI.md` §6.6). `benzer`in sayıları o
sınavdan hiç geçmedi, çünkü sınava sokulamıyordu.

`tarih=None` varsayılan ve bugünkü davranışı birebir koruyor. Verildiğinde
karşılaştırma **katı küçüktür** ve `datetime`sizdir: korpus tarihleri ISO
dizgi, ISO dizgilerde sözlük sırası takvim sırasıdır. Katılık ayrıca
"kendini dışla"yı bedavaya çözer — aynı gün oynanan maçlar da düştüğü için
sorulan maç kendi cevabına giremez.

Ölçüldü:

| sorgu | evren | kesilen | uyarlanan yarıçap | bulunan |
|---|---:|---:|---:|---:|
| kesmesiz | 31.103 | 0 | %2,0 | 241 |
| `2023-08-01` öncesi | 15.640 | 15.463 | **%3,0** | 308 |

Yarım korpusta hedef örnekleme ulaşmak zorlaşıyor ve yarıçap genişliyor. Bu,
ileri yürüyüş ölçümünün kendi örneklem sorusudur (§5.1).

**Sızıntı sözleşmesi.** `benzer`, `tests/test_sizinti.py`te **hiç
geçmiyordu**. Dosyanın kendi gerekçesi burada birebir işledi: *"yeni bir
tahminci eklendiğinde onu kimse otomatik denetlemiyordu."* `benzer` bir
tahminci değil — tahmin üretmez, ampirik bir sayım verir — ama sızıntı riski
aynıdır ve daha sinsidir: ürettiği sayı "geçmişte ne oldu" diye sunulur.

Üç denetim eklendi ve dosyanın kuralı korundu: **her denetimin yanında
bilerek sızdıran bir kurgu var.** Kesmesiz sorgunun geleceği gerçekten
gördüğü ayrıca sınanıyor — yoksa kesme testi, korpusta hiç gelecek maç
olmadığı için de yeşil kalırdı.

---

## 3. Yarım kalmış olan: `_wilson`

`benzer.py`'deki takma adın kendi yorumu zaten şunu yazıyordu: *"private bir
sembol iki sıçramayla dolaşıyordu. Tek kaynak: `ortak`."* Ama takma ad
duruyordu, çünkü iki çağıran onu hâlâ `benzer`den ithal ediyordu — yani
sıçrama devam ediyordu, sadece gerekçesi yorumda yazılıydı.

`kalibrasyon.py` ve `scripts/super_toto_sezon.py` artık `ortak.wilson`
çağırıyor; takma ad kalktı. `backtest._wilson`'a **dokunulmadı**: o
`backtest`in kendi dışa açık adı ve `tests/test_backtest.py` onu ismen ithal
ediyor — ayrı bir karar.

Aynı fonksiyon, aynı sayı: kalibrasyon eğrisi değişmedi (31.103 maç, 93.309
nokta, bant bant aynı yüzdeler).

---

## 4. Eklenen tek yeni sayı: mesafe kalitesi (FAZ 10)

`tolerans_genisledi` bir boolean: "yarıçap büyüdü". Büyüdüğünde okuyanın
soracağı tek soru şudur — *gerçekten benzer maç mı bulundu, yoksa örneklem
toplamak için uzağa mı uzanıldı?* Bunu gösteren hiçbir sayı yoktu.

Deponun kuralı **"karara girmeyen sayı üretme"**dir, ve bu blok yeni bir soru
sormuyor: var olan bir bayrağı okunabilir kılıyor. Niçin karara girdiği
ölçüldü — aynı oran, iki sorgu:

| tolerans | ortanca mesafe / tavan | piyasa |
|---|---|---|
| 0,02 | %1,58 / %2 | her sembolde GA **içinde** |
| 0,05 | **%3,88 / %5** | iki sembolde "GA **DIŞINDA**" |

İkinci sorgu bir bulgu gibi görünüyor: 3.596 maçta beraberlik piyasanın
dediğinin **4,3 puan üstünde** ve güven aralığı piyasayı dışarıda bırakıyor.
Ama ortancası tavanın dörtte üçünde — o küme "aynı fiyat" değil, yarıçapın
kenarı. Eski çıktıda bu ayrımı yapacak hiçbir sayı yoktu.

Sıralı listeden bedavaya geliyor; ikinci bir sıralama yok.

---

## 5. Reddedilenler — ve gerekçelerinin nerede ölçüldüğü

### 5.1 L1 / L2 / Jensen-Shannon karşılaştırması (FAZ 9)

Plan doğru sırayı söylüyor: *"önce baseline backtest sonucu oluştur, sonra
alternatifleri aynı test setinde karşılaştır."* **O baseline yok** (§6.1).
Ölçüm protokolü kurulmadan üç mesafe metriği eklemek, planın kendi §20 kabul
kriterini (Brier/log-kaybı ile karşılaştır) karşılayamaz.

Ayrıca `_mesafe`'nin L∞ seçimi keyfi değil; gerekçesi fonksiyonun kendi
docstring'inde: *"hiçbir sembolde X puandan fazla ayrılmasın"* kuralı,
kullanıcının "aynı oranlar" fikrinin karşılığıdır ve Öklid bir semboldeki
büyük sapmayı iki küçük sapmayla örtebilir. Bu bir performans iddiası değil,
**anlam** iddiası — ve bir Brier farkı onu tek başına çürütmez.

**Hangi koşulda açılır:** §6.1'in koşumu var olduğunda, aynı kesitte dört
metrik yan yana.

### 5.2 Bonferroni / FDR (FAZ 12)

Planın kendisi *"uygulamadan önce neden gerekli olduğunu belgeleyip backtest
et"* diyor. Mevcut `COK_DILIM` uyarısı bir düzeltme değil **görünürlük**
sağlıyor. Bir p-değeri düzeltmesi eklemek, bu modülün bugün hiç üretmediği
bir nesneyi — p-değerini — üretmeyi gerektirir; Wilson aralığı ve
`piyasa_ga_icinde` bayrağı aynı işi düzeltmesiz görüyor.

`GELISTIRME_PLANI_ESLEMESI.md` §4 (faz 16–17) aynı kararı `backtest` için
verdi: *"`gecti` yalnızca güven aralığının tamamı sıfırın altındaysa."*

### 5.3 100K / 500K benchmark (§22) ve ayrı zaman pencereleri (FAZ 7)

Korpus **31.103 satır** ve sürümlenmiş bir dosya. 500K satırlık bir ölçüm var
olmayan bir veriyi ölçer. Planın kendi §22'si *"önce profiler ile darboğazı
bul"* diyor — ve ölçülmüş darboğazlar zaten kapatılmış: `_olasilik_tablosu`
önbelleği olmadan her sorgu ~2 sn sürüyordu, `odds._arindirilmis`
önbelleğinin gerekçesi de ölçülmüş (`korpus_haftalari` süresinin **%92'si**
shin kök bulucusundaydı).

"Son 1/3/5 yıl" pencereleri ayrı bir rapor olarak yazılmadı: `tarih=`
parametresi + mevcut `sezon` süzgeci bunu **çağıranın** kurabileceği bir
sorguya çevirdi. Dört sezonluk bir korpusta "son 5 yıl" ile "tüm zaman" aynı
şeydir.

### 5.4 `AnalysisConfig` (FAZ 16) ve dataclass/TypedDict katmanı (FAZ 14)

Altı sabit, altısı da tek modülde, her biri `#:` yorumuyla **niçin o değer
olduğu** yazılı. Bir config nesnesi bu yorumları dağıtır ve `HEDEF_ORNEKLEM`'i
ithal eden `web_app.py`'yi kırar.

Dataclass katmanı için `GELISTIRME_PLANI_ESLEMESI.md` §3.3'ün gerekçesi
birebir geçerli: `pyproject.toml` `spor_toto.benzer`'i kademeli mypy'ın
`ignore_errors` grubunda tutuyor; tip modeli o kararın **sonucu**, eksikliği
değil. Bu boydaki bir modül için altı yeni tip, planın kendi uyarısına düşer:
*"Gereksiz abstraction üretme."*

FAZ 17'nin istediği ayrım ayrıca **zaten var**: `benzer_maclar` saf sözlük
döner, `yaz()` ayrı fonksiyon, JSON ayrı, `/api/benzer` aynı sözlüğü basar,
`frontend/lib/types.ts` onu birebir aynalar. Analiz mantığında tek bir
`print()` yok.

### 5.5 `tolerans_uyarlandi` → `adaptive_tolerance` (FAZ 15)

Ad **sözleşmedir**: `BenzerResponse` içinde, arayüz kartı okuyor,
`api-sozlesme.json` bekçiliyor. Değiştirmek yığının iki ucunu ayrıştırır ve
karşılığında hiçbir şey ölçmez.

`GELISTIRME_PLANI_ESLEMESI.md` §5 (faz 9) aynı kararı `ci95` için verdi:
*"Ad sözleşme olduğu için kaldı; yanına gerçek aralık kondu."*

### 5.6 Karar motoru katmanı (FAZ 18)

Planın teşhisi doğru ve depo ona zaten uyuyor: *"`benzer.py` doğrudan bahis
önerisi üretmeye zorlanmamalı."* Modül docstring'i bunu birinci cümlede
söylüyor: *"Bu modül tahmin üretmez."*

Ama planın önerdiği `decision engine` katmanı deponun **ölçülmüş durma
kuralıyla** çatışıyor. `ISTATISTIK_YOL_HARITASI.md` §6.5:

> Kapanış çizgisini yenebiliyor muyuz? — **hayır, ölçüldü.** Arayış kapandı.

`arena.py` on bir ayrı koşumu tek kesitte topladı: **hiçbir aile piyasayı
geçmedi.** Bir karar motoru bu bulgunun üstüne kurulamaz; kurulursa
ölçülmemiş bir üstünlüğü ima eder — ve bu, planın kendi §25 Kural 7'sinin
(*"piyasa farkını otomatik olarak edge kabul etme"*) ihlali olur.

**Hangi koşulda açılır:** §6.5'in dört sorusundan biri "evet"e döndüğünde.

---

## 6. Alınmayan ama kaydedilen

Bunlar reddedilmedi; sıraya girmesi için ölçülmüş bir gerekçe bekliyorlar.

### 6.1 `benzer`in ileri yürüyüş ölçümü (FAZ 4) — sıradaki asıl iş

Cevaplanmamış tek büyük soru: *benzer geçmiş maçların ampirik dağılımı,
kronoloji zorlandığında piyasayı Brier/log-kaybında geçiyor mu?*

§2.3 bunun **ön koşulunu** kurdu; koşumun kendisi yapılmadı çünkü:

- `evaluate.ileri_yuruyus` hafta grupları üzerinde çalışıyor, `benzer` ise
  tek maç sorgusu — bir uyarlama katmanı gerekiyor;
- korpus 4 sezon: eğitim 2122–2223 → sınav 2324, sonra 2324 eklenip 2425.
  İki kat, ve §2.3'te ölçüldüğü gibi yarım korpusta yarıçap zaten
  genişliyor — yani ölçümün kendisi bir örneklem sorusu açıyor.

**Hangi koşulda açılır:** ayrı bir tur olarak, hemen. Baseline
`predict.referans_fabrikalar()`'ın `piyasa` çizgisi. Bu koşum olmadan §5.1 de
açılamaz.

### 6.2 Çizgi ekseni — açılış vs kapanış (FAZ 8)

Korpus iki fiyatı da taşıyor: `acilis_*` (31.099 satır, kaynak `Avg`) ve
`kapanis_*` (`AvgC`). `benzer` her zaman `oranlar`ı kullanıyor ve ölçüldü ki
o **31.103 satırın hepsinde kapanış** fiyatı (`oran_kapanis` = 1,
`oran_kaynak` = `AvgC`).

Yani bu modül bugün sessizce "kapanış çizgisinde bu fiyatı gören maçlar"
sorusuna cevap veriyordu. Bu turda yapılan tek şey **onu yazmak** oldu (modül
docstring'i ve `README.md`); bir `--cizgi` seçeneği eklenmedi.

**Neden:** iki fiyat arasındaki farkın cevabı değiştirip değiştirmediği
ölçülmedi. Ölçülmeden bir seçenek eklemek deponun kuralınca bakım borcudur.
**Hangi koşulda açılır:** §6.1'in koşumu iki çizgide ayrı ayrı sürüldüğünde.

### 6.3 `cli.py` ve `health.py` bağlanması

`benzer` `spor_toto/cli.py`'de alt komut değil ve `health.py` değişmezlerinde
hiç geçmiyor; `check.sh`'in CLI duman testi de onu koşmuyor. Kayda geçiyor;
bir değişmez önermek, önce neyin değişmez olduğunu ölçmeyi gerektirir.

---

## 7. Bu turda değişen ve değişmeyen sayılar

Refactor, öncesi/sonrası karşılaştırılmadan tamamlanmış sayılmaz (planın §20
kabul kriteri, deponun da kuralı).

**Değişen sayı yok.** Dört adımın hiçbiri mevcut bir çıktıyı oynatmadı:

| Sayı | Önce | Sonra |
|---|---:|---:|
| `benzer_maclar(tolerans=0.02, yontem="orantili")` → `n` | 710 (293/184/233) | **aynı** |
| `benzer_maclar(tolerans=0.02)` (shin) → `n` | 241 | **aynı** |
| Kalibrasyon eğrisi | 31.103 maç / 93.309 nokta | **aynı** |

**Eklenen anahtarlar** (hepsi additif, hiçbir anahtar kaldırılmadı):
`as_of`, `evren_kesilen`, `mesafe`. TS tipi ve `api-sozlesme.json` yenilendi.

**Değişen davranışlar** — üçü de bir hatayı hataya çevirdi, hiçbiri geçerli
bir sorguyu bozmadı:

| Girdi | Önce | Sonra |
|---|---|---|
| `oran=inf,3.04,2.44` | çalışır, sayı üretir | `ValueError` |
| `oran=nan,…` | reddedilir, **yanlış mesaj** | `ValueError`, doğru sembolü söyler |
| `--tolerans 0.50` | kabul, bütün korpus "benzer" | `ValueError` |
| `?tolerans=0.9` | sessizce 1,0'a kırpılır, 200 | 400 |
| `?en_az=0` | sessizce 1'e kırpılır, 200 | 400 |
| `?en_az=abc` | varsayılana düşer, 200 | **aynı** (eski sözleşme korundu) |
