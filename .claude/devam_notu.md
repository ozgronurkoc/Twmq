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

**2026-09-13 — dal `claude/devam-edelim-q99bac` (ikinci iş)**

### Bu oturumda ne yapıldı — kupon başına AYRI bütçe (§3.71)

Devam notunun listesindeki adımların hepsi dışarıya bağlıydı (6. hafta, 5.
haftanın sonucu, operasyon kanalı) ya da bilerek ertelenmişti. O yüzden
listede olmayan bir şey arandı ve bulundu: `coklu.py`nin kurduğu ailede
**bütün kuponlar aynı alt sistemi** oynuyordu ve bu ölçülmemiş bir kısıttı.

Hedef şu: `P(15/15) = Σ_j q_j · p_alt_j`. Bir kuponun alt sistemini
genişletmenin değeri `q_j` ile çarpılıyor ve `q_j` **iki mertebe** ayrışıyor
(hepsi favori ↔ 81. bileşim). Eşit bölmek, o hâlde, olası bileşime az
olanaksız bileşime çok vermek demek. Arama artık **ayrılabilir bir sırt
çantası** çözüyor.

**Ölçülen (114 hafta, gerçek bütçe 21.000 kolon):**

    tavan      tek tip   tahsisli   kazanç   kapanan açık
       27       %9,353    %10,000   ×1,069          %33,7
       81       %9,864    %10,488   ×1,063          %44,3
      729      %10,602    %11,031   ×1,041          %64,0
    serbest küme tavanı %11,272 → plan tavanın %94,1'inden %97,9'una

Yuvarlak bütçede (19.683) kazanç daha küçük (×1,016–1,031) ve **fark
ölçülebilir**: 21.000'de ikinci bir etken var — tek tip ailede bedel `M · c`
çarpımına sıkışıyor ve artan **harcanamıyor** (eski arama 21.000 kolonun
19.683'ünü kullanıyordu). `coklu.py` "bütçe merdiveni kalktı" diyordu; ölçüm
onu düzeltti, merdiven yarı yarıya kalkmıştı.

**570 kıyasın 570'inde geri gidiş yok** ve bu tanım gereği: tek tip aday
aramada kaldı, yani yeni arama eskisinin üst kümesi. Referans gövde
`scripts/tahsis_kiyasi.py::tek_tip_arama`da ve test onu **çağırıyor**.

**Arama ayrıca hızlandı:** `d` başına tek Pareto cephesi (16 DP), eskiden
`(M, d)` başına bir DP (128) → 0,63 → 0,38 sn/hafta.

### Yan işler

* **Eksen kuralı ilk kez sınandı.** `eksen_sec` "en emin `d` maç" diyor ve
  docstring'i bunu gerekçesiyle savunuyordu, ama ölçmemişti.
  `coklu_plan_serisi` bir `eksen_sirasi` parametresi aldı ve 20 haftada
  ölçüldü: ters sıra **×0,755**, tek takas araması ×1,0002 (7 takas). Kural
  doğru — artık varsayım değil ölçüm.
* **`en_iyi_secim` cephenin son noktası oldu** (`secim.secim_cephesi`): iki
  gövde tek gövdeye indi, bekçisi var.
* **Prototipte bir kusur çıktı ve bekçisi yazıldı.** Cephe `bütçe // M` ile
  çıkarılınca hiçbir kupon ortalamanın üstüne çıkamıyor ve kazanç **tam
  olarak sıfır** görünüyor. İlk koşum böyleydi ve "tahsis işe yaramıyor"
  diye okunabilirdi.
* **Bağlı sayıların hepsi yeniden ölçüldü** (plan değiştiği için): §3.67 iki
  tablo, §3.68 (banko duyarlılığı; tek sistem satırları birebir aynı), §3.69
  küçük bütçe bloğu, §3.70 bağımlılık tabloları. **Hiçbirinde hüküm
  değişmedi.** Kütükte sekiz girdi güncellendi, üç yeni girdi açıldı.

Belge zinciri: test 1.949 → **1.959**, betik 36 → 37, README §9 Karar
katmanı 42 → 46 ve Çoklu kupon 15 → 21.

### Sıradaki adım

1. **6. hafta geldiğinde `--yaz` ile dondur** — ve bu hafta donacak kayıt
   artık **tahsisli** plandır (aynı tavan, aynı bütçe, daha yüksek hedef).
   Akış değişmedi: `coklu_kupon.py --hafta N --butce 21000 --tavan 81 --yaz`.
2. **5. haftanın sonucu girildiğinde ilk ileriye dönük satır okunacak.** O
   kayıt eski aramayla donmuştu; kayıt bir koşum kaydıdır, yeniden
   hesaplanmaz.
3. **Operasyon hâlâ açık ve tek engel bu.** 81–729 kupon bir haftada fiilen
   yatırılabiliyor mu, hangi kanaldan? Tahsisli planda kuponlar **farklı
   boyda** (gerçek bütçede ortalama 7,6 ayrı bedel) — operasyon sorusunun
   cevabı bunu da kapsamalı.
4. **Değişken derinlikli eksen** (§3.71'in açık bıraktığı yer). Eksen bugün
   sabit boyda: bütün kuponlarda aynı `d` maç tekleştirilir. Tavan 729'da
   serbest kümeye kalan açık %2,1'e indi ama **tavan 27'de hâlâ %12,7** —
   yani az kuponla oynanacaksa masada değer var. Olası dalda daha çok,
   olanaksız dalda daha az ayrıştıran bir karar ağacı onu alabilir; bu yeni
   bir arama demek (`coklu_plan_serisi`nin çarpanlaması sabit `d`ye bağlı).
5. **Sönüm ekseni.** Aynı imza üç ölçümde çıktı (§3.60, §3.64, §3.68);
   dördüncü örneklem 2026/27 birikimi ve haftalık sonuçla kendiliğinden
   geliyor. §3.68'in yeniden ölçümünde 2025/26 oranı ×1,00 → ×0,96, yani
   imza aynı yerde.

### Neden böyle

Hedef 15/15, bütçe sabit, iş: **sabit kolon bütçesi altında `P(15/15)`'i
enbüyüklemek.** Bu oturum tam o işi yaptı — operasyon cevabı beklenirken
oynanacak planın kendisi iyileşti ve iyileşme **aynı parada, aynı kupon
sayısında**. Kalan başlık da ölçüldü ve nerede olduğu belli: az kuponlu
tarafta, ve onu alacak şey eksenin sabit boyundan kurtulmak.

## Geçmiş girdiler

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
