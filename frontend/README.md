# frontend/

Spor Toto Lab arayüzü. Next.js 14 App Router + TypeScript + Tailwind.
**Yalnızca TSX** — projede hiç `.html` dosyası, Jinja şablonu ya da
`dangerouslySetInnerHTML` yoktur.

> Tek istisna `app/layout.tsx`: Next.js App Router'ın kök bileşeni JSX olarak
> `<html>` ve `<body>` döndürmek zorundadır. Bu çerçevenin API'sidir, elle
> yazılmış HTML değildir.

## Çalıştırma

```bash
# API + UI birlikte (repo kökünden)
bash scripts/run_next_dev.sh     # UI :3000, API :8080

# yalnızca UI (API'nin ayrıca çalışıyor olması gerekir)
npm run dev
```

## Backend bağlantısı

`NEXT_PUBLIC_API_URL` **boş bırakılır**. İstekler aynı origin'e gider ve
`next.config.mjs`'deki rewrite ile Flask `:8080`'e proxy'lenir. Replit
önizlemesinde tarayıcı `127.0.0.1`'e ulaşamadığı için bu şarttır.

## Yapı

```
app/
  layout.tsx          kök — tema sağlayıcı + kabuk
  page.tsx            Formül (motorun tamamı)
  istatistik/         sezon dağılımı + hafta detayı
  saglik/             sistem sağlığı (kategorili değişmezler)
  icon.tsx            favicon (next/og ile TSX'ten üretilir)
  globals.css         tasarım token'ları
components/
  shell/              kenar çubuğu, sayfa geçişi, tema
  formul/             maç ızgarası, olasılık girişi, sonuç panelleri
  istatistik/         grafikler (inline SVG), hafta tablosu, filtre, veri kalitesi
  ui/                 kart, buton, sekme, anahtar… (elle yazıldı)
lib/
  types.ts            /api/solve dahil tüm API sözleşmesi
  api.ts              tipli, AbortController ile iptal edilebilir istemci
  utils.ts            cn(), normalize, biçimlendirme
  kurulum.ts          formül kurulumunun kalıcılığı + paylaşılabilir bağlantı
  kume-ici.ts         üretmeden önce görülen koşul + küre-kaplama alt sınırı
  transfer.ts         hafta → formül devri (idempotent)
```

## Sonuç sekmeleri soruya göre bölünür

Sekmeler bir zamanlar backend modüllerinin birebir yansımasıydı — Özet,
Kupon, Dağılım, Olasılık, Bayes, Markov, Hata frekansı, Fire, Log. Dokuz
sekme, ama kullanıcının dört sorusundan ikisi üçe-dörde dağılmış
durumdaydı. Şimdi sekme = soru:

| Sekme | Cevapladığı soru | İçindekiler |
|---|---|---|
| **Ne aldım** | Kaça mal oldu, ne garanti ediyor? | garanti durumu, bedel, motor notları, bütçe planları, kapsama dağılımı, uniform taban |
| **Ne yazacağım** | Kupona ne yazacağım? | kupon tablosu |
| **Ne kadar riskli** | Tahminlerime göre ne olur? | exact vs Monte Carlo, hata bütçesi, küme-içi çözülme, Bayes |
| **Zayıf halkalar** | Hangi maçı değiştirmeliyim? | hata frekansı, fire (seçim dışı) |
| Log | — | çalışma logu |

Birleştirilen sekmelerin içinde bölüm başlıkları vardır; yoksa birleştirme
sadece uzun bir liste olurdu.

**Markov'un "hayatta kalma" tablosu kaldırıldı.** Sunucuda
`p_stay = Σ_{s∈seç} p(s)` ve `p_survive` onların çarpımı — yani girdi
tarafındaki küme-içi kartının kütle çubuklarıyla *birebir aynı sayılar*.
Aynı sayıyı ikinci kez, üstelik yalnızca motor çalıştıktan sonra göstermek
bilgi eklemiyordu. Kümülatif eğri kaldı, ama yatay ekseninin kupon sırası
olduğu — bir zaman değil — artık açıkça yazıyor.

