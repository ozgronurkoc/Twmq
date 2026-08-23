"use client";

import * as React from "react";

import { SEMBOLLER } from "@/lib/types";
import type { OlculmusIsabet, Sembol, TahminSatiri, TahminUyarisi } from "@/lib/types";
import { cn } from "@/lib/utils";
import { BenzerKart } from "@/components/benzer/kart";
import { Callout, Card, CardBody, Stat } from "@/components/ui/primitives";
import { SYM_BG, SYM_TEXT } from "@/components/istatistik/viz";


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
            <th className="py-2 pr-3 text-right font-medium">Seçim</th>
            <th className="py-2 pr-1 text-right font-medium" title="Korpusta eğitilmiş yeniden kalibrasyon — geçmedi">
              Alt.
            </th>
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
                <BenzerKart oranlar={t.oranlar ?? null} />
              </td>
              <td className="py-2 pr-3">
                <OlasilikCubugu olasilik={t.olasilik} enOlasi={t.en_olasi} />
              </td>
              <td className="py-2 pr-3 text-right whitespace-nowrap">
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
              {/*
                Alternatif AYNI sembolu seciyorsa yalnizca guveni yazilir;
                FARKLI seciyorsa sembol de yazilir ve vurgulanir — asil bilgi
                orada. Sifir farkli secim, alternatifin siralamayi hic
                degistirmedigi anlamina gelir ve bu gorulmeli.
              */}
              <td className="py-2 pr-1 text-right whitespace-nowrap tabular-nums text-muted-foreground">
                {t.alternatif?.en_olasi ? (
                  t.alternatif.en_olasi === t.en_olasi ? (
                    yuzde(t.alternatif.guven)
                  ) : (
                    <span className="font-semibold text-warning">
                      {t.alternatif.en_olasi} {yuzde(t.alternatif.guven)}
                    </span>
                  )
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
  if (!isabet.olculdu || !isabet.manset) {
    return (
      <Callout ton="warning" baslik="İsabet ölçülemedi">
        {isabet.not ?? "Oran arşivi eksik."} Ölçülmüş isabet olmadan bu
        olasılıklar okunmamalıdır.
      </Callout>
    );
  }
  const m = isabet.manset;
  const a = isabet.alternatif;
  return (
    <Card>
      <CardBody className="space-y-3">
        <div className="text-[13px] font-semibold">
          Bu tahminciler geçen sezon ne yaptı?
        </div>

        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            etiket="Maç başına isabet"
            deger={yuzde(m.mac_basina_isabet)}
            alt={`${m.n_mac} maç · ${isabet.n_hafta} hafta`}
          />
          <Stat
            etiket="Haftada doğru"
            deger={`${m.hafta_ortalamasi} / 15`}
            alt={`en iyi hafta ${m.en_iyi_hafta}`}
          />
          <Stat
            etiket="Brier"
            deger={m.brier}
            alt={`log kaybı ${m.log_kaybi}`}
          />
          <Stat
            etiket="14+ tutan hafta"
            deger={`${m.hafta_14_arti} / ${isabet.n_hafta}`}
            ton={m.hafta_14_arti ? "neutral" : "danger"}
            alt={`13+ : ${m.hafta_13_arti}`}
          />
        </div>

        {/*
          Iki tahminci yan yana. Alternatif ORTALAMADA daha iyi ama gecmedi;
          bunu gizlemek de manset yapmak da yanlis olurdu. Fark ve araligi
          birlikte durur — aralik sifiri iceriyorsa "gecmedi" yazar.
        */}
        {a ? (
          <div className="overflow-x-auto rounded-xl border border-line">
            <table className="w-full min-w-[520px] border-collapse text-[12.5px]">
              <thead>
                <tr className="border-b border-line bg-muted/40 text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
                  <th className="px-3 py-2 font-medium">Tahminci</th>
                  <th className="px-3 py-2 text-right font-medium">Brier</th>
                  <th className="px-3 py-2 text-right font-medium">Fark</th>
                  <th className="px-3 py-2 text-right font-medium">%95 aralık</th>
                  <th className="px-3 py-2 text-right font-medium">Geçti</th>
                </tr>
              </thead>
              <tbody>
                {[m, a].map((s) => (
                  <tr key={s.ad} className="border-b border-line/60 last:border-0">
                    <td className="px-3 py-2">
                      <span className="font-medium">{s.ad}</span>
                      {s.ad === isabet.referans ? (
                        <span className="ml-1.5 text-[10.5px] text-muted-foreground">
                          manşet
                        </span>
                      ) : null}
                      {s.aciklama ? (
                        <div className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                          {s.aciklama}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{s.brier}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {s.fark ? s.fark.fark.toFixed(4) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                      {s.fark
                        ? `[${s.fark.alt.toFixed(4)}, ${s.fark.ust.toFixed(4)}]`
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {s.gecti === undefined ? (
                        "—"
                      ) : s.gecti ? (
                        <span className="font-semibold text-success">EVET</span>
                      ) : (
                        <span className="text-muted-foreground">hayır</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="text-[11.5px] leading-relaxed text-muted-foreground">
          Kesit: {isabet.kesit}
          {a ? (
            <>
              {" · "}Alternatif <strong>31.103 maçlık korpusta</strong> eğitildi
              ve burada ölçüldü; iki set arasında ortak maç yok.
            </>
          ) : null}
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
