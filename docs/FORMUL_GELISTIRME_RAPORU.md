# Formül Sayfası — Çalışma Raporu

Bu belge `/` (Formül) sayfasında yapılan **F0–F6** çalışmasının kaydıdır: neyin
ölçüldüğü, hangi kararın neden verildiği, yolda hangi hataların çıktığı ve neyin
bilerek yapılmadığı.

Sıradaki işler ayrı belgededir:
[`FORMUL_YOL_HARITASI.md`](FORMUL_YOL_HARITASI.md).

---

## 0. Özet

Sayfa motorun tamamını zaten açığa çıkarıyordu; eksik olan **motor değil, karar
desteğiydi**. Yedi iş yapıldı:

| # | İş | Bir cümlede |
|---|----|-------------|
| F0 | Bedel modu | `auto` modunda 8 kat abartılı olan "tahmini bedel" düzeltildi |
| F1 | Küme-içi koşulu | 14-garantinin koşulu üretmeden önce, canlı görünür oldu |
| F2 | Bayat sonuç | Girdi değişince sonucun eskiye ait olduğu söyleniyor |
| F3 | Sekmeler | 9 sekme → 5; motor bloğuna göre değil soruya göre |
| F4 | Maç kimliği | Izgarada takım adları; devirde kendiliğinden geliyor |
| F5 | Yerleşim | Yatay taşma, örtülen kontrol, mobilde kaydırma |
| F6 | Senaryo kıyası | Çalıştırılan modlar yan yana, doğruluk kurallarıyla |
| — | Kalıcılık | Kurulum tarayıcıya yazılıyor + paylaşılabilir bağlantı |

Yanında dört gerçek hata bulundu ve düzeltildi (§4), iki yerde **aynı sayının iki
kez gösterildiği** tespit edilip tekilleştirildi (§5).

Arayüzün o güne kadar **hiçbir otomatik kapısı yoktu**; CI'a `frontend` işi
eklendi ve saf mantık için 37 vakalık bağımlılıksız bir denetim yazıldı (§6).

---

## 1. Teşhis: sayfa neye göre kurulmuştu

Sonuç sekmeleri backend modüllerinin birebir yansımasıydı — Özet, Kupon, Dağılım,
Olasılık, Bayes, Markov, Hata frekansı, Fire, Log. Dokuz sekme, ama kullanıcının
dört sorusundan **ikisi üçe dörde dağılmıştı**:

| Soru | Cevabın dağıldığı yer |
|------|----------------------|
| Kaça mal olacak, ne garanti ediyor? | Özet ✓ |
| Kupona ne yazacağım? | Kupon ✓ |
| Seçimim ne kadar riskli? | Olasılık + Markov + Dağılım + Fire |
| Hangi maçı değiştirmeliyim? | Hata frekansı + Fire `by_match` + Markov `transitions` |

