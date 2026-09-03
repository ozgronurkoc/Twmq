# Bilgi Grafı — Token Ölçüm Kütüğü

**Ölçüm tarihi:** 2026-08-31 · **Depo:** `ozgronurkoc/twmq`
**Cetvel:** `tiktoken` `cl100k_base` — gerçek BPE tokenizer, **Claude'un
tokenizer'ı değil**. İki ölçümde de aynı cetvel kullanıldı, dolayısıyla oran
geçerli; ham sayılar Claude faturasının birebir karşılığı değildir.
**Yöntem:** soruyu cevaplamak için bağlama girmesi gereken içeriğin token sayısı.

## Ölçüm sorusu

> `backend/spor_toto` paketinde hangi modüller var, her biri ne yapıyor, ve
> kalite kapısı `scripts/check.sh` hangi kontrolleri çalıştırıyor?

## Sonuç

| | Öncesi (grafik yok) | Sonrası (grafik var) |
|---|---:|---:|
| Bağlama giren içerik | 65.657 karakter | 7.652 karakter |
| **Token** | **26.020** | **2.920** |
| Kalan oran | %100 | **%11,2** |

**Fark: 23.100 token · düşüş %88,8.**

`CLAUDE.md` her oturumda **666 token** sabit maliyet getiriyor (ilk ölçümde 530
idi; oto tazeleme belgelenince büyüdü — sayı güncellendi). Oturumun ilk
sorusunda gerçek maliyet `2.920 + 666 = 3.586` token, yani düşüş **%86,2**.
İkinci sorudan itibaren bu maliyet bir daha ödenmez.

Oto tazeleme hook'u ayrıca oturum başına çıktı üretir: her şey yolundaysa
**0 satır** (sessiz), şüpheli sayı varsa sayı başına 1 satır. **Şu an 0 satır**
— bayat girdi 0, şüpheli sayı 0.

## Ölçümün yapıldığı komutlar

**Öncesi** — grafik yokken zorunlu keşif:
```
ls backend/spor_toto/  ·  ls backend/scripts/ backend/tests/
cat scripts/check.sh
head -25 <her modül>            # 52 modül
```

**Sonrası** — `CLAUDE.md`'nin tarif ettiği yol, depo taranmadan:
```
python3 .claude/graf_sorgu.py ozet
python3 .claude/graf_sorgu.py modul
python3 .claude/graf_sorgu.py komut check
```

## Bu sayıyı okurken bilinmesi gerekenler

1. **Temel bilerek düşük tutuldu.** "Öncesi" ölçümünde modüllerin tamamı değil,
   yalnızca ilk 25 satırı okundu. Gerçek bir keşifte daha fazlası okunur, yani
   gerçek "öncesi" maliyeti 26.020'den yüksektir. Düşük temel = düşük görünen
   kazanç.

2. **Cevabın ayrıntı düzeyi aynı değil.** Grafik `check.sh`'ı **tek cümlelik
   özetle** veriyor; betiğin gövdesi (hangi adım hangi sırayla, gerekçeleriyle)
   grafta yok. Gövde gerekiyorsa dosya yine okunur ve kazanç o soruda oluşmaz.
   Ayrıca graf 51 modül tanıyor, 52 değil: `__init__.py` docstring'siz olduğu
   için yazılmadı.

3. **Bu soru grafın ZAYIF tarafından.** `references/schema.md` kendi
   sözleriyle: modül envanteri `ls`/`grep` ile yeniden üretilebilir, "grafın
   orada kazandırdığı zaman azdır"; asıl değer `sayilar` bölümündedir. Yani
   %88,8 en iyi durum değil.

4. **Üretim maliyeti ölçülmedi.** Grafı üretmek depo çapında bir keşif
   gerektirdi (iki kez `pytest --collect-only`, paket kurulumları, `.gitignore`
   ve şema okumaları). Bu tur enstrümante edilmedi, o yüzden buraya bir sayı
   yazılmıyor. Kesin olan: üretim, tek bir sorunun kazandırdığından pahalıdır —
   kazanç ikinci sorudan itibaren birikir.

5. **Bölüm bazlı okumak şart.** Grafın tamamı **7.943 token**. Tamamı okunsaydı
   kazanç 26.020 → 7.943 olurdu (%69,5). Bölüm bazlı sorgu bunu 2.920'ye
   indiriyor; `CLAUDE.md` bu yüzden "grafın tamamını okuma" diyor.

## Yeniden ölçmek için

```bash
python3 .claude/graf_sorgu.py ozet
python3 .claude/graf_sorgu.py tazelik      # bayat girdi 0 olmalı
```

---

## Otomatik enjeksiyon — ölçülen bedeli

