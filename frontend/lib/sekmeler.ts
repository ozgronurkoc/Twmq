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
 */
export interface Sekme {
  href: string;
  etiket: string;
}

export const ISTATISTIK_SEKMELERI: Sekme[] = [
  { href: "/istatistik", etiket: "Sezon" },
  { href: "/istatistik/oranlar", etiket: "Oranlar" },
  { href: "/istatistik/geri-test", etiket: "Geri test" },
];

/** `?last=N`'i koruyarak sekme adresi üretir. */
export function sekmeAdresi(href: string, last: number | null): string {
  return last && last > 0 ? `${href}?last=${last}` : href;
}
