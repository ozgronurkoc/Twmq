# Sağlık Katmanı — Çalışma Raporu ve Yol Haritası

**Tarih:** 2026-08-17 (önceki turlar: 2026-08-16, aynı gün ilk tur)
**Dal:** `claude/dosyalari-gelistirme-vy2py4`
**Kapsam:** `/saglik` sayfası, `spor_toto/health.py`, `health_history.py`,
`meta.py`, `engines.py`, `payloads.py`, `/health` + `/api/health*` uçları

> Bu belge iki şeyi bir arada tutar: **bugün ne yapıldığı** (§1–§8) ve
> **bundan sonra ne yapılacağı** (§9–§11). Kararların *gerekçesi*
> `SAGLIK_VIZYONU.md`'dedir; burası yapılan işin ve bekleyen işin dökümüdür.
> İkisi ayrışırsa vizyon belgesi asıldır: burada yazan her madde onun
> koyduğu sınırların içinde kalmalıdır.

---

## 0. Özet

Bu turda önceki yol haritasının **tamamı** kapatıldı: önce önerilen sıradaki
üç iş (liveness/readiness ayrımı, meta + mod kapsamı, teşhis düzeltmeleri),
ardından bilerek ertelenmiş olan geri kalan maddeler (süre eşikleri, zaman
serisi, kullanıcı kuponu, örnek çeşitliliği, alarm, örnek kimliği, CLI'nin
tek yola bağlanması, `auto` modunun süresi).

| | Tur başı | Bugün |
|---|---|---|
| Kontrol sayısı | 17 | **23** |
| İlan edilip sınanmayan mod | 4 | **0** |
| `/api/meta` sözleşmesi | doğrulanmıyordu | **`meta_sozlesmesi`** |
| `/api/stats` + `/api/backtest` gövdesi | doğrulanmıyordu | **`stats_sozlesmesi`** |
| Kupon sınıfı kapsamı | 1 | **4** (8 çift, 7 çift+banko, 9 çift, üçlü) |
| Bayes preset'leri | 1/5 koşuyordu | **5/5** |
| `variant` | hiç koşmuyordu | **1..3** |
| `/health` | tam raporu koşuyordu (o günkü haliyle ~370 ms, soğukta ~2,1 sn) | **liveness, ~2 ms** |
| Readiness önbelleği | yok | **5 sn TTL + `?fresh=1`** |
| Süre eşiği | yok | **her kontrolde `butce_ms`** |
| Sunucu tarafı geçmiş | yok | **halka tampon + `/api/health/history`** |
| Kullanıcının kendi kuponu | doğrulanamıyordu | **`POST /api/health/kupon`** |
| Alarm | yok | **durum değişiminde, opt-in** |
| Örnek kimliği | yok | **pid/host/etiket, raporda ve liveness'ta** |
| Mod mantığının kopyası | 3 (web, health, CLI) | **1 (`engines.py`)** |
| `auto` modu süresi (256 nokta) | ~11,3 sn | **~3,5 sn** |
| Düşen kontrolün detayı | `AssertionError:` | **`… @ health.py:246`** |
| Sağlık katmanının testi | 23 | **84** |
| Tüm süit | 608 | **705** |

Isınmış tam rapor 370 ms → **~520 ms**: yeni kapsamın bedeli, bilerek ödendi.

---

## 1. Tek kaynak: `meta.py`, `engines.py`, `payloads.py`

Kapsam boşluklarının sebebi teşhis değil **yapıydı**: ilan edilen envanter
(`MODES`, sınırlar) ve gövde kurucular `web_app.py` içindeydi; web_app zaten
`health`i import ettiği için sağlık onlara erişemiyordu.

- **`meta.py`** — `MODES`, `ENGINE_DEFAULTS`, `LIMITS`, `meta_payload()`.
  `/api/meta` yalnızca bunu `jsonify` eder; `_engine_params()` de bantları
  `LIMITS`'ten okur, arayüzün gördüğü bant ile uygulanan bant ayrışamaz.
- **`engines.py`** — mod çalıştırıcıları + `adaylar()` / `en_iyi_aday()`.
  `/api/solve`, sağlık ve **CLI** aynı kodu kullanır. Üç kopya vardı.
- **`payloads.py`** — `stats_payload()` / `backtest_payload()`. Veri katmanı
  doğrulanıyordu ama arayüzün okuduğu gövde sınanmıyordu.