`.claude/hooks/user-prompt.sh` her mesajda çalışır ve mesaj grafla ilgiliyse
ilgili girdileri bağlama koyar. **Bu bir token kazancı değil, bir güvence
mekanizmasıdır** ve ölçülen bedeli şudur:

| Durum | Elle sorgu | Hook ile | Fark |
|---|---:|---:|---:|
| Geniş soru (51 modül + `check.sh`) | 2.920 | 3.036 | **+116** |
| Hedefli soru (tek modül) | 168 + *çağrı kararı* | 202 | ~eşit |
| Grafla ilgisiz mesaj | 0 | **0** | 0 |

Geniş soruda hook **pahalıya geliyor** (+%4): `moduller` 51 girdiyle tek mesaja
sığmadığı için enjeksiyon yalnızca işaret koyar, sorgu yine koşar. Karşılığında
alınan şey token değil **kesinlik**: `CLAUDE.md` yönlendirmedir ve atlanabilir;
enjeksiyon atlanamaz.

Bir kusur ölçümle bulundu ve düzeltildi: enjektörün ilk hali 51 girdinin 8'ini
basıyordu. Bu soruyu cevaplamıyordu, Claude yine sorgu koşuyordu ve enjeksiyon
**668 token'lık saf ek yük** oluyordu (668 + 2.920 > 2.920). Kural değişti: tam
cevap veremiyorsan kısmi cevabın parasını ödeme, tek satır işaret koy (~30 token).

## Grafın bulup kapattığı üç şey

Graf kurulurken üç gerçek kusur ortaya çıktı. Üçü de ölçümle bulundu, üçü de
kapatıldı:

1. **Belgelerdeki test sayısı 22 eksikti.** 5 belgede 7 yerde `1.879` yazıyordu;
   eksiksiz süit (lightgbm + scikit-learn kurulu) **1.938** topluyor. Fark
   `test_agac.py`'nin 22 testi: `lightgbm` yoksa modül `importorskip` ile hiç
   toplanmıyor ve bekçi o kurulumda **atlıyor**, yani sapma yerelde görünmüyordu.
   CI `[test,kalite,model]` kurduğu için orada kırmızıydı. Yedi yer düzeltildi.

2. **Bir bekçinin kör noktası vardı.** `test_test_dosya_sayisi_belgelerle_ayni`
   yalnızca `"N test dosyası"` ifadesini tarıyordu; `README.md` §9 aynı sayıyı
   `"(62 dosya → 1.879 test)"` biçiminde yazıyor ve oradaki **62 yanlıştı**
   (gerçek 63). Bekçi göremedi. İkinci desen (`N dosya →`) eklendi — 5 belgede
   sıfır yanlış pozitif üretiyor, ve 62 geri konularak kırmızı yaktığı
   **kanıtlandı**.

3. **Üç boru hattının yeniden üretim komutu yazılı değildi.** `.gitignore`
   "tek komutla yeniden uretilir" diyordu ama komutu vermiyordu, dolayısıyla
   graf onları **yazamıyordu** (kaynağı olmayan girdi yazılmaz). Komutlar koddan
   doğrulanıp `.gitignore`'a yazıldı; graf 7 → **10** boru hattına çıktı.
   `kosumlar/` bilerek dışarıda: boru hattı değil, `--kaydet` ile biriken yerel
   defter — geçmiş ölçüm koşumları yeniden üretilemez.

## Graphify ile karşılaştırma (aynı soru, aynı cetvel)

`graphify` 0.9.53 kuruldu (`uv tool install graphifyy`) ve `graphify update .`
ile çalıştırıldı: **19,6 sn**, 363 dosya, 8.773 düğüm, 18.366 kenar, 343
topluluk. Aracın kendi raporu **"Token cost: 0 input · 0 output"** diyor ve bu
doğrulandı — çıkarım saf AST (tree-sitter), LLM çağırmıyor.

| Soru | Grafik yok | Bu depo (elle) | Bu depo (hook) | Graphify |
|---|---:|---:|---:|---:|
| Geniş (51 modül + `check.sh`) | 26.020 | 2.920 | 3.036 | **2.158** |
| Hedefli (tek modül) | — | 168 | 202 | **2.231** |

**Yalnız token sayarsan Graphify kazanıyor** (26.020 → 2.158, %91,7). Ama sayı
tek başına yanıltıcı ve bu, kütüğün baştan beri uyardığı tuzağın ta kendisi:

