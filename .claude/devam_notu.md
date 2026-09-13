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

**2026-09-13 — dal `claude/devam-edelim-w8mob0`**

### Bu oturumda ne yapıldı — **operasyon** fiyatlandı (§3.74)

Not'un sıradaki adımlarından 1 ve 2 veriye bağlı (5. haftanın sonucu girilmedi,
6. hafta yok). Açık duran tek iş **operasyondu** ve §3.73 onun yalnızca
yarısını fiyatlamıştı: 81'de takılmanın bedeli hedefte 1,8 puan. Fiyatlanmayan
yarısı sorunun içindeki "**güvenle**" kelimesiydi — 81 kupon elle giriliyor.

**Önce bir gövde hatası çıktı.** `coklu.p_onbes` **oynanan** kuponu
puanlayamıyor: olasılıkları topluyor ve bu yalnızca kuponlar ayrıkken doğru.
Bir kupon iki kez girilirse ayrıklık bozulur ve toplam aynı kolonu iki kez
sayar — ölçüldü, sapma **tek yöne**: gerçek %9,563 iken `p_onbes` %9,601
diyor. Yani denetim en çok ihtiyaç duyulduğu anda iyimser.
`operasyon.birlesim_p_onbes` kolonları tek tek sayıyor.

**Ölçülen (114 hafta, 21.000 kolon, tek slipin o haftanın `P`si içindeki payı):**

    tavan   P(15/15)  hedef   atlama/kopya      takas          fazla
       27     %10,00  %75,2   +3,70 | +44,23   +2,33 | +41,62   −0,85
       81     %10,49  %77,0   +1,23 | +42,76   +0,79 | +39,53   −0,28
      243     %10,81  %78,1   +0,41 | +35,93   +0,27 | +31,98   −0,09
      729     %11,03  %78,8   +0,14 | +26,59   +0,09 | +26,04   −0,03

Üç şey çıktı:

1. **`fazla` işaret `P`yi YÜKSELTİYOR**, bedeli parada: 81 kuponda tek bir
   fazla işaret **+65.610 TL** (bütçenin %31'i).
2. **Ortalama küçük, en kötü 35 kat büyük** — ve sebebi yoğunlaşma:
   **81 kuponun ortalama 11'i hedefin yarısını taşıyor** (en kötü haftada 2).
3. **Eşikler uzak.** 81 → 729 çıkmak ancak **11 kuponda 1** yanlış
   işaretlenirse zarara dönüyor; 81'i özensiz girmek 729'un kazancını ancak
   13 kuponda 1 hatada geri veriyor. Yani operasyon hatası **hiçbir kararı
   değiştirmiyor**.

### Ölçüm kâğıtta kalmadı — kayda girdi

Yoğunlaşmadan çıkan kural ("kuponları olasılığa göre azalan sırala, ilk kümeyi
iki kez oku") ancak girişi yapan kişinin elindeki dosyada varsa işe yarar.
`coklu_kupon.py` artık kuponları azalan sırada yazıyor ve `plan.denetim` bloğu
en büyük payı + yarıyı taşıyan kupon sayısını taşıyor. **Sıralama gerçek iş
yapıyor**: aramanın kendi çıktısı azalan değil (51 gerçek hafta × tavan
kıyasının 6'sında karışık). Donmuş beş kayıt tesadüfen sıralıydı; bekçi artık
artefaktın kendisini sınıyor.

### Yan işler

* `spor_toto/operasyon.py` + `tests/test_operasyon.py` (22 bekçi) +
  `scripts/operasyon_kiyasi.py`.
* Kayıplar **kapalı formdur ama kesindir** (örtüşme dâhil); bekçisi kolon
  kolon sayan `birlesim_p_onbes`e karşı koşuyor, biri gerçek arşiv haftasında.
* `_tekil_tanik` ikinci tanığı görünce duruyor — 729 kuponda yarım milyon çift
  var ve erken çıkış onu darboğaz olmaktan çıkardı.
* `operasyon.py` kapının doctest listesine girdi. `core.SEMBOLLER` yeniden
  kullanıldı (ilk sürümde kopyalanmıştı).
* Belge zinciri: test 1.974 → **1.996**, dosya 75 → 76, betik 39 → 40,
  README §7 modül ağacı 58 → 59, §9'a `operasyon` satırı.

### Sıradaki adım

1. **6. hafta geldiğinde `--yaz` ile dondur.**
   `coklu_kupon.py --hafta N --butce 21000 --tavan 81 --yaz`. Kayıt artık
   `denetim` bloğuyla geliyor — giriş sırası orada yazılı.
2. **5. haftanın sonucu girildiğinde ilk ileriye dönük satır okunacak.**
   (5. hafta 2026-09-13'te donduruldu; **o kaydın üstüne yazma** — arama
   §3.71/3.72'den sonra iyileşti ve bugün yeniden koşulsa daha iyi bir plan
   veriyor, ama kaydın değeri donmuş olmasında.)
3. **Operasyonun kalan yarısı saf lojistik** ve bu depodan ölçülemez: bir
   insan 81 kuponu kupon kapanmadan girebiliyor mu? Ölçmek için giriş süresi
   kaydı gerekir. İstatistiksel yarısı kapandı.
4. **Sönüm ekseni.** Dördüncü örneklem 2026/27 birikimiyle kendiliğinden
   geliyor.
5. **Kapanan üç başlık:** değişken derinlik (§3.72), zamanlama (§3.73) ve
   operasyonun istatistiksel yarısı (§3.74). Üçünün de yeniden açılma şartı
   ölçülmüş olarak yazılı.

### Neden böyle

Bu oturum da bir kazanç aramadı, **bir riski fiyatladı**. Proje "81 kupon
yatırabilir miyiz" sorusunu bir yıldır açık tutuyordu ve soru aslında ikiydi:
*yatırabilir miyiz* (lojistik) ve *doğru yatırabilir miyiz* (ölçülebilir).
İkincisi ölçüldü ve cevabı rahatlatıcı — ama asıl çıktı rahatlama değil, iki
somut şey: `p_onbes`in oynanan kuponda yalan söylediğinin bulunması ve
kaydın artık denetlenebilir sırada yazılması.

## Geçmiş girdiler

**2026-09-13 (önceki, dal `claude/devam-edelim-51rff7`)** — **hedefin kendisi**
ölçüldü (§3.73). Deponun her ölçüsü haftalıktı, sahibinin hedefi değil; çeviri
(`1 − Π(1 − p_w)`) hiç yapılmamıştı. Ölçülen: 114 hafta, 8 ayrık 13 haftalık
pencere, 21.000 kolon — 1 kupon %64,2 · 27 kupon %75,2 · 81 kupon %77,0 ·
729 kupon **%78,8** (pencere aralığı %69,9–86,7, haftalar arası `P` on altı
kat ayrışıyor). §3.67–3.71'in işi hedef kademesinde **14,6 puan**; haftalık
×1,47 olan kazanç hedefte ×1,23 ve fark **doymadır**. Aynı oturumda zamanlama
ekseni açıldı ve **kapandı** (`ufuk.kahin_tahsisi` üst sınırı ×1,031 ortalama,
en çok ×1,051 — `1 − Π(1 − p)` doyuyor); yaklaşıklığın Jensen yanlılığı
ölçülüp `coklu_kiyasi.py` kesin hesaba çevrildi. `spor_toto/ufuk.py` +
`tests/test_ufuk.py` (9 bekçi) + `scripts/ufuk_kiyasi.py`.

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