---

## 2. Kontroller: 17 → 23

| Kontrol | Kategori | Bağladığı değişmez |
|---|---|---|
| `meta_sozlesmesi` | `ucuca` | Her sınırda `min ≤ varsayılan ≤ max`; preset/mod listeleri motorla aynı; `has_scipy` gerçekle aynı |
| `stats_sozlesmesi` | `ucuca` | `/api/stats` + `/api/backtest` gövdeleri tutarlı; `?last=` gövdenin tamamını daraltıyor |
| `mod_envanteri` | `motor` | 7 modun hepsi koşuyor; `garanti: True` açık bırakmıyor, `maxcov` gerçekten kaplamıyor |
| `bayes_presetleri` | `olasilik` | 5 preset'in posterior'ları 1'e toplanıyor, hiçbiri kaplamayı bozmuyor |
| `fix16_varyantlari` | `cekirdek` | `variant` 1..3 de 16 satır / 14-garanti veriyor |
| `tahmin_referanslari` | `analiz` | Tahmin ölçümü tekrarlanabilir: `duzgun` = 0,667, sıralama piyasa < sezon_sabiti < duzgun (T4) |

Ayrıca `encoder`, `fix16_garanti` ve `distance_layers` artık **dört kupon
sınıfında** koşuyor ve her sınıfın beklenen bedeli tabloda yazılı
(`KUPON_SINIFLARI`): kontrol "kaplama geçerli" demekle kalmıyor, "bu sınıfta
bedel tam olarak bu" diyor.

**`stats_sozlesmesi` yazılırken gerçek bir uyumsuzluk yakaladı:** gövdede
`params` diye bir alan yok (`meta` + `strategy` var). Kontrolün ilk hâli
yanlış alanı arıyordu ve düştü — tam da olması gerektiği gibi.

---

## 3. `/health` ile `/api/health` ayrıldı

| Uç | Rol | İçerik | Ölçülen süre |
|---|---|---|---|
| `/health` | liveness | Süreç + sürüm + uptime + örnek kimliği | **~2 ms** |
| `/api/health` | readiness | Tam rapor | ~520 ms (ilk koşu ~2,1 sn) |

Liveness "bu süreci öldür mü?", readiness "bu sürece trafik ver mi?"
sorusudur. Düşen bir değişmez ikinciyi kırmızıya çevirir; süreci öldürmek
onu düzeltmez — aynı kod her konteynerde aynı şekilde düşer.

**Ölçüldü:** dışarıya açılan tek port Next.js'tir, dolayısıyla platform
probe'u Flask'ın `/health`ine erişemiyordu. `next.config.mjs` artık `/health`i
de proxy'liyor: liveness'ın var olup dışarıdan ulaşılamaz olması yarım
çözümdü — bir probe'un sorabileceği tek adres yine tam raporu koşan uçtu.

Readiness üstünde 5 sn TTL önbellek (`HEALTH_TTL_S`), `?fresh=1` atlar.
Önbellekten dönen gövde bunu saklamaz — `summary.onbellek` yaşını yazar.

---

## 4. Süre eşikleri

Her `CheckSpec` bir `butce_ms` taşır (ölçülen ısınmış sürenin ~3 katı).
Aşım kontrolü **düşürmez**: değişmez hâlâ geçerli, yalnızca beklenenden
pahalı. `ok` kalır, rapor `degraded` işaretlenir, süre çubuğu ambere döner
ve detaya `süre 50 ms > bütçe 10 ms` yazılır.

**Isınma ayrımı zorunluydu:** sürecin ilk raporu numpy/scipy import'unu ve
veri setinin ilk okunmasını da üstlenir (~2,1 sn ↔ ~520 ms). İlk koşuda
bütçe uygulanmaz ve rapor bunu `summary.isinma` ile söyler; sayfa da
"bu, sürecin ilk koşusu" bandını gösterir.

---

## 5. Zaman serisi ve alarm

`spor_toto/health_history.py` — süreç ömürlü halka tampon (200 kayıt,
`HEALTH_HISTORY_LIMIT`) ve `GET /api/health/history`.

Cevapladığı soru: **"ne zamandan beri kırmızı?"** Özet bloğu durumu, o
durumda geçen koşu sayısını, değişim zamanını ve son sağlıklı koşuyu verir.

