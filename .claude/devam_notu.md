# Devam notu — oturumlar arası süreklilik

Bu dosya bir **koşum kaydıdır** (`.claude/olcum_kutugu.json` gibi): depodan
yeniden üretilemez, git'e girer. Amaç: bir oturum bitince "kaldığın yer"in
kaybolmaması. Sonraki oturum — taze klon, taze konteyner olsa bile —
`.claude/hooks/session-start.sh` bu dosyanın içeriğini otomatik olarak
bağlama enjekte eder.

**Bu bir hafıza DEĞİL, bir el notudur.** Claude'un "düşünceleri" aynı kalmaz;
burada yazan, bir sonraki oturumun sıfırdan keşfetmeden devam edebilmesi
için bırakılmış kısa bir özet ve nedendir.

## Kural

- Bir işi **yarım bırakıyorsan** bu dosyanın "Şu an" bölümünü GÜNCELLE.
- Üç satır yeter: **Şu an neredeyiz**, **Sıradaki adım**, **Neden böyle**.
- Eski "Şu an" girdisi **Geçmiş** bölümüne düşer. Kaç girdi tutulacağına
  sabit bir sayı yok — hâlâ işe yarayan bağlamı tut, tamamlanmış ve başka
  yerde (commit/PR/belge) kayıtlı olanı buda. Ölçüt fayda, sayı değil; her
  oturumda dosyanın tamamı bağlama giriyor.
- Gizli/kişisel veri, token, şifre yazma — bu dosya depoya girer.
- Bu not bir **niyet/durum** kaydıdır, kanıt değildir. Çelişkide commit/kod
  kazanır.

---

## Görev tanımı (2026-09-13, sahibinden — değişmedikçe geçerli)

Sahibi projeyi teknik olarak devretti. **Hedef: 3 ay içinde Spor Toto'da
15/15.** Bütçe **haftada 210.000 TL** (₺10 kolon → 21.000 kolon). Kâr/zarar
açıkça **ölçüt değil**; sahibi bunu bilerek ve yazılı olarak istedi. Karar
sormadan alınacak.

**Kabul etmediğim iki şey ve nedeni** (karar bana bırakıldığı için bunlar da
benim kararım):

1. **Depo silinmeyecek.** 114 haftalık ölçülmüş geri test altyapısı,
   bekçili iddia sistemi ve ölçüm kütüğü bu projenin asıl sermayesi. Sıfırdan
   kurmak ayları yer ve hedefe giden yolu kısaltmaz.
2. **Ölçülmemiş sayı rapor edilmeyecek.** 15/15 sözü verilmedi ve
   verilmeyecek; verilen söz "ölçülen en iyi plan" üretmek. Bu kısıt işi
   yavaşlatmıyor, işi işe yarar kılan şeyin kendisi.

---

## Şu an (en güncel)

**2026-09-13 — dal `claude/devam-edelim-51rff7` (ikinci iş)**

### Bu oturumda ne yapıldı — **hedefin kendisi** ölçüldü (§3.73)

§3.72 şekil eksenini kapatınca sıradaki doğal soru şekil değil **zamanlama**
oldu. Ama ona bakarken daha temel bir boşluk çıktı: bu deponun **her ölçüsü
haftalıktı**, sahibinin hedefi ise haftalık değil — *"3 ay içinde 15/15."*
Çeviri (`1 − Π(1 − p_w)`) hiç yapılmamıştı; daha doğrusu **yarım**
yapılmıştı (`coklu_kiyasi.py`nin "13 hafta" sütunu ortalamayla).

**Ölçülen (114 hafta, 8 ayrık 13 haftalık pencere, 21.000 kolon):**

    kupon     hafta P(15)    HEDEF   pencere aralığı   gözlenen
        1         %7,489    %64,2       %53,4–74,9        7/8
       27        %10,003    %75,2       %66,0–84,3        8/8
       81        %10,489    %77,0       %68,1–85,5        7/8
      729        %11,034    %78,8       %69,9–86,7        8/8

Üç şey çıktı:

1. **Hedef tek sayı değil, aralık.** %69,9–%86,7; haftalar arası `P` **on
   altı kat** ayrışıyor (%2,3 ↔ %37,2).
2. **§3.67–3.71'in işi hedef kademesinde 14,6 puan etti** (%64,2 → %78,8).
   Haftalık `P`de ×1,47 olan kazanç hedefte ×1,23 — fark **doymadır** ve
   doyma bu bölümün asıl bulgusu.
3. **Yaklaşıklık tek yöne yanlıydı** (Jensen, 0,6–0,7 puan düşük).
   `coklu_kiyasi.py` kesin hesaba çevrildi, §3.67'nin iki tablosu yeniden
   koşuldu.

