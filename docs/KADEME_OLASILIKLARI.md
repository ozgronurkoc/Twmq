# Kademe Olasılıkları — 15, 14, 13 ve 12'yi Tutturmak

**Tarih:** 2026-08-30
**Dal:** `claude/spor-toto-analysis-probability-eqeyz8`
**Ölçüm hattı:** `backend/scripts/kademe_analizi.py`
**Kesit:** 114 tam hafta (15 maçının hepsinde oran + resmî ikramiye tablosu),
4 sezon (2022/23 – 2025/26); arşiv tarafında 223 haftalık ikramiye tablosu

> Bu belge tek bir soruyla başladı: **"bu projeyle 15/15 yapma olasılığımız
> nedir?"** Cevap ölçüldü ve aşağıdadır. Soru büyüdüğü için 14, 13 ve 12
> kademeleri de aynı hatta bağlandı — para zaten orada.
>
> Belgedeki her sayı `python scripts/kademe_analizi.py` ile yeniden üretilir.
> Yeniden üretilemeyen bir sayı bu belgeye girmemiştir.

---

## 0. Özet — üç cümle

1. Proje, tek kolonda 15/15 olasılığını **1/14.348.907'den 1/16.416'ya**
   çıkarıyor: **874 kat**. Bu gerçek, ölçülmüş ve abartısız bir kazanç.
2. Ama 874 × (neredeyse sıfır) hâlâ neredeyse sıfırdır: gerçekçi bir
   bütçeyle (haftalık 150 TL) 15/15 olasılığı **%0,22**, yani ortalama
   **9 yılda bir**. 114 haftanın hiçbirinde gerçek sonuç modelin **ilk 64
   kolonu** içinde çıkmadı.
3. Projenin gerçek işi 15 değil **12–13**: aynı 150 TL'de 12+ tutturma
   olasılığı **%35,1**. Para da oradan geliyor.

**Ve bir uyarı:** aşağıdaki para bölümü (§5) bazı bütçelerde %100'ün
üstünde geri dönüş gösteriyor. Bu bir kâr vaadi **değildir** — nedeni §5.3'te
(beş madde ve bir durma kuralı) ve §9'da yazılıdır; okunmadan §5
kullanılmamalıdır.

---

## 1. Yöntem ve neden ayrı bir hat

Olasılıklar piyasa oranlarından `odds.implied_probs` ile, projenin
varsayılan marj arındırmasıyla (**`shin`**) üretilir. Hizalama doğrulandı:
2025/26 kesitinde Brier **0,5787** ve favori isabeti **%54,9** çıkıyor —
README §5.4'ün yayımladığı 0,579 ve %54,9 ile birebir aynı. Yani bu belgenin
sayıları arşivin bilinen sayılarıyla aynı temele oturuyor.

**`getiri.kupon_kademeleri` ile karıştırılmamalıdır.** O fonksiyon kademe
olasılıklarını *kaplama kodu* için hesaplar: 14-garanti veren, seçim
kümesinden küçük bir kolon altkümesi. 15/15 sorusu farklıdır — 15'i
tutturmak için seçim kümesinin **tamamını** oynamak gerekir. Bu belgedeki
bedeller o yüzden tam sistemin bedelidir (işaret sayılarının çarpımı) ve
kaplama koduyla kıyaslanamaz.

Bir hafta, işaretler `s_i` ve kaçak (küme dışına çıkan) maç kümesi `K` ise,
tam olarak `15-|K|-j` doğru yapan **kolon sayısı**:

```
e_j({s_i - 1 : i ∉ K})  ×  Π_{i ∈ K} s_i
```

`e_j` elemanter simetrik polinomdur. Kaçak maçlarda her işaret yanlıştır, o
yüzden çarpan olarak girerler. Bu sayım §5'te paranın temelidir: tam sistem
bir haftada 12'yi **bir kez değil yüzlerce kez** tutturur.

---

## 2. Tek kolonda 15/15

