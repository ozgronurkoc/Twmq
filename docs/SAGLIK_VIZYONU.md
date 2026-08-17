# Sağlık Sayfası — Vizyon ve Tasarım Kararları

**Sayfa:** `frontend/app/saglik/page.tsx` (`/saglik`)  
**Motor:** `backend/spor_toto/health.py`  
**Uçlar:** `GET /health` (liveness), `GET /api/health` (readiness),
`GET /api/health/checks`  
**Testler:** `backend/tests/test_health.py`, `backend/tests/test_api_health.py`,
`backend/tests/test_meta.py`  

> Bu belge sayfanın **neden** var olduğunu ve hangi kararlarla bugünkü hâlini
> aldığını kaydeder. **Ne yaptığı** README'de, **nasıl çağrıldığı** API
> bölümündedir. Buradaki her sınır ve her "yapmaz" bilinçlidir; sonradan
> değiştirilecekse gerekçesiyle birlikte değiştirilmelidir.

---

## 1. Tek cümlelik vizyon

> **Sağlık sayfası, ürünün vaadinin _şu anda_, _bu makinede_, _bu sürümde_ hâlâ
> geçerli olduğunu kanıtlar.**

Ürünün vaadi tektir ve dar tanımlıdır: *seçim kümesi içinde doğru sonuç varsa,
oynanan kolonlardan en az biri en fazla 1 maç hatalı olur.* Bu vaat
kombinatoryal bir iddiadır — doğruluğu görüşe, piyasaya veya şansa bağlı
değildir. Bağlı olduğu tek şey, çalışan kodun hâlâ o matematiği uygulamasıdır.

Sağlık sayfası bunu her çağrıda yeniden ölçer. Sayfanın varlık sebebi
"sistem ayakta mı" sorusu **değildir**; o soruyu 200 dönen herhangi bir uç
zaten cevaplar. Sorulan soru şudur: **ayakta olan şey hâlâ vaat ettiğimiz şey mi?**

---

## 2. Test yeşilken bu sayfa neden var?

En sık gelen itiraz: "629 test geçiyor, ayrıca çalışma zamanında ne arıyoruz?"

Test ile sağlık kontrolü **aynı iddiayı farklı zaman ve zeminde** sınar:

| | `pytest` | `/api/health` |
|---|---|---|
| **Ne zaman** | Commit anında | Her çağrıda, canlıda |
| **Nerede** | CI makinesinde | Kullanıcıya hizmet eden süreçte |
| **Neyle** | O günkü kilitlenmiş bağımlılıklarla | Kurulu olan gerçek sürümlerle |
| **Neyi kanıtlar** | Kod doğru yazılmış | Çalışan şey hâlâ doğru davranıyor |
| **Kaçırdığı** | Dağıtım, ortam, veri, sürüm kayması | Kodun test edilmemiş yolları |

Aradaki boşluk teorik değildir. Şu senaryoların hiçbirini test yakalamaz:

- **scipy dağıtımda kurulamamış.** CI'da vardı, sunucuda yok. Kod çalışır,
  `exact` modu sessizce kaybolur.
- **numpy majör sürüm atlamış.** Testler eski kilitle geçmiş, dağıtımda yeni
  sürüm gelmiş, kayan nokta davranışı değişmiş.
- **Veri dosyası dağıtıma girmemiş.** `/istatistik` boş döner, motor çalışmaya
  devam eder — hata log'u bile yoktur.
- **Yanlış commit yayınlanmış.** Testler doğru sürümü doğrulamıştır; sunucudaki
  başka bir sürümdür.

### 2.1 Aynı fonksiyon iki yerde koşar — bu tekrar değildir

`tests/test_health.py` doğrudan `run_health()` çağırır; CI adımı da
`python -m spor_toto.health` çalıştırır; canlı uç da aynı fonksiyonu çağırır.
Tek bir kontrol tanımı, üç ayrı soruya cevap verir:

```
CHECKS (tek tanım)
   ├── pytest        → "bu commit doğru mu?"
   ├── CI adımı      → "yayınlanmaya uygun mu?"
   └── GET /api/health → "yayınlanmış olan hâlâ doğru mu?"
```