İki şey seriye **girmez**: kısmi koşular (`?only=`) ve önbellekten dönen
cevaplar. Birincisi "5/5 geçti" ile "22/22 geçti"yi yan yana koyardı,
ikincisi aynı ölçümü iki kez sayardı.

**Alarm** yalnızca durum DEĞİŞİMİNDE tetiklenir (HEALTHY↔DEGRADED↔UNHEALTHY),
arka planda POST atar ve her hatasını yutar. Varsayılan kapalıdır
(`HEALTH_ALARM_URL`); kapalıyken değişim yine log'a yazılır. Her kırmızı
koşuda bildirim göndermek bildirimleri okunmaz yapardı — okunmayan alarm,
alarmsızlıktan kötüdür: korunduğunu sanırsın.

---

## 6. Kullanıcının kendi kuponu

`health.kupon_denetle()` + `POST /api/health/kupon` + sayfadaki *"Kendi
kuponunu doğrula"* bloğu. Sayfanın en kolay yanlış anlaşılan sınırını
kapatır: HEALTHY, kullanıcının kendi kuponunun doğrulandığı anlamına
gelmiyordu.

Verilen kupon aynı kombinatoryal zorunluluklardan geçer: kaplama garantisi
(modun ilan ettiği söze göre), mesafe muhasebesi, satır/kolon muhasebesi,
alt sınır ve olasılık tutarlılığı.

İki kasıtlı karar: sonuç kayıtlı raporun tablosuna **karışmaz** (ayrı blok,
ayrı uyarı metni) ve düşmesi **503 üretmez** — bir kuponun değişmezi
servisin sağlık durumu değildir; 503 izlemeyi yanlış yere baktırırdı.

---

## 7. Arayüz ve motor tarafındaki diğer düzeltmeler

- **Otomatik yenilemede iptal**, **hata koşusunun geçmişe düşmesi**, **sekme
  gizliyken duraklatma** (önceki turdan).
- **Durum adreste** (`?only=`), **sekme başlığında** (`⚠`/`✗`), durum kartı
  `aria-live`, düşenler özetinden karta atlama, "en yavaş kontrol"
  istatistiği, önbellek rozeti.
- **Sunucu geçmişi kartı** ve **kupon denetimi bloğu** (bu tur).
- **Örnek kimliği** durum kartında: `örnek vm#31100`.
- **`auto` modu** artık ILP'ye ayrı bütçe veriyor (`auto_ilp_limit`, 3 sn):
  256 noktalık kuponda **11,3 sn → 3,5 sn**, aynı 32 kolon. Kaybedilen tek
  şey "optimallik kanıtlandı" bayrağı; kanıt isteyen `--mode exact` kullanır.
  CLI'de `auto` tam bütçeyle koşmaya devam eder — kullanıcı komutu bilerek
  çalıştırmış ve karşısında oturuyordur.
- **Düşen kontrol kırılma yerini yazıyor**: `AssertionError: … @ health.py:246`.

---

## 8. Testler ve doğrulama

**79 test** (tur başı 24). Tüm süit: **1.022 test**.

| Dosya | Konu |
|---|---|
| `tests/test_health.py` | Rapor şekli, kategori bütünlüğü, `only`, kırılma yeri, **süre bütçeleri**, **kupon sınıfları**, **örnek kimliği**, **kupon denetimi** |
| `tests/test_api_health.py` | Gövde sözleşmesi, liveness/readiness, önbellek, **zaman serisi**, **kupon ucu** |
| `tests/test_meta.py` | Envanter tutarlılığı, mod çalıştırıcıları, her modun `/api/solve` ile koşabilmesi |
| `tests/test_health_history.py` | Halka tampon, "ne zamandan beri", **alarmın yalnızca değişimde tetiklenmesi** |

Playwright ile sürüldü: sağlıklı durum (açık/koyu tema), **bilerek kırılmış
durum** (kritik kırmızı + bilgi amaçlı amber, `/api/health` 503 iken
`/health` 200), **bütçe aşımı** (DEGRADED + amber çubuk + bant), ağ kesikken
"ulaşılamadı" kaydı, sunucu geçmişi kartı, kupon denetimi (geçerli ve
geçersiz kupon), kısmi koşu ve paylaşılan `?only=` bağlantısı. Kırma sonrası
kod geri alındı. `tsc --noEmit`, `npm run check` ve `next build` temiz.

