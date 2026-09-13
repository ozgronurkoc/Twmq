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

**2026-09-13 — dal `claude/devam-edelim-tkk1b8`**

### Bu oturumda ne yapıldı — banko ekseni açıldı ve **kapandı**

Devam notunun 1. sıradaki adımı "banko kalibrasyonu, yeniden açılacak"
diyordu. Açıldı ve ölçüldü; sonuç beklenenin tersi ve **karar değişmedi**.
Ayrıntı `docs/ISTATISTIK_YOL_HARITASI.md` §3.68, üretici
`cd backend && python scripts/banko_duyarliligi.py` (~9,5 dk).

Üç cevap, üçü de "hayır":

1. **Açık gerçek.** Planın `P(15/15)` iddiası ilk kez plan düzeyinde sınandı
   (Poisson-binom, 15/15 tutan **hafta sayısı** — maç düzeyi kapsamadan
   bağımsız bir istatistik). Havuzlanmış 114 haftada model **karamsar**: tek
   sistemde beklenen 8,54 ↔ gerçekleşen 15 (×1,76, iki yanlı 0,0444); 729
   kuponda 12,09 ↔ 20 (×1,65). Gerçek bütçede düz ölçekte ölçülen banko
   sapması (`p₁` −%5,8 düşük, `n = 684`) açığı **kapatıyor** (×1,05–1,25) ve
   o 5,8 bu sınava ayarlanmadı — ayrı bir istatistikten geldi.

2. **Ama açık GÜNCEL DEĞİL.** Sezon sınavı §3.64'ün imzasını verdi: 729
   kuponda ×2,24 · ×2,25 · ×1,65 · **×1,00**. Havuzlanmış sayı 2023/24'ten
   geliyor; 2025/26'da model zaten tutuyor ve **düzeltilmiş** model fazla
   iyimser olurdu (sapmalı cetvel 5,84 hafta bekliyor, gerçekleşen 4). Bu
   imzanın üçüncü görünüşü (§3.60, §3.64, şimdi bu).

3. **Karar hiç değişmiyor.** `tavan = 1`'de oynanan kupon **114/114**
   haftada birebir aynı. Çoklu şekillerde plan kıpırdıyor ama taban cetvelde
   hiçbir satırda iyileşmiyor (%9,353 → %9,289, gözlenen 20 → 17). Sıralama
   korunuyor, §3.67'nin ×1,45'i etkilenmiyor. Sebep mekanik: sapma, planın
   zaten en emin olduğu maçlara uygulanan neredeyse çarpımsal bir
   dönüşümdür ve adayları **yeniden sıralamaz** — kalibrasyon *sayıyı*
   değiştiriyor, *seçimi* değiştirmiyor.

**Sonuç:** `karne.BANKO_Q_DUZELTMESI = 0,0` kalıyor, durma kuralı
yürürlükte, ve belgelerdeki `P(15/15)` sayıları **yeniden ölçeklenmedi** —
havuzlanmış ×1,76'yla hepsini büyütmek 2023/24'ü geçmişe uydurmak olurdu.
Eklenen şey bir **okuma kuralı** (`coklu.py` başlığı).

Eklenen dosyalar: `spor_toto/duyarlilik.py`, `scripts/banko_duyarliligi.py`,
`tests/test_duyarlilik.py` (14 bekçi). Belge zinciri kapatıldı: test 1.916 →
**1.930**, dosya 73 → **74**, betik 34 → **35**, modül 56 → **57**; §3.67 de
bu oturumda yazıldı (çoklu kupon bulgusu yol haritasında hiç yoktu).

### Sıradaki adım

1. **Haftalık üretim hattı.** `scripts/coklu_kupon.py` haftanın oynanacak
   çoklu kuponlarını üretiyor, ama `scripts/super_toto_hafta.py` hâlâ tek
   sistem kuruyor. Oynanan kupon değişmeden §3.67 kâğıt üstünde kalır. Bu
   oturumun bulgusu şunu ekliyor: geçişin **kalibrasyon** tarafında bir
   engeli yok — sapma seçimi değiştirmiyor, yani karar yalnızca operasyon
   (kaç kupon fiilen yatırılabilir) sorusuna bağlı.
2. **Bağımsızlık varsayımı, çoklu kupon kesitinde.** §3.46 korpusta ölçtü
   (kuyruk üst sınırda %5 şişiyor) ama `P(15/15)` çarpımı çoklu kupon
   şeklinde yeniden ölçülmedi. Not: §3.68'in havuzlanmış ×1,76'sı bağımlılık
   **değil** marjinal sapmayla kapanıyor, yani bağımlılık bu açığın taşıyıcı
   sebebi değil — ama mutlak değerin ikinci kaynağı hâlâ o.
3. **Operasyon.** 27–729 kupon tek haftada fiilen yatırılabiliyor mu, hangi
   kanaldan? Sahibi "çözeriz" dedi, plan **tavansız** kuruluyor; tavan
   ortaya çıkınca `VARSAYILAN_KUPON_TAVANI` ona göre ayarlanır. Artık 1.
   maddenin de önkoşulu bu.
4. **Sönümün kendisi bir eksen.** Aynı imza üç ayrı ölçümde çıktı. Dördüncü
   bir örneklem (2026/27 birikimi) ya "piyasa keskinleşti"yi doğrular ya da
   üç ölçümün aynı gürültüyü gördüğünü. §3.64'ün durma kuralı (`n ≥ 300`)
   bunu zaten bekliyor; haftalık sonuç girildikçe kendiliğinden birikir.

### Neden böyle

Hedef 15/15, bütçe sabit, iş iyi tanımlı: **sabit kolon bütçesi altında
`P(15/15)`'i enbüyüklemek.** Bu oturum çarpanın *içindeki* `p`lere baktı ve
oradan kazanç **çıkmadığını** ölçtü — sapma gerçek ama güncel değil, ve
güncel olsa bile planı değiştirmiyor. O hâlde sıra geri şekle ve operasyona
dönüyor: kazancın ölçülmüş olduğu yer orası ve oynanan kupon hâlâ tek
sistem.

## Geçmiş girdiler

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
