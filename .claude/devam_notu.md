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

Sahibi projeyi teknik olarak devretti. **Hedef: Spor Toto'da 15/15.**
Bütçe **haftada 210.000 TL** (₺10 kolon → 21.000 kolon). Kâr/zarar açıkça
**ölçüt değil**; sahibi bunu bilerek ve yazılı olarak istedi. Karar sormadan
alınacak.

> **GÜNCELLEME (2026-09-14): üç aylık kısıt gevşedi.** Sahibi *"süre
> sıkıntın olmasın"* dedi. Cümle iki anlama da gelebilir (çalışma temposu ↔
> hedefin ufku); ikisi de aynı yöne baktığı için **ufuk kısıtı bağlayıcı
> değil** varsayıldı. Farklı kastedildiyse tek düzeltilecek şey budur ve
> ölçümlerin hiçbiri boşa gitmez — §3.78 hedefi ufuk ufuk veriyor.
>
> Bunun iki sonucu ölçüldü: hedef **13 hafta %77,0 → 39 hafta %99,0**
> (§3.78), fatura **39 haftada −₺4,51 M** (§3.79).
>
> **İKİNCİ GÜNCELLEME (2026-09-14): toplam bütçe tavanı da yok.** Sahibinin
> sözü: *"Toplam bütçe tavan yok."* Bu ikisi birlikte hedefin türünü
> değiştiriyor — haftalık `P > 0` olduğu sürece tavansız oynayan **kesin**
> tutturur. *"Ulaşabilir miyiz"* kapandı; kalan iki soru ölçüldü (§3.80):
> hedefin kendisi **ortanca ₺42.649** ödüyor (tutturduğumuz haftalarda
> ortanca 528 kişi daha tutturuyor), ve bugünkü bütçede ilk isabete kadar
> beklenen brüt harcama **₺1,86 M** (beklenen 8,9 hafta, %90 için 19,3).
>
> **ÜÇÜNCÜ GÜNCELLEME (2026-09-14): haftalık tavan yine ₺210.000.**
> Sahibi cepheyi kendi seçti. Yani üç parametre de artık sabit ve yazılı:
> **haftalık ₺210.000 · toplam tavan yok · süre tavanı yok.** Cephede
> karar verilecek bir şey kalmadı; beklenen 8,9 hafta, %90 için 19,3 hafta,
> beklenen brüt ₺1,86 M (net ≈₺1,03 M).

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

**2026-09-14 — dal `claude/match-analysis-coupon-page-p7w5dd`**

### Bu oturumda: `/kupon` sayfası — **1. aşama (giriş tablosu) ayakta**

Sahibi yeni bir sayfa istedi ve zinciri kendi cümlesiyle kurdu: *15 satır ·
elle maç ve 1/0/2 oranı · oran analizinden veri çek · kupon oluştur · en
mantıklı seçenekler · **tüm liglerin** sonucu · açılış/kapanış ve
shin/güç/orantılı seçilebilsin.*

Plan taslağı sunuldu, **kararlar sahibine soruldu ve sahibi "anlatacağım"
dedi** — yani olasılık kaynağı (piyasa ↔ karne ↔ karışım), kuponun nerede
üretileceği, bütçe ve §6.1'in sırası **HENÜZ KARARA BAĞLANMADI**. Sahibi
uygulamalı anlatmayı tercih etti; o yüzden yalnızca zincirin ilk halkası
yazıldı.

Yazılanlar: `frontend/lib/kupon.ts` (saf: doğrulama · marj · favori ·
kalıcılık), `frontend/components/kupon/izgara.tsx` (15×6 ızgara, Tab satır
boyunca / ok-Enter sütun boyunca), `frontend/app/kupon/page.tsx`, kenar
çubuğu kaydı, README/replit/ARCHITECTURE_NEXT sayfa tabloları.

