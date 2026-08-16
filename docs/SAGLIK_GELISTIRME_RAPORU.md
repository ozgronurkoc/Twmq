# Sağlık Katmanı — Çalışma Raporu ve Yol Haritası

**Tarih:** 2026-08-16  
**Dal:** `claude/health-page-development-4ahakf`  
**Commit'ler:** `980a865` (motor + arayüz), `ff8d99b` (vizyon belgesi)  
**Kapsam:** `/saglik` sayfası, `spor_toto/health.py`, `/api/health*` uçları  

> Bu belge iki şeyi bir arada tutar: **bugün ne yapıldığı** (§1–§6) ve
> **bundan sonra ne yapılacağı** (§7–§9). Kararların *gerekçesi*
> `SAGLIK_VIZYONU.md`'dedir; burası yapılan işin ve bekleyen işin dökümüdür.

---

## 0. Özet

| | Öncesi | Sonrası |
|---|---|---|
| Kontrol sayısı | 14 | **16** |
| Kategori | yok (düz liste) | **6** |
| Kontrol açıklaması | yok | **hepsinde, testle zorunlu** |
| Veri katmanı kapsamı | yok | **2 kontrol** (istatistik + oran) |
| Kısmi çalıştırma | yok | **`?only=` / `--only`** |
| Bilgi amaçlı düşüş | 503 | **200 + DEGRADED** |
| Ortam bilgisi | yok | **python/numpy/scipy/flask + platform** |
| Sağlık katmanı testi | 4 | **23** |
| Uçlar | `/api/health` | `+ /api/health/checks` |

İki commit, 16 dosya, +1.640 / −155 satır. Tüm süit (564 test) yeşil,
`tsc --noEmit` ve `next build` temiz.

---

## 1. Çıkış noktası: sayfadaki asıl sorun

Sayfa çalışıyordu ama **okunamıyordu.** Bir satır şuydu:

```
[✓] fix16_yetersiz_cifte    0.0 ms    6 cifte reddedildi
```

Bunun ne anlama geldiğini bilmek için Python kaynağını açmak gerekiyordu.
Sayfa 14 kontrolü listeliyor, hiçbirinin **neyi koruduğunu** söylemiyordu.
Üç somut eksik vardı:

1. **Anlam yok.** Kriptik `name` ve ham `detail` dışında bilgi yoktu.
2. **Yapı yok.** Düz liste, düşen kontrolün adını söylüyor; hatanın hangi
   katmanda olduğunu söylemiyordu.
3. **Kapsam boşluğu.** `/istatistik` sayfasının dayandığı veri katmanı
   (tarihsel sonuçlar + oran arşivi) hiç doğrulanmıyordu.

Ayrıca yanlış bir sinyal üretiyordu: `scipy` kurulu değilse rapor
**UNHEALTHY** diyordu — oysa motor sorunsuz çalışıyor, yalnızca ILP çözücü
devre dışı kalıyordu.

---

## 2. Backend — `spor_toto/health.py`

### 2.1 Kontroller artık veri, kod değil

Önceden kontroller `(ad, fonksiyon)` ikilisiydi. Şimdi her biri bir `CheckSpec`:

```python
@dataclass(frozen=True)
class CheckSpec:
    name: str          # fix16_garanti
    category: str      # cekirdek
    aciklama: str      # "16 satırlık sabit kaplama gerçekten 14-garanti…"
    fn: Callable[[], str]
    critical: bool = True
```

`aciklama` **zorunludur ve testle denetlenir** (`test_health_report_dict_shape`).
"Ne yapıyor" değil, **"kırılırsa ne kaybederiz"** sorusuna cevap verir.

### 2.2 Kategori modeli

Kategoriler motorun katmanlarını izler ve **ciddiyet sırasına** dizilidir:

