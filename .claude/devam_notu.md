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

**2026-09-13 — dal `claude/devam-edelim-sltxrg`**

### Bu oturumda ne yapıldı — **kupon ≠ slip** (§3.75)

Not'un sıradaki adımlarından 1 ve 2 hâlâ veriye bağlı (5. haftanın sonucu
girilmedi, 6. hafta yok) ve 4 birikmeyi bekliyor. Açık duran tek iş 3'tü ve
"saf lojistik, bu depodan ölçülemez" diye kapatılmıştı. O cümle bir şeyi
**sormadan doğru kabul ediyordu**: *81 kupon 81 slip demek.*

Demek değil. Planın kuponları birer kutudur; iki kutu **bir tek** konumda
ayrışıyorsa o konumdaki sembol kümeleri birleştirilip tek kutu yazılabilir.
Bu bir yaklaşıklık değil **özdeşlik**: aynı kolonlar, aynı kolon sayısı,
aynı `P(15/15)` (ölçülen sapma en çok 7,2·10⁻¹⁶). Değişen tek şey kaç kez
elle kutu doldurulacağı.

**Ölçülen (114 tam hafta, 21.000 kolon):**

    tavan  kupon   slip  en kötü     ×   kutucuk →          ×   en büyük slip
       27     27   21,5       26  1,26   701 →   561     1,25    6.561 kolon
       81     81   60,1       75  1,35 1.945 → 1.447     1,34    6.561 kolon
      243    243  162,6      215  1,49 5.290 → 3.550     1,49    6.561 kolon
      729    729  458,7      632  1,59 14.295 → 9.003    1,59    2.187 kolon

En büyük birleşmiş slip (6.561 kolon) deponun bir yıldır **tek giriş**
saydığı tek sistem kuponunun (19.683) üçte biri — iddia yeni bir varsayım
getirmiyor.

### Asıl bulgu: **tahsis birleşmeyi öldürüyor**

İki kutu ancak bir tek konumda ayrışıyorsa birleşir. §3.71 her kupona ayrı
alt sistem bütçesi verdiğinden alt sistemler de ayrışıyor ve ayrışan iki
kupon **hiç** birleşmiyor. Tavan 81'de: tahsisli 81 → 60,1 slip (×1,35),
tekdüze 79,1 → 27,5 (×2,88), yani tahsis **×2,19 slip** demek. Tavan 27'de
kupon sayısı aynı (27,0 ↔ 27) ve fark **tamamen** birleşmeden geliyor.

**Karar: §3.71 ayakta.** Tahsisin hedefteki kazancı +2,22 puan (%76,98 ↔
%74,76), bedeli 32,6 fazla slip; zarara dönmesi için **1 slipte 5** (takas)
ya da **1 slipte 9** (atlama) hata gerekir — bu özensizlik değil, girişin
hiç yapılmamış olması demektir. Tavan kararı da değişmedi ve biraz
rahatladı: §3.74'ün 81 → 729 eşiği kupon cinsinden %9,06 iken slip
cinsinden **%10,52**.

### Ölçüm kâğıtta kalmadı — kayda girdi

`coklu_kupon.py` artık kayda `slipler` listesini de yazıyor (`kuponlar`
plandır, ölçümler onun üstünden koşar) ve bastığı tablo artık sliplerdir.
`denetim` bloğu slip sayısını, kutucuk sayısını ve sliplerin kendi
yoğunlaşmasını taşıyor. Özdeşlik iki yerde sınanıyor ve ikincisi asıl
olan: yazarken sesli patlıyor **ve artefaktın kendisinde**
(`test_coklu_kaydinin_SLIPLERI_ayni_kolonlari_oynuyor` donmuş dosyaları
tarar) — §3.74'ün sıralama dersi birebir buydu.

### Yan işler

* `spor_toto/sadelestirme.py` + `tests/test_sadelestirme.py` (24 bekçi) +
  `scripts/sadelestirme_kiyasi.py`.
* Gövde **grup birleştirme** (her turda en çok kazandıran konum, fixpoint'e
  kadar). İkişer birleştirme sıraya duyarlıydı (5. haftada 60 rastgele
  sırada en iyisi 30, bu gövde 25); dilim ayrıştırması 26 buluyor ama
  tahsisli planda nokta kümesi 19.683'e çıktığı için koşamıyor. Işın
  araması (8 ve 40) hiçbir haftada iyileştirmedi.