3^15 = 14.348.907 kombinasyonun **tamamı** her hafta için açıldı.

| | olasılık | ne demek |
|---|---:|---|
| Rastgele tek kolon | 1/14.348.907 | 275.940 yıl |
| **Modelin en iyi kolonu (ortalama)** | **1/16.416** | **316 yıl** |
| Medyan hafta | 1/27.093 | 521 yıl |
| En iyi hafta | 1/1.307 | 25 yıl |
| En kötü hafta | 1/200.998 | 3.865 yıl |

**Çarpan: 874x.** Ortalama en olası sembolün olasılığı %52,3'tür; 15 maçta
üst üste tutması gereken budur.

---

## 3. Gerçeğe karşı sınama — sonuç kaçıncı sıradaydı

§2 modelin kendi iddiasıdır. Asıl soru şu: 114 gerçek haftada, gerçekleşen
sonuç modelin olasılık sıralamasında **kaçıncı** sıradaydı?

| ilk N kolon | model diyor | **gözlenen** |
|---:|---:|---:|
| 1 | %0,01 | **0/114** |
| 256 | %0,62 | 3/114 (%2,6) |
| 1.024 | %1,67 | 5/114 (%4,4) |
| 4.096 | %4,20 | 13/114 (%11,4) |
| 16.384 | %9,78 | 21/114 (%18,4) |
| 65.536 | %20,77 | 33/114 (%28,9) |
| 262.144 | %39,50 | 63/114 (%55,3) |
| 1.048.576 | %65,34 | 88/114 (%77,2) |

**Gerçek sonucun medyan sırası: 205.612.** En iyi hafta 86. sıra.

İki okuma:

- **15/15 için:** tipik bir haftada doğru kolonu bulmak için ~205 bin kolon
  gerekirdi. Modelin ilk kolonu 114 haftada **hiç** tutmadı.