| # | Kategori | Kontroller |
|---|---|---|
| 1 | `cekirdek` — Çekirdek | `encoder`, `fix16_garanti`, `fix16_yetersiz_cifte`, `distance_layers` |
| 2 | `motor` — Çözücüler | `blok_motor`, `heuristic` |
| 3 | `olasilik` — Olasılık | `olasilik_exact`, `monte_carlo`, `bayes_dirichlet`, `markov_chain` |
| 4 | `analiz` — Analiz | `error_freq`, `fire_scenarios`, **`veri_seti`**, **`oran_arsivi`** |
| 5 | `ucuca` — Uçtan uca | `pipeline_result_shape` |
| 6 | `ortam` — Ortam | `scipy_flag` *(bilgi amaçlı)* |

`cekirdek` düşmüşse aşağıdaki her şey şüphelidir; `analiz` düşmüşse çekirdek
hakkında hiçbir şey söylenmiş olmaz.

### 2.3 İki yeni kontrol — veri katmanı

**`veri_seti`** — `/istatistik`'in dayandığı tarihsel veri setini doğrular:
hafta sayımı, her haftanın 15'lik sonuç dizisi, `n1+n0+n2 = 15`, pozisyon
istatistiklerinin toplamı, geçiş matrisinin hafta başına 14 geçiş üretmesi ve
veri kalitesi çatışmalarının sıfır olması.

**`oran_arsivi`** — piyasa oranı arşivini doğrular: kapsama oranı, favori
isabet muhasebesinin (`hit + miss = with_odds`) tutması, çapraz tablo
toplamlarının satır/sütun bazında örtüşmesi, bant toplamları ve marjın
pozitif olması.

> **Kritik tasarım kararı:** Dosya **yoksa** bu bir hata değildir — motor veri
> setinden bağımsız çalışır, yalnızca istatistik sayfası boş kalır. Kontrol bu
> iki durumu ayırır: dosya yoksa geçer ve nedenini yazar; dosya varsa iç
> tutarlılığı sağlamak **zorundadır**.

### 2.4 DEGRADED — her düşüş 503 değildir

`critical=False` olan kontroller düştüğünde rapor UNHEALTHY olmaz:

| Durum | Koşul | `ok` | `degraded` | HTTP |
|---|---|---|---|---|
| **HEALTHY** | Her şey geçti | `true` | `false` | 200 |
| **DEGRADED** | Yalnızca bilgi amaçlı kontrol düştü | `true` | `true` | **200** |
| **UNHEALTHY** | En az bir kritik düştü | `false` | `false` | 503 |

İlke: *HTTP durum kodu "beni trafikten çıkar" demektir, "bir eksiğim var"
demek değildir.* DEGRADED bir süreç doğru cevap vermeye devam eder; onu yük
dengeleyiciden düşürmek olmayan bir kesinti üretir.

### 2.5 Kısmi çalıştırma

`secili_checkler(only)` bir kontrol adını veya kategori adını (virgülle
çoklu) süzer. Tanım sırası korunur, tekrarlı adlar iki kez koşmaz, bilinmeyen
ad **ValueError** yükseltir — sessizce boş küme koşturmak "hiçbir şey
düşmedi" diyen bir rapor üretirdi.

### 2.6 Rapora eklenenler

`duration_ms` (toplam), `categories[]` (kategori özetleri), `degraded`,
`summary.slowest`, `summary.env` (python, platform, numpy, scipy, flask),
`summary.only`, `summary.kismi`, `summary.kayitli_kontrol`.

### 2.7 CLI

```bash
python -m spor_toto.health                  # kategorili çıktı + düşenlerin özeti
python -m spor_toto.health --list           # kontrol envanteri (çalıştırmadan)
python -m spor_toto.health --only olasilik  # tek kategori veya tek kontrol
python -m spor_toto.health --json
```

Çıktı artık kategori başlıklarıyla gruplu; sonda **düşen kontrollerin ne
koruduğu** ayrıca özetleniyor. Bilinmeyen `--only` değeri çıkış kodu 2 verir.

---

## 3. API — `web_app.py`

| Uç | Değişiklik |
|---|---|
| `GET /api/health` | `?only=` desteği; bilinmeyen ad → **400**; DEGRADED → **200** |
| `GET /api/health/checks` | **Yeni.** Kontrol envanterini çalıştırmadan döner |
| `GET /` | Uç listesine `/api/health/checks` eklendi |

---

## 4. Arayüz — `/saglik`

### 4.1 Yeni dosya: `components/saglik/parts.tsx` (343 satır)