* `en_az_slip` kesin enküçüğü arıyor (yalnız bekçi için) ve ölçülen dört
  küçük ailede açgözlü sonuçla **eşit** çıktı.
* `coklu_kupon.py`nin "kullanım" satırı düzeldi: `M × kolon` yazıyordu ve
  §3.71'den beri kupon bedelleri eşit değil, yani çarpım bir yalandı.
* Belge zinciri: test 1.996 → **2.021**, dosya 76 → 77, betik 40 → 41,
  README §7 modül ağacına `sadelestirme`, §9'a katman satırı.

### Sıradaki adım

1. **6. hafta geldiğinde `--yaz` ile dondur.** Kayıt artık `slipler`
   bloğuyla geliyor — girilecek kutular orada yazılı.
2. **5. haftanın sonucu girildiğinde ilk ileriye dönük satır okunacak.**
   (5. hafta 2026-09-13'te donduruldu; **o kaydın üstüne yazma.**)
3. **Operasyonun kalan yarısı küçüldü ama kapanmadı.** Soru artık "bir
   insan 81 kupon girebiliyor mu" değil "**60 slip** girebiliyor mu", ve en
   büyüğü deponun zaten tek giriş saydığı kupondan küçük. Ölçmek için hâlâ
   giriş süresi kaydı gerekiyor.
4. **Sönüm ekseni.** Dördüncü örneklem 2026/27 birikimiyle kendiliğinden
   geliyor.
5. **Kapanan dört başlık:** değişken derinlik (§3.72), zamanlama (§3.73),
   operasyonun istatistiksel yarısı (§3.74) ve slip yükü (§3.75). Dördünün
   de yeniden açılma şartı ölçülmüş olarak yazılı.
6. **Çürük iddia — karar bekliyor (2026-09-14).** "Beraberlik hiçbir maçta
   favori olmaz" iki yerde yazılı (`spor_toto/odds.py` `season_1x2_summary`
   yorumu, `components/istatistik/charts.tsx:824` arayüz metni) ve birleşik
   kesitte **yanlış**: `cross["0"]["0"] == 1` (2023_24 h42 m7,
   Kayserispor–Konyaspor, p₀=0,3735). İddianın bekçisi yoktu, o yüzden
   sessizce yanlış kaldı. Düzeltme yapılmadı — sahibi karar verecek.

### Neden böyle

Bu oturum yeni bir kazanç aramadı, **kapatılmış bir sorunun içindeki
varsayımı** sorguladı. "Ölçülemez" denen şey ölçülemezdi; ölçülebilir olan,
onun yanında sessizce doğru kabul edilen sayıydı. Çıktı iki şey: yükün
gerçek sayısı, ve §3.71'in ölçülmemiş bedelinin ilk kez fiyatlanması —
fiyat kararı değiştirmedi ama artık biliniyor.

## Geçmiş girdiler

**2026-09-13 (önceki, dal `claude/devam-edelim-w8mob0`)** — **operasyon**
fiyatlandı (§3.74). Önce bir gövde hatası çıktı: `coklu.p_onbes` **oynanan**
kuponu puanlayamıyor (olasılıkları topluyor, bu yalnız kuponlar ayrıkken
doğru) ve sapma tek yöne bakıyor — gerçek %9,563 iken %9,601 diyor, yani
denetim en çok ihtiyaç duyulduğu anda iyimser; `operasyon.birlesim_p_onbes`
kolonları tek tek sayıyor. Ölçülen (114 hafta, 21.000 kolon): `fazla` işaret
`P`yi **yükseltiyor** ve bedeli parada (81 kuponda +65.610 TL, bütçenin
%31'i); ortalama slip küçük ama en kötüsü 35 kat büyük ve sebebi yoğunlaşma
(**81 kuponun ortalama 11'i hedefin yarısını taşıyor**, en kötü haftada 2);
eşikler uzak — 81 → 729 çıkmak ancak 11 kuponda 1 hatada zarara dönüyor.
Hüküm: operasyon hatası **hiçbir kararı değiştirmiyor**. Yoğunlaşmadan çıkan
denetim sırası kayda girdi (`coklu_kupon.py` kuponları azalan yazıyor,
`plan.denetim` bloğu) ve bekçi **artefaktın kendisini** sınıyor — aramanın
çıktısı azalan değildi (51 hafta × tavan kıyasının 6'sında karışık).
`spor_toto/operasyon.py` + 22 bekçi + `scripts/operasyon_kiyasi.py`.

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
