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
  transfer.ts         hafta → formül devri (idempotent)
```

## Kurulumun kalıcılığı

Formül sayfasının kurulumu — 15 maçın işaretleri, olasılık satırları ve
motorun bütün ayarları — iki ayrı taşıyıcıya yazılır (`lib/kurulum.ts`).
Sonuç ikisine de girmez; sonuç türetilmiş veridir, kurulum ise kullanıcının
elle ürettiği tek şeydir.

| | Yerel depo | Bağlantı |
|---|---|---|
| Ne zaman | her değişiklikte, kendiliğinden | yalnızca **Bağlantıyı kopyala**'ya basınca |
| Nerede | `localStorage`, yalnızca o tarayıcı | URL (~110 karakter) |
| Kayıp | yok (JSON) | olasılıklar binde bir + normalize |

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
`padStart(3)` alanı taşırıyordu). `scripts/kurulum-check.mjs` bu sınırı ve
diğer gidiş-dönüş vakalarını bağımlılık eklemeden denetler.

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
