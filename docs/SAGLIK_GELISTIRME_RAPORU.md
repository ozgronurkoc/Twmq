# Sağlık Katmanı — Çalışma Raporu ve Yol Haritası

**Tarih:** 2026-08-17 (önceki tur: 2026-08-16)
**Dal:** `claude/dosyalari-gelistirme-vy2py4`
**Kapsam:** `/saglik` sayfası, `spor_toto/health.py`, `spor_toto/meta.py`,
`spor_toto/engines.py`, `/health` + `/api/health*` uçları

> Bu belge iki şeyi bir arada tutar: **bugün ne yapıldığı** (§1–§6) ve
> **bundan sonra ne yapılacağı** (§7–§9). Kararların *gerekçesi*
> `SAGLIK_VIZYONU.md`'dedir; burası yapılan işin ve bekleyen işin dökümüdür.

---

## 0. Özet

Bu tur, bir önceki turun yol haritasındaki **önerilen sıradaki üç işi**
(§9: 7.1 → 7.2+7.3 → 7.9+7.6+7.7) ve yanlarındaki ucuz kazançları
(7.4, 7.5, 7.8, 7.14–7.18) kapattı.

| | Öncesi | Sonrası |
|---|---|---|
| Kontrol sayısı | 17 | **21** |
| İlan edilip sınanmayan mod | 4 (`auto`, `exact`, `butce`, `maxcov`) | **0** |
| `/api/meta` sözleşmesi | doğrulanmıyordu | **`meta_sozlesmesi` kontrolü** |
| Bayes preset'leri | yalnızca `dengeli` koşuyordu | **5'i de koşuyor** |
| `variant` parametresi | hiç koşmuyordu | **1..3 koşuyor** |
| `/health` | `/api/health` ile aynı handler (~500 ms) | **liveness, ~2 ms** |
| Readiness önbelleği | yok | **5 sn TTL + `?fresh=1`** |
| Düşen kontrolün detayı | `AssertionError:` | **`… @ health.py:246`** |
| Oto yenilemede iptal | yok | **her çağrı öncekini iptal eder** |
| Ulaşılamayan koşu | geçmişe düşmüyordu | **kırmızı "ulaşılamadı" kaydı** |
| Sekme gizliyken yenileme | sürüyordu | **duraklıyor** |
| Durum adreste / sekme başlığında | yok | **`?only=` + `⚠ Sistem sağlığı`** |
| Sağlık katmanının testi | 23 | **44** |
| Tüm süit | 608 | **629** |

Üç commit. Isınmış tam rapor 370 ms → **500 ms** (yeni kapsamın bedeli;
en yavaş kontrol artık `mod_envanteri`, ~129 ms).

---

## 1. Tek kaynak: `meta.py` ve `engines.py`

`/api/meta`'nın ilan ettiği envanter (modlar, motor varsayılanları,
sınırlar) `web_app.py` içindeydi ve sağlık katmanı ona **erişemiyordu**:
web_app zaten `health`i import ediyor, ters yön dairesel olurdu. Kapsam
boşluğunun sebebi buydu — teşhis değil, yapı.

**`spor_toto/meta.py`** — `MODES`, `MODE_IDS`, `ENGINE_DEFAULTS`, `LIMITS`,
`MATCH_COUNT`, MC/fire sabitleri ve `meta_payload()`. `/api/meta` artık
yalnızca bunu `jsonify` eder; `_engine_params()` de parametre bantlarını
`LIMITS`'ten okur, böylece arayüzün gördüğü bant ile uygulanan bant
ayrışamaz.

**`spor_toto/engines.py`** — mod çalıştırıcıları (`_run_*` → `run_*`).
`/api/solve` ve sağlık **aynı kodu** koşturur. İkinci bir kopya, biri
güncellenip diğeri unutulduğu gün ikisini de değersizleştirirdi (§8).
`butce` modunun kupon daraltma mantığı da `run_butce()` içine alındı ve
uygulanan planın yeni `Encoder`'ını döndürüyor.