`durumu()`, `DurumIkonu`, `goreliZaman()`, `KontrolSatiri`, `KategoriKarti`,
`GecmisSeridi`, `OrtamKarti`. Repodaki `components/istatistik/parts.tsx`
düzeniyle aynı.

### 4.2 Sayfadaki değişiklikler

- **Kategori kartları.** Her kartta geçen/toplam, süre ve *"Yalnızca bunu
  çalıştır"* düğmesi.
- **Satır başına açıklama.** Kontrolün ne koruduğu birincil, ham `detail`
  ikincil (mono, sönük).
- **Süre çubuğu.** Rapordaki en uzun kontrole göre ölçekli — hangi kontrolün
  raporu yavaşlattığı gözle görülür. Performans gerilemesi de bir gerilemedir.
- **Üç durumlu ikonografi.** Geçti (yeşil) / kritik düştü (kırmızı) / bilgi
  amaçlı düştü (amber). Üçüncüsü kırmızı **değildir**.
- **Düşenler özeti** sayfanın başında, açıklamalarıyla.
- **"Yalnızca düşenler" filtresi.** Yalnızca görünürlüğü değiştirir;
  kontrollerin hepsi her zaman koşar.
- **Otomatik yenileme** (Kapalı / 15 sn / 1 dk / 5 dk). Her zaman **tam**
  raporu koşar — kısmi bir koşuyu arka planda tekrarlamak sayfayı giderek daha
  az şey doğrulayan bir yeşil göstergeye dönüştürürdü.
- **Oturum içi çalışma geçmişi.** Son 8 koşu; arada bir düşen bir kontrol tek
  çalıştırmada görünmez.
- **Kısmi koşu bandı**, tek tıkla tam rapora dönüş.
- **Çalışan ortam kartı** ve **JSON kopyala**.
- **Hydration güvenliği.** Göreli zaman ("14 sn önce") yalnızca mount sonrası
  hesaplanır; sunucuda hesaplanırsa uyuşmazlık olur.

### 4.3 Tip katmanı — `lib/types.ts`

`HealthKategoriId`, `HealthKategori`, `HealthEnv`, `HealthSummary`,
`HealthCheckInfo`, `HealthChecksResponse` eklendi; `HealthCheck` ve
`HealthReport` genişletildi. `lib/api.ts`'te `getHealth(only?, signal?)` ve
`getHealthChecks()`.

Sayfa kategorileri, açıklamaları ve kritiklik bayrağını **rapordan okur**,
hiçbirini sabit kodlamaz — mevcut bir kategoriye eklenen yeni kontrol
arayüzde kendiliğinden belirir.

---

## 5. Testler

**23 test** (öncesi 4). Tüm süit: **564 test, ~65 sn.**

**`tests/test_health.py`** (16) — konu başına:

| Konu | Testler |
|---|---|
| Temel rapor | `run_health_all_pass`, `health_report_dict_shape`, `health_includes_core_and_analysis`, `print_report_no_crash` |
| Kategori bütünlüğü | `her_check_bilinen_kategoride`, `check_adlari_tekil`, `kategori_ozeti_toplami_tutar` |
| Envanter | `envanter_calistirmadan_listeler` |
| `only` süzgeci | `only_tek_kontrol`, `only_kategori`, `only_coklu_ve_sira_korunur`, `only_tekrarli_ad_iki_kez_calismaz`, `only_bilinmeyen_ad_hata_verir`, `only_bos_hepsini_calistirir` |
| Ortam / ölçüm | `env_bilgisi_raporda`, `slowest_en_uzun_kontrolu_gosterir` |

**`tests/test_api_health.py`** (7, yeni dosya) — gövde sözleşmesi, kategori
kapsaması, `?only=` kategori, bilinmeyen ad → 400, boş `only`, envanter ucu,
`/health` ile `/api/health` eşdeğerliği.

### 5.1 Doğrulama yöntemi

Testlere ek olarak uygulama gerçekten ayağa kaldırıldı ve Playwright ile
sürüldü:

