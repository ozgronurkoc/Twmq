"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  ISTATISTIK_SEKMELERI,
  sekmeAdresi,
  type Sekme,
} from "@/lib/sekmeler";
import { cn } from "@/lib/utils";

/**
 * İstatistik ailesinin sekme şeridi.
 *
 * Sayfa `ISTATISTIK_YOL_HARITASI.md` §6.8 G1'de bölündü: 7.210 px'lik tek
 * akış üç soruya ayrıldı. Şerit bölmeyi **gezinilebilir** kılan parçadır —
 * onsuz üç sayfa birbirini bilmez ve kullanıcı geri tuşuyla dolaşır.
 *
 * ─── `?last` neden href'te taşınıyor ─────────────────────────────────────
 *
 * Değişmez kural 3 ("tek filtre satırı") bölünmeyle birlikte **genişledi**:
 * *"tek dilim"*. Aynı anda görünen her blok aynı `?last` üzerinden
 * hesaplanır **ve sekme geçişinde dilim korunur**. Şerit dilimi href'e
 * yazmasaydı `/istatistik?last=12`'den oranlara geçen kullanıcı sessizce
 * tüm sezona düşerdi — iki sayfa aynı anda iki farklı kesiti anlatırdı ve
 * hiçbir yerde yazmazdı.
 */

export function IstatistikSekmeleri({
  last,
  sekmeler = ISTATISTIK_SEKMELERI,
}: {
  last: number | null;
  sekmeler?: Sekme[];
}) {
  const yol = usePathname();
  return (
    <nav
      aria-label="İstatistik sayfaları"
      className="flex flex-wrap items-center gap-1 border-b border-line-strong"
    >
      {sekmeler.map((s) => {
        // Tam esitlik: `/istatistik` her seyin oneki oldugu icin
        // `startsWith` kullanilsaydi butun sekmeler ayni anda etkin
        // gorunurdu.
        const etkin = yol === s.href;
        return (
          <Link
            key={s.href}
            href={sekmeAdresi(s.href, last)}
            aria-current={etkin ? "page" : undefined}
            className={cn(
              "-mb-px border-b-2 px-3 py-2 text-[13px] transition-colors",
              etkin
                ? "border-primary font-medium text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {s.etiket}
          </Link>
        );
      })}
    </nav>
  );
}
