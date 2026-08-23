"use client";

import * as React from "react";

import { ARINDIRMA, HAFTALAR, HAFTA_SAYISI, SUPER_TOTO_SEZON, doluHaftaSayisi, haftaDoluMu, sonuclananHaftaSayisi } from "@/lib/super-toto";
import { MAC_SAYISI } from "@/lib/types";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { TabPanel } from "@/components/ui/tabs";
import {
  BosHafta,
  DoluHafta,
  HaftaSekmeleri,
  haftaUrldenOku,
  haftaUrleYaz,
} from "@/components/super-toto/haftalar";

export default function SuperTotoPage() {
  // Adresteki `?hafta=` okunana kadar 1. hafta gosterilir; okuma bir
  // efektte yapilir (hidrasyon uyusmazligi olmasin diye).
  const [secili, setSecili] = React.useState(1);

  React.useEffect(() => {
    const w = haftaUrldenOku();
    if (w !== null) setSecili(w);
  }, []);

  function haftaSec(week: number) {
    setSecili(week);
    haftaUrleYaz(week);
  }

  const dolu = doluHaftaSayisi();
  const sonuclanan = sonuclananHaftaSayisi();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[30px] italic leading-tight">Süper Toto</h1>
        <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
          İşlenen sezon burada yaşar: her hafta kendi sekmesinde durur, hafta
          seçilince o haftanın verisine gidilir. Veri backend&apos;den gelir
          (<code>backend/data/super_toto</code>); bu sayfa hiçbir sayıyı
          kendi hesaplamaz.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge ton="primary">{SUPER_TOTO_SEZON}</Badge>
          <Badge>{HAFTA_SAYISI} hafta</Badge>
          <Badge>arındırma: {ARINDIRMA}</Badge>
          <Badge>haftada {MAC_SAYISI} maç</Badge>
          <Badge ton={dolu ? "success" : "warning"}>
            {dolu} / {HAFTA_SAYISI} hafta girildi
          </Badge>
          <Badge ton={sonuclanan ? "success" : "neutral"}>
            {sonuclanan} hafta sonuçlandı
          </Badge>
        </div>
      </header>

      <HaftaSekmeleri secili={secili} onSec={haftaSec} />

      {HAFTALAR.map((h) => (
        <TabPanel key={h.week} id={String(h.week)} active={h.week === secili}>
          <Card>
            <CardHeader
              title={`${h.week}. hafta`}
              hint={
                h.close_date
                  ? `Kapanış ${h.close_date} · ${SUPER_TOTO_SEZON}`
                  : `${SUPER_TOTO_SEZON} · kapanış tarihi henüz belli değil`
              }
              action={
                <Badge ton={haftaDoluMu(h) ? "success" : "neutral"}>
                  {haftaDoluMu(h) ? "veri var" : "veri yok"}
                </Badge>
              }
            />
            <CardBody>
              {haftaDoluMu(h) ? <DoluHafta hafta={h} /> : <BosHafta hafta={h} />}
            </CardBody>
          </Card>
        </TabPanel>
      ))}
    </div>
  );
}