- Sağlıklı durum, açık ve koyu tema.
- **Bilerek kırılmış durum** (bir kritik + bir bilgi kontrolü düşürülerek):
  kritik kırmızı, bilgi amaçlı amber, uç 503 dönerken sayfa raporu göstermeye
  devam ediyor. Kırma sonrası kod geri alındı.
- Etkileşimler: "yalnızca düşenler" filtresi, kategori bazlı kısmi
  çalıştırma, tam rapora dönüş, geçmiş şeridi, otomatik yenileme düğmeleri.
- JS konsol hatası yok.

---

## 6. Belgeler

- **`docs/SAGLIK_VIZYONU.md` (yeni, 334 satır)** — sayfanın neden var olduğu,
  test/health ayrımı, ne kanıtlanıp ne kanıtlanmadığı, kontrol yazma
  sözleşmesi, DEGRADED gerekçesi, bilinçli sınırlar, yol haritası.
- Sabit kontrol sayıları temizlendi. `README.md`, `backend/README.md`,
  `frontend/README.md`, `docs/ARCHITECTURE_NEXT.md`, `scripts/check.sh` ve CI
  workflow'unda **"13 invariant" / "14 invariant"** diye üç farklı ve üçü de
  yanlış sayı duruyordu; sürekli geride kalıyorlardı.

---

## 7. Yol haritası — öncelik sırasıyla

Sıra "en çok riski/belirsizliği kaldıran" ölçütüne göredir. Efor kabaca:
**S** = birkaç saat, **M** = yarım–bir gün, **L** = birkaç gün.

### Öncelik 1 — Dağıtım riski

#### 7.1 `/health` ile `/api/health` ayrılmalı `[M]`

`@app.route("/health")` ve `@app.route("/api/health")` **aynı handler'a**
bağlı; ikisi de 16 kontrolün tamamını koşuyor (~340 ms, soğuk başlangıçta
~615 ms).

`.replit`'te `deploymentTarget = "autoscale"`. Platform probe'u `/health`'e
her vurduğunda bu bedel ödeniyor; sıfıra inmiş bir konteyner uyandığında ısınma
bedeli de eklenir. Probe zaman aşımına düşerse platform **sağlıklı** bir
konteyneri öldürür — yani sağlık kontrolü kesintiye *sebep olabilir*.

**Çözüm:** liveness / readiness ayrımı.

| Uç | Rol | İçerik | Süre |
|---|---|---|---|
| `/health` | liveness | Süreç ayakta + sürüm | ~0 ms |
| `/api/health` | readiness / teşhis | Tam rapor | ~340 ms |

Üstüne kısa bir önbellek (örn. 5 sn TTL, `?fresh=1` ile atlanır) hem probe'u
hem de sekmesini açık bırakan kullanıcıyı korur.

> **Uyarı:** `/health` gövdesi değişir. Bugün ona bakan bir şey varsa kırılır;
> `test_kisa_yol_health_ayni_govdeyi_verir` testi de güncellenmelidir.

### Öncelik 2 — Kapsam boşlukları

#### 7.2 `/api/meta` sözleşmesi kontrol edilmiyor `[S]`

Formül sayfasının **tamamı** modları, Bayes preset'lerini, motor
varsayılanlarını ve sınırları `/api/meta`'dan okur, hiçbirini sabit kodlamaz.
Meta bozulursa ana sayfa çöker ama sağlık raporu yemyeşil kalır.

Ucuz bir tutarlılık kontrolü çok şey yakalar: her limitte `min ≤ default ≤ max`,
`STRENGTH_PRESETS` ile meta'daki preset listesinin örtüşmesi, `needs_scipy`
bayrağının `HAS_SCIPY` ile tutarlılığı, `symbols` ve `match_count`'un motorla
aynı olması.

#### 7.3 İlan edilen 7 moddan 4'ü hiç sınanmıyor `[M]`

Sağlık `fix16`, `block` ve `heuristic` koşturuyor. **`auto`, `exact`,
`butce`, `maxcov` kapsam dışı.** Meta'da ilan edilen ama bozuk bir mod,
doğrudan kullanıcıya çarpan bir hatadır.