Bu, istatistik sayfasının G kolunda adı konmuş kök sorunun aynısıdır: sayfa
**veri kaynağına göre** bölünmüş, **soruya göre** değil
([`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md) §6).

### 1.1 Ölçülmüş en keskin bulgu

README'nin kendi örnek kuponu, `backend/scripts/check.sh`'ın kendi örnek
olasılıklarıyla çalıştırıldı:

```
P(seçim kümesi doğru sonucu içeriyor) = %0,0149   (~1/6.700)
P(15 doğru)                            = %0,002
```

Kaybın çoğu üç bankoda: 7. maç (p=0,20), 14. maç (p=0,25), 5. maç (p=0,40).
Diğer on iki maç birlikte %0,745 veriyor; **bu üç banko onu 50 kat kesiyor.**

Bu sayı, sayfanın en görünür ögesi olan büyük yeşil **"14-garanti VAR"**
kalkanının *koşuludur*. Kalkan doğrudur ama koşulludur ve koşulun olasılığı bir
sekme öteideydi, üstelik varsayılan olarak kapalıydı. Görmek için: olasılık
girişini aç → 45 hücre doldur → üret → 13 sn bekle → Olasılık sekmesini aç.

Bu, doğrudan §1.2'deki taahhüde ("belirsizlik saklanmaz, ölçülür ve gösterilir")
dokunan bir boşluktu ve F1'in gerekçesi oldu.

---

## 2. Yapılanlar

### 2.1 Kurulum kalıcılığı ve paylaşılabilir bağlantı (`1da72c5`)

Sayfa durumunu hiçbir yerde tutmuyordu: yenileme 15 maçın işaretlerini, 45
olasılık hücresini ve motor ayarlarını sıfırlıyordu.

Kurulum artık iki taşıyıcıya yazılır (`frontend/lib/kurulum.ts`) ve **ikisi ayrı
işe yarar**:

| | Yerel depo | Bağlantı |
|---|---|---|
| Ne zaman | her değişiklikte, kendiliğinden | yalnızca *Bağlantıyı kopyala* |
| Nerede | `localStorage`, yalnızca o tarayıcı | URL (~110 karakter) |
| Kayıp | yok (JSON) | olasılıklar binde bir + normalize; maç adları hiç girmez |

Öncelik **URL > yerel depo**: paylaşılan bağlantıyı açan kişi kendi eski
kurulumunun kalıntısını değil, gönderilen kurulumu görür. Devir paketi
(`?hafta=51`) bunlardan sonra çalışır ve yalnızca olasılıkların üzerine yazar —
hafta detayından gelenin işaretleri korunur.

**Sonuç kaydedilmez.** Sonuç türetilmiş veridir; kalıcı olan tek şey kullanıcının
elle ürettiği kurulumdur. Aynı gerekçe F6'daki senaryo listesi için de geçerlidir.

### 2.2 Bedel artık moda göre (F0)

Yapışkan çubuktaki "tahmini bedel" tek formülle hesaplanıyordu:

```js
mode === "fix16" && cifte >= 7 ? uzay / 8 : uzay
```

Üç ayrı durum vardır ve tek sayıya indirilemezler:

| Mod | Ne söylenir | Neden |
|---|---|---|
| `fix16` | kesin — `uzay / 8` | blok 2⁷ noktayı 16 satıra indirir |
| `bütçe` / `maxcov` | tavan — girilen bütçe | motor bütçeyi aşmaz |
| diğerleri | aralık — küre-kaplama alt sınırı … tam sistem | kesin sayıyı arama sonunda motor bilir |

Alt sınır istemcide hesaplanır (`⌈uzay / (1 + Σ(kᵢ−1))⌉`) ve sunucunun
`alt_sinir`'iyle birebir tutar — bu bir testtir, varsayım değil.

### 2.3 Üretmeden önce görülen koşul (F1)

`frontend/lib/kume-ici.ts` koşulu istemcide hesaplar (`∏ᵢ Σ_{s∈seçᵢ} pᵢ(s)`, 15
çarpma) ve işaretler değiştikçe canlı gösterir. Yanında maç başına kütle
çubukları ve **verime göre** sıralı ekleme önerileri durur — küme-içi kazancın
bedel artışına oranı, ikisi birlikte:

```
7.  + 1 ev sahibi   küme-içi ×3.50   bedel ×2.00   verim ×1.75
14. + 1 ev sahibi   küme-içi ×3.00   bedel ×2.00   verim ×1.50
```

Sunucuya gitmemesi bir optimizasyon değil, **ürün kararıdır**: sayı ancak canlı
olduğunda seçimi yönlendirir.

Kart bir mod ya da işaret **önermez**; kullanıcının kendi girdiği olasılıkların
çarpımını ve o çarpımı büyütmenin bedelini gösterir. §1.1'deki "araç tahmin
etmez" taahhüdü burada da geçerlidir.

### 2.4 Bayat sonuç işareti (F2)

Sonuç üretildikten sonra girdi değişince ekrandaki kupon, bedel ve olasılıklar
sessizce eskiye ait oluyordu. Artık işaretlenir ve "yeniden üret" düğmesi verilir.

**Sonuç silinmez** — eski sonuç hâlâ okunabilir bilgidir; yalnızca artık neyi
anlattığı söylenir. Parmak izi kurulum kodlamasından gelir; kodlama modun
etkilemediği alanları dışarıda bıraktığı için `fix16`'dayken bütçeyi değiştirmek
sonucu bayatlatmaz.

### 2.5 Sekmeler soruya göre (F3, `d915d18`)

| Sekme | Cevapladığı soru |
|-------|------------------|
| Ne aldım | garanti, bedel, bütçe planları, mod kıyası, kapsama dağılımı, uniform taban |
| Ne yazacağım | kupon tablosu |
| Ne kadar riskli | exact vs Monte Carlo, hata bütçesi, küme-içi çözülme, Bayes |
| Zayıf halkalar | hata frekansı, fire (seçim dışı) |
| Log | çalışma logu |

Birleştirilen sekmelerin içine bölüm başlıkları kondu; yoksa birleştirme sadece
uzun bir liste olurdu.

### 2.6 Maç kimliği (F4, `b06030a`)

Izgara uzun süre yalnızca 1–15 numaralarını gösterdi; 16 satırlık bir kuponu elle
doldururken "7. maç hangisiydi" sorusunun cevabı ekranda yoktu. Adlar üç yoldan
gelir: toplu giriş (satır başına bir ad), **devirde kendiliğinden**, ve kupon
kopyasının başlık satırına.

Ad taşımak bir **tahmin** taşımak değildir — hangi maçın hangisi olduğunu söyler,
hangi sembolün tutacağını değil — bu yüzden devrin "işaretler taşınmadı" sözünü
bozmaz. Adlar `localStorage`'da durur, bağlantıya girmez ve çözüme hiç girmediği
için sonucun parmak izine de dahil değildir.

### 2.7 Senaryo karşılaştırması (F6, `1841fab`)

Mod seçimi bu sayfadaki en pahalı karardır ama gözle yapılamıyordu: bir modu
çalıştırıp diğerine geçince öncekinin sayıları siliniyordu. Ölçülmüş bir kıyas:

| Mod | Satır | Kolon | Alt sınır | Garanti |
|---|---:|---:|---:|---|
| auto | 16 | 32 | 29 | var |
| maxcov | 12 | **12** | 29 | **yok** |
| fix16 | 16 | 32 | 29 | var |

Üç kural karara doğruluk kazandırır:

1. **Yalnızca aynı seçimle koşulanlar kıyaslanır.** Arada bir maç çifte yapıldıysa
   fark moddan değil seçimden gelir; o satırlar soluklaştırılıp uyarılır.
2. **Garanti vermeyen bir çalışma "en ucuz" sayılmaz.** `maxcov` listenin en
   ucuzu görünür ama farklı bir şey satın alır. Bu, §3.4'teki "maxcov garanti
   vermez" kuralının karşılaştırma tablosundaki karşılığıdır.
3. **Aynı kurulum tekrar koşulursa satır yerinde yenilenir.**

---

## 3. Vizyonla bağı

| Taahhüt (README §1) | Bu çalışmadaki karşılığı |
|---|---|
| **1.1** Garanti kombinatoryaldir | Küme-içi kartı garantiyi *güçlendirmez*; garantinin **koşulunu** ölçer. "Ne aldım" (kombinatoryal) ile "Ne kadar riskli" (senin tahminlerin) ayrı sekmelerdir |
| **1.2** Belirsizlik saklanmaz, ölçülür | Koşul artık üretmeden önce ve varsayılan görünür; fire "Zayıf halkalar" sekmesinde karara yakın duruyor |
| **1.4** Kaynak dürüstlüğü | Bağlantının kayıplı olduğu (binde bir + normalize), adların taşınmadığı, listenin kaydedilmediği kullanıcıya yazılıyor |
| **§3.3** Satır ≠ kolon | Bedel üç durumda ayrı ayrı, hiçbirinde uydurma tek sayı olmadan |
| **§3.4** `maxcov` garanti vermez | Karşılaştırma tablosunda "en ucuz" iddiasının dışında tutuluyor |

Ayrıca üç yeni ürün kuralı README §7.2'ye eklendi (9, 10, 11): anlamı olmayan
sayı basılmaz sebebi yazılır; ekrandaki sonuç girdiyi anlatmıyorsa söylenir;
kıyas ancak aynı şey üzerindeyse yapılır.

---

## 4. Yolda bulunan hatalar

Dördü de bu çalışma sırasında ölçümle çıktı ve düzeltildi.

### 4.1 Kodlama taşması — sessizce başka kupon üretiyordu

Kurulum kodlaması sabit genişliklidir. İlk sürüm olasılığı binde birlik ondalıkla
yazıyordu: `padStart(3)`. Ama binde birlik bir olasılık **0..1000** arası değer
alır, yani banko bir maçta (p=1,0) alan **dört** karaktere taşar. Sabit
genişlikli çözme o maçtan sonraki *bütün* maçları kaydırıyor, hiçbir yerde
patlamıyor ve **sessizce başka bir kupon** üretiyordu.

36 tabanında iki karaktere geçildi (1000 = `"rs"`, 36² = 1296 > 1000); taşma
imkânsız. Yan fayda: 90 karakter yerine 60.

### 4.2 `auto` modunda 8 kat abartılı bedel

Ölçüldü: aynı kupon için buton **256 kolon** diyordu, motor **32** üretiyordu.
Bütçe modlarında ise gerçek tavan zaten kullanıcının girdiği bütçeydi. (§2.2)

### 4.3 Telefonda yatay taşma

Olasılık girişi açıkken sayfa yatay kayıyordu: olasılık ızgarasının
`min-w-[420px]`'i, ızgara ögesinin varsayılan `min-width:auto`'su yüzünden **tüm
sol kolonu** 390 px yerine 462 px'e itiyor ve kendi `overflow-x-auto`
sarmalayıcısı bunu içeride tutamıyordu. İki kolona `min-w-0` eklendi; `scrollWidth`
482 → 390.

Bu hata mevcuttu; F1'de eklenen "Olasılık girişini aç" bağlantısı onu daha
ulaşılır yaptığı için düzeltildi.

### 4.4 Yapışkan çubuk bir kontrolü tıklanamaz yapıyordu

F4'ün ad girişi eklenince çıktı: kontrol ilk açılışta tıklanamıyordu. Ölçüldü —
düğme 1011–1074, çubuk 996–1088, `elementFromPoint` çubuğu döndürüyor. İki
sebebi vardı:

1. **Çubuk şişmişti.** F0'da eklenen uzun bedel açıklaması onu 100 px'e
   çıkarmıştı. Açıklamanın tam hâli Motor kartına, **modun seçildiği yere**
   taşındı; çubukta tek satır sayı kaldı → 92 px.
2. **Kontrol tam katlama çizgisine denk geliyordu.** Ad girişi ızgaranın üstüne
   alındı.

**Kalan sınır dürüstçe yazılıyor:** viewport'a sabitlenmiş bir eylem çubuğu
arkasındaki içeriği kaçınılmaz olarak örter. Söz verilebilecek şey daha zayıf ama
ölçülebilir: *hiçbir kontrol erişilemez değildir* — her kontrol görünür alanın
ortasına kaydırıldığında gerçekten en üstteki ögedir. İki viewport'ta 104 kontrol
üzerinde test edilir.

### 4.5 Kaydırmanın iki turu

Mobilde sonuç ~2400 px aşağıda başlıyordu; butona basınca ekranda hiçbir şey
değişmiyordu. Çalışması iki tur aldı, ikisi de ölçümle:

1. **İlk deneme hiç kaydırmadı.** Olay işleyicisinden çağrıldığında yumuşak
   kaydırma daha uçarken `setCalisiyor` kaynaklı yeniden render araya girip
   animasyonu iptal ediyordu — `scrollY` 0'da kalıyordu, oysa aynı çağrı tek
   başına 2019'a götürüyor. Commit sonrasına taşındı.
2. **İkinci deneme yarım kaldı.** Sayfa o anda henüz kısa (2818 px → en fazla
   1974'e kaydırılabilir) ama sonuç kolonu 2441'de başlıyor; tarayıcı hedefi
   tavana kırpıyordu. Sonuç gelip sayfa uzayınca bir kez daha denenir — kullanıcı
   o arada sonucu zaten ekrana getirdiyse dokunulmaz. Sonuç alanı üst=573 → 16.

---

## 5. Tekilleştirilen iki yer

### 5.1 Markov'un "hayatta kalma" tablosu

`backend/spor_toto/markov.py` okundu:

```python
p_stay = sum(pr[s] for s in sel)   # = küme-içi kartındaki kütle
p_in  *= p_stay                    # p_survive = p_kume_ici
```

Yani o tablo, F1'de eklenen kartın kütle çubuklarıyla **birebir aynı sayılardı**.
Aynı sayıyı ikinci kez, üstelik yalnızca motor çalıştıktan *sonra* göstermek bilgi
eklemiyordu; girdi tarafındaki hâli hem canlı hem de yanında ne yapılacağını
söylüyor. Tablo kaldırıldı.

Kümülatif eğri kaldı ama dürüstleştirildi: **yatay ekseni kupon sırasıdır, bir
zaman değil.** Maçlar bağımsız olduğu için son değer sıralamadan etkilenmez,
yalnızca inişin şekli değişir — bu artık yazıyor.

### 5.2 Küme-içi kartının varsayılan hâli

Açılışta kart **%100,0** gösteriyordu. Sebep: varsayılan olasılık satırları tüm
kütleyi zaten işaretli sembollere veriyor, yani koşul tanım gereği 1. O sayıyı
basmak "seçimin kesin tutar" demek olurdu.

Kart artık sayı yerine sebebi yazıyor ve bilgisiz taban çizgisini
(`uzay / 3¹⁵` = %0,00178) üretmeyi öneriyor. Aynı sınıfta ikinci bir kusur:
kütleler eşitken ilk üç satır "en zayıf" diye sarıya boyanıyordu — sıralamanın
keyfî sonucu. Fark yoksa zayıf da yok.

---

## 6. Denetim

Arayüzün o güne kadar **hiçbir** otomatik kapısı yoktu — §4.1'deki kodlama hatası
bu yüzden sessizce geçebilirdi.

`frontend/scripts/check.mjs` tarayıcı gerektirmeyen her şeyi denetler ve
**bağımlılık eklemez**: `tsc` zaten devDependency olduğu için modülleri geçici bir
dizine çevirir, dosya düz `node` ile koşar.

| Bölüm | Vaka | Çekirdek iddia |
|---|---:|---|
| Kurulum kodlaması | 16 | Banko maçta alan taşmaz; bozuk alan varsayılana düşer **ve raporlanır**; okunamayan olasılık girişi **kapalı** açılır |
| Küme-içi | 14 | Backend'in `exact` değeriyle birebir; alt sınır sunucunun `alt_sinir`'iyle aynı; anlamsız %100 basılmaz |
| Senaryo | 7 | "En ucuz" yalnızca aynı seçimden ve yalnızca garantililerden seçilir |
| **Toplam** | **37** | |

Ek olarak, tarayıcı gerektiren altı uçtan uca süit Playwright ile koşuldu
(kalıcılık, devir, F0–F2, sekme yapısı, maç adları, örtüşme). Bunlar repoya
**girmedi**: Playwright bir bağımlılıktır ve onu eklemek ayrı bir karardır
(bkz. yol haritası, K7).

CI'a `frontend` işi eklendi: `npm run check` + `npm run build`.

---

## 7. Bilerek yapılmayanlar

| Fikir | Neden hayır |
|---|---|
| Küme-içi kartının işaret **önermesi** | Araç tahmin etmez. Kart çarpanı ve bedeli gösterir; hangi maça hangi sembolün ekleneceği kullanıcının kararıdır |
| Maç adlarının bağlantıya girmesi | 15 takım adı URL'i üç katına çıkarır; `transfer.ts`'te aynı karar verilmişti |
| Senaryo listesinin kaydedilmesi | Türetilmiş veri kaydedilmez; kalıcı olan tek şey kurulumdur |
| Adres çubuğunun kendiliğinden güncellenmesi | Geçmişi kirletir ve devir işaretiyle (`?hafta=`) çakışırdı |
| Yerel depoda olasılıkların kodlamadan geçmesi | Kullanıcının yazdığı `0.4234` sırf sayfa yenilendiği için `0.423` olurdu |
| Playwright'ın repoya eklenmesi | Ayrı bir karar; §6'daki süitler bu turda dışarıda koşuldu |
