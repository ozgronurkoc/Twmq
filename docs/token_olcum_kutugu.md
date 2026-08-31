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

`CLAUDE.md` her oturumda **530 token** sabit maliyet getiriyor. Oturumun ilk
sorusunda gerçek maliyet `2.920 + 530 = 3.450` token, yani düşüş **%86,7**.
İkinci sorudan itibaren bu maliyet bir daha ödenmez.

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

## Grafı ne zaman yeniden çıkarmalı

Ölçüt **zaman değil, dosyanın değişip değişmediğidir**
(`.claude/skills/knowledge-graph/references/sinirlar.md`): hash tutuyorsa altı
ay önceki girdi geçerlidir, tutmuyorsa dünkü girdi geçersizdir.

**Önce her zaman bunu koş — kararı o versin:**
```bash
python3 .claude/graf_sorgu.py tazelik
```
`bayat girdi: 0` ise yapacak bir şey yok. Değilse aşağıya bak.

| Ne olduysa | Ne yapmalı |
|---|---|
| `tazelik` **DEGISTI** diyor | Yalnızca o girdiyi yeniden ölç. Tamamını üretme. |
| `tazelik` **DOSYA YOK** diyor | Girdiyi **sil**. Taşındıysa yeni yolla yeniden yaz. |
| `backend/spor_toto/` altına modül eklendi/silindi | `moduller` bölümünü yeniden üret. |
| `test_belgeler.py` bekçisi eklendi/değişti | `kapilar` bölümünü yeniden üret. |
| `.gitignore` boru hattı yorumları değişti | `boru_hatlari` bölümünü yeniden üret. |
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