Asıl kazanç şu değişmezi bağlamaktır: **her modun ürettiği sonuç, meta'daki
`garanti` bayrağıyla uyuşmalı** — özellikle `maxcov`'un `garanti: False`
olması ve gerçekten garanti *vermemesi*.

Süre bütçesi gözetilmeli: ILP'yi ya küçük bir kupona indir ya da
`pytest -m slow` tarafında bırak.

#### 7.4 Bayes preset'leri sınanmıyor `[S]`

`bayes_dirichlet` elle verilen güçlerle koşuyor, meta'nın ilan ettiği
preset'lerle değil. CLI duman testi yalnızca `dengeli`yi kullanıyor;
diğerleri hiçbir yerde koşmuyor.

#### 7.5 `variant` parametresi sınanmıyor `[S]`

Alternatif 16 satırlık kümeler (`--variant`) hiçbir kontrolde koşmuyor. Her
varyantın da 14-garanti vermesi gerekir.

### Öncelik 3 — Mevcut koddaki gerçek sorunlar

#### 7.6 Otomatik yenilemede iptal yok `[S]`

`setInterval(() => void yukle(null))` çağrısı `AbortSignal` almıyor. Kısmi bir
koşu ile arka plandaki tam koşu çakışırsa cevaplar **geliş** sırasına göre
yazılıyor, **gönderim** sırasına göre değil; ekranda yanlış rapor kalabilir.
Her yeni çağrı öncekini iptal etmeli.

#### 7.7 Geçmiş şeridi yalnızca başarılı koşuları kaydediyor `[S]`

`setGecmis` `try` bloğunun içinde; backend'e ulaşılamadığında geçmişe hiçbir
şey düşmüyor. Oysa zaman çizelgesinde en çok görmek isteyeceğin olay tam da
odur. Hata durumları da bir kayıt olarak ("ulaşılamadı", kırmızı) eklenmeli.

#### 7.8 Sekme gizliyken yenileme sürüyor `[S]`

Arka plandaki sekme 5 dakikalık aralıkla saatlerce koşuyor, geçmiş şeridi
anlamsız kayıtlarla doluyor. `document.visibilityState` ile duraklat, sekme
geri geldiğinde bir kez koştur.

#### 7.9 Hata satırı kayboluyor `[S]` — en ucuz kazanç

`_run` istisnayı `f"{type(e).__name__}: {e}"` diye yassıltıyor. Bir assert
düştüğünde hangi satırda kırıldığı görünmüyor. Traceback'in **son karesini**
(`health.py:226`) detaya eklemek birkaç satır; canlıda hata ayıklarken farkı
büyük.

### Öncelik 4 — Teşhis gücü

#### 7.10 Süre eşikleri `[M]`

Her `CheckSpec`'e beklenen süre bandı. Aşınca kontrol **düşmesin** ama
`degraded` işaretlensin ve süre çubuğu ambere dönsün. Bugün performans
gerilemesi yalnızca gözle yakalanıyor.

> Isınma farkı (ilk koşu ~615 ms, sonrakiler ~340 ms) hesaba katılmalı; yoksa
> her soğuk başlangıç yanlış alarm üretir.

#### 7.11 Sunucu tarafı zaman serisi `[M]`

Son N raporun özeti (`ok`, `passed`, süre, düşen adlar) bellekte halka
tamponda tutulsun, `GET /api/health/history` ile verilsin. Bugün
cevaplanamayan soruyu açar: **"ne zamandan beri kırmızı?"** Oturum içi geçmiş
sekme kapanınca gidiyor.

#### 7.12 Kullanıcı kuponuyla koşma `[L]`

Bugün rapor **sabit** örnek kupon üzerinde koşuyor; HEALTHY, kullanıcının
kendi kuponunun doğrulandığı anlamına gelmiyor. `/api/solve` sonucunu aynı
değişmezlerden geçiren bir mod bu boşluğu kapatır.

#### 7.13 Örnek çeşitliliği `[M]`

Tek kupon sınıfı (8 çift, 256 nokta) kapsanıyor. Sabit tohumlu birkaç sınıf
daha (çok bankolu, çok çiftli, üçlü içeren) determinizmi bozmadan kapsamı
genişletir.

### Öncelik 5 — Arayüz cilası