### Zamanlama ekseni: açıldı ve KAPANDI

"Parayı iyi haftalara yığ" fikri aritmetiğe de makul geliyordu (güçlü
haftanın mutlak marjinal getirisi zayıfınkinin iki katı). Üst sınırdan
ölçüldü: `ufuk.kahin_tahsisi` bütün pencerenin eğrilerini **önceden bilerek**
dağıtıyor — uygulanamaz, dolayısıyla hiçbir gerçek kural onu geçemez.
Ölçülen: 8 pencerede ortalama **×1,031**, en çok ×1,051. Sebebi tek cümle:
`1 − Π(1 − p)` **doyar**. Haftalık sabit bütçe artık bir varsayım değil
**ölçülmüş bir tercih**.

### Operasyon sorusu küçüldü

Açık duran tek engel operasyondu ve şimdi hedefin kendi para biriminde
fiyatlandı: 729 kupona çıkmanın toplam kazancının (14,6 puan) **%75'i 27
kuponda**, **%88'i 81 kuponda** alınıyor. Donan kayıt zaten 81 kuponluk,
yani 729'a çıkmanın hedefe katkısı **1,8 puan**. Soru kapanmadı ama
küçüldü — operasyon 81'de takılırsa kaybedilen ölçülmüştür.

### Yan işler

* `spor_toto/ufuk.py` + `tests/test_ufuk.py` (9 bekçi) + `scripts/ufuk_kiyasi.py`.
* `kahin_tahsisi` yeni bir çözücü yazmıyor: hedef `Σ −log(1 − p_w)` ve bu
  §3.71'in sırt çantasının aynısı, o yüzden `coklu._ust_kabuk` +
  `_tahsis_kabuklu` yeniden kullanılıyor.
* `pencereler`/`ufuk_ortalamasi` tek gövdede; iki betik de onu çağırıyor.
* `ufuk.py` kapının doctest listesine girdi.

Belge zinciri: test 1.965 → **1.974**, dosya 74 → 75, betik 38 → 39,
README §7 modül ağacı 57 → 58.

### Sıradaki adım

1. **6. hafta geldiğinde `--yaz` ile dondur.**
   `coklu_kupon.py --hafta N --butce 21000 --tavan 81 --yaz`.
2. **5. haftanın sonucu girildiğinde ilk ileriye dönük satır okunacak.**
3. **Operasyon** — artık fiyatlı. Gerçek soru "729 kupon yatırabilir miyiz"
   değil, **"81 kuponu güvenle yatırabiliyor muyuz"**; 729'un üstü 1,8 puan.
4. **Sönüm ekseni.** Dördüncü örneklem 2026/27 birikimiyle kendiliğinden
   geliyor.
5. **Kapanan iki başlık:** değişken derinlik (§3.72) ve zamanlama (§3.73).
   İkisinin de yeniden açılma şartı ölçülmüş olarak yazılı.

### Neden böyle

Bu oturum bir kazanç aramadı, **hedefi ölçtü**. Proje bir yıldır haftalık
sayılar üretiyordu ve sahibinin sorduğu soruya ("üç ayda olur mu") hiç
doğrudan cevap vermemişti. Artık cevap var, aralığıyla ve okuma kuralıyla:
bugünkü planla **%77**, ve kalan üç serbest değişkenin ikisi (şekil,
zamanlama) ölçülerek kapandı. Geriye operasyon ve modelin kendisi kalıyor.

## Geçmiş girdiler

**2026-09-13 (önceki, aynı dal)** — değişken derinlikli eksen (§3.72) kuruldu,
ölçüldü ve **beklenti yanlandı**: kuponlar artık eminlik sırasının ön ek
ağacında bir antizincir (sabit derinlik özel hâli, yani arama üst küme), ama
kazanç binde birler (×1,0001–×1,0003, 570/570 geri gidiş yok). Niçin'i de
ölçüldü ve sezgisel içermiyor: sabit derinlikli plan bu ailede **yerel en
iyi** (aynı yuva sayısında en iyi takas binde 0,23). Plan eksen kütlesinin
%83,3'ünü terk ediyor ve bu bir fırsat değil — kapatmak kupon yuvası da
harcıyor. Aynı oturumda kendi ilk sürümümdeki bir ölçüm hatası yakalandı
(`λ` ikili araması yanlış hedefe koşuyor, aday dejenere tek sisteme
düşüyordu) ve `tahsis_kiyasi.py` `degisken_derinlik=False`a alındı ki
§3.71'in tablosu tek mekanizmayı yalıtsın.

