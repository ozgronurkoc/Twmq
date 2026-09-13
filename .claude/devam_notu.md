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

### Bu oturumda ne yapıldı — çoklu kupon üretim hattına bağlandı (§3.69)

Devam notunun 1. sıradaki adımı buydu: `coklu_kupon.py` planı üretiyordu ama
hiçbir yere **yazmıyordu**, yani §3.67'nin ×1,45'i 114 haftalık geri testte
kalıyordu ve ileriye dönük tek bir tanık bile birikmiyordu.

**Kurulan hat.** `coklu_kupon.py --yaz` planı `hafta_NN_coklu.json` olarak
donduruyor (git'e girer); `super_toto_degerlendir.py` onu **tek sistemle
aynı gövdeyle** puanlıyor (`kupon_degerlendir`, her kupon için). Kayıt
kuponların *kendisini* taşıyor, tarifi değil — §3.65'in 2. Tahmin satırı
motoru söküldüğü için bağımsız doğrulanamıyor ve o hata tekrarlanmadı;
`p_onbes` kaydın kolonlarından yeniden ölçülüyor
(`test_coklu_kaydi_KENDINI_dogruluyor`).

**5. hafta SONUÇ GÖRÜLMEDEN donduruldu** (81 kupon × 243 kolon = 19.683,
`P(15/15)` %15,937 ↔ tek sistem %13,081, tavansız %17,242). İleriye dönük
tanıkların birincisi bu; git geçmişi `results_known: false` ile doğruluyor.
1–4. haftalar da donduruldu ama sonuç girildikten **sonra**, ve kayıtları
bunu ilan ediyor.

### Ölçülen ve BEKLENTİYE TERS çıkan şey

İlk dört canlı haftada, her hafta o haftanın **kendi** kolon bütçesinde:

    en iyi kolon toplamı   tek sistem 47   çoklu 45
    12+ kolon              tek sistem 194  çoklu 10
    13+ kolon              tek sistem 28   çoklu 0

Model dördünde de çoklu kuponu önde gösteriyor (×1,24 · ×1,57 · ×1,34 ·
×1,47); gerçekleşen göstermiyor. Farkın neredeyse tamamı 3. haftadan:
tek sistem 14/15 tutunca 864 kolonun 178'i 12+ oldu, çoklu plan 11/15.

**Bir açıklama denendi ve yanlandı.** "Bütçe rejimi farklı, çoklu kupon
küçük bütçede kademe tarafında bedel ödüyor" hipotezi ölçüldü
(`coklu_kiyasi.py --butce 3888`, 114 hafta) ve tam tersi çıktı: küçük
bütçede de 12+ kolon 5.309 → **8.673** (+%63), gerçekleşen 15/15 4/114 →
11/114. Yani dört haftalık ters sonuç gürültü. `n = 4` hiçbir şey
kanıtlamaz — ve bu cümle iki yöne de bakıyor.

### Yan işler

* **Kütüğün komut şeması bekçisizdi.** Geçen oturumda `komutlar`a yanlış
  alan adıyla (`ne`, `ne_yapar` değil) girdi ekledim; şema kapısı yalnızca
  `sayilar`a baktığı için yeşil geçti ve kusur `graf_sorgu.py komut <terim>`
  çağrısında **KeyError ile çökerek** çıktı. Düzeltildi ve bekçisi yazıldı
  (`test_kutuk_KOMUT_girdilerinin_semasi_TAM`; kusuru geri koyup kırmızı
  olduğu doğrulandı).
* **`coklu.p_onbes` tip yalanı.** İmza `-> float`, gövde `np.float64`
  döndürüyordu. Sessiz kalmadı: kaydın JSON çıktısı `np.bool_` üzerinden
  `TypeError` attı. Düzeltildi, bekçisi var.
* `coklu_kiyasi.py` tablosu küçük bütçelerde **aynı satırı iki kez basmış
  gibi** görünüyordu (`kupon_ort` yuvarlanıyor); `tavan` sütunu eklendi.
* Belge zinciri: test 1.930 → **1.938**, README §9 Süper Toto 108 → 114,
  Çoklu kupon 13 → 14, Ölçüm kütüğü 5 → 6, §1 katman dökümü 39 → 45.

### Sıradaki adım

1. **6. hafta geldiğinde `--yaz` ile dondur.** Akış: `coklu_kupon.py
   --hafta N --butce 21000 --tavan 81 --yaz`, sonuç girilince
   `super_toto_degerlendir.py` kaydı kendiliğinden puanlar. Tanık ancak
   böyle birikir ve bu artık tek komutluk bir iş.
2. **5. haftanın sonucu girildiğinde ilk ileriye dönük satır okunacak.**
   Beklenti kurulmasın: bir hafta hiçbir şey söylemez. Kayıt oynanan kupon
   değil, o yüzden bu satır bir *karar* değil bir *tanık*.
3. **Operasyon hâlâ açık ve artık tek engel bu.** 81–729 kupon bir haftada
   fiilen yatırılabiliyor mu, hangi kanaldan? Kalibrasyon tarafında engel
   olmadığı §3.68'de ölçüldü; oynanan kuponu değiştirmek bu cevaba bağlı.
   Tavan ortaya çıkınca `coklu.VARSAYILAN_KUPON_TAVANI` ona göre ayarlanır.
4. **Bağımsızlık varsayımı, çoklu kupon kesitinde** (§3.46 korpusta ölçtü).
   §3.68 havuzlanmış açığın marjinal sapmayla kapandığını gösterdi, yani
   bağımlılık taşıyıcı sebep değil — ama mutlak değerin ikinci kaynağı o.
5. **Sönüm ekseni.** Aynı imza üç ölçümde çıktı (§3.60, §3.64, §3.68);
   dördüncü örneklem 2026/27 birikimi ve haftalık sonuçla kendiliğinden
   geliyor.

### Neden böyle

Hedef 15/15, bütçe sabit, iş: **sabit kolon bütçesi altında `P(15/15)`'i
enbüyüklemek.** Ölçülen en büyük kazanç kuponun şeklinde (×1,45) ve o
kazanç hâlâ oynanmıyor. Bu oturum onu oynanır hâle getirmedi — operasyon
cevabı yok — ama **ölçülür** hâle getirdi: artık her hafta iki kayıt yan
yana duruyor ve aralarındaki fark hafta hafta birikiyor. Karar için gereken
şey buydu; dört haftanın aleyhte çıkması da tam olarak bu yüzden kayda
geçti, gizlenmedi.

## Geçmiş girdiler

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
