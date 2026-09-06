# Düz Sisteme Geçiş — Kaplama Katmanının Sökülmesi

**Tarih:** 2026-09-06
**Dal:** `claude/sohbet-ebsjo9`
**Ölçüm hattı:** `backend/scripts/sistem_kiyasi.py`
**Kesit:** 2026/27 3. ve 4. hafta · yedi kolon bütçesi · iki ikramiye tablosu

> Bu belge bir **sökümün gerekçesidir**. Depo bugüne kadar kuponu kaplama
> koduyla kurdu; bundan sonra düz (tam sistem) kuracak ve kaplama katmanı
> depodan çıkacak.
>
> Belgenin var olma sebebi şudur: **kaplama sökülünce bu kararın kanıtı da
> sökülür.** Aşağıdaki kıyas kaplama tarafı hâlâ ayaktayken koşuldu ve
> çıktısı buraya donduruldu. Sökümden sonra `sistem_kiyasi.py` koşamaz;
> gerekçe yalnızca bu belgede kalır.

> **Kaplamanın ayakta olduğu son nokta: `4b0fa40`** (`4b0fa406b3346a7204c6768d60d5a5ad7559c511`).
> O commit'te `core.solve_fix16`, Hamming(7,4) bloğu, sistem fiyat tablosu ve
> 14-garanti aritmetiği hâlâ çalışıyor; kaplama tarafının davranışını yeniden
> görmek gerekirse başlangıç noktası orasıdır. (`kaplama-son` git etiketi
> atıldı ama bu oturumun git aktarımı yalnızca kendi dalını push edebiliyor,
> yani etiket uzağa **gitmedi** — çıpa bu yüzden SHA olarak buraya yazıldı.)

---

## 0. Özet — üç cümle

1. Aynı **kolon** bütçesinde her sistemin erişebildiği en iyi şekil
   karşılaştırıldığında düz kazanıyor: E[TL]'de **1,78×–5,26×**, ve
   `P(≥12)`'de de her kademede önde.
2. Fark sistemden değil **şekilden** geliyor: `solve_fix16` en az yedi çifte
   istiyor ve bu, kaplamayı yayvan şekillere (8/7/0, 4/8/3) hapsediyor; düz
   yoğunlaşabiliyor (11/4/0, 10/0/5).
3. **Bu bir kâr vaadi değildir.** Düz oynamanın kendisi 114 hafta üzerinde
   zaten ölçüldü (`KADEME_OLASILIKLARI.md`): haftalık geri dönüş medyanı
   **%0**, büyük bütçede zarar olasılığı **%99–100**. Düz kaplamadan iyi;
   iyi olan hâlâ zarar ediyor.

---

## 1. Kaplama neyi satıyordu

`core.solve_fix16` yedi çifteyi Hamming(7,4) bloğuna koyar (16 satır,
kanıtlanmış optimal), kalan her şeyi — fazla çifteler ve **bütün üçlüler** —
o 16 satırın içine tam sistem olarak yerleştirir. Bedel bu yüzden düz bedelin
tam **sekizde biri**dir:

```
kaplama bedeli = 2^çifte · 3^üçlü / 2⁷ · 16        (düz bedelin 1/8'i)
düz bedeli     = 2^çifte · 3^üçlü
```

Karşılığında verdiği şey **14-garanti**: doğru sonuç seçim kümesinin içindeyse
en az bir kolon en fazla 1 hatalıdır. Düzde ise doğru sonuç kümedeyse bir kolon
**15** yapar. Yani düz kaplamadan kesin olarak güçlüdür; kaplamanın sattığı tek
şey **ucuzluktur**.

### Kaçak aritmetiği iki sistemde

| | en iyi kolon | `≥12` için eşik |
|---|---|---|
| kaplama | `≥ 14 − k` (**alt sınır**) | `k ≤ 2` |
| düz | `= 15 − k` (**eşitlik**) | `k ≤ 3` |

Düzdeki eşitlik bir sadeleşmedir: `hedef_olasiligi` artık temkinli bir alt
sınır değil, tam sayıdır. `secim.py`nin *"ölçümde gerçekleşen isabet bu sayının
üstünde çıkar"* uyarısı düz modda geçersizdir.

---

## 2. Doğrulama — önce bilinen bulgu yeniden üretildi

`ISTATISTIK_YOL_HARITASI.md` §3.40 şunu ölçmüştü: *aynı işaretler iki sistemde
kolon başına aynı beklentiyi verir* (₺46,88 ↔ ₺46,16). Kıyasa güvenmeden önce
bu bağımsız olarak yeniden üretildi — kaplama tarafı kaba kuvvetle, 864 kolon
tek tek gezilerek:

```
3. hafta, aynı işaretler (4/8/3):
  fix16          864 kolon ·   363.750 TL · kolon başına 421,0 TL
  tam sistem   6.912 kolon · 2.916.294 TL · kolon başına 421,9 TL
  sapma %0,22 — doğrusallık TUTUYOR
```

`python scripts/sistem_kiyasi.py --dogrula --hafta 3`

Yani **sistem seçimi tek başına üstünlük satmıyor.** Depo bunu doğru ölçmüştü.

---

## 3. Asıl kıyas — aynı bütçede erişilebilen en iyi şekil

§2 *aynı işaretleri* karşılaştırır. Buradaki soru farklıdır: aynı **kolon**
bütçesinde her sistem **hangi şekle erişebiliyor** ve o şekil ne kazandırıyor?

`python scripts/sistem_kiyasi.py`

### 3. hafta (1. haftanın ikramiye tablosu)

| tavan | DÜZ şekil | kolon | E[TL] | P≥12 | KAPLAMA şekil | kolon | E[TL] | P≥12 | oran |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | 11/4/0 | 16 | 50.034 | 0,118 | 8/7/0 | 16 | 27.075 | 0,090 | **1,85×** |
| 64 | 9/6/0 | 64 | 134.764 | 0,189 | 6/9/0 | 64 | 63.727 | 0,146 | **2,11×** |
| 256 | 10/0/5 | 243 | 382.113 | 0,358 | 5/9/1 | 192 | 133.367 | 0,223 | **2,87×** |
| 864 | 7/5/3 | 864 | 937.411 | 0,458 | 4/8/3 | 864 | 364.537 | 0,381 | **2,57×** |
| 3.888 | 6/4/5 | 3.888 | 2.600.268 | 0,656 | 3/7/5 | 3.888 | 920.943 | 0,581 | **2,82×** |
| 10.368 | 6/2/7 | 8.748 | 4.737.387 | 0,789 | 2/8/5 | 7.776 | 1.244.832 | 0,643 | **3,81×** |
| 59.049 | 5/0/10 | 59.049 | 15.093.032 | 0,960 | 1/7/7 | 34.992 | 3.013.268 | 0,843 | **5,01×** |

### 4. hafta (1. haftanın ikramiye tablosu)

| tavan | DÜZ şekil | kolon | E[TL] | P≥12 | KAPLAMA şekil | kolon | E[TL] | P≥12 | oran |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | 11/4/0 | 16 | 23.688 | 0,073 | 8/7/0 | 16 | 13.324 | 0,054 | **1,78×** |
| 256 | 10/0/5 | 243 | 220.935 | 0,268 | 4/11/0 | 256 | 68.185 | 0,141 | **3,24×** |
| 864 | 9/0/6 | 729 | 499.951 | 0,388 | 4/8/3 | 864 | 196.665 | 0,275 | **2,54×** |
| 3.888 | 6/4/5 | 3.888 | 1.349.628 | 0,535 | 3/7/5 | 3.888 | 556.220 | 0,467 | **2,43×** |
| 59.049 | 5/0/10 | 59.049 | 8.150.479 | 0,905 | 0/9/6 | 46.656 | 2.195.096 | 0,748 | **3,71×** |

### Oran ikramiye tablosuna bağlı değil

Aynı kıyas 2. haftanın tablosuyla (14 kademesi ₺2,15M değil ₺202K) koşulduğunda
mutlak TL üç kat düşüyor ama oran duruyor: **1,87×–5,26×**.

`python scripts/sistem_kiyasi.py --odul-hafta 2`

### Neden

Kaplamanın seçtiği şekiller hep yayvan (8/7/0, 4/8/3, 3/7/5), düzünkiler yoğun
(11/4/0, 10/0/5, 9/0/6). Sebep tek: **en az yedi çifte şartı.** Kaplama
kolonlarını geniş bir seçim uzayına yaymak zorunda; düz parayı favorilere
yığabiliyor ve her kolonun kendi tutma olasılığı yükseliyor.

İkinci gözlem: **kolon başına verim kolon sayısıyla düşüyor** (3. haftada
₺3.127/kolon → ₺81/kolon). Yani kaplamanın "8 kat ucuza 8 kat büyük uzay"
takası, beklenen değerde geri veriliyor.

---

## 4. Sayıların sınırı — okunmadan kullanılmasın

- **Mutlak TL güvenilir değil.** Tek bir haftanın ikramiye tablosuna dayanır ve
  o tablo hafta hafta on kat oynar. Manşet **orandır**.