## Senaryo karşılaştırma

Mod seçimi bu sayfadaki en pahalı karardır ama gözle yapılamıyordu: bir
modu çalıştırıp diğerine geçince öncekinin sayıları ekrandan siliniyordu.
Artık çalıştırılan modlar bir tabloda yan yana durur (`lib/senaryo.ts`).

Üç kural karara doğruluk kazandırır:

1. **Yalnızca aynı seçimle koşulanlar kıyaslanır.** Arada bir maç çifte
   yapıldıysa "32 yerine 64 kolon" farkı moddan değil seçimden gelir;
   liste bunu gizlemez, o satırları soluklaştırıp uyarır.
2. **Garanti vermeyen bir çalışma "en ucuz" sayılmaz.** `maxcov` 12
   kolonla en ucuz görünür ama 14-garanti vermez — farklı bir şey satın
   alır. "En ucuz" cümlesi yalnızca garantili satırlardan seçilir.
3. **Aynı kurulum tekrar koşulursa satır yerinde yenilenir.** Varyant
   denerken liste aynı satırın kopyalarıyla dolup asıl karşılaştırmayı
   ekrandan itmemeli.

Liste **kaydedilmez**: senaryolar türetilmiş veridir, tıpkı `sonuc` gibi.
Kalıcı olan tek şey kurulumdur — kullanıcının elle ürettiği tek şey odur.

## Üretimden sonra kaydırma

Telefonda sonuç bloğu ~2400 px aşağıda başlıyor: "Formülü üret"e
basıldığında ekranda hiçbir şey değişmiyor, çalışma göstergesi bile
görünmüyordu. Artık dar ekranda (`xl` kırılma noktasının altında) sonuç
alanına kaydırılır; geniş ekranda sonuç zaten girdinin yanındadır ve
kaydırmak kullanıcıyı yerinden etmek olurdu.

İki ince nokta ölçümle çıktı:

- **Kaydırma olay işleyicisinden değil, commit sonrasından tetiklenir.**
  İşleyiciden çağrıldığında yumuşak kaydırma daha uçarken `setCalisiyor`
  kaynaklı yeniden render araya giriyor ve animasyon iptal oluyordu
  (`scrollY` 0'da kalıyordu, oysa aynı çağrı tek başına 2019'a götürüyor).
