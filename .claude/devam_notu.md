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

**2026-09-13 — dal `claude/devam-edelim-q99bac`**

### Bu oturumda ne yapıldı — bağımsızlık varsayımı çoklu kupon kesitinde (§3.70)

Önceki notun 4. sıradaki adımı buydu. `coklu.py`nin "Sınır" bölümü şunu
yazılı bir **varsayım** olarak bırakmıştı: *"bağımlılık her iki şekli de aynı
yönde etkiler, oran görece dayanıklıdır"*. Cümlenin ikinci yarısı (mutlak
değerin varsayıma bağlı olduğu) §3.46'da ölçülmüştü; **birinci yarısı hiç
ölçülmemişti** ve §3.67'nin ×1,45'i tam olarak o yarıya dayanıyor.

**Kurulan makine.** `kuyruk.kapsama` §3.46'nın tek faktörünü üç sembole
taşıyor: `Z_i` sembolleri **rütbeye göre** kesiyor, yani favori
göstergesinde eşik birebir aynı kalıyor ve ölçülen `ρ → a` çevirisi yeniden
kalibre edilmeden geçiyor (bekçisi
`test_kapsama_FAVORI_gostergesi_IKILI_modelin_AYNISI`). Kupon başına ikili
eşik kurma yolu **reddedildi** — iç içe eşikler ayrık eksen sembollerini iki
kez sayar; bekçisi `test_kapsama_BUTUN_kolonlar_oynanirsa_bir` ve reddedilen
yol tam orada düşüyor. `ρ`nun belirlemediği tek parça (kötü haftada 2.↔3.
sembol paylaşımı) uydurulmadı, iki uç ayrı ayrı hesaplandı.

**Durma kuralı ölçüm görülmeden yazıldı ve ayrı commit'le mühürlendi**
(1316851): en kötü makul `a`da oran 1'in altına düşerse ya da bağımsız
orandan %10'dan fazla gerilerse eksen yeniden açılır.

**Ölçülen (114 hafta, 19.683 kolon):** oran gerilemedi, **büyüdü** —
×1,40 → ×1,45 (en kötü makul `a`, `rutbe`) / ×1,43 (`oransal`); 21.000
kolonda ×1,42 → ×1,46. **0/114 haftada** çoklu plan tek sistemin gerisine
düşüyor ve en iyi tavan her senaryoda 729'da kalıyor. Mutlak değerler
şişiyor ve **şekle göre farklı**: tek sistem ×1,075, 81 kupon ×1,101, 729
kupon ×1,113 — yani bağımlılık çoklu kupona biraz daha yarıyor. Eksen
kapandı; kapanan şey *"bağımlılık yok"* değil, *"olsa bile şekil kararını
çevirmiyor ve tavanı ölçüldü"*.

### Yan işler — ikisi de bir sayı yalanıydı

* **`coklu.p_alt` ham sözlükten okunuyordu** (`p_eksen` normalleştirilmiş
  matristen). Arşiv olasılıkları dört haneye yuvarlı ve satır 1,0001
  topluyor; `plan.p_onbes` aynı kuponu yeniden ölçen `p_onbes`ten binde
  0,3'e kadar sapıyordu, üstelik fazlalık adaylara **eşit binmediği** için
  aramanın sıralamasını da oynatabiliyordu. Kusur `kapsama`nın `a = 0`
  sağlaması yazılırken çıktı. Mevcut bekçi göremiyordu çünkü girdisi
  Dirichlet'ten geliyor (satır tam 1); yeni bekçi arşivin yuvarlamasını
  taklit ediyor ve düzeltme geri konup **kırmızı olduğu doğrulandı**. İki
  tablo yeniden koşuldu: basılan hanelerde hiçbir sayı değişmedi, değişen
  tek şey tavan 3'ün kupon ortalaması (2,5 → 2,4). Canlı haftalara
  değmemişti (kayıtların olasılıkları tam 1 topluyor) — bekçinin kusuru
  görememesinin sebebi de o.
* **§3.46'nın senaryo tablosunda bayat bir satır vardı.** Korpus üst sınırı
  22 ligli korpustan (`+0,00080`) kalmıştı; korpus daraltıldığında aynı
  tablonun kesit satırı güncellenmiş, senaryo satırı güncellenmemişti — tablo
  kendi kendisiyle çelişiyordu. Yeniden ölçüldü (`+0,00070`, `a = 0,0011`,
  `P(K≥14) = 9,293·10⁻⁴`); öteki iki satır birebir aynı, hüküm değişmedi.
* **`scripts/setup.sh` uzak oturumda kurulumu bitiremiyordu:** dağıtımın
  `python3-blinker`ı pip dışında kurulu ve RECORD'u yok, pip onu
  kaldıramadığı için kurulumun tamamı düşüyordu — `numpy` bile gelmiyordu.
  İkinci deneme eklendi (`--ignore-installed blinker`), gerekçe betikte.

Belge zinciri: test 1.938 → **1.949**, §1 katman dökümü 662 → 672, betik
35 → 36, README §9 Kuyruk 12 → 22 ve Çoklu kupon 14 → 15.

### Sıradaki adım

1. **6. hafta geldiğinde `--yaz` ile dondur.** Akış değişmedi:
   `coklu_kupon.py --hafta N --butce 21000 --tavan 81 --yaz`, sonuç girilince
   `super_toto_degerlendir.py` kaydı kendiliğinden puanlar.
2. **5. haftanın sonucu girildiğinde ilk ileriye dönük satır okunacak.** Bir
   hafta hiçbir şey söylemez; kayıt oynanan kupon değil, o yüzden o satır bir
   *karar* değil bir *tanık*.
3. **Operasyon hâlâ açık ve tek engel bu.** 81–729 kupon bir haftada fiilen
   yatırılabiliyor mu, hangi kanaldan? Kalibrasyon (§3.68) ve artık
   bağımlılık (§3.70) tarafında engel **yok**; oynanan kuponu değiştirmek bu
   cevaba bağlı. Tavan ortaya çıkınca `coklu.VARSAYILAN_KUPON_TAVANI` ona
   göre ayarlanır.
4. **Aramayı bağımlı hedefe göre koşmak** (§3.70'in açık bıraktığı yer).
   Bugünkü plan bağımsızlık altında kuruluyor; bağımlılık onu yalnızca
   yeniden fiyatlıyor. Tavanlar arası sıralama bağımlı hedefte de okundu
   (değişmiyor), ama `coklu_plan_serisi`nin `p_eksen · p_alt` çarpanlaması
   tam olarak bağımsızlıktan gelir ve aramanın kendisi ölçülmedi. Ölçülen
   sisme küçük olduğu için sıra bunda **değil**.
5. **Sönüm ekseni.** Aynı imza üç ölçümde çıktı (§3.60, §3.64, §3.68);
   dördüncü örneklem 2026/27 birikimi ve haftalık sonuçla kendiliğinden
   geliyor.

### Neden böyle

Hedef 15/15, bütçe sabit, iş: **sabit kolon bütçesi altında `P(15/15)`'i
enbüyüklemek.** Ölçülen en büyük kazanç kuponun şeklinde ve o kazanç hâlâ
oynanmıyor — engel operasyon. Bu oturum engeli kaldırmadı ama kazancın
**son ölçülmemiş dayanağını** ölçtü: şekil kararı bağımsızlık varsayımına
bağlı değil. Sırada duran soruların hiçbiri artık kalibrasyon ya da
varsayım tarafında değil; hepsi ya operasyon ya da hafta hafta biriken
tanık.

## Geçmiş girdiler

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
