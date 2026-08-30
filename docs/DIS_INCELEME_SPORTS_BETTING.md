# Dış çalışma incelemesi — `georgedouzas/sports-betting`

**Kapsam:** Sabit oranlı bahis için bir **scikit-learn araç kutusunun** bu
projeye ne kattığı ve **ne katmadığı**.
**Tarih:** 2026-08-30 · İncelenen sürüm: `main`, 6.078 satır, MIT, PyPI'da
**İlgili belgeler:** [`DIS_INCELEME.md`](DIS_INCELEME.md) (aynı türün ilki) ·
[`DIS_INCELEME_ALPHAPY.md`](DIS_INCELEME_ALPHAPY.md) (ikincisi) ·
`README.md` §7 · `ISTATISTIK_YOL_HARITASI.md` §3.45 · `VERI_TOPLAMA_VE_ISLEME.md` §6I

> **Künye — bu bizim ölçümümüz değildir.** Aşağıda `sports-betting`in
> **kendi** belgelerinden alınan tek bir sayı yok; deponun README'sindeki
> geri test tablosu (yıllık %22–54 ROI) kendi örnek verisinde, kendi
> ölçütleriyle üretilmiş ve bizim "geçti" ölçütümüzü (güven aralığının
> **tamamı** sıfırın dışında) kullanmıyor. Bu belgedeki bütün sayılar
> **bizim kesitimizde, bizim kurallarımızla** ölçüldü.

---

## 1. Niçin bakıldı, ne çıktı

Soru öncekilerle aynı: *"Bu repoda bize uyarlayabileceğimiz bir şey var mı?"*

Cevap: **model olarak hiçbir şey; bir ölçü, bir kalite kapısı — ve
beklenmedik biçimde, bizim kendi depomuzda dört kusur.**

İlk iki inceleme (`zakariae-boui`, AlphaPy) bir *dış kanıt* ve bir *eksik
ölçü* getirmişti. Bu inceleme bir üçüncü türü getirdi: **onların
disiplinine bakarken bizim kendi kodumuzdaki kusurlar görünür oldu.**
Dördü de bu belgeyle birlikte düzeltildi (§5).

| Ne | Sonuç |
|---|---|
| Değer bahsi getirisi (`deger.py`) | **Alındı, ölçüldü** — üç pazarda da kâr yok |
| Küresel bire-bir eşleştirme | **Alınmadı** — teşhis, dokunacağı hiçbir vaka olmadığını ölçtü |
| Yan pazarlardan 1X2 türetme | **Zaten vardı** (`skor.py`, A6) ve geçmemişti |
| Doctest + `pytest-randomly` + `interrogate` + `pip-audit` | **Alındı** — ilk koşumda dört kusur buldu |
| MCP sunucusu | **Denendi, ölçüt 1'i geçmedi** — yan ürünü kalıcı oldu |

---

## 2. İki depo, iki farklı iş