- **Beklenen değer kâr göstergesi değildir.** Dağılım jackpot terimi tarafından
  taşınır; `KADEME_OLASILIKLARI.md` §5.2'nin medyanı **%0**'dır.
- **Şekil ataması sıralamaya dayanır** (üçlü en yüksek `p₃`, tek en düşük
  `p₂`). Bu kesin değil: 2026/27'nin dört haftasının dördünde `en_iyi_secim`in
  cevabıyla birebir örtüşüyor, 400 rastgele haftanın %81–83'ünde. Aynı sıralama
  iki tarafa da uygulandığı için kıyası yanlı yapmaz.
- **Kaplamanın E[TL]'si 1/8 kısayoluyla hesaplanır.** §2 bunu %0,22 sapmayla
  doğruladı ve sapma kaplama **lehine** — gerçek fark buradakinden biraz büyük.
- **İki hafta ölçüm değildir.**

---

## 5. Geçiş planı

| # | Aşama | Çıktı |
|---|---|---|
| 0 | Bu belge + `sistem_kiyasi.py` + kütük etiketleme + `kaplama-son` git etiketi | kanıt donduruldu |
| 1 | Düz seçim motoru (`secim.py`, `duz.py`) + kupon yolu | 5. haftanın kuponu düz kurulur |
| 2 | Kaplama gövdesinin sökülmesi | `core.py` sadeleşir, `engines.py`/`sistem.py` kalkar |
| 3 | Ölçüm hatları düze | `karne`, `hafta_hakki`, `backtest`, `secim_kalibrasyonu`, `fire_scenarios` |
| 4 | Yeniden ölçüm, kütük ve belgeler | kaplama ölçeğindeki sayıların düz karşılıkları |

### Kararlar

- **Kaçak eşiği `k ≤ 3`.** Mekanizma (Poisson-binom kaçak dağılımı) birebir
  korunur; değişen tek şey garantinin aritmetiğinden gelen sayıdır. Para hedefi
  aynı kalır: en az 12.
- **Bütçe tavanı varsayılansız zorunlu parametredir.** Düzde üçlünün kaçağı
  sıfır olduğu için tavan yoksa `P(k≤3)`'ü enbüyükleyen plan her maçı üçlü
  yapmaktır: `3¹⁵ = 14.348.907` kolon, `P = 1,0`, ₺10 bedelle **₺143 milyon**.
  "Tavan yok" dejenere bir cevaptır; motor tavan verilmezse `ValueError` atar.
- **Kayıt yeniden yazılmaz.** Kaplama ölçeğindeki kütük girdileri silinmez,
  etiketlenir; düz ölçümler yanlarına eklenir. Precedent: `orantili → shin`
  marj arındırması ve `₺1,50 → ₺10` kolon bedeli geçişleri.

---

## 6. Sökümün ölçülmüş yüzeyi

| Modül | Satır | Akıbet |
|---|---:|---|
| `spor_toto/karne.py` | 2.050 | düze çevrilir (10 `sistem_secimi` çağrısı) |
| `spor_toto/core.py` | 1.076 | kaplama gövdesi çıkar; `Encoder`, `SEMBOLLER`, `parse_picks` kalır |
| `spor_toto/hafta_hakki.py` | 900 | düze çevrilir |
| `spor_toto/secim.py` | 879 | `bedel_hesapla`, `sistem_secimi`, 7-çifte kısıtı çıkar |
| `spor_toto/backtest.py` | 542 | `_kaplama` ve `secim_uret` yolu çıkar |
| `spor_toto/fire_scenarios.py` | 280 | düz altında yeniden kurulur |
| `spor_toto/engines.py` | 277 | **tamamı çıkar** |
| `spor_toto/sistem.py` | 276 | **tamamı çıkar** |

`core.py`'de ne kalacağı ölçüldü: depo genelinde `SEMBOLLER` 41, `Encoder` 35,
`parse_picks` 10 yerde kullanılıyor — kaplamaya ait değiller. `solve_fix16` 13,
`Fix16Hatasi` 8, `HAMMING_BLOK_BOYU` 5 yerde: bunlar gider.

**Kırıcı API değişikliği:** `/api/solve` ve `/api/health/kupon` `mode` alanı
alıyor (`fix16`/`auto`/`block`/`exact`/`heuristic`); modlar gidince sözleşme
değişir ve `frontend/lib/api-sozlesme.json` sürümlenir.

**Testler:** kaplamaya değen **22 dosya** var; `test_engines.py` (34 test) ve
`test_sistem.py` (10) bütünüyle düşer. Süitin küçülmesi beklenen sonuçtur.