---

## 9. Yol haritası

Kapsam boşluğu kalmadı; açık maddeler **ölçek** ve **kalıcılık** ile ilgili.

| # | Adım | Çözdüğü sorun | Efor |
|---|---|---|---|
| 9.1 | **Kalıcı zaman serisi** — halka tampon yerine diske/DB'ye | Süreç yeniden başlayınca geçmiş sıfırlanıyor; "geçen hafta ne oldu?" cevapsız | M |
| 9.2 | **Örnekler arası birleştirme** | Her worker kendi tamponunu ve önbelleğini tutuyor | L |
| 9.3 | **Süre bantlarının kendini ayarlaması** | Bant elle yazılıyor; makine yavaşlarsa toplu yanlış alarm | M |
| 9.4 | **Kupon denetiminde mod matrisi** | Bugün kullanıcının kuponu tek modda denetleniyor | S |
| 9.5 | **Alarm gövdesinin biçimlenmesi** (Slack/webhook şablonu) | Bugün ham JSON gidiyor | S |

### 9.1 Önerilen sıradaki iki iş

1. **9.1 + 9.2 birlikte** — kalıcı zaman serisi ve örnekler arası birleştirme.
   Ayrı ayrı yapılırsa ikinci iş birincinin şemasını yeniden yazdırır: "hangi
   örnek, ne zaman, ne ölçtü" aynı kaydın üç alanıdır.
2. **9.4** — kupon denetimini mod matrisine açmak. Birkaç saatlik iş ve
   kullanıcının doğrudan gördüğü yüzeyi genişletir; `kupon_denetle()` zaten
   mod parametresi alıyor, eksik olan yalnızca arayüz ve matris koşusu.

**9.3 sırası sonra:** süre bantlarının kendini ayarlaması kalıcı ölçüm
gerektirir, yani 9.1 olmadan yapılamaz.

---

## 10. Bilinçli olarak yapılmayacaklar

| Yapılmayacak | Neden |
|---|---|
| Kontrolleri arayüzden düzenlemek | Değişmezler koddadır, yapılandırmada değil |
| Sağlığı metrik panosuna dönüştürmek | Bu bir APM işidir; sayfa vaadin kanıtıdır |
| Tahmin isabetini ölçen kontrol | İsabet istatistik katmanının işidir (geri test, hold-out); bu sayfa vaadin canlıda geçerliliğini ölçer, modelin kalitesini değil |
| Kontrol mantığının ikinci kopyası | Biri güncellenip diğeri unutulduğu gün ikisi de değersizleşir |
| Liveness'ın değişmez koşması | Probe'u tam rapora bağlamak, sağlıklı konteyneri öldürtür |
| Her kırmızı koşuda alarm | Okunmayan alarm, alarmsızlıktan kötüdür |

---

## 11. Bugünkü referans değerler

| Ölçü | Değer |
|---|---|
| Kayıtlı kontrol | 24 |
| Kategori | 6 |
| Kritik olmayan kontrol | 1 (`scipy_flag`) |
| Tam rapor süresi (ısınmış) | ~520 ms |
| Tam rapor süresi (ilk koşu) | ~2,1 sn |
| Liveness (`/health`) | ~2 ms |
| Readiness önbelleği | 5 sn TTL, `?fresh=1` atlar |
| Zaman serisi tamponu | 200 koşu, süreç ömürlü |
| Alarm | kapalı (`HEALTH_ALARM_URL` ile açılır) |
| En yavaş kontrol | `mod_envanteri` (~129 ms, 7 mod) |
| `auto` modu (256 nokta) | ~3,5 sn (önce ~11,3 sn) |
| Sağlık katmanının testi | 79 |
| Tüm süit | 1.022 test, ~7 dk |
| Kupon sınıfları | 8 çift/256 · 7 çift+8 banko/128 · 9 çift/512 · üçlü içeren/768 |

---

## 12. İlgili belgeler

| Belge | İçerik |
|---|---|
| `docs/SAGLIK_VIZYONU.md` | Sağlık katmanının **neden**i, tasarım kararları, kontrol yazma sözleşmesi |
| `docs/ARCHITECTURE_NEXT.md` | Backend/frontend ayrımı, uç listesi |
| `README.md` | Kullanım, API, health CLI |
| `backend/README.md` | Backend kurulum ve komutlar |