---

## 2. Dört yeni kontrol (17 → 21)

| Kontrol | Kategori | Bağladığı değişmez |
|---|---|---|
| `meta_sozlesmesi` | `ucuca` | Her sınırda `min ≤ varsayılan ≤ max`; preset ve mod listeleri motordakiyle aynı; `has_scipy` gerçekle aynı; `match_count` motor ve veri katmanıyla aynı |
| `mod_envanteri` | `motor` | İlan edilen 7 modun hepsi koşuyor; `garanti: True` olan açık nokta bırakmıyor, `garanti: False` olan `maxcov` gerçekten kaplamıyor |
| `bayes_presetleri` | `olasilik` | 5 preset'in de posterior'ları 1'e toplanıyor ve hiçbiri kaplamayı bozmuyor |
| `fix16_varyantlari` | `cekirdek` | `variant` 1..3 de 16 satır ve 14-garanti veriyor, en az biri kanonikten farklı |

**`mod_envanteri` neden küçük kuponda koşar.** Örnek kuponda (256 nokta)
ILP tek başına ~11 saniye sürüyor; kontrol 7 çiftli, 128 noktalık bir kupon
kullanıyor. Ölçülen şey çözümün kalitesi değil, modun ayakta olması ve
bayrağının doğru olmasıdır — bu soru uzayın büyüklüğünden bağımsızdır.

**`maxcov` için kanıt kombinatoryaldır.** Bütçe (8 kolon) alt sınırın (16)
altında seçilir: tam kaplama matematiksel olarak imkânsızdır. Yani kontrol
"bu girdide böyle çıktı" demez, "başka türlü olamaz" der (§4, madde 2).
Bayrak ile davranış ayrışırsa kullanıcı **garanti sandığı** bir kupon oynar.

---

## 3. `/health` ile `/api/health` ayrıldı

İkisi aynı handler'a bağlıydı: `/health`e vuran her şey tam raporun bedelini
ödüyordu (açılış bekleme döngüleri, konteyner içi yoklamalar, `/health`i
canlılık sinyali sanan her izleme).

**Ölçüldü:** bugünkü dağıtımda dışarıya açılan tek port Next.js'tir ve
`next.config.mjs` yalnızca `/api/*`'ı proxy'ler — yani platform probe'u
Flask'ın `/health`ine şu an ulaşmıyor. Yol haritasındaki 7.1 maddesi bu
noktada bir varsayım içeriyordu. Risk yine de gerçek ama **gizli**: dağıtım
hedefi autoscale, ve Flask portu bir probe'a bağlandığı gün sağlıklı bir
konteyner yalnızca rapor yavaş diye öldürülebilirdi.

| Uç | Rol | İçerik | Ölçülen süre |
|---|---|---|---|
| `/health` | liveness | Süreç + sürüm + uptime | **~2 ms** |
| `/api/health` | readiness | Tam rapor | ~500 ms (ilk koşu ~2,2 sn) |

Ayrımın anlamı: liveness "bu süreci öldür mü?", readiness "bu sürece trafik
ver mi?" sorusudur. Düşen bir değişmez ikinciyi kırmızıya çevirir; ama
süreci öldürmek onu düzeltmez — aynı kod her konteynerde aynı şekilde düşer.

Üstüne **5 sn TTL önbellek** (`HEALTH_TTL_S`), `?fresh=1` ile atlanır.
Önbellekten dönen gövde bunu saklamaz: `summary.onbellek` yaşını yazar,
sayfa rozetle gösterir. Kısmi koşular ayrı kovada tutulur — aynı kovaya
düşselerdi kısmi bir yeşil tam raporun yerine geçerdi.