| # | Öneri | Efor |
|---|---|---|
| 7.14 | **Durum URL'e yansısın** (`/saglik?only=olasilik`) — düşen kategorinin bağlantısı paylaşılabilir olur, yenilemede kaybolmaz | S |
| 7.15 | **Sekme başlığı durumu göstersin** (`⚠ Sağlık`) — bu sayfa arka planda açık tutulmak için var; alarm altyapısı gerektirmeyen en yakın "haber verme" | S |
| 7.16 | **`aria-live`** durum kartında — otomatik yenilemede HEALTHY→UNHEALTHY geçişi ekran okuyucuya sessiz (`components/istatistik/parts.tsx:45`'te örneği var) | S |
| 7.17 | **Düşen kontrole atlama** — özetteki addan ilgili karta anchor | S |
| 7.18 | **"Kategori" istatistiği zayıf** — hiç değişmiyor; yerine "en yavaş kontrol" | S |

### Öncelik 6 — Operasyon

#### 7.19 Alarm bağlantısı `[M]`

Sağlık kırmızıya döndüğünde kimseye haber gitmiyor; birinin bakıyor olması
gerekiyor. Bugünkü kullanım için bilinçli bir sadeleştirme, ama kalıcı değil.

#### 7.20 Örnek kimliği `[S]`

Rapor, çağrıyı karşılayan süreci anlatıyor. Çok örnekli bir dağıtımda "hangi
örnek?" sorusu cevapsız. Rapora süreç/örnek etiketi eklenmeli.

---

## 8. Bilinçli olarak yapılmayacaklar

| Yapılmayacak | Neden |
|---|---|
| Kontrolleri arayüzden düzenlemek | Değişmezler koddadır, yapılandırmada değil |
| Sağlığı metrik panosuna dönüştürmek | Bu bir APM işidir; sayfa vaadin kanıtıdır |
| Tahmin isabetini ölçen kontrol | Araç tahmin etmez; bu sayfa da etmez |
| Kontrol mantığının ikinci kopyası | Biri güncellenip diğeri unutulduğu gün ikisi de değersizleşir |

---

## 9. Önerilen sıradaki üç iş

1. **7.1** — tek gerçek dağıtım riski; geri kalanların hepsinden önce gelir.
2. **7.2 + 7.3** — sağlığın kapsamını ürünün asıl kırılgan yüzeyine (meta
   sözleşmesi ve ilan edilen modlar) genişletir. Kapsam kazancı en yüksek,
   maliyeti orta.
3. **7.9 + 7.6 + 7.7** — üçü birlikte yarım günlük iş, teşhis kalitesini
   belirgin yükseltir.

**7.10** ve **7.11** güçlü ama sırası sonra: ikisi de kalıcı durum getiriyor,
yani önce 7.1'deki önbellek/probe kararının netleşmesi gerekiyor.

---

## 10. Bugünkü referans değerler

Bu tablo bir sözleşme değil, karşılaştırma tabanıdır.

| Ölçü | Değer |
|---|---|
| Kayıtlı kontrol | 16 |
| Kategori | 6 |
| Kritik olmayan kontrol | 1 (`scipy_flag`) |
| Tam rapor süresi (ısınmış) | ~340 ms |
| Tam rapor süresi (ilk koşu) | ~615 ms |
| En yavaş kontrol | `monte_carlo` (~122 ms, 5.000 örnek) |
| Sağlık katmanının testi | 23 |
| Tüm süit | 564 test, ~65 sn |
| Örnek kupon | `1,10,1,12,0,10,2,10,1,12,02,1,10,2,10` |
| Örnek kuponun uzayı | 8 çift → 256 nokta, alt sınır 29 kolon |

---

## 11. İlgili belgeler

| Belge | İçerik |
|---|---|
| `docs/SAGLIK_VIZYONU.md` | Sağlık katmanının **neden**i, tasarım kararları, kontrol yazma sözleşmesi |
| `docs/ARCHITECTURE_NEXT.md` | Backend/frontend ayrımı, uç listesi |
| `README.md` | Kullanım, API, health CLI |
| `backend/README.md` | Backend kurulum ve komutlar |