Kapılar: `npm run lint` · `npm run typecheck` · `node scripts/check.mjs`
(57 → **60** denetim; yeni üçü `lib/kupon.ts`'i tutuyor) · `npm run build`
geçti. Marj denetimi uydurma değil: 5. haftanın 1. maçının (1.26/6.48/13.54)
marjı beslemedeki ölçülmüş `0.0218` ile karşılaştırılıyor.

### Sıradaki adım

**Sahibi anlatmaya devam edecek** — 2. aşamanın (satır başına `/api/benzer`
sorgusu) şekli onun anlatacağı akışa göre kurulacak. Ölçülmemiş olarak
duran ve karara bağlanmayı bekleyen dört şey yukarıda yazılı.

Teknik olarak hazırda bekleyenler değişmedi: 729 kuponun operasyonu (§3.75),
6. haftada `--yaz` ile dondurma, kesintisiz 13 haftalık pencere çıkınca
§3.81'in öbeklenme sınavı.

### Neden böyle

Girdinin şekli (hangi alanlar, hangi doğrulama, neyin kalıcı olduğu)
sonraki bütün halkaları belirliyor; önce o şekil elle denenir, sonra
üstüne sorgu bağlanır. Sayfanın kendisi hiçbir şey **doldurmuyor**: depo
5. haftanın Pinnacle oranlarını taşıyor ama sahibinin gireceği fiyat iddaa
bülteninden gelecek ve ikisi aynı değil — hazır tablo, kullanıcının başka
bir bültenle çalıştığını gizlerdi.

## Geçmiş girdiler

### 2026-09-14 — dal `claude/proje-durumu-ilerleme-8h7l86`

### Bu oturumda: parametreler kilitlendi, **son açık varsayım sınandı** (§3.81)

Sahibi haftalık tavanı ₺210.000'de bıraktı. Üç parametre de sabit artık
(haftalık ₺210.000 · toplam tavan yok · süre tavanı yok) ve §3.80'in
cephesi tek satıra indi. Geriye sahibinin ilgilendiği **tek** sayı kaldı:
*ne kadar sürer* (8,9 hafta beklenen, %90 için 19,3).

O sayı tek bir ölçülmemiş varsayıma dayanıyordu — **haftalar arası
bağımsızlık** — ve bu oturumda sınandı (`scripts/haftalar_arasi.py`, yeni
hat). Aranan şey heterojenlik değil (o zaten modelde), **artık** bağımlılık:

* `p` serisi gecikme-1: **r = +0,1852**, permütasyon %95 null
  [−0,206, +0,213], p = 0,0842 → geçmedi.
* İsabet öbeklenmesi: 4 haftada 23 ↔ null [13,0 · 27,0]; 8 haftada 3 ↔
  [0,0 · 4,0] → geçmedi.

Holm'lu ikisi de geçmedi → **ön kayıtlı kurala göre eksen kapandı**,
bekleme sayıları duruyor. **Ama kapanışın iki sınırı var ve ikisi de
çıktıya yazılı:** (1) ilişki sıfır *ölçülmedi*, sıfırdan **ayrılamadı** ve
işaret **pozitif** — gerçek olsaydı kuyruğu uzatırdı; (2) sınav yalnız 4 ve
8 haftalık pencerede koşabildi, ilgilendiğimiz 13–26 hafta arşivde
kesintisiz bulunmadığı için **hiç sınanmadı** ("ÖLÇÜLEMEDİ" satırı bekçili).

**Yan ölçüm, iyi haber:** model `p` %10,489 (E 9,5 hafta) ↔ gerçekleşen
%18,421 (E 5,4 hafta). §3.68 bu açığı ölçtü ve *"güncel değil"* dedi, o
yüzden hüküm arada — ama bugünkü tablo **muhafazakâr** taraftan yazılı.

### Sıradaki adım

Karar tarafında bekleyen bir şey **kalmadı**; sıradakiler teknik:

1. **729 kupona çıkmanın operasyonu** — birinci iş (+1,8 puan **ve**
   +₺7.660/hafta). Engel: 458,7 slip; giriş süresi kaydı sahibinden.
2. 6. hafta geldiğinde `--yaz` ile dondur; 5. haftanın sonucu girilince
   ilk ileriye dönük satır okunacak (**o kaydın üstüne yazma**).
3. **Kesintisiz 13 haftalık pencere çıkınca** §3.81'in öbeklenme sınavı o
   boyda tekrarlanır (yeniden açılma şartı yazılı).
4. Havuz ekseni (§3.51) `n = 3`te; sönüm ekseni birikmeyi bekliyor.
5. **Bant sabiti İKİYE AYRILDI — dokunmadan önce oku** (favori karnesi işi,
   dal `claude/favori-match-statistics-tp6lg4`). `odds.FAVORI_BANTLARI`
   **modelin** sınırlarıdır: `recalibrate.KADEMELER` içinde `"bant"`
   *oturtulan* bir kademe, yani sınırlar oynarsa model başka kovalarla
   yeniden oturur ve ona bağlı bütün ölçümler sessizce değişir. Rapor
   tablosunu incelttiğimde önce bu sabiti değiştirdim ve
   `test_recalibrate::test_bant_sinirlari` kırmızıya döndü — kusuru o
   yakaladı. Arayüzün sınırları ayrı: `FAVORI_BANTLARI_RAPOR` (8 bant).
   İkisini "aynılaştırmak" akla yatkın görünüyor ve **yapılmamalı**;
   raporun modelin *inceltmesi* olduğunu bir bekçi tutuyor.

### Neden böyle

Üç parametre kilitlenince proje bir "karar" işi olmaktan çıkıp bir
**yürütme** işine döndü. Bu oturumda yapılan son şey, yürütmenin dayandığı
tek ölçülmemiş varsayımı sınamaktı — geçti, ama nerede sınanamadığı da
yazıldı. Bundan sonrası hafta biriktirmek ve 729 kuponun operasyonu.


**2026-09-14 (önceki, aynı dal)** — iki tavan da kalktı (§3.80): hedef
**kesin**, soru fiyatı ve süresi. 15/15 tutturunca alınan **ortanca
₺42.649** (o haftalarda ortanca 528 kazanan daha var); bütçe cephesi
kuruldu (`butce_egrisi.py`): bütçe büyüdükçe bekleme kısalır, beklenen
harcama büyür.

**2026-09-14 (önceki, aynı dal)** — ufuk açıldı, **fatura ölçüldü**
(§3.79): görev ölçeğinde ROI **0,449** (729 kuponda 0,486), hafta başı
net −₺115.541, 39 haftada −₺4,51 M. Ölçerken bulgu: **devir haftası
bizim haftamız değil** — 26 devir haftasının **0'ında** tutturmuşuz
(beklenen 4,79; p = 0,0023). `scripts/coklu_karne.py` + 7 bekçi.

**2026-09-14 (önceki, aynı dal)** — varlık kanıtları arandı (§3.77:
Benter/Ranogajec/Mandel, üçü de burada tekrarlanamıyor), **yığma ekseni**
ölçülüp kapandı (kâhin 13 kat seçeneği varken kullanmadı, ×1,0312), ve
dış bakış **kurala** bağlandı (`dis-tarama` becerisi + CLAUDE.md +
bekçisi). Ayrıca §3.78: hedef bir **süre** sorusu — 13/26/39 hafta →
%77,0 / %94,9 / %99,0.

**2026-09-14 (önceki, aynı dal)** — **iki tavan ölçüldü** (§3.76):
kombinatorik eksenin tamamı **+2,6 puan** (81 kupon %77,0 → serbest küme
%79,6; 1,8'i yalnızca 729 kupon), ve model ekseninde **1 hedef puanı =
0,02–0,047 Brier** — projenin piyasayı geçen tek bulgusu (Betfair,
ΔBrier −0,00100) hedefte ≈0,02 puan. `scripts/bilgi_esnekligi.py` +
`ufuk_kiyasi.py --serbest` + 9 bekçi + `docs/DIS_UFUK_TARAMASI.md`.
Yön: kalan tek gerçek kaldıraç matematik değil **operasyon**.

**2026-09-13 (önceki, dal `claude/devam-edelim-sltxrg`)** — **kupon ≠ slip**
ölçüldü (§3.75). "81 kupon = 81 slip" sessiz bir varsayımdı ve yanlıştı: tek
konumda ayrışan iki kutu **özdeş** olarak birleşiyor (sapma ≤ 7,2·10⁻¹⁶).
Ölçülen (114 hafta, 21.000 kolon): tavan 81'de 81 kupon → **60,1 slip** (en
kötü 75), kutucuk 1.945 → 1.447; en büyük birleşmiş slip 6.561 kolon, deponun
zaten tek giriş saydığı kuponun üçte biri. Asıl bulgu: **tahsis birleşmeyi
öldürüyor** (tekdüze 27,5 ↔ tahsisli 60,1 slip, ×2,19) — ama §3.71 **ayakta**:
tahsisin hedefteki +2,22 puanı zarara dönmek için 1 slipte 5 (takas) ya da 1
slipte 9 (atlama) hata ister. `coklu_kupon.py` artık kayda `slipler` yazıyor,
özdeşlik donmuş artefaktın üstünde bekçili. Yan iş: `sadelestirme.py` + 24
bekçi + `sadelestirme_kiyasi.py`.

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
