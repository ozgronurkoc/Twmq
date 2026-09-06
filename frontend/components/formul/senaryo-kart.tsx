"use client";

import * as React from "react";
import { RotateCcw, TriangleAlert } from "lucide-react";

import { enIyiVerim, type Senaryo } from "@/lib/senaryo";
import { olasilikYaz } from "@/lib/kume-ici";
import { cn, sayi } from "@/lib/utils";
import { Badge, Button, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { TABLO_SARMAL } from "@/components/ui/tablo";

/**
 * Calistirilan kuponlarin yan yana karsilastirmasi.
 *
 * Tek is: **isaret** secimini akildan yapilan bir kiyas olmaktan
 * cikarmak. Bir maci daha cifte yapmak kume-ici olasiligi buyutur ve
 * bedeli katlar; kart o takasi gosterir, bir kupon ONERMEZ.
 *
 * Eskiden mod kiyasiydi (fix16 / butce / maxcov). Modlar kaplamayla
 * birlikte dustu; duzde ayni isaretler her zaman ayni kolonlari verir.
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
  const enVerimli = enIyiVerim(liste);
  const farkliVar = liste.some((s) => s.secimParmak !== guncelSecim);

  return (
    <Card>
      <CardHeader
        title="Çalıştırdığın kuponlar"
        hint="Hangi işaret seti kaç kolona ne kadar küme-içi olasılık veriyor. Bu liste bir kupon önermez; oturum boyunca tutulur, kaydedilmez."
      />
      <CardBody className="space-y-3">
        <div className={TABLO_SARMAL}>
          <table className="w-full min-w-[520px] text-[12.5px]">
            <thead>
              <tr className="text-left text-[10.5px] uppercase tracking-[0.06em] text-muted-foreground">
                <th className="pb-2 pr-3 font-medium">Kupon</th>
                <th className="pb-2 pr-3 text-right font-medium">Satır</th>
                <th className="pb-2 pr-3 text-right font-medium">Kolon</th>
                <th className="pb-2 pr-3 text-right font-medium">Küme-içi</th>
                <th className="pb-2 pr-3 text-right font-medium">Kolon başına</th>
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
                        <span className="font-mono">{s.baslik}</span>
                        {ekranda ? <Badge ton="primary">ekranda</Badge> : null}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-right font-mono">{sayi(s.satir)}</td>
                    <td className="py-2 pr-3 text-right font-mono font-semibold">
                      {sayi(s.bedel)}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                      {s.pKumeIci === null ? "—" : olasilikYaz(s.pKumeIci)}
                    </td>
                    <td
                      className={cn(
                        "py-2 pr-3 text-right font-mono text-muted-foreground",
                        enVerimli?.id === s.id && "text-success",
                      )}
                    >
                      {s.pKumeIci === null || s.bedel <= 0
                        ? "—"
                        : olasilikYaz(s.pKumeIci / s.bedel)}
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
              Soluk satırlar <strong>başka bir maç seçimiyle</strong> koşuldu —
              yani listenin asıl konusu onlar. Kolon bedeli farkı doğrudan
              seçimin büyüklüğünden geliyor; bu bir kusur değil, ölçülen şeyin
              kendisi.
            </p>
          </div>
        ) : null}

        {enVerimli ? (
          <p className="text-[11.5px] leading-relaxed text-muted-foreground">
            Kolon başına en çok küme-içi olasılığı{" "}
            <strong className="font-mono">{enVerimli.baslik}</strong> veriyor —{" "}
            <strong>{sayi(enVerimli.bedel)} kolon</strong>.{" "}
            <strong>Bu bir öneri değildir:</strong> küme-içi olasılık kazanma
            olasılığı değil, <em>en iyi kolon = 15 − kaçak</em> aritmetiğinin
            geçerli olma koşuludur. İkramiye, kolon bedeli ve kaç kişinin
            tutturduğu bu orana girmez.
          </p>
        ) : null}
      </CardBody>
    </Card>
  );
}