Açılış bekleme döngüleri (`run_next_dev.sh`, `run_prod.sh`) artık
`/health`'e bakıyor: readiness bir değişmez düştüğünde 503 döndüğü için
"API ayağa kalkmadı" gibi görünüyordu.

---

## 4. Düşen kontrol artık nerede kırıldığını söylüyor

`_run` istisnayı `f"{type(e).__name__}: {e}"` diye yassıltıyordu; assert'ler
çoğunlukla mesajsız olduğu için canlıda düşen bir kontrol yalnızca
`AssertionError:` yazıyordu. Traceback'in **son karesi** eklendi:

```
AssertionError: BILEREK KIRILDI @ health.py:246
```

---

## 5. Arayüz

**Doğruluk (7.6–7.8):**

- **Otomatik yenilemede iptal.** `setInterval(() => void yukle(null))`
  `AbortSignal` almıyordu; kısmi bir koşu ile arka plandaki tam koşu
  çakışırsa cevaplar **geliş** sırasına göre yazılıyordu. Artık tek bir
  `AbortController` ref'i her yeni çağrıda öncekini iptal ediyor.
- **Hata da bir kayıttır.** `setGecmis` `try` bloğunun içindeydi;
  ulaşılamayan koşu geçmişe hiç düşmüyordu — oysa zaman çizelgesinde en çok
  görmek isteyeceğin olay tam odur. Artık kesik çerçeveli, kırmızı
  "ulaşılamadı" kaydı giriyor.
- **Sekme gizliyken duraklama.** `visibilitychange` ile duruyor, sekme geri
  geldiğinde bir kez koşuyor.

**Tanılama (7.14–7.18):**

- Durum adrese yansıyor (`/saglik?only=olasilik`) ve açılışta okunuyor.
- Sekme başlığı durumu taşıyor (`⚠` / `✗`).
- Durum kartı `aria-live` — otomatik yenilemede HEALTHY→UNHEALTHY geçişi
  ekran okuyucuya sessizdi.
- Düşenler özetindeki ad ilgili kategori kartına atlıyor.
- "Kategori" istatistiği (hiç değişmiyordu) yerine **en yavaş kontrol**.
- Önbellekten gelen rapor rozetle işaretleniyor; düğmeler `?fresh=1` gönderiyor.

---

## 6. Testler ve doğrulama

**44 test** (öncesi 23). Tüm süit: **629 test**.

| Dosya | Test | Konu |
|---|---|---|
| `tests/test_health.py` | 19 | Rapor şekli, kategori bütünlüğü, `only` süzgeci, ortam, **kırılma yeri**, **yeni kapsamın kayıtlı olması** |
| `tests/test_api_health.py` | 11 | Gövde sözleşmesi, `?only=`, 400, **liveness/readiness ayrımı**, **önbellek** |
| `tests/test_meta.py` (yeni) | 14 | Envanter tutarlılığı, mod çalıştırıcıları, `maxcov`'un garanti vermemesi, **her modun `/api/solve` ile koşabilmesi** |

Testlere ek olarak uygulama ayağa kaldırıldı ve Playwright ile sürüldü:

- Sağlıklı durum, açık ve koyu tema, konsol hatası yok.
- **Bilerek kırılmış durum** (bir kritik + bir bilgi kontrolü düşürülerek):
  kritik kırmızı ve detayında `@ health.py:246`, bilgi amaçlı amber,
  `/api/health` 503 dönerken `/health` 200 kalıyor, sayfa raporu göstermeye
  devam ediyor, sekme başlığı `✗`. Kırma sonrası kod geri alındı.
- **Ağ kesik** durumda geçmiş şeridine "ulaşılamadı" kaydı düşüyor.
- Kısmi koşu, paylaşılan `?only=` bağlantısı, tam rapora dönüş, özetten
  karta atlama.

`tsc --noEmit`, `npm run check` (37 denetim) ve `next build` temiz.

---

## 7. Yol haritası — öncelik sırasıyla