| | **sports-betting** | **Spor Toto Lab** |
|---|---|---|
| Oyun | **Sabit oranlı** bahis (bahisçiye karşı) | **Müşterek** havuz (kalabalığa karşı) |
| Kazanma koşulu | `p_model > p_piyasa` — piyasayı yenmek | `p_piyasa > oynanma_payı` — piyasayı yenmek **gerekmez** |
| Çıktı | Değer bahsi listesi | 14-garanti **kaplama kodu**, en az kolon |
| Model | Herhangi bir sklearn kestiricisi (`ClassifierBettor`) | Sabit tahminci ailesi + arena |
| Doğrulama | `TimeSeriesSplit` | **Sezon dışarıda bırakmalı** + iç içe CV + eşleştirilmiş bootstrap |
| "Geçti" ölçütü | Tabloda pozitif ROI | Güven aralığının **tamamı** sıfırın dışında |
| Veri | İndirilir (canlı besleme, ücretli oran API'si) | Depoda **sürümlü** (yeniden üretilebilir) |
| Yüzey | Python + CLI + MCP + tarayıcıdan bahis oynatma | Python + CLI + JSON API + Next.js arayüz |

Bu tabloyu okumanın doğru yolu: **iki depo aynı işi farklı yapmıyor, farklı
iş yapıyor.** `getiri.py`nin baştan yazdığı ayrım — `edge = p_piyasa −
oynanma_payı` — onların bütün çerçevesini kupona uygulanamaz kılıyor. Buna
rağmen alınacak bir şey çıktı, çünkü bizim de **sabit oranlı** yan
pazarlarımız var (`/pazarlar`) ve orada onların çerçevesi tam olarak
geçerli.

---

## 3. Alınan: değer bahsi getirisi (`spor_toto/deger.py`)

**Kaynak:** `evaluation/_base.py::BaseBettor.bet` · `::score` ·
`_model_selection.py::_fit_bet` · `_rules.py::OddsComparisonBettor`

### 3.1 Kapatılan boşluk

`pazar.py` alt/üst 2,5 ve Asya handikabını **kalibrasyon** olarak ölçüyordu,
**getiri** olarak ölçmüyordu. Ayrım önemsiz değil: iyi kalibre bir fiyat,
üstüne bahis oynanınca marj kadar kaybettirir. *"Piyasa dürüst mü"* sorusu
soruluydu, *"bu masadan para kalkar mı"* sorusu hiç sorulmamıştı.

### 3.2 Modülün tasarım kilidi — ve niçin bir testle tutuluyor

`p·o > 1` kuralı bir **model olasılığı** ile bir **fiyat** ister. İkisi aynı
sütundan alınırsa kural **hiç ateşlenmez**: ham ima edilen olasılıklar
(`1/o`) 1'den fazlasına toplanır, marj arındırma o fazlalığı geri alır,
dolayısıyla `p·o = 1/(1+marj) < 1` her ayakta.

> Bu satır ilk yazımda **ters** yazılmıştı (*"her ayak değerli görünür"*) ve
> onu düzelten şey `test_ayni_kaynak_HICBIR_ayagi_degerli_yapmaz` oldu.
> Kayda geçiyor: doctest ve bekçi yazmanın değeri tam olarak budur.

Bu yüzden ikisi ayrı kaynaktan gelir ve ayrım arşivde zaten var:

    p  ←  Avg   bütün bahisçilerin ortalaması, marj arındırılmış
    o  ←  Max   her ayakta en iyi fiyat (bir zarf, bir bahisçi değil)

`bahisci.py` `b_Max`in **olasılık olarak okunamayacağını** yazar (toplamı
1'in altında kalır). Doğrudur ve burada engel değil **dayanaktır** — `Max`
bir olasılık değil bir fiyattır. Yöntem literatürde *"Beating the bookies
with their own numbers"* (Kaunitz ve ark., 2017) diye geçer;
`OddsComparisonBettor`ın yaptığı da budur.

### 3.3 Alınan üç ölçü

1. **Değer bahsi kuralı** — `p·o − 1 > alpha`, **ve** karşılıklı dışlayan
   grup içinde yalnızca **en yüksek beklenen getirili tek ayak**. İkinci
   kural olmadan aynı maçın iki ayağına birden oynanır: kendi kendine karşı
   bahis, marjı iki kez ödemek. Bu disiplin bizde hiçbir yerde yazılı
   değildi.
2. **Bahis başına getiri (yield)** — `_fit_bet`in tanımıyla birebir.
3. **Yıllıklandırılmış Sharpe** — `BaseBettor.score`. **Asya handikabında
   özel değeri var:** `pazar.py` AH için Brier'i bilerek hesaplamıyor
   (çizgilerin %53'ü çeyrek, sonuç kesirli bir getiri). Getiri tabanlı bir
   ölçü kesirli sonuçları doğal olarak yutar.

**ROI taşınmadı.** `sports-betting` onu `stake · toplam / init_cash` diye
yazar; bu, `verim`in `n · stake / init_cash` ile çarpımıdır — yeni bilgi
değil, bir **kasa parametresi**. Kasa büyüklüğü seçilerek ROI istenen sayıya
getirilebilir.

### 3.4 Ölçülen sonuç: hiçbir pazarda kâr yok

Yapı `backtest.py` ile aynı üç parçalı: tek strateji · `alpha` taraması ·
**sezon dışarıda bırakmalı** sağlama. Okunacak sayı üçüncüsüdür.

| Pazar | Maç | Bahis | Verim | %95 aralık | Karar |
|---|---:|---:|---:|---|---|
| 1X2 | 1.737 | 190 | +21,36% | [−15,78, +77,73] | kârlı **değil** |
| alt/üst 2,5 | 1.694 | 274 | +0,61% | [−11,52, +13,65] | kârlı **değil** |
| Asya handikabı | 1.694 | 52 | +18,96% | [−6,88, +43,34] | kârlı **değil** |

Üç aralık da sıfırı içeriyor. **On birinci ölçümün yanında on ikincisi:
piyasa yan pazarlarda da yenilmiyor.**

Aralıkların genişliği bir kusur değil stratejinin özelliği: `Max/Avg` açığı
uzun atışlarda en geniştir (bahisçi anlaşmazlığı orada büyür), yani kural
doğal olarak uzun atışa yığılır — 1X2'de seçilen bahislerin **medyan oranı
3,55**.

### 3.5 Yazarken çıkan iki kusur

İkisi de **ölçümden önce yazılı olan** kurallara dayanarak düzeltildi:

- `alpha` seçimi kısıtsızken **kendi gürültüsünü seçiyordu**: `alpha=0,12`
  üç bahisle %1.267 "verim" gösteriyor ve seçim onu seçecek kadar yüksek.
  Kısıt bir ayar değil, `EN_AZ_BAHIS`in zaten yazılı gerekçesinin sonucu
  (*"altında ortalama kendi gürültüsünü ölçer"*).
- `pazar._ah_getiri` bir **kapama oranıdır** (iade 0,5), para getirisi değil
  (iade 0). İkisi ayrı fonksiyon ama çeyrek çizgi bölünmesi tek yerde:
  `pazar.ah_bilesenler` çıkarıldı.

---

## 4. Alınmayan: küresel eşleştirme — teşhis reddetti

**Kaynak:** `sources/_resolver.py::pair_rosters`

Onların eşleştiricisi bizimkinden iki noktada farklı: **bire-bir kısıt** (bir
fikstür ikinci bir bültene verilemez) ve **artık-tek kuralı** (her iki tarafta
tek aday kaldıysa eşik aranmaz). Hedef `build_gecmis_sezon.py`nin elediği 49
haftaydı.

Kod yazılmadan önce teşhis koşuldu (`--teshis`, yeni) ve cevap tek satırdı:

```
mac (elenen haftalar dahil):
     0  ayirt_edilemedi          <- kuresel atamanin dokunabilecegi TEK sinif
    86  aday_yok_esik_alti
   233  aday_yok_uzak
```

**156 haftanın hiçbirinde** pencerede iki adayın birden eşiği geçtiği bir maç
yok; hiçbir fikstür iki bülten maçına atanmıyor. Yani önerilen strateji bu
kesitte **çalışacak bir şey bulamazdı** ve alınmadı.

`build_odds.py` tarafı da aynı biçimde reddedildi: `odds_rapor.json`un 48
eşleşmeyen maçının tamamı **milli takım haftasıdır** (Türkiye–İspanya,
Ukrayna–Fransa …) ve football-data o maçları hiç taşımıyor. Kapsama sorunu,
eşleştirme sorunu değil.

`_resolver.normalize_team_name` de alınmadı ve bu da ölçüldü: bizim
`sadelestir` aynı örneklerde **1,000** veriyor
(`ÜMRANİYESPOR↔Umraniyespor`, `ADANA DEMİRSPOR A.Ş↔Adana Demirspor`,
`FENERBAHÇE AŞ↔Fenerbahce`).

> **Ama teşhis başka bir şey buldu** — ve o gerçek bir kusurdu. §5.1.

---

## 5. Beklenmedik sonuç: incelemenin bulduğu dört kusur

Bu bölüm incelemenin asıl getirisidir. Dördü de **bizim** kodumuzda ve
hiçbiri `sports-betting`den kopyalanmadı; onların disiplinini uygularken
görünür oldular.

### 5.1 Türkçe noktalı `İ`, sözlüğün bir bölümünü sessizce öldürmüştü

```
"MARSILYA".lower()  ->  "marsilya"                  sozlukte VAR
"MARSİLYA".lower()  ->  "marsi" + U+0307 + "lya"    sozlukte YOK
```

İkisi ekranda aynı görünür. `BULTEN_ESLERI`nin anahtarları düz ASCII olduğu
için, bülten yazımında `İ` geçen her satır **hiçbir zaman çalışmadı** —
`marsilya`, `sporting lizbon`, `milano`. Bülten **büyük harfli bir
görselden** OCR ile okunduğu için `İ` orada kural dışı değil **normal
hâldir**: kusur, sözlüğe en çok ihtiyaç duyulan yerde vuruyordu.

Üç düzeltme, her biri ayrı ölçüldü:

| Düzeltme | Kabul edilen hafta |
|---|---|
| (başlangıç) | 107 |
| Unicode birleşen işaret temizliği | **110** |
| OCR `/` sütun ayracı artığı | **112** |
| teşhiste doğrulanan 7 sözlük satırı | **112** |

Katkı tamamen **eklemeli**: 5 yeni hafta, kaybolan hafta yok, değişen 1/0/2
dizisi yok. Çapraz doğrulama gerilemedi, **güçlendi** — ortak hafta 29→31,
birebir aynı 28→30; ayrışan yine tek ve aynı bilinen kupon sırası vakası.

Kupon × korpus kesişimi yeniden ölçüldü: **1.155/1.605 → 1.200/1.680.**

### 5.2 `/api/health` önbellek testi bir duvar saati kırılganlığıydı

`pytest-randomly` ilk koşumda düşürdü. Kusur sıralamada değil
**varsayımdaydı**: test üretim TTL'ine (5 sn) yaslanıyordu, oysa 27
değişmezin ölçümü tek başına **2,1 sn** sürüyor ve süit `-n auto` koştuğu
için yük altında bu rahatça 5 sn'yi aşıyor. Aşınca ikinci çağrı taze ölçüm
yapıyor ve test *"önbellek çalışmıyor"* diye düşüyordu — oysa çalışıyordu.
Ölçülen şey önbellek **politikası** olmalı, ölçümün hızı değil.

### 5.3 İki docstring sayısı yanlıştı

Doctest kapısı iş başı yapar yapmaz: `wilson(40, 41)` için yazılan 0,8724
gerçekte **0,874**; `deger.sec` eşitlikte **ilk** ayağı seçiyor, belgede
ikincisi yazılıydı. İkisi de bu incelemede yazılmış satırlardı — yani kapı
mürekkep kurumadan işe yaradı.

### 5.4 Servis kökünün uç envanteri eskimişti

MCP deneyinin envanter denetimi buldu: `/api/pazar` ve `/api/takimlar`
aylardır kayıtlı, çalışır ve `replit.md`de yazılıyken servis kökünün
`endpoints` listesinde **yoktu** — liste elle yazılıydı. Artık
`web_app.uc_envanteri()` ile Flask'ın kayıt tablosundan türüyor.

**Genel ders:** bir envanter elle tutulduğu sürece, onu okuyan her yüzey
eksik bir dünya görür.

---

## 6. Zaten vardı: yan pazarlardan 1X2 türetme

Planın bir maddesi *"yan pazarlar 1X2 tahmin yoluna hiç girmiyor"* diyordu.
**Yanlıştı** ve düzeltmesi kayda geçiyor: `skor.py` (A6) bunu zaten yapıyor
— alt/üst 2,5 → `μ`, Asya handikabı → `δ`, oradan skor dağılımı ve 1X2.
İlk grep `egitim/predict/dixon_coles/recalibrate` dosyalarına bakmıştı ve
`skor.py`yi atlamıştı.

Dahası, `skor.py` bunu **ölçmüş** ve sonuç negatif:

    turet+düzeltme  −0,000063  %95 [−0,000287, +0,000155]  geçmedi
    50/50 karışım   −0,000107  %95 [−0,000223, +0,0000038] geçmedi

31.101 maç, 183 hafta, sezon dışarıda bırakmalı, on ayrı bootstrap tohumu.

Geriye **tek bir denenmemiş varyant** kalıyor ve adıyla kayda geçiyor:
türetilmiş olasılığın 1X2 fiyatından **ayrışma büyüklüğü**
(`|p_skor − p_1X2|`) bir **sıcaklık** değişkeni olarak
`recalibrate.KADEMELER`e girmedi. Ayrım `bahisci.py`nin ayrımıdır:
*"anlaşmazlık yön değil sıcaklık sorusudur"*; orada bahisçiler arası, burada
pazarlar arası. Denenmemesinin sebebi kapsam: `egitim_korpus.csv` alt/üst ve
AH fiyatlarını **taşımıyor**, yani `build_egitim.py`ye iki sütun grubu
eklenip korpusun yeniden inşası gerekir. Ayrı bir iştir.

---

## 7. Denendi ve geçmedi: MCP sunucusu

Dört ölçüt **sonuç görülmeden** yazıldı.

| # | Ölçüt | Sonuç |
|---|---|---|
| 2 | Sözleşmeyi bölmüyor | **GEÇTİ** — `--envanter` `saglam: true` |
| 3 | Kapıyı yavaşlatmıyor | **GEÇTİ** — import 0,05 sn |
| 4 | Üretimi taşımıyor | **GEÇTİ** — `run_prod.sh` / `.replit` değişmedi |
| 1 | Yeni yetenek getiriyor | **GEÇMEDİ** |

Beş adımlı zincir kuruldu ve çalıştı (yetenekler → tahmin → 2.000 kolon
bütçeli kupon → geri test → kuponun kendi doğrulama ucundan geçmesi; tek
süreçte, ağsız, 44,7 sn, hepsi HTTP 200). Ama **her adım zaten bir uçtur** ve
hepsi `curl` ile erişilebilir. Kazanç gerçek fakat **ergonomiktir**: ajan
uçları kendi keşfeder, sunucu ayağa kaldırmak gerekmez, zincir kabuk
istemez. Bu bir *yetenek* değil bir *kolaylıktır*.

Modül depoda duruyor ve kendi başlığında bunu yazıyor; durması bir karar
değil, kullanıcının görmesi içindir.

**Tasarım kilidi kayda değer.** `/api/solve`ın parametre çevirisi Flask
işleyicisinin **içinde**, `cli.py`nin kendi çevirisi ayrıca var. Üçüncü bir
yüzey üçüncü bir çevirici demekti ve o an `/api/meta` tek kaynak olmaktan
çıkardı. Sunucu bu yüzden `test_client` kullanıyor: süreç içi, ağsız, ama
gövde ve doğrulama **tek**.

> **Onların kendi pini bugün kırık.** `sports-betting` `mcp>=1.2` yazıyor ve
> `from mcp.server.fastmcp import FastMCP` ile çağırıyor; `mcp` 2.x'te
> `FastMCP` **`MCPServer` oldu**, yani bugün temiz bir ortama kurulunca
> kendi MCP sunucusu `ModuleNotFoundError` veriyor. Biz 2.x API'siyle yazdık.

---

## 8. Alınan: kalite kapısı

| Araç | Ne yakalar | Sonuç |
|---|---|---|
| `--doctest-modules` | Belgelerdeki **sayılar** eskiyor mu | İki yanlış sayı buldu (§5.3) |
| `pytest-randomly` | Testler arası gizli varsayım | Bir kırılganlık buldu (§5.2) |
| `interrogate` | Docstring kapsaması | Taban %75 (ölçülen %76,2) |
| `pip-audit` | Bağımlılık açıkları | Beyan edilen bağımlılıklar temiz |

Doctest **tamamına değil, sayı üreten fonksiyonlara** konuldu:
`ortak.wilson/brier/bant_adi/favori_dilimi`, `getiri.pay_beklentisi`,
`takim.h2h_tablosu`, `deger.sec`. `getiri`nin `q → 0` limiti örnek olarak
öğretici bir hâl aldı — naif ve kararlı form yan yana koşuyor ve naif formun
dördüncü hanede **aşağı doğru** yanıldığı artık yürütülebilir.

`pip-audit` **beyan edilen** bağımlılıkları denetler, bütün ortamı değil:
çıplak koşunca dört bulgu çıkıyor (`setuptools`, `urllib3`, `wheel`,
`pyjwt`) ve dördü de **taban imajdan** geliyor; hiçbiri `pyproject.toml`de
yazılı değil ve projenin sürüm seçme yetkisi yok. Böyle bir kapı ya sürekli
kırmızı durur ya da susturulur. `scripts/bagimliliklar.py` bu ayrımı yapıyor
— `sports-betting`in `noxfile.py`ı da aynısını yapıyor.

`bandit` **alınmadı**: ruff'in `select` listesi zaten `S` (flake8-bandit)
kurallarını koşuyor.

`interrogate` eşiği önce **90 yazıldı ve bu bir tahmindi**; kapı onu hemen
düşürdü (gerçek %75,9). Ölçüldü, sonra biraz altına konuldu. Kendi kuralımızı
(*"eşik ölçüm sonucuna bakılmadan değil, ölçülerek konur"*) ihlal eden bir
satırı yine ölçüm düzeltti.

---

## 9. Alınmayanlar ve gerekçeleri

| Onlarda | Niçin alınmadı |
|---|---|
| `ClassifierBettor` · `BettorGridSearchCV` | `arama.SezonKatlayici` iç içe **sezon** CV'si kuruyor; onların iç halkası `TimeSeriesSplit`. `agac.py`/`yigin.py` model tarafını zaten kapsıyor |
| `cloudpickle` ile model kaydı | `artefakt.py` modeli **JSON** zarfında, korpus sha256 + eğitim tarihi + sürümle saklıyor ve bayatlığı `health`te kırmızı yapıyor. Pickle hem güvensiz hem denetlenemez — geri adım olurdu |
| `--model models.py:bettor` | Kullanıcının verdiği Python dosyasını `exec` etmek. Yüzeyimiz web; kabul edilemez |
| `pandera` şemaları | `health.py`nin 27 değişmezi + `api_sozlesme.py` aynı işi bağımlılıksız yapıyor |
| `execution/` (tarayıcıdan bahis) | Spor Toto müşterek ve bayi/uygulama üzerinden oynanıyor; API yok. Kendi README'leri de bunun bahisçi şartlarını ihlal ettiğini yazıyor |
| `sources/` sağlayıcı soyutlaması | İki beslememiz var ve ikisi de depoda sürümlü. Soyutlama boş bir kat olurdu |
| Kelly / kasa yönetimi | `getiri.py` niçin yanlış alet olduğunu zaten yazıyor: havuzda ödeme kaç kolonun tutturduğuna bağlıdır |
| `_resolver` (eşleştirme + normalizasyon) | Ölçüldü, dokunacağı vaka yok (§4) |
| `find_betting_moment` | Aranan boşluk yoktu: `/api/tahmin` **açılış** oranı kullanıyor, ekranda yazıyor ve A1 farkını (Brier 0,5964 ↔ 0,5940) ölçmüş hâlde taşıyor |
| `CHANGELOG.md` (53 KB) | `README.md` §-numaralı kayıt aynı işi gerekçeleriyle yapıyor; ikinci bir kronoloji ayrışırdı |
| `bandit` | ruff `S` kurallarını zaten koşuyor |

---

## 10. Özet

Depo bize **bir ölçü** (`deger.py`) ve **bir kalite kapısı** kattı; model
tarafında hiçbir şey katmadı ve katmaması bekleniyordu — iki depo farklı oyun
oynuyor.

Asıl getirisi bu değil. İnceleme, kendi kodumuzda **dört kusur** bulmamızı
sağladı: sessizce ölü bir sözlük (5 hafta kayıp), gizli bir duvar saati
kırılganlığı, iki yanlış docstring sayısı ve eskimiş bir uç envanteri.
Hiçbiri `sports-betting`den kopyalanmadı; hepsi onların disiplinini kendi
depomuza uygularken görünür oldu.

Ve bir kez daha, en önemli sonuç bir **hayır**: yan pazarlarda da kâr yok
(§3.4), önerilen eşleştirme stratejisinin dokunacağı bir vaka yok (§4), MCP
yeni bir yetenek getirmiyor (§7). Üçünün de sayısı var.
