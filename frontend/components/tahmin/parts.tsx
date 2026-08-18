"use client";

import * as React from "react";

import type { OlculmusIsabet, Sembol, TahminSatiri, TahminUyarisi } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Callout, Card, CardBody, Stat } from "@/components/ui/primitives";
import { SYM_BG, SYM_TEXT } from "@/components/istatistik/viz";

const SEMBOLLER: Sembol[] = ["1", "0", "2"];

const GUNLER = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"];

/** "2026-08-18" → "18 Ağustos, Salı". Çözülemezse ham değer döner. */
function gunEtiketi(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  const ay = d.toLocaleDateString("tr-TR", { day: "numeric", month: "long" });
  return `${ay}, ${GUNLER[d.getDay()]}`;
}

export const yuzde = (v: number | null | undefined, basamak = 1) =>
  v === null || v === undefined ? "—" : `%${(100 * v).toFixed(basamak)}`;

/**
 * Tek maçın olasılık çubuğu.
 *
 * Üç sembol yan yana, genişlikleri olasılıkla orantılı. Renk KİMLİK takip
 * eder (`viz.ts` sözleşmesi): 1 hep aynı renk, sıralamaya göre değişmez.
 * En olası sembol kalınlaşır — ama **rengi değişmez**, çünkü renk "hangi
 * sembol" sorusunu cevaplar, "hangisi favori" sorusunu değil.
 */
