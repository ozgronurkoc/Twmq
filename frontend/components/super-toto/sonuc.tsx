"use client";

/**
 * SONUÇ sekmesi — haftanın karnesi, tahmin kayıtlarının DIŞINDA.
 *
 * Niçin ayrı bir sekme: sonuç geldiğinde tahmin panelleri sonuçla
 * doluyordu. Maç tablosuna bir "Sonuç" sütunu giriyor, kupon kartına
 * "9/15 küme içinde" ekleniyor, rozet "sonuçlandı"ya dönüyordu. Yani
 * **dondurulmuş bir kaydın üzerine sonradan bilinen bir şey yazılıyordu**
 * ve kayıt artık "o an ne biliniyordu" sorusunu temiz cevaplayamıyordu.
 *
 * Bu panel o bilgiyi kendi alanına alır ve 1. ile 2. Tahmin'i **aynı
 * ölçüyle** karneler — biri ötekinin yerine geçmez, ikisi yan yana durur.
 *
 * Buradaki hiçbir sayı arayüzde hesaplanmaz: hepsi
 * `scripts/super_toto_frontend._sonuc_blok` üzerinden
 * `super_toto_degerlendir`den gelir.
 */

import * as React from "react";

import type { SuperTotoHafta, SuperTotoSonuc } from "@/lib/super-toto";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { yuzde as _yuzde } from "@/lib/utils";

const SEM_ADI: Record<string, string> = { "1": "1", "0": "X", "2": "2" };

