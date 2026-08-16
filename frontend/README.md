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
```

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
npx tsc --noEmit     # tip kontrolü
npm run build        # üretim derlemesi
```
