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

**2026-09-14 — dal `claude/proje-durumu-ilerleme-8h7l86`**

### Bu oturumda: varlık kanıtları arandı (§3.77) + duruş **kurala bağlandı**

Sahibi §3.76'nın dış taramasını yeterli bulmadı ve haklıydı: istediği bir
tarama değil bir **duruş**tu (*"hep böyle dışa dönük ol"*) ve bir soru
sormamıştım — *"dışarıda bu hedefe çoktan ulaşmış biri olabilir."*

**Arandı. Bulunan üç vaka ve niçin burada tekrarlanamadıkları:**
Benter (~1 mlr $, at yarışı) — orada **fiyatı kalabalık koyar**, burada doğa
koyar, kalabalık yalnızca ikramiyeyi böler; Ranogajec/Woods — kârın
belirleyicisi model değil **%8–13 iade**, Spor Toto'da iade yok; Mandel (14
piyango) — tam kaplama burada **₺143.489.070**, üç aylık bütçenin 52,6 katı.
Ve **bulunamayan** da bulgu: 1X2 havuzunu ölçülerek yendiği gösterilmiş tek
kişi/sendika/proje yok; bulunanlar ya para havuzlayan sendikalar ya iddia
satan platformlar (`sportoto.pro`, `Hedef15`, …) — ölçülmüş kayıt yok.

**Ve arama bir ÖLÇÜM üretti.** Mandel'in ikinci yarısı (*"doğru çekilişe
yığ"*) bu depoda hiç sorulmamıştı: zamanlama ızgarası 4 katta kesiliyordu,
pencereyi tek haftaya yığmak ise 13 kat. Izgara 13'e çıkarıldı (6,5 + 13,0),
kâhin yeniden koşuldu: **yeni basamakları bir kez bile kullanmadı**, kazanç
×1,0312'de kaldı. Sebep: hedef hafta içi harcamada **içbükey**. Eksen
kapandı — kâhin geçemiyorsa uygulanabilir hiçbir kural geçemez.

**Duruş kalıcı hâle getirildi** (asıl istenen buydu):
`.claude/skills/dis-tarama/SKILL.md` (yordam + fiyatlama tavanları + arama
kalıpları + tuzaklar), CLAUDE.md'ye "Depo dışına bakmak — varsayılan duruş"
bölümü (üç soru), ve bunun **bekçisi**
(`test_dis_tarama_durusu_CLAUDE_MDde_ve_becerisi_yerinde`) — kural budanırsa
suit kırmızıya döner.

### Ek ölçüm (aynı oturum): hedef bir **süre** sorusu (§3.78)

Sahibi *"bilimle ulaşabilir miyiz"* diye sordu. Hiç değiştirilmemiş tek
eksen ufuktu; aynı plan, aynı bütçe, yalnız süre: **13 hafta %77,0 · 26
hafta %94,9 · 39 hafta %99,0** (81 kupon; gözlenen 4/4 ve 2/2). Üç aydan
altı aya çıkmak **+17,9 puan** — kombinatorik eksenin tamamının yedi katı,
729 kupona çıkmanın on katı, en iyi model bulgusunun dokuz yüz katı.
Engel bilgi değil **takvim**. Süre sahibinin kararı; sayı kararı değil
**bedelini** veriyor.

### Sıradaki adım

1. **729 kupona çıkmanın operasyonu** — hâlâ birinci iş (+1,8 puan, 458,7
   slip). Giriş süresi kaydı sahibinden gelmeli.
2. 6. hafta geldiğinde `--yaz` ile dondur; 5. haftanın sonucu girilince ilk
   ileriye dönük satır okunacak (**o kaydın üstüne yazma**).
3. Denenmemiş tek veri kapısı: FootyStats Süper Lig xG — beklenen değeri
   §3.76'nın çeviri oranıyla peşinen düşük, ama kontrolü ucuz.
4. **Hedef para olursa** iki kapalı eksen anında açılır: kalabalıktan sapmak
   (Benter'in ekseni) ve çoklu kuponda entropi. Bu, dış taramanın en önemli
   koşullu bulgusu.

### Neden böyle

Bir duruş, bir oturumun iyi niyetine bırakılırsa bir sonraki oturumda yok
olur. Bu depoda kalıcı olan tek şey **bekçisi olan** şeydir — o yüzden dışa
dönüklük de bir dosyaya değil, bir teste bağlandı.

## Geçmiş girdiler

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