- **Beklenmeyen bulgu:** gözlenen kapsama, modelin dediğini **sistematik
  olarak aşıyor** (262.144'te %55,3 ↔ %39,5). Bu tek yönlü sapma
  açıklanmamıştır. Üç aday: (a) maçlar arası bağımsızlık varsayımı fazla
  temkinli, (b) 114 haftalık şans, (c) kesit yanlılığı (milli maç haftaları
  dışarıda). **Ayrıştırılmadan §5'in lehte sayıları buna yaslanmamalıdır.**

> **2026-09-05 — ayrıştırıldı.** Açık gerçek ve ölçüldü
> (`ISTATISTIK_YOL_HARITASI.md` §3.60): oynanan şeklin kesitinde
> (114 hafta, 14G, 2.000 TL) model %30,2 derken gerçekleşen %41,2 —
> **+%11,1 [+%2,1, +%20,0]**, sıfır dışında.
>
> * **(a) tek başına yetmiyor.** §3.46 hafta içi bağımlılığı ölçtü ve
>   korpus üst sınırında kuyruk yalnız **%5** şişiyor; açık onun iki katı.
> * **(c) zayıfladı.** İşaret 4/4 sezonda aynı yönde (+%10,2 · +%19,2 ·
>   +%13,3 · +%2,6).
> * **Mekanizma maç düzeyinde:** optimizatörün **banko** maçlarına
>   atadığı `q` gerçekleşenden **5,6 puan yüksek** (%37,3 ↔ %31,7, Wilson
>   [%28,6, %35,0] modelin `q`sunu dışarıda bırakıyor). Banko bir sıralama
>   dilimi değil ayrık bir karardır, yani bulgu ortalamaya dönüş eseri
>   olamaz.
> * **Denendi ve yetmedi:** global yeniden kalibrasyon (`kalibre_bias`,
>   §3.61) — kusur banda özgü, dönüşüm global.
>
> Bu paragrafın uyarısı **kalkmadı, daraldı**: açığın *varlığı* artık
> ölçülü, *kaynağı* hâlâ tam açıklanmış değil.

---

## 4. Kademe olasılıkları — asıl tablo

Tam sistem, bütçeye göre. Her hücrede **model diyor / gözlenen (114 hafta)**.

| haftalık | kolon | P(15) | P(≥14) | P(≥13) | P(≥12) |
|---:|---:|---:|---:|---:|---:|
| 15 TL | 9 | %0,04 / %0,0 | %0,46 / %0,0 | %2,52 / %7,0 | %8,76 / %19,3 |
| 30 TL | 18 | %0,07 / %0,0 | %0,74 / %2,6 | %3,74 / %8,8 | %11,99 / %21,9 |
| 75 TL | 28 | %0,10 / %0,0 | %1,00 / %4,4 | %4,83 / %11,4 | %14,83 / %27,2 |
| **150 TL** | 81 | %0,22 / %1,8 | %1,98 / %5,3 | %8,45 / %13,2 | **%22,94 / %35,1** |
| 300 TL | 162 | %0,36 / %1,8 | %2,95 / %7,9 | %11,55 / %18,4 | %28,85 / %39,5 |
| 750 TL | 486 | %0,77 / %2,6 | %5,51 / %11,4 | %18,76 / %25,4 | %41,08 / %52,6 |
| **1.500 TL** | 735 | %1,04 / %3,5 | %7,04 / %15,8 | %22,83 / %27,2 | **%47,45 / %57,0** |
| 3.000 TL | 1.458 | %1,59 / %5,3 | %9,78 / %19,3 | %28,84 / %33,3 | %55,11 / %65,8 |
| 15.000 TL | 6.599 | %4,05 / %11,4 | %20,15 / %28,1 | %48,24 / %56,1 | %75,98 / %88,6 |
| 30.000 TL | 19.683 | %7,47 / %12,3 | %31,26 / %43,9 | %63,61 / %72,8 | %87,48 / %93,9 |
| 96.000 TL | 58.991 | %13,22 / %21,1 | %45,70 / %54,4 | %78,40 / %86,8 | %95,16 / %97,4 |
| 270.000 TL | 177.147 | %22,37 / %29,8 | %62,62 / %71,9 | %90,33 / %95,6 | %98,97 / %99,1 |
| 810.000 TL | 531.441 | %36,24 / %46,5 | %79,69 / %85,1 | %97,49 / %99,1 | %100 / %100 |

**Bu tablonun okunuşu — kademeler arası uçurum.** Haftalık 150 TL'de:

- 15 tutturmak: %0,22 → ortalama **455 hafta** (≈ 9 yıl)
- 14 tutturmak: %1,98 → ortalama **51 hafta** (≈ 1 sezon)
- 13 tutturmak: %8,45 → ortalama **12 hafta**
- 12 tutturmak: %22,94 → ortalama **4 hafta**

**Her kademe inişi olasılığı ~3 kat büyütüyor.** 15'ten 12'ye inmek
olasılığı **104 kat** artırıyor. README §5.4'ün "haftaların %67'si 12+"
ölçümü bu tablonun içindedir ve doğrulanır: 3.000 TL bandında gözlenen
%65,8.

### 4.1 Bir yıl oynasak

Haftalık olasılıklar küçüktür ama bir sezon boyunca birikirler. 52 hafta,
model olasılığıyla, **en az bir kez** tutturma:

| haftalık | yıllık bedel | haftalık P(15) | **yıllık P(15)** | yıllık P(≥12) |
|---:|---:|---:|---:|---:|
| 150 TL | 7.800 TL | %0,22 | **%10,8** | ~%100 |
| 750 TL | 39.000 TL | %0,78 | **%33,3** | ~%100 |
| 1.500 TL | 78.000 TL | %1,04 | **%41,9** | ~%100 |
| 3.000 TL | 156.000 TL | %1,59 | **%56,6** | ~%100 |
| 15.000 TL | 780.000 TL | %4,05 | **%88,3** | ~%100 |

**Bu tablo yanıltıcı okunmaya en açık olanıdır.** "78.000 TL harcarsam
%42 ihtimalle 15 tutturacağım" doğrudur ama eksiktir: aynı yıl içinde
**medyan hafta %9 döndürür** (§5.2), yani parayı tutturana kadar
kaybedersiniz ve tutturduğunuz hafta ikramiye seyrelmiş olur (§6). Yıllık
olasılık bir *bilet sayısı* ölçüsüdür, bir kâr ölçüsü değil.

---

## 5. Para

### 5.1 Kademelerin payı

Resmî ikramiye tabloları, seyreltme modellenmiş (`havuz × m / (w + m)`;
`m` = o kademeyi tutturan kolon sayımız, `w` = kalabalığın kazananları).

| haftalık | 15'ten | 14'ten | 13'ten | 12'den |
|---:|---:|---:|---:|---:|
| 15 TL | %0,0 | %0,0 | %25,6 | **%74,4** |
| 150 TL | %33,9 | %18,1 | %18,9 | %29,0 |
| 1.500 TL | %36,8 | %17,7 | %19,8 | %25,7 |
| 30.000 TL | %33,2 | %22,1 | %21,0 | %23,7 |
| 810.000 TL | %47,7 | %19,3 | %15,9 | %17,2 |

Küçük bütçede paranın tamamı 12–13'ten gelir. Bütçe büyüdükçe 15'in payı
artar ama **hiçbir bütçede yarıyı geçmez**: 12+13+14 birlikte her zaman
paranın yarısından fazlasını taşır.

### 5.2 Haftalık geri dönüş — ortalamaya değil medyana bakın

> **YENİDEN ÖLÇÜLDÜ (2026-09-04) — kolon bedeli ₺1,50 değil ₺10.**
>
> Aşağıdaki tablo `getiri.VARSAYILAN_KOLON_BEDELI` (₺1,50, açıkça varsayım)
> ile hesaplanmıştı ve §5.3-4 bunu bir sınır olarak yazıyordu. Bedel üç
> bağımsız kökenden **₺10** olarak doğrulandı (ST EXTRA kupon ekranı ·
> bayi/resmî uygulama beyanı · sistem fiyat tablosunun 250 satırının 250'si
> de 10'un katı) ve `kademe_analizi.py` artık ölçülen bedeli kullanıyor.
>
> Getiri oranı bedele **ters orantılı** olduğu için aşağıdaki her sayı
> ₺10 ölçeğinde **6,67'ye bölünür**. Yeniden koşumun kendisi:
>
> | haftalık | **medyan** | ortalama | %25 | %75 | −1 hafta | −3 hafta | −5 hafta |
> |---:|---:|---:|---:|---:|---:|---:|---:|
> | 1.000 TL | **%0** | %42 | %0 | %5 | %30 | %19 | %13 |
> | 2.000 TL | **%0** | %39 | %0 | %8 | %32 | %21 | %16 |
> | 5.000 TL | **%0** | %54 | %0 | %11 | %30 | %20 | %17 |
> | 20.000 TL | **%3** | %37 | %0 | %15 | %29 | %20 | %19 |
> | 200.000 TL | **%5** | %44 | %1 | %21 | %25 | %20 | %20 |
> | 1.800.000 TL | **%8** | %47 | %2 | %27 | %42 | %38 | %35 |
> | 5.400.000 TL | **%6** | %49 | %2 | %42 | %42 | %32 | %29 |
>
> Ve bootstrap artık tek yönde konuşuyor:
>
> | haftalık | gözlenen | %95 aralık | **P(zarar)** |
> |---:|---:|---|---:|
> | 200.000 TL | %44 | [%17, %88] | **%99** |
> | 1.800.000 TL | %47 | [%30, %65] | **%100** |
> | 5.400.000 TL | %49 | [%28, %74] | **%100** |
>
> **§5.3'ün üç şartından (c) düştü:** en iyi 5 hafta çıkarılınca hiçbir
> bütçede %100'ün üstü kalmıyor — zaten hiçbir bütçede %100'e yaklaşan
> gözlenen getiri de yok. *"%100 üstü geri dönüş"* okuması **ölçek
> hatasıydı** ve kapandı.
>
> **Değişmeyen tek şey medyandır ve o zaten %0'dı.** Aşağıdaki tablo eski
> ölçekte doğrudur ve öyle bırakılmıştır — kayıt yeniden yazılmaz.



| haftalık | **medyan** | ortalama | %25 | %75 | −1 hafta | −3 hafta | −5 hafta |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 150 TL | **%0** | %277 | %0 | %36 | %193 | %109 | %61 |
| 750 TL | **%5** | %363 | %0 | %71 | %193 | %122 | %86 |
| 1.500 TL | **%9** | %293 | %0 | %51 | %174 | %121 | %91 |
| 3.000 TL | **%19** | %249 | %0 | %97 | %188 | %120 | %102 |
| 30.000 TL | **%35** | %290 | %9 | %137 | %162 | %119 | %108 |
| 270.000 TL | **%50** | %310 | %11 | %180 | %278 | %238 | %207 |
| 810.000 TL | **%38** | %324 | %10 | %281 | %273 | %201 | %168 |

`−k hafta` = en çok kazandıran k hafta çıkarılınca kalan geri dönüş.

**Bu tablonun tek önemli satırı medyandır.** Haftalık 150 TL oynayan biri
için **tipik hafta %0 döndürür** — hiçbir şey. Üst çeyrekte bile yatırdığının
ancak üçte birini geri alır. Ortalamanın %277 olması, 114 haftanın 3–5
tanesinin bütün seriyi taşımasındandır: 150 TL bandında en iyi **tek** hafta
çıkarılınca %277 → %193, üç hafta çıkarılınca %109, beş hafta çıkarılınca
**%61**'e düşüyor.

### 5.3 %100'ün üstündeki geri dönüş — neden bir kâr vaadi değil

Yüksek bütçelerde geri dönüş %300 civarında ve bootstrap %95 aralığı
100'ün üstünde kalıyor (270.000 TL: **%310**, GA [%203, %433]). Bu sayıyı
saklamıyoruz ama **kâr vaadi olarak okunması yanlıştır**:

1. **Ağır kuyruk bootstrap'i güvenilmez kılar.** Toplam kârın %34–55'i 114
   haftanın **3'ünden** geliyor. Yeniden örnekleme bu kadar tekil olayla
   aralığı olduğundan dar verir.
2. **Tek hafta izlendiğinde tablo normale dönüyor.** 2025/26 28. hafta
   elle izlendi: 531.441 kolon = 797.162 TL, dönen 388.729 TL — **%49**.
   Havuzun %0,3'ünü alıyoruz ve toplanan paranın ~%0,3'ünü koyuyoruz. Yani
   *tipik* hafta tam olarak kurum payı kadar kaybettiriyor.
3. **Sermaye ve dayanma süresi.** 810.000 TL/hafta bandında haftaların
   yalnızca ~%37'si kârda; en uzun kayıp serisi 17–18 hafta; gereken
   sermaye onlarca milyon TL.
4. ~~**Kolon bedeli doğrulanmadı.**~~ **KAPANDI (2026-09-04):** bedel ₺10, üç bağımsız kökenden. Eski metin: 1,50 TL, `getiri.py` CLI varsayılanıdır.
   Bütün para sonuçları buna **doğrusal** bağlıdır: 2,50 TL olsaydı her
   geri dönüş %40 düşerdi ve tablo büyük ölçüde %100'ün altına inerdi.
5. **§3'teki açıklanmamış sapmaya yaslanıyor.** Gözlenen kapsama modelin
   dediğini aşıyor; o fazlalık şansa aitse geri dönüşler düşer.

**Durma kuralı.** Bu eksende "üstünlük var" denebilmesi için üç şart:

| şart | bugün |
|---|---|
| (a) kolon bedelinin doğrulanması | **sağlanmıyor** — 1,50 TL bir varsayım |
| (b) §3'teki gözlenen ↔ model sapmasının açıklanması | **sağlanmıyor** |
| (c) en iyi 5 hafta çıkarılınca hâlâ %100 üstü | **kısmen** — 3.000 TL ve üstünde sağlanıyor (%102–207), altında sağlanmıyor (%61–91) |

(c)'nin yüksek bütçelerde sağlanması dikkate değerdir ve bu eksenin
kapatılmamasının sebebidir. Ama (a) ve (b) açıkken **tek başına yeterli
değildir**: (a) sağlanmazsa bütün tablo ölçek hatasıyla kayar, (b)
sağlanmazsa üstünlüğün kaynağı bilinmiyor demektir. Üçü birden
sağlanmadan bu belgeye "kâr edilebilir" cümlesi girmemelidir.

---

## 6. Seyreltme — projenin ölçülmemiş sınırı

**Bu, projenin bugüne kadar ölçmediği ve 15/15 hedefini asıl kısıtlayan
etkidir.**

| gerçek sonucun sırası | hafta | 15 bilen (medyan) | ikramiye (medyan) |
|---|---:|---:|---:|
| 1 – 1.000 | 5 | 1.167 | **13.228 TL** |
| 1.000 – 20.000 | 17 | 507 | 62.598 TL |
| 20.000 – 150.000 | 26 | 17 | 1.301.856 TL |
| 150.000 – 600.000 | 27 | 8 | 2.352.972 TL |
| 600.000 – 3.000.000 | 34 | 0 | **14.734.596 TL** |

**Spearman(sıra, 15 bilen sayısı) = −0,843.**

Model favorileri işaretler; kalabalık da favorileri işaretler. Bu yüzden
tuttuğunuz hafta, **herkesin tuttuğu haftadır**. Modelin en sevdiği bantta
kişi başı ikramiye 13.228 TL, en sevmediği bantta 14,7 milyon TL — **1.100
kat** fark.

Sonuç, tahmin katmanı için sert bir sınırdır: **tahmin gücünü artırmak
kazancı orantılı artırmaz**, çünkü olasılıkta kazanılanın büyük kısmı
ikramiyede geri verilir. Bu, README §1.1'in "yön doğru, miktar yetersiz"
teşhisine üçüncü bir boyut ekler: yön doğru olsa ve miktar yetse bile
**seyreltme** kazancı yiyor.

Bu ölçüm, `getiri.py`'nin `KALABALIK_MODELLERI` eksenini de doğruluyor:
kalabalık modeli bir süs değil, sonucun işaretini belirleyen bileşendir.

---

## 7. Devir haftaları — olumsuz sonuç

Havuz devrettiğinde (önceki hafta 15 bileni yok) o hafta oynamak avantajlı
mı? Müşterek bahiste bilinen bir +BD durumudur, sınandı:

| haftalık | devirli hafta (25) | normal hafta (89) |
|---:|---:|---:|
| 30.000 TL | %236 | %306 |
| 270.000 TL | %485 | %261 |
| 810.000 TL | %285 | %334 |

**Tutarlı bir yön yok** — bütçeye göre işaret değiştiriyor. 25 haftada
gürültü baskındır. Bu eksen bugün **ölçülemez**; ayırt edilebilmesi için
belirgin biçimde daha çok devirli hafta gerekir.

---

## 8. Arşiv veri kalitesi — 32 anormal hafta

`data/sportoto_arsiv/*.json` içinde **223 haftanın 32'sinde** 12. kademe
kazanan sayısı medyanın (41.516) onda birinden az. Örnek: 2024/25 42.
haftada 12. kademede **13** kazanan ve 951.224 TL kişi başı ikramiye
görünüyor — normal bir Spor Toto haftasının şekli bu değildir.

**Etkisi somuttur:** bu haftalar elenmeden alınan kademe ortalaması, tek bir
rastgele kolonun beklenen değerini 1,50 TL'ye karşı **4,99 TL** gösteriyor
(yani %332 geri dönüş — imkânsız). Elendikten sonra medyan haftada **0,122
TL**, yani **%8**; ortalama haftada %45. Bu ikincisi kurum payıyla
uyumludur.

`kademe_analizi.py` bunları `anormal_haftalar()` ile işaretler. **Öneri:**
`sportoto_arsiv` okunurken aynı denetim `data_quality` bloğuna bağlanmalı —
README §1.3'ün doktrini tam olarak budur ve bu eksen bugün denetimsizdir.
Bu belgenin §5 sayıları 15. kademeden hesaplandığı için kirlenmemiştir
(kazancın %0'ı anormal haftalardan gelir), ama kademe ortalaması alan her
gelecek hesap kirlenir.

---

## 9. Sınırlar

- **114 hafta, 4 sezon.** Küçük örneklem; §5'in kuyruk ağırlıklı sayıları
  buna çok duyarlı.
- **Milli maç haftaları kesit dışı** (oran yok). Kapsama hiçbir zaman %100
  olmayacak — README §5.3.
- **Piyasa oranı ≠ iddaa oranı.** Seviye tutmaz, yapı tutar; olasılıklar
  piyasa oranından gelir, iddaa marjı (%17,2) hesaba girmez.
- **Kolon bedeli 1,50 TL doğrulanmadı** (§5.3-4).
- **Seyreltme tek yönlü modellendi:** kendi kolonlarımızı ekliyoruz ama
  kalabalığın davranışının bizim oynamamızdan etkilenmediğini varsayıyoruz.
  Küçük bütçelerde geçerli, 531.441 kolonda tartışmalı.
- **Bağımsızlık varsayımı.** Kaçak dağılımı Poisson-binomdur; maçlar arası
  bağımlılık ölçülmedi ve §3'teki sapmanın adaylarından biridir.

---

## 10. Sonuç

**Sorulan soruya cevap: bu projeyle 15/15'i güvenilir biçimde
yapamazsınız.** Haftalık olasılık gerçekçi bütçelerde %0,2–1,6 bandındadır;
bir yıl boyunca oynanırsa %11–57'ye çıkar (§4.1) ama bu bir *bilet sayısı*
ölçüsüdür, kâr değil — o yılın medyan haftası yatırılanın %0–19'unu
döndürür (§5.2). 114 haftalık gerçek veride modelin en iyi kolonu **hiç**
tutmadı. Projeyi 874 kattan çok daha iyi hale
getirseniz bile §6'daki seyreltme kazancı yiyor: 15/15 bir mühendislik
problemi değil, bir piyangodur.

**Projenin gerçekten yaptığı şey 12–13 kademesidir** ve orada ölçülmüş,
gerçek bir yetenek var: 150 TL'de %35 ihtimalle 12+, 3.000 TL'de %66. README
§1.6'nın "kazanmayı garanti etmez" satırı yerinde duruyor; bu belge onu
sayıyla dolduruyor.

**Bu belgeden çıkan üç iş** (öncelik sırasıyla):

1. **Seyreltme ölçümünü ürüne bağla** (§6). Bugün hiçbir yerde görünmüyor;
   oysa kademe seçimini belirleyen etki bu. `getiri.py`'nin kalabalık
   ekseniyle birleşir.
2. **Arşiv anormal hafta denetimi** (§8). `data_quality` bloğuna bağlanmalı;
   bugün sessizce ortalamaları bozuyor.
3. **§3'teki gözlenen ↔ model sapmasını ayrıştır.** Bağımsızlık varsayımı mı,
   şans mı, kesit yanlılığı mı — §5'in bütün lehte sayıları buna dayanıyor.