Kontrol mantığının ikinci bir kopyası **yoktur ve olmamalıdır.** Bir değişmez
iki yerde ayrı ayrı yazılırsa, biri güncellenip diğeri unutulduğu gün ikisi de
değersizleşir.

---

## 3. Ne kanıtlanır, ne kanıtlanmaz

Sayfanın güvenilirliği, neyi kanıtlamadığını açıkça söylemesine bağlıdır.

### 3.1 Kanıtlanan

- 16 satırlık sabit kaplama gerçekten 14-garanti veriyor (en kötü durumda
  hata ≤ 1, açıkta nokta yok).
- Mesafe muhasebesi kapanıyor: 0 ve 1 hatalı noktaların toplamı arama uzayının
  tamamını veriyor.
- Olasılık raporu kendi içinde çelişmiyor (`p15 + p14 = p_küme_içi`).
- Simülasyon ile kesin hesap aynı yeri gösteriyor.
- Bayes kaplamayı değiştirmiyor, yalnızca tahmini yumuşatıyor.
- Seçim **dışı** bölgenin kombinatoryal sınırları geçerli.
- İstatistik ve oran katmanlarının verisi kendi içinde tutarlı.
- API'nin döndürdüğü sonuç sözleşmesi eksiksiz.
- `/api/meta`'nın ilan ettiği envanter kendi içinde tutarlı: her sınırda
  min ≤ varsayılan ≤ max, preset ve mod listeleri motordakiyle aynı.
- İlan edilen **her mod** koşuyor ve `garanti` bayrağı gerçeği söylüyor —
  özellikle `maxcov`'un garanti *vermediği* de kanıtlanıyor.
- Her Bayes preset'i çalışıyor ve hiçbiri kaplamayı bozmuyor.
- Alternatif 16'lık kümeler (`variant`) de 14-garanti veriyor.

### 3.2 Kanıtlanmayan — ve asla kanıtlanmayacak olan

| Kanıtlanmaz | Neden |
|---|---|
| Maç sonucu tahmininin isabeti | Araç tahmin etmez; bu sayfa da etmez |
| Kazanma olasılığının artışı | Garanti maliyeti düşürür, şansı büyütmez |
| **Kullanıcının kendi kuponunun** doğruluğu | Kontroller **sabit bir örnek kupon** üzerinde koşar |
| İkramiye / beklenen değer | Motorun kapsamı dışında |

Üçüncü satır en kritik ve en kolay yanlış anlaşılanıdır. Sağlık raporu
`1,10,1,12,0,10,2,10,1,12,02,1,10,2,10` sabit kuponuyla çalışır (8 çift,
256 nokta, alt sınır 29 kolon). **HEALTHY, kullanıcının az önce ürettiği
kuponun doğrulandığı anlamına gelmez** — motorun o kupon sınıfında doğru
davrandığı anlamına gelir. Kullanıcının kendi sonucu her `/api/solve`
çağrısında `guaranteed` / `worst` / `acik` alanlarıyla ayrıca doğrulanır;
ikisi farklı katmandır ve birbirinin yerine geçmez.

---

## 4. Bir kontrolün taşıması gereken nitelikler

Yeni kontrol eklemek ucuzdur; **kötü** bir kontrol eklemek pahalıdır, çünkü
düşen ilk yanlış alarmdan sonra bütün sayfaya olan güven gider. Sözleşme:

**1. Deterministik olmalı.** Rastgelelik içeren her kontrol sabit tohumla
koşar (`monte_carlo` → `seed=42`, `heuristic` → `seed=42`). Arada bir düşen
bir kontrol, düşmeyen bir kontrolden daha zararlıdır: insanları raporu
görmezden gelmeye eğitir.

**2. Kombinatoryal zorunluluk sınamalı, örnek doğrulamamalı.** İyi kontrol
"bu girdide şu çıktı geldi" demez; "bu **matematiksel olarak** başka türlü
olamaz" der. `fire_scenarios` bunun örneğidir: bir maç işaret dışındaysa
hiçbir kolon 15 tutturamaz — bu kupona bağlı değildir, kırılırsa mesafe
hesabı bozulmuş demektir.

