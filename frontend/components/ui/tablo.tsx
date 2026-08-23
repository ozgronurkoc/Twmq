/**
 * Tablo iskelesinin paylaşılan sınıfları — **tek kaynak**.
 *
 * Aynı iki sınıf dizgisi yirmi yedi yerde harfi harfine tekrar ediyordu
 * (sekiz dosyada). Tek başına her biri zararsız; birlikte, tablo
 * tipografisini değiştirmek isteyen birinin yirmi yedi yeri bulup hepsini
 * aynı şekilde değiştirmesi gerektiği anlamına geliyordu — ve biri
 * unutulduğunda fark derlemede değil, ancak iki tabloya yan yana bakınca
 * görülürdü.
 *
 * **Neden `<table>`'ın kendi sınıfı burada yok.** O sınıf her çağrı yerinde
 * farklı bir genişlik alt sınırı taşır (`min-w-[520px]`, `min-w-[720px]`…)
 * ve Tailwind'in tarayıcısı yalnızca **kaynakta harfi harfine geçen**
 * sınıfları üretir. Genişliği bir şablon dizgisine taşımak sınıfın hiç
 * üretilmemesine, yani sessizce bozulan bir düzene yol açardı. Bu yüzden
 * genişlik çağrı yerinde, değişmeyen kısım burada.
 */

/** Yatay kaydırma sarmalı — dar ekranda tablo sayfayı taşırmaz. */
export const TABLO_SARMAL = "scroll-slim overflow-x-auto";

/** Başlık satırı: küçük, büyük harf, seyrek harf aralığı. */
export const TABLO_BASLIK_SATIRI =
  "text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground";