**2026-09-13 (önceki, dal `claude/devam-edelim-q99bac`)** — kupon başına
**ayrı** alt sistem bütçesi (§3.71). Arama ayrılabilir bir sırt çantası
çözüyor (`_tahsis`, cephenin üst konveks kabuğunda açgözlü): gerçek bütçede
729 kuponda %10,602 → %11,031 (×1,041), serbest küme tavanının %94,1'inden
%97,9'una. 570 kıyasın 570'inde geri gidiş yok (tek tip aday aramada kaldı,
referans gövde `scripts/tahsis_kiyasi.py::tek_tip_arama`). Aynı oturumda
eksen kuralı ilk kez ölçüldü (ters sıra ×0,755, tek takas ×1,0002),
`en_iyi_secim` cephenin son noktası oldu, arama 0,63 → 0,38 sn/haftaya indi
ve bağlı sayıların hepsi yeniden ölçüldü.

**2026-09-13 (önceki, aynı dal)** — bağımsızlık varsayımı çoklu kupon
kesitinde ölçüldü (§3.70). `kuyruk.kapsama` §3.46'nın tek faktörünü üç
sembole taşıdı (rütbe eşikleri → favori göstergesinde ikili modelin birebir
aynısı, `ρ` yeniden kalibre edilmedi); kupon başına ikili eşik kurma yolu
reddedildi ve bekçisi yazıldı. Ölçülen: oran **gerilemedi, büyüdü** (×1,42 →
×1,48 en kötü makul `a`da), 0/114 haftada çoklu plan geride, mutlak değerler
%12'ye kadar şişiyor. Aynı oturumda `coklu.p_alt`ın ham sözlükten okunması
düzeltildi (binde 0,3'lük sayı yalanı, arama sıralamasını da
oynatabiliyordu), §3.46'nın senaryo tablosundaki bayat satır yeniden ölçüldü
ve `scripts/setup.sh`e `--ignore-installed blinker` yedeği eklendi (uzak
oturumda kurulum bitmiyordu).

**2026-09-13 (önceki)** — çoklu kupon üretim hattına bağlandı (§3.69):
`coklu_kupon.py --yaz` planı `hafta_NN_coklu.json` olarak donduruyor, kayıt
kuponların kendisini taşıyor ve `super_toto_degerlendir.py` onu tek sistemle
aynı gövdeyle puanlıyor. **5. hafta sonuç görülmeden donduruldu** (81 kupon ×
243 kolon, `P(15/15)` %15,937 ↔ tek sistem %13,081). İlk dört canlı hafta
**aleyhte** çıktı (12+ kolon: tek sistem 194, çoklu 10; farkın neredeyse
tamamı 3. haftadan) ve "küçük bütçe rejimi" açıklaması ölçülüp **yanlandı**
(3.888 kolonda da 12+ kolon 5.309 → 8.673). `n = 4` hiçbir şey kanıtlamaz ve
bu cümle iki yöne de bakıyor.

**2026-09-13 (önceki)** — banko ekseni açıldı ve kapandı (§3.68).
Planın `P(15/15)` iddiası ilk kez plan düzeyinde sınandı: havuzlanmış 114
haftada model karamsar (tek sistemde 8,54 ↔ 15, ×1,76) ve bağımsız ölçülen
banko sapması açığı kapatıyor — **ama açık güncel değil** (2025/26'da 729
kuponda ×1,00; düzeltilmiş model o sezonda fazla iyimser olurdu) **ve karar
değişmiyor** (oynanan kupon 114/114 haftada birebir aynı). Sonuç:
`BANKO_Q_DUZELTMESI = 0,0` kalıyor, `P(15/15)` sayıları yeniden
ölçeklenmedi, beklemenin bedeli sıfır. Aynı oturumda §3.67 yazıldı (çoklu
kupon bulgusu yol haritasında hiç yoktu).


**2026-09-13 (önceki)** — çoklu kupon işi: `coklu.py` + 13 bekçi +
`coklu_kiyasi.py` + `coklu_kupon.py`. Çarpım kısıtı kalktı, `P(15/15)` aynı
bütçede ×1,45 (19.683 kolon), gerçek bütçede (21.000) ×1,42. Alt kademe
beklentisi **yalanlandı**: 12+ tutturan kolon 18.628 → 26.274 (+%41), yani
ödünleşme yok. Ayrıntı artık belgede: `docs/ISTATISTIK_YOL_HARITASI.md`
§3.67 (bu oturumda yol haritasına bağlandı) ve `coklu.py` başlığı.


**2026-09-13 (önceki)** — `docs/PROJE_GECMISI.md` yazıldı: 521 commit, ilk
commit'ten HEAD'e kronolojik, hash+tarih+mesaj+stat. Depo sığ klonlanmıştı,
`git fetch --unshallow` gerekti (yoksa yalnız 273 commit görünüyor). Aynı
oturumda bu devam notu mekanizması kuruldu.