* Geniş soruda dönen şey bir *cevap* değil, **kesilmiş bir düğüm listesi**
  (645 düğümün 58'i) — içinde `frontend/package.json`, `token-optimizer`
  betikleri gibi soruyla ilgisiz düğümler var. "Her modül ne yapıyor" ve
  "`check.sh` hangi kontrolleri koşuyor" sorularının ikisi de cevapsız kaldı.
* Hedefli soruda (`kalibrasyon modülü ne yapıyor?`) **yanlış düğümler** döndü:
  `test_getiri.py`, `FORMUL_GELISTIRME_RAPORU.md` bölümleri, xG belgesi —
  `backend/spor_toto/kalibrasyon.py` listede **yok**. Bu depodaki graf aynı
  soruya 202 token'da doğru üç modülü verdi.

**Bu karşılaştırma eksiktir ve öyle sayılmalıdır.** `graphify update` aracın
yalnızca LLM'siz yarısıdır; `graphify extract` semantik geçişi bir API anahtarı
ister ve bu ortamda anahtar yoktu. Aracın kendi çıktısı da bunu söylüyor:
"set GEMINI_API_KEY … to use Gemini for semantic extraction". Semantik geçişle
`query` sonuçları belirgin biçimde daha iyi olabilir — **ölçmedim, dolayısıyla
iddia etmiyorum.**

Graphify'ın gerçekten iyi olduğu yer başka bir soru sınıfı: yapısal bağımlılık.
`graphify explain "health.py"` 607 token'da modülün 101 bağlantısını
(imports / imported-by, satır numaralarıyla) veriyor — bu depodaki graf bunu
hiç yapmıyor. İki araç aynı işi yapmıyor.

**Uyarı:** `graphify-out/` **25 MB** ve içindeki `GRAPH_REPORT.md` tek başına
**~37.500 token**. Tamamı okunursa kazanç değil kayıp olur. `.gitignore`'a
eklendi (türetilmiş çıktı sürümlenmez).

## Grafı ne zaman yeniden çıkarmalı

Ölçüt **zaman değil, dosyanın değişip değişmediğidir**
(`.claude/skills/knowledge-graph/references/sinirlar.md`): hash tutuyorsa altı
ay önceki girdi geçerlidir, tutmuyorsa dünkü girdi geçersizdir.

**Envanter artık kendiliğinden tazeleniyor.** `.claude/hooks/session-start.sh`
her Claude oturumunun başında `moduller`/`kapilar`/`boru_hatlari` bölümlerini
kaynaktan yeniden ölçer (~0,3 sn) ve `sayilar`ı denetleyip **yalnızca uyarır**.
Aşağıdaki tablo, hook'un yapamadığı ya da senin karar vermen gereken durumlar
içindir.

**Elle kontrol için:**
```bash
python3 .claude/graf_sorgu.py tazelik
```
`bayat girdi: 0` ise yapacak bir şey yok. Değilse aşağıya bak.

| Ne olduysa | Ne yapmalı |
|---|---|
| `tazelik` **DEGISTI** / **DOSYA YOK** diyor | **Hook halleder** — bir sonraki oturumda tazelenir. Beklemek istemiyorsan: `python3 .claude/graf_uret.py` |
| Modül, bekçi ya da boru hattı eklendi/silindi/değişti | **Hook halleder.** Üç envanter bölümü de kaynaktan yeniden ölçülür. |
| Oturum açılışında **SUPHELI SAYI** uyarısı | Hook bunu **düzeltmez**, düzeltemez. Sayıyı üreten komutu koş, sonucu `sayilar`a yaz, `anildigi_yerler`i güncelle. |
| Taze klon açtın | Envanter kendiliğinden gelir; **`komutlar` ve `sayilar` GELMEZ** — graf git dışıdır, o iki bölüm elle birikir. Hook bunu açılışta yazar. |
| Bir sayı değişti (test, kontrol, metrik) | `sayilar` girdisini yeniden ölç **ve** `anildigi_yerler`i `grep` ile doğrula — asıl pahalı hata bu listenin eksik kalmasıdır. |
| Dal değiştirdin ya da büyük birleştirme geldi | `tazelik` koş; `bayat girdi: 0` ise dokunma. |
| Üzerinden zaman geçti, kod değişmedi | **Hiçbir şey.** Zaman tek başına hiçbir girdiyi yanlışlamaz. |

**Sıfırdan üretmek** yalnızca şema sürümü değiştiğinde ya da graf bozulduğunda
gerekir. O zaman dosya **silinir** ve göç yazılmaz — defter yerel ve tamamen
yeniden üretilebilir (`references/schema.md`).

**Bir uyarı:** bu grafın CI bekçisi **yok**. `tazelik` elle çağrılır; kimse
çağırmazsa graf sessizce bayatlar. Git dışı olmasının sebebi tam olarak budur —
bayat bir defter yalnızca onu yazan makineyi yanıltır, `git pull` yapan
herkesi değil.