**3. Bütçesine sadık olmalı.** Tüm rapor birkaç yüz milisaniyede bitmeli;
sayfa canlıda, isteğe bağlı olarak da otomatik yenilemeyle çağrılır. Ağır
doğrulamalar (ILP ile optimal kanıtı gibi) `pytest -m slow` işidir, bu
sayfanın değil.

**4. Ne koruduğunu yazmalı.** `aciklama` alanı zorunludur ve testle
denetlenir. Kontrolün adı geliştiriciye yeter; sayfayı okuyan kişiye yetmez.
Açıklama "ne yapıyor" değil, **"kırılırsa ne kaybederiz"** sorusuna cevap
vermelidir.

**5. Ölçtüğü gerçek değerleri döndürmeli.** `detail` alanı "ok" demez;
`rows=16 bedel=32 worst=1` der. Geçen bir kontrolün sayıları, düşen bir
kontrolün hata mesajı kadar değerlidir — sapma ancak böyle görülür.

---

## 5. Kategori modeli — "hangi katman bozuldu?"

Düz bir liste, düşen kontrolün adını söyler; hatanın **nerede** olduğunu
söylemez. Kategoriler motorun katmanlarını izler, böylece rapor doğrudan bir
teşhis konumuna işaret eder:

| Kategori | Katman | Düşerse |
|---|---|---|
| `cekirdek` | Kodlama, 14-garanti, mesafe muhasebesi, varyantlar | **Ürünün ana vaadi geçersiz.** Yayın durdurulur |
| `motor` | Alternatif çözücüler + ilan edilen 7 modun tamamı | Bir mod güvenilmez; fix16 hâlâ ayakta olabilir |
| `olasilik` | Exact, Monte Carlo, Bayes (+ preset'ler), Markov | Sayılar yanlış; garanti hâlâ geçerli olabilir |
| `analiz` | Hata frekansı, fire, veri seti, oran arşivi, geri test | Yorum katmanı bozuk; motor sağlam |
| `ucuca` | `/api/meta` sözleşmesi ve API sonuç sözleşmesi | Arayüz yanlış okuyor olabilir |
| `ortam` | Bağımlılık envanteri | Bir yetenek eksik olabilir |

Bu sıralama tesadüfi değildir: **yukarıdan aşağıya doğru ciddiyet azalır.**
`cekirdek` düşmüşse aşağıdaki her şey şüphelidir. `analiz` düşmüşse çekirdek
hakkında hiçbir şey söylenmiş olmaz.

---

## 6. Kritik / bilgi ayrımı ve DEGRADED durumu

Sayfanın en tartışmalı kararı: **her düşüş 503 değildir.**

Önceki sürümde `scipy_flag` de diğerleriyle aynı listedeydi. scipy'nin
yokluğu servisin çalışmadığı anlamına gelmez — yalnızca kesin çözücü (ILP)
devre dışıdır, motorun geri kalanı sorunsuz çalışır. Ama rapor "UNHEALTHY"
diyordu. Bu, izleme açısından zehirlidir: gerçekten kırmızı olması gereken
durumla, bilinen ve kabul edilmiş bir eksikliği aynı renge boyar.

Bugünkü karar tablosu:

| Durum | Koşul | `ok` | `degraded` | HTTP | Anlamı |
|---|---|---|---|---|---|
| **HEALTHY** | Her şey geçti | `true` | `false` | 200 | Vaat geçerli |
| **DEGRADED** | Yalnızca `critical=False` düştü | `true` | `true` | **200** | Vaat geçerli, bir yetenek eksik |
| **UNHEALTHY** | En az bir kritik düştü | `false` | `false` | 503 | Vaat sorgulanır |

İlke: **HTTP durum kodu "beni trafikten çıkar" demektir, "bir eksiğim var"
demek değildir.** DEGRADED bir süreç isteklere doğru cevap vermeye devam
eder; onu yük dengeleyiciden düşürmek gerçek bir kesinti üretir, oysa ortada
kesinti yoktur.

Bir kontrolün `critical=False` olması **istisnadır ve gerekçe ister.** Ölçüt
tektir: *bu kontrol düşerken, kullanıcının aldığı sonuç hâlâ doğru mu?* Cevap
"evet, yalnızca bir seçenek eksik" ise bilgi amaçlıdır. En ufak tereddütte
kritik olarak işaretlenir.

---

## 6.1 Liveness ile readiness ayrı uçlardır

`/health` ile `/api/health` bir dönem **aynı handler'a** bağlıydı: ikisi de
bütün değişmezleri koşuyordu. Dağıtım hedefi autoscale olduğu için platform
probe'u her vuruşta tam raporun bedelini ödüyordu ve probe zaman aşımına
düşerse platform **sağlıklı** bir konteyneri öldürüyordu — yani sağlık
kontrolünün kendisi kesinti üretebiliyordu.

| Uç | Rol | İçerik | Süre |
|---|---|---|---|
| `/health` | liveness | Süreç ayakta + sürüm + uptime | ~2 ms |
| `/api/health` | readiness / teşhis | Tam rapor | ~500 ms (ilk koşu ~2,2 sn) |

Ayrımın anlamı şudur: **liveness "bu süreci öldür mü?" sorusudur, readiness
"bu sürece trafik ver mi?" sorusu.** Düşen bir değişmez ikinciyi kırmızıya
çevirir; ama süreci öldürmek onu düzeltmez — aynı kod her konteynerde aynı
şekilde düşer, kapatmak yalnızca kesintiyi büyütür.

`/api/health` üstünde kısa bir TTL önbelleği (5 sn, `HEALTH_TTL_S`) vardır;
`?fresh=1` onu atlar ve sayfadaki "yeniden çalıştır" düğmesi bunu kullanır.
Önbellekten dönen gövde bunu **saklamaz**: `summary.onbellek` yaşını yazar,
sayfa da rozetle gösterir. Ne zaman ölçüldüğünü gizleyen bir sağlık raporu
kendini değersizleştirir. Kısmi koşular ayrı kovada tutulur — aynı kovaya
düşselerdi kısmi bir yeşil tam raporun yerine geçerdi.

---

## 7. Kısmi çalıştırma (`?only=`)

Tam rapor ~500 ms sürer. Düşen tek bir kontrolü kovalarken bu her denemede
ödenen bir vergidir ve insanları sayfayı yenilemek yerine tahmin yürütmeye
iter.

`?only=` bir kontrolü veya bütün bir kategoriyi tek başına koşturur. Sayfada
her kategori kartındaki *"Yalnızca bunu çalıştır"* düğmesi budur.

İki tasarım kararı bunu güvenli kılar:

1. **Kısmi rapor kendini açıkça işaretler.** `summary.kismi` true döner ve
   sayfa bunu bir bant olarak gösterir: *"kayıtlı 21 kontrolün 5 tanesi
   çalıştı"*. Kısmi bir yeşil, tam bir yeşil gibi görünemez.
2. **Otomatik yenileme her zaman tam raporu koşar.** Kısmi bir koşuyu arka
   planda tekrarlamak, sayfayı giderek daha az şey doğrulayan bir yeşil
   göstergeye dönüştürürdü.

Bilinmeyen bir kontrol adı 400 döner. Sessizce boş küme koşturmak, "hiçbir
şey düşmedi" diyen bir rapor üretirdi — mümkün olan en kötü yanlış cevap.

---

## 8. Sayfanın okuma sırası

Bilgi mimarisi tek bir varsayım üzerine kurulu: **sayfaya bakan kişinin
aklında bir soru vardır ve cevabı saniyeler içinde istemektedir.**

| Sıra | Blok | Cevapladığı soru |
|---|---|---|
| 1 | Durum kartı | "İyi mi kötü mü?" |
| 2 | Düşenler özeti | "Ne bozuldu?" |
| 3 | Kategori kartları | "Hangi katman, tam olarak ne?" |
| 4 | Çalışma geçmişi | "Sürekli mi, arada bir mi?" |
| 5 | Çalışan ortam | "Hangi sürümlerde?" |

Yalnızca 1. blok her zaman okunur. Geri kalanı, bir öncekinin cevabı
yetmediğinde okunur — bu yüzden ayrıntı aşağı doğru artar, yukarı doğru değil.

**Süre çubuğu** her satırda görünür çünkü performans gerilemesi de bir
gerilemedir. Bir kontrolün 8 ms'den 400 ms'ye çıkması hiçbir değişmezi
kırmaz, ama bir şeyin değiştiğini kesin olarak söyler.

**Çalışma geçmişi** oturum içi tutulur çünkü tek bir yeşil koşu, arada bir
düşen bir kontrol hakkında hiçbir şey söylemez. **Ulaşılamayan koşular da**
bu şeride düşer: zaman çizelgesinde en çok görmek isteyeceğin olay tam odur
ve yalnızca başarılı koşuları kaydeden bir geçmiş "iyi günlerin" kaydına
dönüşür. Kalıcı değildir; kalıcı olması gereken gün, o zaten §10'daki zaman
serisi işidir.

**Sekme başlığı** durumu taşır (`⚠ Sistem sağlığı`). Alarm altyapısı
gerektirmeyen en yakın "haber verme" biçimidir ve bu sayfa arka planda açık
tutulmak için vardır. Aynı sebeple otomatik yenileme sekme gizliyken
**duraklar**: arka planda saatlerce koşan bir sekme, geçmiş şeridini
kimsenin bakmadığı kayıtlarla doldurur.

**Adres durumu taşır** (`/saglik?only=olasilik`): düşen bir kategorinin
bağlantısı paylaşılabilir ve yenilemede kaybolmaz.

---

## 9. Bilinçli sınırlar

Bunlar eksik değil, **kapsam dışı** kararlardır. Değiştirilmeleri gerekirse
gerekçesi bu bölümde güncellenmelidir.

**Sabit örnek kupon.** Kontroller tek bir kupon sınıfını (8 çift, 256 nokta)
kapsar; mod envanteri ayrıca küçük bir sınıfı (7 çift, 128 nokta) kullanır.
Rastgele kupon üretmek kapsamı genişletirdi ama determinizmi bozardı — ve
arada bir düşen bir kontrol, hiç olmamasından kötüdür (§4, madde 1). Geniş
girdi taraması `pytest`'teki fuzz invariant testlerinin işidir.

**Modlar küçük kuponda sınanır.** `mod_envanteri` ILP'yi 128 noktalık bir
uzayda koşturur; örnek kuponda aynı denetim tek başına ~11 saniye sürerdi.
Sınanan şey çözümün kalitesi değil, ilan edilen modun ayakta olması ve
`garanti` bayrağının gerçeği söylemesidir — bu soru uzayın büyüklüğünden
bağımsızdır (§4, madde 3).

**İlk koşu yanıltıcıdır.** Süreç yeni başladığında ilk rapor ~2,1 sn sürer;
sonrakiler ~500 ms. Fark ısınmadır (numpy/scipy ilk import, veri seti ve
oran arşivinin ilk okunması), gerileme değil. Süre eşiğine dayalı bir alarm
kurulacaksa bu hesaba katılmalıdır.

**Sayfa kendini ölçmez.** Rapor motorun sağlığını ölçer; Flask sürecinin
bellek kullanımını, istek gecikmelerini veya hata oranlarını değil. Bunlar
uygulama izleme (APM) işidir ve bu sayfanın işi değildir.

**Alarm yoktur.** Sağlık kırmızıya döndüğünde kimseye haber gitmez; birinin
bakıyor olması gerekir. Bugünkü kullanım için bilinçli bir sadeleştirmedir.

**Tek süreç, tek makine.** Rapor çağrıyı karşılayan süreci anlatır. Çok
örnekli bir dağıtımda "hangi örnek?" sorusu cevapsızdır.

---

## 10. Yol haritası

Sıra, "en çok belirsizliği kaldıran" ölçütüne göredir.

| # | Adım | Çözdüğü sorun |
|---|---|---|
| 1 | **Süre eşikleri** — her kontrole beklenen süre bandı; aşınca `degraded` | Performans gerilemesi bugün yalnızca gözle görülüyor |
| 2 | **Zaman serisi** — son N koşunun sunucuda saklanması (`/api/health/history`) | Geçmiş oturumla sınırlı; sekme kapanınca kayboluyor |
| 3 | **Kullanıcı kuponuyla koşma** — `/api/solve` sonucunu doğrulayan bir mod | Sabit örnek kupon sınırı (§3.2, §9) |
| 4 | **Örnek çeşitliliği** — sabit tohumlu birkaç kupon sınıfı | Tek kupon sınıfı; determinizm korunarak |
| 5 | **CLI'nin de aynı yolu kullanması** — `cli.py` mod dağıtımı `engines.py`'ye | Mod mantığının ikinci kopyası hâlâ CLI'de duruyor |
| 6 | **Alarm bağlantısı** — kırmızıya dönüşte bildirim | Birinin bakıyor olması varsayımı |
| 7 | **Örnek kimliği** — rapora süreç/örnek etiketi | Çok örnekli dağıtımda "hangi örnek?" |

Bilinçli olarak **yapılmayacaklar**: kontrolleri arayüzden düzenlemek
(değişmezler koddadır, yapılandırmada değil), sağlık geçmişini metrik
panosuna dönüştürmek (bu bir APM işidir), tahmin isabetini ölçen bir kontrol
eklemek (§3.2).

---

## 11. Bugünkü referans değerler

Bu tablo bir sözleşme değil, karşılaştırma tabanıdır. Sapma gerekçesiz
olmamalıdır.

| Ölçü | Değer |
|---|---|
| Kayıtlı kontrol | 21 |
| Kategori | 6 |
| Kritik olmayan kontrol | 1 (`scipy_flag`) |
| Tam rapor süresi (ısınmış) | ~500 ms |
| Tam rapor süresi (ilk koşu) | ~2,1 sn |
| Liveness (`/health`) süresi | ~2 ms |
| Readiness önbelleği | 5 sn TTL (`HEALTH_TTL_S`), `?fresh=1` atlar |
| En yavaş kontrol | `mod_envanteri` (~129 ms, 7 mod) |
| Sağlık katmanının test sayısı | 44 |
| Örnek kupon | `1,10,1,12,0,10,2,10,1,12,02,1,10,2,10` |
| Örnek kuponun arama uzayı | 8 çift → 256 nokta, alt sınır 29 kolon |
| Mod envanteri kuponu | 7 çift → 128 nokta, alt sınır 16 kolon |

---

## 12. Kontrol eklerken

```bash
cd backend
python -m spor_toto.health --list             # mevcut envanter
python -m spor_toto.health --only <kategori>  # dar döngüde çalış
```

1. Kontrolü `_check_<ad>()` olarak yaz; ölçtüğü gerçek değerleri döndür.
2. `CHECKS` tablosuna `CheckSpec` olarak ekle — kategori ve açıklama zorunlu.
3. `critical=False` verecekseniz §6'daki ölçütü karşıladığını gerekçelendirin.
4. Rastgelelik varsa tohumu sabitleyin.
5. `pytest tests/test_health.py tests/test_api_health.py tests/test_meta.py`
   çalıştırın.
6. Toplam süreye etkisini ölçün; §11'deki tabanı belirgin biçimde aşıyorsa
   ya kontrolü ucuzlatın ya da `pytest -m slow` tarafına taşıyın.

**Mevcut** bir kategoriye kontrol eklerken arayüz tarafında hiçbir şey
yapılması gerekmez: sayfa kategorileri, açıklamaları ve kritiklik bayrağını
rapordan okur, hiçbirini sabit kodlamaz. Yeni kontrol kendi kategorisinde
kendiliğinden belirir.

**Yeni bir kategori** eklemek tek bir istisnadır: `frontend/lib/types.ts`
içindeki `HealthKategoriId` birleşim tipi de genişletilmelidir. Bu yalnızca
tip düzeyinde bir kısıttır (çalışma zamanı yine de doğru render eder), ama
tip ile motor arasındaki bağı kasten sıkı tutuyoruz — arayüzün backend'i
doğru okuyup okumadığını söyleyen tek mekanizma odur.