Efor kabaca: **S** = birkaç saat, **M** = yarım–bir gün, **L** = birkaç gün.

### Öncelik 1 — Teşhis gücü

#### 7.1 Süre eşikleri `[M]`

Her `CheckSpec`'e beklenen süre bandı. Aşınca kontrol **düşmesin** ama
`degraded` işaretlensin ve süre çubuğu ambere dönsün. Bugün performans
gerilemesi yalnızca gözle yakalanıyor.

> Isınma farkı (ilk koşu ~2,1 sn, sonrakiler ~500 ms) hesaba katılmalı;
> yoksa her soğuk başlangıç yanlış alarm üretir. Önbellek kararı netleştiği
> için bu iş artık serbest.

#### 7.2 Sunucu tarafı zaman serisi `[M]`

Son N raporun özeti (`ok`, `passed`, süre, düşen adlar) bellekte halka
tamponda tutulsun, `GET /api/health/history` ile verilsin. Bugün
cevaplanamayan soruyu açar: **"ne zamandan beri kırmızı?"** Oturum içi
geçmiş sekme kapanınca gidiyor.

### Öncelik 2 — Kalan kopya

#### 7.3 CLI de `engines.py`'yi kullansın `[M]`

`spor_toto/cli.py` kendi mod dağıtımını taşıyor (`--mode auto/exact/butce/
maxcov`). API ve sağlık tek yolda birleşti, CLI hâlâ ayrı. Davranış farkları
var (`--mode exact` `exact_limit`i yok sayıyor), bu yüzden taşıma dikkatli
yapılmalı ve `test_cli.py` genişletilmeli.

### Öncelik 3 — Kapsam

#### 7.4 Kullanıcı kuponuyla koşma `[L]`

Rapor **sabit** örnek kupon üzerinde koşuyor; HEALTHY, kullanıcının kendi
kuponunun doğrulandığı anlamına gelmiyor. `/api/solve` sonucunu aynı
değişmezlerden geçiren bir mod bu boşluğu kapatır.

#### 7.5 Örnek çeşitliliği `[M]`

Bugün iki kupon sınıfı kapsanıyor (8 çift/256 nokta; mod envanteri için
7 çift/128 nokta). Sabit tohumlu birkaç sınıf daha (çok bankolu, üçlü
içeren) determinizmi bozmadan kapsamı genişletir.

#### 7.6 `/api/stats` ve `/api/backtest` sözleşmeleri `[S]`

`veri_seti` ve `oran_arsivi` veri katmanını doğruluyor, `geri_test` boru
hattını; ama uçların **gövde şekli** (arayüzün okuduğu alanlar) sınanmıyor.
`meta_sozlesmesi` ile aynı sınıftan ucuz bir kontrol.

### Öncelik 4 — Operasyon

#### 7.7 Alarm bağlantısı `[M]`

Sağlık kırmızıya döndüğünde kimseye haber gitmiyor; birinin bakıyor olması
gerekiyor. Sekme başlığı (§5) bunun en yakın vekili, ama yerine geçmez.

#### 7.8 Örnek kimliği `[S]`

Rapor, çağrıyı karşılayan süreci anlatıyor. Çok örnekli bir dağıtımda "hangi
örnek?" sorusu cevapsız. Rapora süreç/örnek etiketi eklenmeli.

#### 7.9 Liveness dışarıdan erişilemiyor `[S]`