export function OlasilikCubugu({ olasilik, enOlasi }: {
  olasilik: Record<string, number>;
  enOlasi: string | null;
}) {
  return (
    <div className="flex h-6 w-full overflow-hidden rounded-md border border-line">
      {SEMBOLLER.map((s) => {
        const p = olasilik[s] ?? 0;
        if (p <= 0) return null;
        return (
          <div
            key={s}
            className={cn(
              "flex items-center justify-center text-[10.5px] tabular-nums",
              SYM_BG[s],
              s === enOlasi ? "font-semibold text-white" : "text-white/75",
            )}
            style={{ width: `${Math.max(p * 100, 0)}%` }}
            title={`${s}: ${yuzde(p)}`}
          >
            {p >= 0.14 ? `${s} ${Math.round(p * 100)}` : null}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Maç tablosu. Satır başına: zaman, takımlar, olasılık çubuğu, seçim.
 *
 * `olculen_lig=false` olan satır işaretlenir — ölçülen isabet o maça ait
 * değildir ve bunu satırın kendisinde söylemek, sayfanın altındaki genel
 * uyarıya bırakmaktan dürüsttür.
 */
export function TahminTablosu({ satirlar, yildizGoster = true }: {
  satirlar: TahminSatiri[];
  /**
   * Satır başına "ölçüm evreni dışı" işareti gösterilsin mi.
   *
   * Kaynağın TAMAMI ölçüm dışıysa yıldız her satıra düşer ve hiçbir şey
   * ayırt etmez — gürültü olur. O durumda işaret satırdan kaldırılır ve
   * uyarı bir kez, tepede söylenir.
   */
  yildizGoster?: boolean;
}) {
  const gunler = React.useMemo(() => {
    const m = new Map<string, TahminSatiri[]>();
    for (const s of satirlar) {
      const k = s.tarih || "—";
      const v = m.get(k);
      if (v) v.push(s);
      else m.set(k, [s]);
    }
    return [...m.entries()];
  }, [satirlar]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-[12.5px]">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
            <th className="py-2 pr-3 font-medium">Zaman</th>
            <th className="py-2 pr-3 font-medium">Lig</th>
            <th className="py-2 pr-3 font-medium">Maç</th>
            <th className="py-2 pr-3 font-medium" style={{ width: "34%" }}>
              Olasılık
            </th>
            <th className="py-2 pr-1 text-right font-medium">Seçim</th>
          </tr>
        </thead>
        <tbody>
          {gunler.map(([gun, grup]) => (
            <React.Fragment key={gun}>
              {/* Gun basligi: 100+ satirlik bir tablo baslıksiz okunmaz. */}
              <tr className="bg-muted/40">
                <td
                  colSpan={5}
                  className="py-1.5 pr-3 text-[11px] font-semibold uppercase tracking-[0.06em] text-muted-foreground"
                >
                  {gunEtiketi(gun)}
                  <span className="ml-2 font-normal normal-case tracking-normal opacity-70">
                    {grup.length} maç
                  </span>
                </td>
              </tr>
              {grup.map((t, i) => (
            <tr
              key={`${t.tarih}-${t.saat}-${t.ev}-${t.dep}-${i}`}
              className="border-b border-line/60 last:border-0"
            >
              <td className="py-2 pr-3 whitespace-nowrap tabular-nums text-muted-foreground">
                {t.saat || "—"}
              </td>
              <td className="py-2 pr-3 max-w-[150px] truncate text-muted-foreground" title={t.lig}>
                {t.lig}
                {yildizGoster && !t.olculen_lig ? (
                  <span
                    className="ml-1 text-warning"
                    title="Ölçülen isabet bu lige ait değil"
                  >
                    *
                  </span>
                ) : null}
              </td>
              <td className="py-2 pr-3">
                <span className="font-medium">{t.ev}</span>
                <span className="mx-1.5 text-muted-foreground">–</span>
                <span>{t.dep}</span>
              </td>
              <td className="py-2 pr-3">
                <OlasilikCubugu olasilik={t.olasilik} enOlasi={t.en_olasi} />
              </td>
              <td className="py-2 pr-1 text-right whitespace-nowrap">
                {t.en_olasi ? (
                  <>
                    <span className={cn("font-semibold", SYM_TEXT[t.en_olasi as Sembol])}>
                      {t.en_olasi}
                    </span>
                    <span className="ml-1.5 tabular-nums text-muted-foreground">
                      {yuzde(t.guven)}
                    </span>
                  </>
                ) : (
                  "—"
                )}
              </td>
            </tr>
              ))}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Ölçülmüş isabet kartı — **tahmin tablosundan ayrılamaz.**
 *
 * Sayfanın tek kırmızı çizgisi budur: bir olasılık gösteriliyorsa, o
 * tahmincinin 540 maçta ne yaptığı da gösterilir. Süslenmiş bir olasılık,
 * süslenmemiş bir yalandır.
 */
export function IsabetKarti({ isabet }: { isabet: OlculmusIsabet }) {
  if (!isabet.olculdu) {
    return (
      <Callout ton="warning" baslik="İsabet ölçülemedi">
        {isabet.not ?? "Oran arşivi eksik."} Ölçülmüş isabet olmadan bu
        olasılıklar okunmamalıdır.
      </Callout>
    );
  }
  return (
    <Card>
      <CardBody className="space-y-3">
        <div className="text-[13px] font-semibold">
          Bu tahminci geçen sezon ne yaptı?
        </div>
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            etiket="Maç başına isabet"
            deger={yuzde(isabet.mac_basina_isabet)}
            alt={`${isabet.n_mac} maç · ${isabet.n_hafta} hafta`}
          />
          <Stat
            etiket="Haftada doğru"
            deger={`${isabet.hafta_ortalamasi ?? "—"} / 15`}
            alt={`en iyi hafta ${isabet.en_iyi_hafta ?? "—"}`}
          />
          <Stat
            etiket="Brier"
            deger={isabet.brier ?? "—"}
            alt={`log kaybı ${isabet.log_kaybi ?? "—"}`}
          />
          <Stat
            etiket="14+ tutan hafta"
            deger={`${isabet.hafta_14_arti ?? "—"} / ${isabet.n_hafta ?? "—"}`}
            ton={isabet.hafta_14_arti ? "neutral" : "danger"}
            alt={`13+ : ${isabet.hafta_13_arti ?? "—"}`}
          />
        </div>
        <div className="text-[11.5px] leading-relaxed text-muted-foreground">
          Kesit: {isabet.kesit}
        </div>
      </CardBody>
    </Card>
  );
}

/**
 * Sınırlar. **Kısaltılmaz ve katlanmaz.**
 *
 * Bir uyarıyı "detayları gör" arkasına koymak, onu göstermemektir. En
 * önemlisi ilk sırada: bu tahminci tek kolonla 14+ tutturamaz.
 */
export function Sinirlar({ uyarilar }: { uyarilar: TahminUyarisi[] }) {
  const ton = (ad: string) =>
    ad === "tek_kolon_14_tutmaz" || ad === "kalibrasyon_olculmemis"
      ? ("warning" as const)
      : ("neutral" as const);
  const baslik: Record<string, string> = {
    tek_kolon_14_tutmaz: "Tek kolonla 14+ tutmaz",
    model_yok: "Bu bir model değil, piyasa fiyatı",
    acilis_orani: "Oranlar açılış oranı",
    kalibrasyon_olculmemis: "Bu maçların kalibrasyonu ölçülmedi",
    olcum_evreni_disi: "Bazı maçlar ölçüm evreninin dışında",
  };
  return (
    <div className="space-y-2">
      {uyarilar.map((u) => (
        <Callout key={u.ad} ton={ton(u.ad)} baslik={baslik[u.ad] ?? u.ad}>
          {u.metin}
        </Callout>
      ))}
    </div>
  );
}