- **İki kez denenir.** İlk kaydırmada sayfa henüz kısadır (2818 px → en
  fazla 1974'e kaydırılabilir) ama sonuç kolonu 2441'de başlar; tarayıcı
  hedefi tavana kırpar ve sonuç ekranın alt yarısında kalırdı. Sonuç gelip
  sayfa uzayınca bir kez daha denenir — kullanıcı o arada sonucu zaten
  ekrana getirdiyse dokunulmaz.

## Maç kimliği

Izgara uzun süre yalnızca 1–15 numaralarını gösterdi; 16 satırlık bir kuponu
elle doldururken "7. maç hangisiydi" sorusunun cevabı ekranda yoktu. Artık
maçların adı olabilir:

- **Toplu giriş** (satır başına bir ad). Adlar neredeyse her zaman bir
  yerden kopyalanır; 15 ayrı kutu aynı işi 15 hamleye bölerdi ve dar girdi
  kolonuna 15 kutu daha eklerdi.
- **Devirde kendiliğinden gelir.** Hafta detayındaki "formüle gönder"
  paketinde takım adları zaten vardı, yalnızca notta listeleniyordu.
  Ad taşımak *tahmin* taşımak değildir — hangi maçın hangisi olduğunu
  söyler, hangi sembolün tutacağını değil — bu yüzden devrin "işaretler
  taşınmadı" sözünü bozmaz.
- **Kupon kopyasının başlık satırına girer**, böylece tabloyu bir hesap
  tablosuna yapıştırınca "M7" hangi maçtı sorusu ekranda kalmaz.

Adlar `localStorage`'da durur, **bağlantıya girmez** (15 takım adı URL'i üç
katına çıkarır — `transfer.ts`'teki kararla aynı) ve çözüme hiç girmediği
için sonucun parmak izine de dahil değildir: bir maça ad vermek ekrandaki
sonucu bayatlatmaz.

## Üretmeden önce görülen koşul

14-garanti **koşulludur**: ancak gerçek sonuç seçim kümesinin içindeyse
devreye girer. Sayfanın en görünür ögesi büyük yeşil "14-garanti VAR"
kalkanı, ama koşulun kendisi ölçülmeden bırakılıyordu — görmek için
olasılık girip motoru çalıştırmak ve Olasılık sekmesini açmak gerekiyordu.

`lib/kume-ici.ts` bunu istemcide hesaplar (`∏ᵢ Σ_{s∈secᵢ} pᵢ(s)`, 15 çarpma)
ve işaretler değiştikçe canlı gösterir. Yanında maç başına kütle çubukları
ve **verime göre** sıralı ekleme önerileri durur: küme-içi kazancın bedel
artışına oranı, ikisi birlikte.

Üç kural:

1. **Varsayılan satırlar "bilgi yok" sayılır.** Açılışta tüm kütle işaretli
   sembollerde olduğu için koşul tanım gereği %100 çıkar; sayı basmak
   "seçimin kesin tutar" demek olurdu. Kart sayı yerine sebebi yazar.
2. **Kütleler eşitken "en zayıf üç" yoktur.** Sıralamanın ilk üçünü
   işaretlemek onları keyfî olarak suçlamaktır.
3. **Olasılığı sıfır olan sembol önerilmez.** Bedeli iki katına çıkarır,
   küme-içi kazancı sıfırdır.

Ölçülmüş vaka (README'nin örnek kuponu, `check.sh`'ın örnek olasılıkları):
koşul **%0,0149** — yaklaşık 1/6.700. Kaybın çoğu üç bankoda: 7. maç (0,20),
14. maç (0,25), 5. maç (0,40). Bilgisiz taban çizgisi (hepsi 1/3) ise
`uzay / 3¹⁵` = %0,00178.

## Üretmeden önce söylenen bedel

Üç ayrı durum vardır ve tek sayıya indirilemezler:

| Mod | Ne söylenir | Neden |
|---|---|---|
| `fix16` | kesin — `uzay / 8` | blok 2⁷ noktayı 16 satıra indirir |
| `bütçe` / `maxcov` | tavan — girilen bütçe | motor bütçeyi aşmaz |
| diğerleri | aralık — küre-kaplama alt sınırı … tam sistem | kesin sayıyı arama sonunda motor bilir |

Önceki sürüm üçünü de tek formülle veriyor ve `fix16` dışında **uzayı**
yazıyordu: `auto` modunda aynı kupon için "256 kolon" diyordu, motor 32
üretiyordu — sekiz kat abartı, üstelik ödenecek tutarı söyleyen en görünür
yerde.

Yapışkan çubukta yalnızca **sayı** durur, tek satır. Açıklamanın tamamı
Motor kartında, modun seçildiği yerdedir. Sebep ölçüldü: uzun açıklama
çubuğu 100 px'e çıkarmış ve çubuk, ilk açılışta altındaki kontrolün tam
üstüne oturmuştu (düğme 1011–1074, çubuk 996–1088 → `elementFromPoint`
çubuğu döndürüyordu, yani tıklanamıyordu).

Viewport'a sabitlenmiş bir eylem çubuğu arkasındaki içeriği kaçınılmaz
olarak örter. Garanti edilen şey daha zayıf ama ölçülebilir bir özelliktir:
**hiçbir kontrol erişilemez değildir** — her kontrol görünür alanın
ortasına kaydırıldığında gerçekten en üstteki ögedir. Bu, iki viewport'ta
104 kontrol üzerinde test edilir.

## Kurulumun kalıcılığı

Formül sayfasının kurulumu — 15 maçın işaretleri, olasılık satırları ve
motorun bütün ayarları — iki ayrı taşıyıcıya yazılır (`lib/kurulum.ts`).
Sonuç ikisine de girmez; sonuç türetilmiş veridir, kurulum ise kullanıcının
elle ürettiği tek şeydir.

| | Yerel depo | Bağlantı |
|---|---|---|
| Ne zaman | her değişiklikte, kendiliğinden | yalnızca **Bağlantıyı kopyala**'ya basınca |
| Nerede | `localStorage`, yalnızca o tarayıcı | URL (~110 karakter) |
| Kayıp | yok (JSON) | olasılıklar binde bir + normalize; maç adları hiç girmez |

Öncelik **URL > yerel depo**: paylaşılan bir bağlantıyı açan kişi kendi eski
kurulumunun kalıntısını değil, gönderilen kurulumu görür. Devir paketi
(`?hafta=51`) bunlardan sonra çalışır ve yalnızca olasılıkların üzerine
yazar — hafta detayından gelen kullanıcının işaretleri korunur.

Üç kural kodda ve testte bağlıdır:

1. **Bozuk alan sessizce yutulmaz.** Okunamayan her alan varsayılana düşer
   *ve* arayüzde adıyla söylenir.
2. **Okunamayan olasılık girişi KAPALI açılır.** Açık bırakıp seçimlerden
   tekdüze değer üretmek, kullanıcının girmediği bir tahmini Bayes'e ve
   Monte Carlo'ya beslemek olurdu.
3. **Adres çubuğu kendiliğinden güncellenmez.** Her tuşa basışta URL yazmak
   geçmişi kirletir ve devir işaretiyle çakışırdı.

Kodlama sabit genişliklidir: bir alan taşarsa ondan sonraki *bütün* maçlar
kayar ve hiçbir yerde patlamaz — sessizce başka bir kupon üretir. İlk sürüm
tam bunu yaptı (binde birlik olasılık `1000` olabilir, yani dört basamak;
`padStart(3)` alanı taşırıyordu). `scripts/check.mjs` bu sınırı ve diğer
gidiş-dönüş vakalarını bağımlılık eklemeden denetler.

Ekrandaki sonucun hâlâ girdiyi anlatıp anlatmadığı da bu kodlamayla
ölçülür: sonuç üretilirken kurulumun parmak izi alınır, girdi değiştiğinde
sonuç **silinmez** ama "eski hâline ait" diye işaretlenir. Kodlama modun
etkilemediği alanları dışarıda bıraktığı için `fix16`'dayken bütçeyi
değiştirmek sonucu bayatlatmaz.

## Tasarım sistemi

Renkler `app/globals.css` içinde HSL bileşenleri olarak; Tailwind bunlara
`hsl(var(--x) / <alpha-value>)` ile bağlanır. Üç temalı kurulum: `:root`
(açık), `prefers-color-scheme` (sistem), `[data-theme]` (kullanıcı seçimi).

İki ürün kuralı tasarıma gömülüdür:

1. **Semboller daima kupon düzeninde (1, 0, 2).** Alfabetik sıralama `01`
   üretir ve kuponu elle doldururken hata yaptırır.
2. **Satır ≠ kolon.** Kolon bedeli hiçbir yerde satır sayısından ayrı
   gösterilmez; ödenecek tutar kolon sayısıdır.

## Grafikler

`components/istatistik/` içindeki görseller bağımlılıksız inline SVG'dir ve
renklerini `--sym-1/0/2` ile `--primary` token'larından alır — bu yüzden koyu
tema bedava gelir, dosyalarda sabit hex yoktur (`viz.ts`). Üç kural:

1. **Renk kimliği takip eder, sıralamayı değil.** Filtre hafta sayısını
   değiştirdiğinde hiçbir seri renk değiştirmez.
2. **Her görselin tablo karşılığı vardır.** Hiçbir değer yalnızca renge ya da
   fare ipucuna bırakılmaz; hafta tablosu tam veriyi taşır.
3. **Tek filtre satırı.** Kartların içine filtre konmaz; aralık seçimi
   `?last=N` ile API'ye gider ve bütün bloklar aynı dilimden hesaplanır.

## Kontroller

```bash
npm run check        # tip kontrolü + kurulum gidiş-dönüş denetimi
npm run build        # üretim derlemesi
```

İkisi de CI'da koşar (`.github/workflows/tests.yml`, `frontend` işi).
