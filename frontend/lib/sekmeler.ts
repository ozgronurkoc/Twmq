/**
 * İstatistik ailesinin sekmeleri — **saf** modül.
 *
 * Bileşenden ayrı durmasının tek sebebi denetlenebilirlik:
 * `scripts/check.mjs` tarayıcı açmadan koşar ve `sekmeAdresi`'ni buradan
 * derleyip sınayabilir. `components/istatistik/sekmeler.tsx` bir istemci
 * bileşenidir (`usePathname`, `next/link`) ve saf bir denetimde
 * derlenemez.
 *
 * Sınanan şey küçük ama kırıldığında sessiz: `?last` sekme adresinde
 * taşınmazsa `/istatistik?last=12`'den oranlara geçen kullanıcı sessizce
 * tüm sezona düşer — iki sayfa aynı anda iki farklı kesiti anlatır ve
 * hiçbir yerde yazmaz. §6.8 G1'in *"sekme geçişinde dilim korunur"*
 * kabul kriteri budur.
 *
 * **`?sezon` de aynı kuralın altındadır ve bir kez unutuldu.** Sezon seçimi
 * eklendiğinde şerit yalnızca `?last` taşıyordu; 2023/24 seçip *Oranlar*a
 * geçen kullanıcı sessizce varsayılan sezona düşüyordu. Aynı arıza, aynı
 * gerekçe — ve `?last` için yazılan bekçi bunu görmemişti çünkü yalnızca
 * `?last`e bakıyordu. Artık ikisi de sınanıyor.
 */
export interface Sekme {
  href: string;
  etiket: string;
}

export const ISTATISTIK_SEKMELERI: Sekme[] = [
  { href: "/istatistik", etiket: "Sezon" },
  { href: "/istatistik/oranlar", etiket: "Oranlar" },
  { href: "/istatistik/surpriz", etiket: "Sürpriz" },
  { href: "/istatistik/geri-test", etiket: "Geri test" },
];

/** `?last=N`'i koruyarak sekme adresi üretir. */
export function sekmeAdresi(
  href: string,
  last: number | null,
  sezon?: string | null,
): string {
  const q = new URLSearchParams();
  if (last && last > 0) q.set("last", String(last));
  if (sezon) q.set("sezon", sezon);
  const qs = q.toString();
  return qs ? `${href}?${qs}` : href;
}
