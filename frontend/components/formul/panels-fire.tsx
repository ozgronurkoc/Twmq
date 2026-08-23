"use client";

import * as React from "react";
import { Flame, ShieldOff } from "lucide-react";

import type { FireBlock, FireReport, SolveResult } from "@/lib/types";
import { cn, sayi } from "@/lib/utils";
import { TABLO_SARMAL } from "@/components/ui/tablo";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Stat,
} from "@/components/ui/primitives";

const TUR_ETIKET: Record<string, string> = {
  banko: "Banko",
  double: "Çifte",
  triple: "Kapama",
  "banko+banko": "Banko + Banko",
  "banko+double": "Banko + Çifte",
  "double+double": "Çifte + Çifte",
};

function etiket(tur: string): string {
  return TUR_ETIKET[tur] ?? tur;
}

/** İlgilendiğimiz skorlar, kupon mantığına göre yüksekten alçağa. */
const SKORLAR = ["15", "14", "13", "12"] as const;

function SkorDagilimi({ blok }: { blok: FireBlock }) {
  const enBuyuk = Math.max(
    ...SKORLAR.map((s) => blok.scores[s] ?? 0),
    1,
  );
  return (
    <div className="space-y-2">
      {SKORLAR.map((s) => {
        const adet = blok.scores[s] ?? 0;
        const pct = blok.pct[s] ?? 0;
        const imkansiz = adet === 0;
        return (
          <div key={s} className="flex items-center gap-3">
            <span
              className={cn(
                "tnum w-20 shrink-0 text-[12px] font-medium",
                imkansiz && "text-muted-foreground",
              )}
            >
              {s} doğru
            </span>
            <div className="h-6 min-w-0 flex-1 overflow-hidden rounded-md bg-muted">
              <div
                className={cn(
                  "h-full rounded-md transition-all duration-500 ease-ios",
                  s === "15" || s === "14" ? "bg-success/70" : "bg-warning/60",
                )}
                style={{ width: `${(adet / enBuyuk) * 100}%` }}
              />
            </div>
            <span className="tnum w-24 shrink-0 text-right font-mono text-[11.5px]">
              {sayi(adet)}
            </span>
            <span className="tnum w-16 shrink-0 text-right font-mono text-[11.5px] text-muted-foreground">
              %{pct.toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function TurKarsilastirma({ blok }: { blok: FireBlock }) {
  const turler = Object.entries(blok.by_type).filter(([, v]) => v.n > 0);
  if (!turler.length) return null;

  // En iyi ulasilabilir skor: 1 fire'da 14, 2 fire'da 13.
  const hedef = (blok.scores["14"] ?? 0) > 0 ? "14" : "13";

  return (
    <div className="space-y-2">
      <p className="text-[12px] text-muted-foreground">
        Aynı sayıda fire, <strong>hangi tür maçta</strong> olduğuna göre farklı
        sonuç veriyor. Aşağıdaki oran, o türde fire olduğunda{" "}
        <strong>{hedef} doğru</strong> tutturma şansıdır.
      </p>
      {turler
        .map(([tur, v]) => ({ tur, v, oran: v.pct[hedef] ?? 0 }))
        .sort((a, b) => b.oran - a.oran)
        .map(({ tur, v, oran }) => (
          <div key={tur} className="flex items-center gap-3">
            <span className="w-32 shrink-0 text-[12px] font-medium">
              {etiket(tur)}
            </span>
            <div className="h-6 min-w-0 flex-1 overflow-hidden rounded-md bg-muted">
              <div
                className="h-full rounded-md bg-primary/65 transition-all duration-500 ease-ios"
                style={{ width: `${Math.min(100, oran)}%` }}
              />
            </div>
            <span className="tnum w-16 shrink-0 text-right font-mono text-[12px] font-semibold">
              %{oran.toFixed(1)}
            </span>
            <span className="tnum w-24 shrink-0 text-right font-mono text-[11px] text-muted-foreground">
              {sayi(v.n)} senaryo
            </span>
          </div>
        ))}
    </div>
  );
}

function MacTablosu({ blok, ikiKat }: { blok: FireBlock; ikiKat: boolean }) {
  const olabilir = blok.by_match.filter((m) => m.can_fail && m.n > 0);
  if (!olabilir.length) return null;
  const hedef = (blok.scores["14"] ?? 0) > 0 ? "14" : "13";

  // En kotu maclar once: hedef skoru tutturma sansi en dusuk olanlar
  const sirali = [...olabilir].sort(
    (a, b) => (a.pct[hedef] ?? 0) - (b.pct[hedef] ?? 0),
  );

  return (
    <div className="space-y-2">
      {ikiKat ? (
        <Callout ton="neutral">
          2-fire tablosunda her senaryo <strong>iki maça birden</strong> yazılır
          (o maç fire olanlardan biriyken koşullu dağılım). Bu yüzden maç
          toplamları genel senaryo sayısının iki katıdır.
        </Callout>
      ) : null}
      <div className={TABLO_SARMAL}>
        <table className="w-full min-w-[460px] text-[12.5px]">
          <thead>
            <tr className="text-left text-[10.5px] uppercase tracking-[0.06em] text-muted-foreground">
              <th className="pb-2 pr-3 font-medium">Maç</th>
              <th className="pb-2 pr-3 font-medium">Tür</th>
              <th className="pb-2 pr-3 text-right font-medium">
                {hedef} doğru şansı
              </th>
              <th className="pb-2 text-right font-medium">Senaryo</th>
            </tr>
          </thead>
          <tbody className="tnum">
            {sirali.map((m) => (
              <tr key={m.mac} className="border-t border-line">
                <td className="py-2 pr-3 font-semibold">{m.mac}.</td>
                <td className="py-2 pr-3 text-muted-foreground">
                  {etiket(m.type)}
                </td>
                <td className="py-2 pr-3 text-right font-mono">
                  %{(m.pct[hedef] ?? 0).toFixed(1)}
                </td>
                <td className="py-2 text-right font-mono text-muted-foreground">
                  {sayi(m.n)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11.5px] leading-relaxed text-muted-foreground">
        En üstteki maçlar, yanılman hâlinde en pahalıya mal olanlardır. O maçı
        çifteye çekmek riski en çok düşüren hamledir.
      </p>
    </div>
  );
}

function FireBolumu({
  blok,
  baslik,
  hint,
  ikiKat,
}: {
  blok: FireBlock;
  baslik: string;
  hint: string;
  ikiKat: boolean;
}) {
  return (
    <Card>
      <CardHeader
        title={baslik}
        hint={hint}
        action={<Badge>{sayi(blok.n)} senaryo</Badge>}
      />
      <CardBody className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <Stat
            etiket="En az 14 doğru"
            deger={`%${blok.p_ge_14.toFixed(2)}`}
            ton={blok.p_ge_14 > 0 ? "success" : "danger"}
            alt={blok.p_ge_14 === 0 ? "bu senaryoda imkânsız" : undefined}
          />
          <Stat
            etiket="En az 13 doğru"
            deger={`%${blok.p_ge_13.toFixed(2)}`}
          />
        </div>
        <SkorDagilimi blok={blok} />
        <div>
          <h4 className="mb-2 text-[13px] font-semibold">Fire türüne göre</h4>
          <TurKarsilastirma blok={blok} />
        </div>
        <div>
          <h4 className="mb-2 text-[13px] font-semibold">Maç bazında</h4>
          <MacTablosu blok={blok} ikiKat={ikiKat} />
        </div>
      </CardBody>
    </Card>
  );
}

export function FirePanel({ r }: { r: SolveResult }) {
  const fire: FireReport | null = r.fire;
  if (!fire) return null;

  if (fire.skipped) {
    return (
      <Card>
        <CardBody className="flex items-start gap-3 py-8">
          <ShieldOff size={18} className="mt-0.5 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <div className="text-[14px] font-semibold">Fire analizi atlandı</div>
            <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
              {fire.reason}
            </p>
            <p className="tnum mt-2 text-[11.5px] text-muted-foreground">
              Maliyet {sayi(fire.maliyet)} · sınır {sayi(fire.esik ?? 0)}
            </p>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Callout ton="warning" baslik="Burası garantinin DIŞI">
        Diğer paneller, gerçek sonuç <strong>seçim kümenin içindeyken</strong> ne
        olduğunu ölçer. Bu panel tersini ölçer: bir veya iki maçın sonucu
        işaretlemediğin bir sembol çıkarsa ne olur. 14-garanti bu bölgede{" "}
        <strong>geçerli değildir</strong> — buradaki sayılar garanti değil, o
        senaryodaki en iyi kolonun performansıdır.
      </Callout>

      {fire.fire1 ? (
        <FireBolumu
          blok={fire.fire1}
          baslik="1 maç işaret dışında"
          hint="Tam bir maçın sonucu seçimlerinin dışına çıkarsa. 15 doğru artık imkânsızdır."
          ikiKat={false}
        />
      ) : null}

      {fire.fire2 ? (
        <FireBolumu
          blok={fire.fire2}
          baslik="2 maç işaret dışında"
          hint="Tam iki maç dışarı çıkarsa. Bu noktada 14 doğru da matematiksel olarak imkânsızdır."
          ikiKat
        />
      ) : null}

      <Callout ton="neutral">
        <span className="flex items-start gap-2">
          <Flame size={14} className="mt-0.5 shrink-0" />
          <span>
            Kapama (üç işaretli) maçlar fire üretemez — küme dışı sembolleri
            yoktur. Kuponda kapama arttıkça bu analizin kapsamı doğal olarak
            daralır.
          </span>
        </span>
      </Callout>
    </div>
  );
}
