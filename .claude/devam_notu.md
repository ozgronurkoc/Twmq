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

**2026-09-13 — dal `claude/project-history-521-commits-bl5e4o`**

### Bulgu 1 — kuponun ŞEKLİ, modelden daha çok değer taşıyor

Depo kuponu **tek bir tam sistem** olarak kuruyordu (`secim.en_iyi_secim`,
Kartezyen çarpım, bedel `2^a·3^b`). İki kusur ölçüldü:

* **Amaç yanlış kademedeydi.** `secim.VARSAYILAN_KACAK_ESIGI = 3`, yani
  `P(en iyi kolon ≥ 12)` enbüyükleniyordu; modül başlığı bunu açıkça yazıyor:
  *"ikramiye eşiği 12'dir, 15 bir yan üründür."* Sahibinin hedefi 15.
  — **Ama ölçüldü ve bu tek başına bir şey değiştirmiyor:** 21.000 kolonda
  `esik=0` ile `esik=3` planları 114 haftanın **hiçbirinde** ayrışmadı.
  Sebebi bütçenin planı zorlaması (9 üçlü + 6 banko). Hipotez ölçümle düştü.

* **Asıl kusur çarpım kısıtının kendisi.** `N` kolonluk en iyi küme
  olasılığa göre en büyük `N` kolondur ve o küme bir **kutu değildir**.
  114 haftada, aynı 19.683 kolonda:

      tek sistem (çarpım)    P(15/15) = %7,489   gerçekleşen 15/114
      serbest (en büyük N)   P(15/15) = %10,865  gerçekleşen 22/114   ×1,45

  Serbest kümeyi birebir oynamak ~4.300 kupon ister (ölçüldü, medyan 4.290),
  ama kazancın çoğu birkaç düzine kuponda alınıyor.

### Yapılanlar

* `backend/spor_toto/coklu.py` — çoklu kupon planlayıcı. `d` maç **eksen**
  (kuponlar arası sabitlenir, en olası `M` bileşim oynanır) + kalan maçlar
  için ortak **alt sistem** (`en_iyi_secim` çözer). `M=1` bugünkü tek
  sistemin kendisi, yani arama mevcut davranışı bir aday olarak geziyor.
* `backend/tests/test_coklu.py` — 10 bekçi, hepsi geçiyor.
* `backend/scripts/coklu_kiyasi.py` — 114 haftalık kıyas koşumu.

**İki bekçi gerçek hata tuttu** (ikisi de yazılırken değil, koşarken):
`p_onbes` plandan ve kupondan iki farklı sayı veriyordu (bileşim indeksi ham
sembol düzeninde kurulup sıralama düzeninde çözülüyordu); ve ilk tasarım
eksen dışını **üçlüye zorluyordu** — `en_iyi_secim` daha iyisini buluyordu
(`P=0,1240` ↔ `0,1142`, üstelik 17.496 ↔ 19.683 kolon), çünkü üçüncü sembolü
küçük bir maçta **çifte** kapsamanın neredeyse tamamını yarı bedele alır.
Zorlama kaldırıldı.

### Kıyas koşuldu — sonuç (114 hafta, 19.683 kolon)

    kupon   model P(15)   gözlenen   13 hafta   12+ kolon
        1       %7,489      15/114     %63,7      18.628   ← bugün
       27       %9,353      20/114     %72,1      21.911
       81       %9,862      21/114     %74,1      24.131
      729      %10,461      22/114     %76,2      26.274
   19.683      %10,865      22/114     %77,6           —   ← üst sınır

**Alt kademe beklentisi yalanlandı.** Çoklu kuponun 12–13'ten bedel
alacağı varsayılmıştı; ölçüldü, **tam tersi**: 12+ tutturan kolon 18.628 →
26.274 (+%41). `coklu.py` başlığındaki yanlış cümle düzeltildi, kütüğe
"beklentiyi yalanladı" notuyla yazıldı. Ödünleşme yok.

Kütüğe dört sayı girdi ve **kütük bekçisi bir hatamı tuttu**: `deger`
alanı, anıldığı iddia edilen dosyada birebir geçmeli; ilk yazdığım bileşik
dizeler ("%7,489 model, 15/114 gerceklesen") hiçbir yerde geçmiyordu.
Girdiler deponun biçimine çevrildi.

### Sıradaki adım

1. Sonraki eksen: **banko kalibrasyonu.** Plan `P(15/15) = Π p₁` biçiminde
   olduğu için en emin maçların olasılık doğruluğu doğrudan çarpan.
   `ISTATISTIK_YOL_HARITASI` §3.64 bankoda modelin `q`sunun gerçekleşenden
   5,6 puan yüksek olduğunu ölçmüş ve kaynağı T1 Süper Lig'e indirmiş; etki
   sönüyor (son sezon +%0,3) ve düzeltme uygulanmamış. Yeniden açılacak.
2. **Haftalık üretim hattına bağla.** `coklu_plan_serisi` henüz yalnızca
   kıyas betiğinden çağrılıyor; `scripts/super_toto_hafta.py` hâlâ tek
   sistem kuruyor. Oynanan kupon değişmeden bu bulgu kâğıt üstünde kalır.
3. **Bağımsızlık varsayımını sına.** `P(15/15)` çarpımı maçları bağımsız
   sayıyor; `kuyruk.py` korpus üst sınırında kuyruğun %5 şiştiğini ölçmüş.
   Oran dayanıklı ama mutlak sayı bu varsayıma bağlı — çoklu kupon
   kesitinde yeniden ölçülmeli.
4. Operasyon: 27–729 kupon tek haftada fiilen yatırılabiliyor mu, hangi
   kanaldan? Sahibi "çözeriz" dedi, o yüzden plan **tavansız** kuruluyor;
   tavan ortaya çıkınca `VARSAYILAN_KUPON_TAVANI` ona göre ayarlanır.

### Neden böyle

Hedef 15/15 ve bütçe sabit. O hâlde iş iyi tanımlı: **sabit kolon bütçesi
altında `P(15/15)`'i enbüyüklemek.** Model iyileştirmesi bu çarpanın
içindeki `p`leri kıpırdatır; kümenin şekli ise çarpanın kendisini
değiştiriyor ve ölçülen kazanç (×1,45) hiçbir model değişikliğinden
alınmadı. O yüzden sıra önce şekilde, sonra kalibrasyonda.

## Geçmiş girdiler

**2026-09-13 (önceki)** — `docs/PROJE_GECMISI.md` yazıldı: 521 commit, ilk
commit'ten HEAD'e kronolojik, hash+tarih+mesaj+stat. Depo sığ klonlanmıştı,
`git fetch --unshallow` gerekti (yoksa yalnız 273 commit görünüyor). Aynı
oturumda bu devam notu mekanizması kuruldu.
