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

**2026-09-13 — dal `claude/devam-edelim-51rff7`**

### Bu oturumda ne yapıldı — değişken derinlikli eksen (§3.72), ve **yanlandı**

Devam notunun 4. maddesi: *"eksen bugün sabit boyda; olası dalda daha çok,
olanaksız dalda daha az ayrıştıran bir karar ağacı tavan 27'deki %12,7'lik
açığın bir kısmını kapatabilir."* Bir **beklentiydi**. Aile kuruldu, ölçüldü,
beklenti **çıkmadı** — ve niçin çıkmadığı da ölçüldü.

Aile: kuponlar artık eminlik sırasının ön ek ağacında bir **antizincir**;
sabit derinlik bunun özel hâli, yani arama üst küme ve gerileyemez.
Büyütme fiyatlı (Lagrange `λ`) çünkü bölmenin değeri ancak para
fiyatlıyken görünür — eşit bölmek tanım gereği hiçbir şey kazandırmaz.

**Ölçülen (114 hafta, gerçek bütçe 21.000 kolon):**

    tavan   sabit derinlik   + değişken     kazanç   kapanan açık
       27         %9,9999     %10,0025   ×1,00026           %0,2
       81        %10,4879     %10,4892   ×1,00013           %0,2
      729        %11,0312     %11,0337   ×1,00023           %1,0

570 kıyasın 570'inde geri gidiş yok, ama kazanç **binde birler**. §3.71 aynı
sütunda %33–64 kapatıyordu; iki mertebe fark.

**Niçin — ve bu kısımda sezgisel yok.** Ağaç açgözlü olduğu için "aile boş"
ile "arama zayıf" ayrılmadan bulgu okunamazdı. Sabit derinlikli planın yaprak
kümesi bu ailenin bir üyesi olduğundan üstünde ailenin hamlesi **tek tek** ve
**kesin** denendi (en düşük olasılıklı yaprağı at + terk edilmiş en olası
düğümü koy, bütçeyi `_tahsis_kabuklu` ile yeniden dağıt, kupon sayısı sabit):
114 haftada ortalama **binde 0,23** (tavan 27). Yani sabit derinlikli plan
bu hamle kümesinde **yerel en iyi** — bulgu ailenin, aramanın değil.

Sabit derinlikli plan eksen kütlesinin **%83,3'ünü terk ediyor** ve bu bir
fırsat gibi görünüyordu; değil. Terk edilen kütleyi kapatmak hem kolon hem
**kupon yuvası** harcıyor ve marjinal getirisi derinleşmeninkiyle aynı yerde
buluşuyor. Tavan 27'deki %12,7'lik açık o hâlde **şekilden değil kupon
sayısından** geliyor — onu kapatan şey ölçülmüş olarak bellidir: daha çok
kupon.

### Yan işler

* **Bir ölçüm hatası yakalandı ve düzeltildi.** İlk sürüm `λ`yı bütçeyi tam
  harcayacak şekilde ikili aramayla buluyordu. Yanlış hedefti: bütçeyi zaten
  tahsis kesin harcıyor, `λ`nın işi ağacın **şeklini** seçmek. Üstelik bedel
  `λ`da süreksiz (ağaç bir anda köke iniyor) ve ikili arama dejenere tek
  yapraklı ağaçta duruyordu — aday sessizce **tek sistemin kendisi**
  oluyordu. Izgara doğrudan gerçek hedefi tarıyor.
* **`tahsis_kiyasi.py` artık `degisken_derinlik=False` ile koşuyor.** §3.71'in
  tablosu tek bir mekanizmayı yalıtmalı; ağacın kazancını ona karıştırmak iki
  bulguyu birbirine yedirirdi. §3.71'in sayıları bu yüzden **değişmedi**.
* **Cepheler tek yere toplandı** (`coklu._cepheler`, 16 DP) ve `_tahsis`
  genelleşti (`_tahsis_kabuklu`, kupon başına ayrı kabuk).
* **Bir bekçi yanlış kademedeydi ve düştü.**
  `test_tahsis_DAHA_OLASI_kupona_daha_cok_kolon` `q`yu `plan.eksen` üzerinden
  okuyordu; değişken derinlikte ortak eksen olmadığı için o yoldan okunan `q`
  bütün kuponlarda aynı çıkıyor ve test kendi ölçtüğü şeyi kaybediyordu.
  İddia zaten tahsise aitti; bekçi oraya indi.
* **Bağlı sayılar yeniden ölçüldü** (plan değiştiği için): §3.67 iki tablo,
  §3.68 banko duyarlılığı (taban satırları birebir aynı), §3.70 bağımlılık
  tabloları (iki bütçe). **Hiçbirinde hüküm değişmedi**, oynama dördüncü
  hanede. Kütükte yedi girdi güncellendi, üç yeni girdi açıldı.

Belge zinciri: test 1.959 → **1.965**, betik 37 → 38, README §9 Çoklu kupon
21 → 27.

### Sıradaki adım

1. **6. hafta geldiğinde `--yaz` ile dondur.** Akış değişmedi:
   `coklu_kupon.py --hafta N --butce 21000 --tavan 81 --yaz`.
2. **5. haftanın sonucu girildiğinde ilk ileriye dönük satır okunacak.** O
   kayıt eski aramayla donmuştu; kayıt bir koşum kaydıdır, yeniden
   hesaplanmaz.
3. **Operasyon hâlâ açık ve tek engel bu** — ve §3.72 onu bir derece daha
   sıkıştırdı: tavan 27 ↔ 729 arasındaki fark **şekille kapatılamıyor**, yani
   "kaç kupon fiilen yatırılabiliyor" sorusu artık planın tek serbest
   değişkeni. Kuponlar farklı boyda (gerçek bütçede ortalama 7,6 ayrı bedel);
   cevap bunu da kapsamalı.
4. **Sönüm ekseni.** Aynı imza üç ölçümde çıktı (§3.60, §3.64, §3.68);
   dördüncü örneklem 2026/27 birikimi ve haftalık sonuçla kendiliğinden
   geliyor.
5. **Kapanan başlık:** değişken derinlik. Yeniden açılmasının şartı ölçülmüş
   olarak bellidir — yerel sınavın hamle kümesi genişletilirse (çoklu takas)
   ya da iki kaynaklı (kolon + kupon) kesin bir ağaç DP'si yazılırsa. Ölçülen
   büyüklük mertebesi göz önüne alındığında ikisi de şu an hedefe götürmüyor.

### Neden böyle

Hedef 15/15, bütçe sabit, iş: **sabit kolon bütçesi altında `P(15/15)`'i
enbüyüklemek.** Bu oturum bir beklentiyi kapattı. Kazanç getirmedi ve
getirmemesi bulgunun kendisi: açık nerede **değil** olduğu artık ölçülü, ve
kalan tek serbest değişken operasyon. Ölçülmemiş bir umut listede durmaktansa
ölçülmüş bir "hayır" olarak kapanması yolu kısaltıyor.

## Geçmiş girdiler

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