function tl(v: number | null): string {
  if (v === null || v === undefined) return "—";
  // `minimumFractionDigits` de sart: yalnizca `maximum` verilince
  // 1.438,60 -> "1.438,6" cikiyordu ve para birimi eksik kurus gosterirdi.
  return (
    v.toLocaleString("tr-TR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) + " TL"
  );
}

export function SonucPaneli({ hafta }: { hafta: SuperTotoHafta }) {
  const s = hafta.sonuc;
  if (!s) return null;
  const adlar = new Map(
    hafta.matches.map((m) => [m.no, `${m.home} – ${m.away}`]),
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-[12.5px]">
        <Badge ton="primary">sonuçlandı</Badge>
        {s.results_entered_at ? <Badge>{s.results_entered_at}</Badge> : null}
        <Badge>{s.kayitlar.length} kayıt karnelendi</Badge>
      </div>

      <p className="max-w-3xl text-[12.5px] leading-relaxed text-muted-foreground">
        {s.note}
      </p>

      {/* ─── kayıtların karnesi ─────────────────────────────────────── */}
      <Card>
        <CardHeader
          title="Kayıtlar ne yaptı"
          hint="1. ve 2. Tahmin aynı ölçüyle; biri ötekinin yerine geçmez"
        />
        <CardBody>
          <div className="-mx-1 overflow-x-auto px-1">
            <table className="w-full min-w-[620px] text-[12.5px]">
              <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="pb-1.5 pr-3">Kayıt</th>
                  <th className="pb-1.5 pr-3 text-right">En iyi kolon</th>
                  <th className="pb-1.5 pr-3 text-right">Kaçak</th>
                  <th className="pb-1.5 pr-3 text-right">Beklenen kaçak</th>
                  <th className="pb-1.5 pr-3 text-right">Küme-içi</th>
                  <th className="pb-1.5">Kaçıran maçlar</th>
                </tr>
              </thead>
              <tbody>
                {s.kayitlar.map((k) => (
                  <tr key={k.ad} className="border-t border-line">
                    <td className="py-1.5 pr-3 font-medium">{k.ad}</td>
                    <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                      {k.best}/15
                    </td>
                    <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                      {k.miss_count}
                    </td>
                    <td className="py-1.5 pr-3 text-right font-mono tabular-nums text-muted-foreground">
                      {k.expected_misses.toFixed(2)}
                    </td>
                    <td className="py-1.5 pr-3 text-right font-mono tabular-nums text-muted-foreground">
                      {_yuzde(k.p_in_set, 3)}
                    </td>
                    <td className="py-1.5 font-mono tabular-nums">
                      {k.misses.length ? k.misses.join(", ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
            <strong>Beklenen kaçak</strong> kuponun kendi olasılıklarından
            gelir: gerçekleşen kaçak ondan büyükse hafta beklenenden kötü,
            küçükse iyi geçmiştir. Tek haftalık bir fark ne kuralı doğrular
            ne yalanlar — kayıt bu yüzden tutuluyor.
          </p>
        </CardBody>
      </Card>

      {/* ─── maç maç ────────────────────────────────────────────────── */}
      <Card>
        <CardHeader
          title="Maç maç"
          hint={`Gerçek sonuç dizisi: ${s.results}`}
        />
        <CardBody>
          <div className="-mx-1 overflow-x-auto px-1">
            <table className="w-full min-w-[620px] text-[12.5px]">
              <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="pb-1.5 pr-2 text-right">#</th>
                  <th className="pb-1.5 pr-3">Maç</th>
                  <th className="pb-1.5 pr-3">Gerçek</th>
                  {s.kayitlar.map((k) => (
                    <th key={k.ad} className="pb-1.5 pr-3">
                      {k.ad}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(s.kayitlar[0]?.per_match ?? []).map((m) => (
                  <tr key={m.no} className="border-t border-line">
                    <td className="py-1.5 pr-2 text-right tabular-nums text-muted-foreground">
                      {m.no}
                    </td>
                    <td className="py-1.5 pr-3 truncate">
                      {adlar.get(m.no) ?? "—"}
                    </td>
                    <td className="py-1.5 pr-3 font-mono font-medium">
                      {SEM_ADI[m.gercek] ?? m.gercek}
                    </td>
                    {s.kayitlar.map((k) => {
                      const r = k.per_match.find((x) => x.no === m.no);
                      if (!r) {
                        return (
                          <td key={k.ad} className="py-1.5 pr-3">
                            —
                          </td>
                        );
                      }
                      return (
                        <td key={k.ad} className="py-1.5 pr-3 font-mono">
                          <span
                            className={
                              r.tuttu ? undefined : "text-danger font-medium"
                            }
                          >
                            {r.pick} {r.tuttu ? "✓" : "✗"}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>

      {/* ─── kalabalık ve piyasa ────────────────────────────────────── */}
      <Card>
        <CardHeader
          title="Kalabalık ve piyasa ne yaptı"
          hint="İkramiyenin niçin büyük ya da küçük olduğunun cevabı"
        />
        <CardBody className="space-y-2 text-[12.5px]">
          <div className="-mx-1 overflow-x-auto px-1">
            <table className="w-full min-w-[520px]">
              <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="pb-1.5 pr-3">Kupon</th>
                  <th className="pb-1.5 pr-3">İşaretler</th>
                  <th className="pb-1.5 pr-3 text-right">Doğru</th>
                  <th className="pb-1.5 text-right">Beklenen</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-line">
                  <td className="py-1.5 pr-3">Kalabalığın en çok oynadığı</td>
                  <td className="py-1.5 pr-3 font-mono">
                    {s.kalabalik.halk_kuponu}
                  </td>
                  <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                    {s.kalabalik.halk_dogru}/15
                  </td>
                  <td className="py-1.5 text-right font-mono tabular-nums text-muted-foreground">
                    {s.kalabalik.beklenen_halk_dogru.toFixed(2)}
                  </td>
                </tr>
                <tr className="border-t border-line">
                  <td className="py-1.5 pr-3">Piyasanın favorileri</td>
                  <td className="py-1.5 pr-3 font-mono">
                    {s.kalabalik.piyasa_kuponu}
                  </td>
                  <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                    {s.kalabalik.piyasa_dogru}/15
                  </td>
                  <td className="py-1.5 text-right font-mono tabular-nums text-muted-foreground">
                    {s.kalabalik.beklenen_piyasa_dogru.toFixed(2)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-[11.5px] leading-relaxed text-muted-foreground">
            Bu iki kupon <strong>tek kolondur</strong>; yukarıdaki kayıtlar
            ise kaplama. Doğrudan kıyaslanamazlar — burada durmalarının
            sebebi haftanın kendisinin kolay mı zor mu geçtiğini
            göstermeleridir.
          </p>
        </CardBody>
      </Card>

      {/* ─── ikramiye ───────────────────────────────────────────────── */}
      {s.payout?.length ? (
        <Card>
          <CardHeader
            title="İkramiye"
            hint={s.payout_source ?? undefined}
          />
          <CardBody>
            <div className="-mx-1 overflow-x-auto px-1">
              <table className="w-full min-w-[420px] text-[12.5px]">
                <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="pb-1.5 pr-3">Kademe</th>
                    <th className="pb-1.5 pr-3 text-right">Kazanan</th>
                    <th className="pb-1.5 text-right">Kişi başı</th>
                  </tr>
                </thead>
                <tbody>
                  {s.payout.map((t) => (
                    <tr key={t.correct} className="border-t border-line">
                      <td className="py-1.5 pr-3 font-mono tabular-nums">
                        {t.correct} bilen
                      </td>
                      <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                        {t.winners.toLocaleString("tr-TR")}
                      </td>
                      <td className="py-1.5 text-right font-mono tabular-nums">
                        {tl(t.prize)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      ) : null}

      {s.results_source ? (
        <p className="text-[11.5px] leading-relaxed text-muted-foreground">
          Sonuç kaynağı: {s.results_source}
        </p>
      ) : null}
    </div>
  );
}

export type { SuperTotoSonuc };