`next.config.mjs` yalnızca `/api/*`'ı Flask'a proxy'ler; `/health` konteyner
dışından çağrılamıyor. Bugün buna ihtiyaç yok (platform Next.js'i yokluyor),
ama liveness'ın var olup ulaşılamaz olması yarım bir çözümdür. İki seçenek:
`/health` için de bir rewrite eklemek, ya da Next tarafına kendi liveness
route'unu koymak. Karar, probe'un hangi süreci sorguladığına bağlı — ikisi
farklı sorulardır ve ikisinin de cevabı gerekebilir.

#### 7.10 Önbellek süreç başınadır `[bilgi]`

Prod'da gunicorn 2 worker ile koşuyor; TTL önbelleği her worker'da ayrıdır.
Zararsızdır (en kötü ihtimalle rapor iki kez koşar) ama §9'daki "tek süreç,
tek makine" sınırının bir başka yüzüdür ve zaman serisi (7.2) yazılırken
hesaba katılmalıdır — bellekte tutulan bir halka tampon, worker'lar arasında
bölünür.

#### 7.11 `auto` modunun süresi `[S]`

Ölçüm sırasında görüldü: `auto`, 256 noktalık örnek kuponda ILP'yi devreye
sokuyor ve **~11 saniye** sürüyor (`exact_limit` varsayılanı 512). Sağlık
bunu küçük kuponda koştuğu için yakalamaz; kullanıcı tarafında ise
"otomatik" modu en yavaş mod hâline getirir. `exact_limit` varsayılanı ya
düşürülmeli ya da ILP'ye ayrı bir zaman sınırı verilmeli.

---

## 8. Bilinçli olarak yapılmayacaklar

| Yapılmayacak | Neden |
|---|---|
| Kontrolleri arayüzden düzenlemek | Değişmezler koddadır, yapılandırmada değil |
| Sağlığı metrik panosuna dönüştürmek | Bu bir APM işidir; sayfa vaadin kanıtıdır |
| Tahmin isabetini ölçen kontrol | Araç tahmin etmez; bu sayfa da etmez |
| Kontrol mantığının ikinci kopyası | Biri güncellenip diğeri unutulduğu gün ikisi de değersizleşir |
| Liveness'ın değişmez koşması | Probe'u tam rapora bağlamak, sağlıklı konteyneri öldürtür |

---

## 9. Önerilen sıradaki üç iş

1. **7.1 + 7.2** — süre eşikleri ve sunucu tarafı zaman serisi. İkisi de
   "ne zamandan beri" sorusunu açar; önbellek kararı netleştiği için artık
   sırası geldi.
2. **7.11** — ölçülmüş, somut ve kullanıcıya doğrudan çarpan tek performans
   sorunu (`auto` modu ~11 sn); birkaç saatlik iş.
3. **7.3** — mod mantığının kalan kopyasını da tek yola bağlar.

---

## 10. Bugünkü referans değerler

Bu tablo bir sözleşme değil, karşılaştırma tabanıdır.

| Ölçü | Değer |
|---|---|
| Kayıtlı kontrol | 21 |
| Kategori | 6 |
| Kritik olmayan kontrol | 1 (`scipy_flag`) |
| Tam rapor süresi (ısınmış) | ~500 ms |
| Tam rapor süresi (ilk koşu) | ~2,1 sn |
| Liveness (`/health`) süresi | ~2 ms |
| Readiness önbelleği | 5 sn TTL, `?fresh=1` atlar |
| En yavaş kontrol | `mod_envanteri` (~129 ms, 7 mod) |
| Sağlık katmanının testi | 44 |
| Tüm süit | 629 test, ~80 sn |
| Örnek kupon | `1,10,1,12,0,10,2,10,1,12,02,1,10,2,10` |
| Örnek kuponun uzayı | 8 çift → 256 nokta, alt sınır 29 kolon |
| Mod envanteri kuponu | 7 çift → 128 nokta, alt sınır 16 kolon |

---

## 11. İlgili belgeler

| Belge | İçerik |
|---|---|
| `docs/SAGLIK_VIZYONU.md` | Sağlık katmanının **neden**i, tasarım kararları, kontrol yazma sözleşmesi |
| `docs/ARCHITECTURE_NEXT.md` | Backend/frontend ayrımı, uç listesi |
| `README.md` | Kullanım, API, health CLI |
| `backend/README.md` | Backend kurulum ve komutlar |
