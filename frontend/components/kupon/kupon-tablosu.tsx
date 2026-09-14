"use client";

import * as React from "react";

import type { KuponSatiri } from "@/lib/kupon";
import type { KurulanKupon } from "@/lib/kupon-kur";
import { MAC_SAYISI, type Sembol } from "@/lib/types";
import { cn, sayi, yuzde } from "@/lib/utils";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

/**
 * Kurulan kupon — hangi macta hangi semboller isaretli ve NEDEN.
 *
 * "Neden" sutunu sus degil: kural karnenin en yuksek ikisini aliyor ve
 * hangi iki yuzdenin secildigi gorunmezse kupon bir kara kutu olur. Uc
 * yuzde de yan yana duruyor, secilenler vurgulu.
 */

const SECILI: Record<Sembol, string> = {
  "1": "bg-sym-1 text-white border-sym-1",
  "0": "bg-sym-0 text-white border-sym-0",
  "2": "bg-sym-2 text-white border-sym-2",
};

export function KuponTablosu({
  satirlar,
  kupon,
}: {
  satirlar: KuponSatiri[];
  kupon: KurulanKupon;
}) {
  return (
    <div className={TABLO_SARMAL}>
      <table className="w-full min-w-[820px] table-fixed border-separate border-spacing-0">
        <colgroup>
          <col className="w-[4%]" />
          <col className="w-[34%]" />
          <col className="w-[22%]" />
          <col className="w-[40%]" />
        </colgroup>
        <thead>
          <tr className={cn(TABLO_BASLIK_SATIRI, "[&>th]:whitespace-nowrap")}>
            <th className="pb-2 pr-2 text-right font-medium">#</th>
            <th className="pb-2 pl-2 font-medium">Maç</th>
            <th className="pb-2 pl-2 font-medium">İşaret</th>
            <th className="pb-2 pl-2 font-medium">Karne — seçilen iki sembol</th>
          </tr>
        </thead>
        <tbody>
          {satirlar.map((satir, i) => {
            const s = kupon.satirlar[i];
            const alt = i === MAC_SAYISI - 1 ? "" : "border-b border-line/50";
            const ad = [satir.ev, satir.dep].filter(Boolean).join(" – ");
            return (
              <tr key={i}>
                <td className={cn("py-2 pr-2 text-right align-middle", alt)}>
                  <span className="tnum text-[12px] text-muted-foreground">{i + 1}</span>
                </td>
                <td className={cn("py-2 pl-2 align-middle", alt)}>
                  <div className="truncate text-[13px]">
                    {ad || <span className="text-muted-foreground/50">adsız</span>}
                  </div>
                  {satir.lig ? (
                    <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                      {satir.lig}
                    </div>
                  ) : null}
                </td>

                <td className={cn("py-2 pl-2 align-middle", alt)}>
                  {s && s.semboller.length ? (
                    <span className="flex items-center gap-1">
                      {s.semboller.map((sem) => (
                        <span
                          key={sem}
                          className={cn(
                            "inline-flex h-7 w-7 items-center justify-center rounded-lg border",
                            "font-mono text-[13px] font-semibold",
                            SECILI[sem],
                          )}
                        >
                          {sem}
                        </span>
                      ))}
                      {s.kaynak === "piyasa" ? (
                        <span
                          className="ml-1 text-[11px] text-warning"
                          title="Bu satırda karne yok (sorgu hata aldı ya da örnek bulunamadı); işaret PİYASADAN seçildi"
                        >
                          piyasadan
                        </span>
                      ) : null}
                      {s.azOrnek ? (
                        <span
                          className="ml-1 text-[11px] text-warning"
                          title="Örneklem 30'un altında — yüzdeler okunmaz sayılır, işaret yine de bu sıradan çıktı"
                        >
                          az örnek
                        </span>
                      ) : null}
                      {s.esitlikBozuldu ? (
                        <span
                          className="ml-1 text-[11px] text-warning"
                          title="Sınırdaki iki sembolün karnesi birebir aynıydı; sıra piyasaya, o da eşitse sembol düzenine (1, 0, 2) göre bozuldu"
                        >
                          eşitlik
                        </span>
                      ) : null}
                    </span>
                  ) : (
                    <span className="text-[12px] text-danger">
                      işaret yok — analiz gerekli
                    </span>
                  )}
                </td>

                <td className={cn("py-2 pl-2 align-middle", alt)}>
                  <span className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                    {(s?.sirali ?? []).map((x, sira) => {
                      const secili = s?.semboller.includes(x.sembol);
                      return (
                        <span
                          key={x.sembol}
                          className={cn(
                            "tnum text-[12px]",
                            secili ? "font-medium" : "text-muted-foreground/60",
                          )}
                          title={
                            s?.kaynak === "piyasa"
                              ? `piyasa ${yuzde(x.piyasa)}`
                              : `karne ${x.deger == null ? "—" : yuzde(x.deger)} · piyasa ${yuzde(x.piyasa)}`
                          }
                        >
                          <span
                            className={cn(
                              "font-mono",
                              secili ? "text-foreground" : "text-muted-foreground/60",
                            )}
                          >
                            {x.sembol}
                          </span>{" "}
                          {s?.kaynak === "piyasa"
                            ? yuzde(x.piyasa)
                            : x.deger == null
                              ? "—"
                              : yuzde(x.deger)}
                          {sira === 1 ? (
                            <span className="ml-1 text-muted-foreground/40">|</span>
                          ) : null}
                        </span>
                      );
                    })}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Kuponun muhasebesi: kac kolon, ne kadar para, haftalik tavanin neresi.
 *
 * Bedel arayuzde SABIT DEGIL — kolon bedeli `/api/meta`dan geliyor
 * (`getiri.KOLON_BEDELI`). Iki yerde yasasaydi biri degistiginde oteki
 * sessizce yalan soylerdi.
 */
export function KuponMuhasebesi({
  kupon,
  bedelTl,
  haftalikTavanTl,
}: {
  kupon: KurulanKupon;
  bedelTl: number | null;
  /** Sahibinin haftalık bütçesi; bilinmiyorsa kıyas yapılmaz. */
  haftalikTavanTl: number | null;
}) {
  const asim =
    bedelTl != null && haftalikTavanTl ? bedelTl / haftalikTavanTl : null;
  const cifteler = kupon.satirlar.filter((s) => s.semboller.length === 2).length;
  const bankolar = kupon.satirlar.filter((s) => s.semboller.length === 1).length;
  const ucluler = kupon.satirlar.filter((s) => s.semboller.length === 3).length;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kutu baslik="Kolon" deger={sayi(kupon.kolon)} />
        <Kutu
          baslik="Bedel"
          deger={bedelTl == null ? "—" : `₺${sayi(bedelTl)}`}
          ton={asim != null && asim > 1 ? "danger" : undefined}
        />
        <Kutu
          baslik="Dağılım"
          deger={`${bankolar} / ${cifteler} / ${ucluler}`}
          alt="banko / çifte / üçlü"
        />
        <Kutu
          baslik="Haftalık tavan"
          deger={
            haftalikTavanTl == null
              ? "—"
              : asim == null
                ? `₺${sayi(haftalikTavanTl)}`
                : `${asim.toFixed(2)}×`
          }
          alt={haftalikTavanTl == null ? undefined : `₺${sayi(haftalikTavanTl)}`}
          ton={asim != null && asim > 1 ? "danger" : "success"}
        />
      </div>
    </div>
  );
}

function Kutu({
  baslik,
  deger,
  alt,
  ton,
}: {
  baslik: string;
  deger: string;
  alt?: string;
  ton?: "danger" | "success";
}) {
  return (
    <div className="rounded-xl border border-line px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
        {baslik}
      </div>
      <div
        className={cn(
          "tnum mt-0.5 text-[16px] font-semibold",
          ton === "danger" && "text-danger",
          ton === "success" && "text-success",
        )}
      >
        {deger}
      </div>
      {alt ? (
        <div className="tnum mt-0.5 text-[11px] text-muted-foreground">{alt}</div>
      ) : null}
    </div>
  );
}

/** Kuponun okunma kılavuzu — kural görünür durur, katlanmaz. */
export function KuponAciklamasi({ kupon }: { kupon: KurulanKupon }) {
  return (
    <p className="text-[11.5px] leading-relaxed text-muted-foreground">
      Kural: her maçta <strong>karnenin en yüksek iki sembolü</strong>{" "}
      işaretlenir. Karne, aynı fiyattaki geçmiş maçların nasıl bittiğidir —
      piyasa değil. Her maç iki sembol taşıdığı için kolon sayısı girdiden
      bağımsız olarak <strong>2¹⁵ = {sayi(2 ** MAC_SAYISI)}</strong> çıkar.{" "}
      {kupon.esitlikli.length ? (
        <>
          {kupon.esitlikli.map((i) => i + 1).join(", ")}. maçta sınırdaki iki
          sembolün karnesi <strong>birebir aynıydı</strong>; sıra piyasaya, o da
          eşitse sembol düzenine (1, 0, 2) göre bozuldu — rastgele seçilseydi
          aynı girdi iki farklı kupon verirdi.{" "}
        </>
      ) : null}
      {kupon.piyasadanSecilen.length ? (
        <>
          {kupon.piyasadanSecilen.map((i) => i + 1).join(", ")}. maçta karne yok;
          işaret <strong>piyasadan</strong> seçildi ve satırda öyle yazıyor.{" "}
        </>
      ) : null}
      {kupon.azOrnekli.length ? (
        <>
          {kupon.azOrnekli.map((i) => i + 1).join(", ")}. maçta örneklem 30&apos;un
          altında — o satırın yüzdeleri okunmaz sayılır, işaret yine de bu
          sıradan çıktı.
        </>
      ) : null}
    </p>
  );
}
