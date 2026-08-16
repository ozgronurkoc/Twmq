"use client";

import * as React from "react";
import { RotateCcw, ShieldCheck, ShieldX, TriangleAlert } from "lucide-react";

import { enUcuzGarantili, type Senaryo } from "@/lib/senaryo";
import { olasilikYaz } from "@/lib/kume-ici";
import { cn, sayi } from "@/lib/utils";
import { Badge, Button, Card, CardBody, CardHeader } from "@/components/ui/primitives";

/**
 * Calistirilan modlarin yan yana karsilastirmasi.
 *
 * Tek is: mod secimini AKILDAN yapilan bir kiyas olmaktan cikarmak. Bu
 * kart bir mod ONERMEZ — hangi garantiyi kac kolona aldigini gosterir,
 * karar kullanicinindir.
 */
export function SenaryoKart({
  liste,
  guncelSecim,
  guncelId,
  onDon,
  disabled,
}: {
  liste: Senaryo[];
  /** Şu anki işaretlerin parmak izi — farklı seçimle koşulanlar işaretlenir. */
  guncelSecim: string;
  /** Ekranda duran sonucun kurulum parmak izi. */
  guncelId: string | null;
  onDon: (s: Senaryo) => void;
  disabled?: boolean;
}) {
  const enUcuz = enUcuzGarantili(liste, guncelSecim);
  const farkliVar = liste.some((s) => s.secimParmak !== guncelSecim);

  return (
    <Card>
      <CardHeader
        title="Çalıştırdığın modlar"
        hint="Aynı seçim üzerinde hangi mod neyi kaç kolona veriyor. Bu liste bir mod önermez; oturum boyunca tutulur, kaydedilmez."
      />
      <CardBody className="space-y-3">
        <div className="scroll-slim overflow-x-auto">
          <table className="w-full min-w-[520px] text-[12.5px]">
            <thead>
              <tr className="text-left text-[10.5px] uppercase tracking-[0.06em] text-muted-foreground">
                <th className="pb-2 pr-3 font-medium">Mod</th>
                <th className="pb-2 pr-3 text-right font-medium">Satır</th>
                <th className="pb-2 pr-3 text-right font-medium">Kolon</th>
                <th className="pb-2 pr-3 text-right font-medium">Alt sınır</th>
                <th className="pb-2 pr-3 font-medium">Garanti</th>
                <th className="pb-2 pr-3 text-right font-medium">Küme-içi</th>
                <th className="pb-2 font-medium" />
              </tr>
            </thead>
            <tbody className="tnum">
              {liste.map((s) => {
                const farkli = s.secimParmak !== guncelSecim;
                const ekranda = s.id === guncelId;
                return (
                  <tr
                    key={s.id}
                    className={cn(
                      "border-t border-line",
                      ekranda && "bg-accent/40",
                      farkli && "opacity-60",
                    )}
                  >
                    <td className="py-2 pr-3">
                      <span className="flex flex-wrap items-center gap-1.5">
                        <span className="font-mono font-semibold">{s.mode}</span>
                        {ekranda ? <Badge ton="primary">ekranda</Badge> : null}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-right font-mono">{sayi(s.satir)}</td>
                    <td
                      className={cn(
                        "py-2 pr-3 text-right font-mono font-semibold",
                        !farkli && enUcuz?.id === s.id && "text-success",
                      )}
                    >
                      {sayi(s.bedel)}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                      {sayi(s.altSinir)}
                    </td>
                    <td className="py-2 pr-3">
                      {s.garanti ? (
                        <span className="flex items-center gap-1 text-success">
                          <ShieldCheck size={13} /> var
                        </span>
                      ) : (
                        <span
                          className="flex items-center gap-1 text-danger"
                          title={`${sayi(s.acik)} nokta kapsanmıyor`}
                        >
                          <ShieldX size={13} /> yok
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                      {s.pKumeIci === null ? "—" : olasilikYaz(s.pKumeIci)}
                    </td>
                    <td className="py-2 text-right">
                      {ekranda ? null : (
                        <Button
                          tip="ghost"
                          boyut="sm"
                          disabled={disabled}
                          onClick={() => onDon(s)}
                        >
                          <RotateCcw size={12} />
                          Dön
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {farkliVar ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-warning/30 bg-warning-soft px-3 py-2.5">
            <TriangleAlert size={15} className="mt-0.5 shrink-0 text-warning" />
            <p className="text-[11.5px] leading-relaxed">
              Soluk satırlar <strong>başka bir maç seçimiyle</strong> koşuldu.
              Onların kolon bedeli bu seçimle kıyaslanamaz — fark moddan değil,
              seçimin büyüklüğünden geliyor olabilir.
            </p>
          </div>
        ) : null}

        {enUcuz ? (
          <p className="text-[11.5px] leading-relaxed text-muted-foreground">
            Bu seçimde 14-garantiyi veren en ucuz çalışma{" "}
            <strong className="font-mono">{enUcuz.mode}</strong> —{" "}
            <strong>{sayi(enUcuz.bedel)} kolon</strong>. Küre-kaplama alt sınırı{" "}
            {sayi(enUcuz.altSinir)} kolon olduğuna göre bunun altına inen bir
            formül <strong>matematiksel olarak yok</strong>. Garanti vermeyen
            modlar daha ucuz olabilir; onlar farklı bir şey satın alır.
          </p>
        ) : null}
      </CardBody>
    </Card>
  );
}
