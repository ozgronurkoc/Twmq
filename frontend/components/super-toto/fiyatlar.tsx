"use client";

/**
 * Haftanin FIYAT KAYNAKLARI ve DONDURULAN KUPONUN gerekcesi.
 *
 * Ikisi de rapor sayfasinda (`backend/scripts/super_toto_sayfa.py`) vardi
 * ama arayuzde yoktu: ayni hafta iki yerde anlatiliyor, biri otekinin
 * bildigini bilmiyordu. Buradaki her sayi beslemeden gelir; bu dosyada
 * hesaplanan tek sey yuzde bicimi degildir — hicbir olcum yoktur.
 */

import * as React from "react";

import type {
  SuperTotoFiyatlar,
  SuperTotoKupon,
} from "@/lib/super-toto";
import { saglayiciAdi } from "@/lib/super-toto";
import { SEMBOLLER as SEM } from "@/lib/types";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { yuzde as _yuzde } from "@/lib/utils";

// Harita ve bicimleyici BURADA YAZILIYDI ve Python tarafiyla ayrismisti
// (soneksiz anahtarda orasi "kapanış" uyduruyor, burasi uydurmuyordu).
// Ikisi de artik `spor_toto.odds`tan turuyor ve arayuze besleme ile
// geliyor — bkz. `lib/super-toto.ts`. `kitapAdi` adi korunuyor: bu dosya
// icinde bes yerde cagriliyor.
const kitapAdi = saglayiciAdi;

function ucluAd(p: Record<string, number> | null): string {
  if (!p) return "—";
  return SEM.map((s) => _yuzde(p[s], 0).replace("%", "")).join(" / ");
}

/** Uc bahisci x iki an — ana fiyatin nicin ana oldugu ve nerede ayrisildigi. */
export function FiyatKaynaklari({
  fiyatlar,
  oddsKind,
}: {
  fiyatlar: SuperTotoFiyatlar;
  oddsKind: string | null;
}) {
  const { books, margins, stale_closing: bayat, rows } = fiyatlar;

  // En buyuk hareket ve en buyuk ayrisma: ikisi de SATIRLARDAN secilir,
  // sabit yazilmaz — gelecek haftalarda baska maclar olacak.
  const enHareket = rows.reduce(
    (a, b) => (Math.abs(b.movement ?? 0) > Math.abs(a.movement ?? 0) ? b : a),
    rows[0]!,
  );
  const enAyrisma = rows.reduce(
    (a, b) => (b.disagreement > a.disagreement ? b : a),
    rows[0]!,
  );

  return (
    <Card>
      <CardHeader
        title="Fiyat kimin fiyatı?"
        hint={`${Object.keys(margins).length} kaynak · marj arındırılmış olasılık`}
        action={oddsKind ? <Badge ton="primary">ana: {kitapAdi(oddsKind.replace(/-/g, "_"))}</Badge> : null}
      />
      <CardBody className="space-y-3">
        <p className="text-[12.5px] leading-relaxed text-muted-foreground">
          Aşağıdaki her hücre <strong>marj arındırılmış olasılıktır</strong>,
          ham oran değil: ham oranın hareketi, piyasanın fikir değiştirmesiyle
          bahisçinin marjını değiştirmesini karıştırırdı.
        </p>

        <div className="flex flex-wrap gap-1.5">
          {Object.entries(margins).map(([k, v]) => (
            <Badge key={k}>
              {kitapAdi(k)} %{v.toFixed(2)}
            </Badge>
          ))}
        </div>

        <div className="-mx-1 overflow-x-auto px-1">
          <table className="w-full min-w-[600px] text-[12.5px]">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-1.5 pr-2 font-medium">#</th>
                {books.map((b) => (
                  <th key={b} className="py-1.5 pr-3 font-medium">
                    {kitapAdi(b)}
                  </th>
                ))}
                <th className="py-1.5 pr-3 text-right font-medium">Hareket</th>
                <th className="py-1.5 text-right font-medium">Ayrışma</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.no} className="border-b border-border/50">
                  <td className="py-1.5 pr-2 tabular-nums text-muted-foreground">
                    {r.no}
                  </td>
                  {books.map((b) => (
                    <td key={b} className="py-1.5 pr-3 font-mono tabular-nums">
                      {ucluAd(r.books[b] ?? null)}
                    </td>
                  ))}
                  <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                    {r.movement_symbol && Math.abs(r.movement ?? 0) >= 0.005 ? (
                      <span
                        className={
                          (r.movement ?? 0) > 0
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-rose-600 dark:text-rose-400"
                        }
                      >
                        {r.movement_symbol} {(100 * (r.movement ?? 0)).toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="py-1.5 text-right font-mono tabular-nums">
                    {(100 * r.disagreement).toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <ul className="list-disc space-y-1.5 pl-5 text-[12.5px] leading-relaxed">
          <li>
            <strong>Ana fiyat neden bu?</strong> Seçim iddia değil ölçüm:{" "}
            <code>scripts/acilis_kapanis.py</code> geçen sezon arşivinde
            kapanışı açılışın önünde ölçtü (Brier %0,27 daha iyi; yedi hareket
            bandının beşinde gerçekleşme kapanışı takip etti; kural kapanışla
            beslenince 36 haftanın 36&apos;sında ≥12 ve hafta başına 2.051
            kolon, açılışta 2.664). Bahisçi tarafında en düşük marj seçildi.
          </li>
          <li>
            <strong>En büyük hareket:</strong> {enHareket.no}. maç —{" "}
            <strong>{enHareket.movement_symbol}</strong> sembolü{" "}
            {(100 * (enHareket.movement ?? 0)).toFixed(1)} puan. Arşiv, bu
            büyüklükteki hareketlerde <strong>kapanışın haklı çıktığını</strong>{" "}
            ölçüyor.
          </li>
          {Object.keys(bayat).length ? (
            <li>
              <strong>Bayat kapanış.</strong> Şu satırlarda kapanış oranı
              açılışla birebir aynı —{" "}
              {Object.entries(bayat)
                .map(([k, ns]) => `${kitapAdi(k)}: ${ns.join(", ")}. maç`)
                .join("; ")}
              . Bunlar fiyat değil, tazelenmemiş kayıttır: o satırlarda
              ayrışma sütununda görünen fark <strong>görüş farkı değil, kayıt
              farkıdır</strong>.
            </li>
          ) : null}
          <li>
            <strong>Ayrışma nerede yoğunlaşıyor?</strong> En büyüğü{" "}
            {enAyrisma.no}. maçta, {(100 * enAyrisma.disagreement).toFixed(1)}{" "}
            puan. Büyük ayrışmada önce yukarıdaki bayatlık listesine
            bakılmalı: iki bahisçi farklı düşünüyor olabilir, ya da biri
            saatler önce durmuş olabilir.
          </li>
        </ul>
      </CardBody>
    </Card>
  );
}

/** Dondurulan kuponun yanindaki REDDEDILENLER — kupon gerekcesini boyle tasir. */
export function KuponGerekcesi({ kupon }: { kupon: SuperTotoKupon }) {
  const varyantlar = kupon.variants ?? [];
  if (varyantlar.length < 2 && !kupon.duyarlilik && !kupon.lines) return null;

  // P(>=12) yalnizca HEDEF kuraliyla dondurulmus kayitlarda var; esik
  // kuraliyla donan 1. ve 2. haftada alan yok ve sutun bastan sona tire
  // olurdu. Tamami bos bir sutun bilgi tasimaz — o yuzden hic cizilmez.
  // Bir tanesi bile doluysa sutun kalir ve eksik olan hucre tire gorunur.
  const hedefVar = varyantlar.some((v) => v.hedef !== null && v.hedef !== undefined);

  return (
    <Card>
      <CardHeader
        title="Kupon niçin bu?"
        hint="kuralın aynı haftada verdiği seçenekler"
      />
      <CardBody className="space-y-3">
        {varyantlar.length > 1 ? (
          <div className="-mx-1 overflow-x-auto px-1">
            <table className="w-full min-w-[560px] text-[12.5px]">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-1.5 pr-3 font-medium">Kupon</th>
                  {hedefVar ? (
                    <th className="py-1.5 pr-3 text-right font-medium">
                      P(≥12)
                    </th>
                  ) : null}
                  <th className="py-1.5 pr-3 text-right font-medium">Kolon</th>
                  <th className="py-1.5 pr-3 text-right font-medium">Küme-içi</th>
                  <th className="py-1.5 pr-3 text-right font-medium">
                    Aynı seti oynayan halk
                  </th>
                  <th className="py-1.5 text-right font-medium">Oran</th>
                </tr>
              </thead>
              <tbody>
                {varyantlar.map((v, i) => {
                  const donmus = (v.label ?? "").includes("DONDURULAN");
                  return (
                    <tr
                      key={i}
                      className={
                        "border-b border-border/50 " +
                        (donmus ? "bg-primary/5 font-medium" : "")
                      }
                    >
                      <td className="py-1.5 pr-3">{v.label ?? "—"}</td>
                      {hedefVar ? (
                        <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                          {_yuzde(v.hedef ?? undefined, 2)}
                        </td>
                      ) : null}
                      <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                        {v.columns?.toLocaleString("tr-TR") ?? "—"}
                      </td>
                      <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                        {_yuzde(v.in_set_p ?? undefined, 3)}
                      </td>
                      <td className="py-1.5 pr-3 text-right font-mono tabular-nums">
                        {_yuzde(v.crowd_in_set_p ?? undefined, 3)}
                      </td>
                      <td className="py-1.5 text-right font-mono tabular-nums">
                        {v.crowd_ratio?.toFixed(2) ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        {kupon.kalabalik_gerekcesi ? (
          <p className="text-[12.5px] leading-relaxed text-muted-foreground">
            {kupon.kalabalik_gerekcesi}
          </p>
        ) : null}

        {kupon.duyarlilik ? (
          <div className="rounded-md border border-border/70 bg-muted/30 p-3">
            <div className="text-[12px] font-medium">Fiyat duyarlılığı</div>
            <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
              {kupon.duyarlilik.not} {kupon.duyarlilik.fark}
            </p>
            {kupon.duyarlilik.picks ? (
              <div className="mt-2 font-mono text-[12.5px]">
                {kupon.duyarlilik.picks.join(" ")}
                {kupon.duyarlilik.hedef !== null ? (
                  <span className="ml-2 text-muted-foreground">
                    P(≥12) {_yuzde(kupon.duyarlilik.hedef ?? undefined, 2)}
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {kupon.lines?.length ? (
          <details className="rounded-md border border-border/70 p-3">
            <summary className="cursor-pointer text-[12.5px] font-medium">
              Oynanacak {kupon.lines.length} satır (14-garantili)
            </summary>
            <div className="mt-2 -mx-1 overflow-x-auto px-1">
              <table className="w-full min-w-[520px] font-mono text-[12px]">
                {/* Mac numarasi basligi olmadan izgara okunmaz: hangi
                    sutunun hangi mac oldugu ancak sayarak bulunurdu. */}
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="py-1 pr-3 font-normal" />
                    {Array.from({ length: 15 }, (_, i) => (
                      <th key={i} className="py-1 pr-2 text-left font-normal">
                        {i + 1}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {kupon.lines.map((satir, i) => (
                    <tr key={i} className="border-b border-border/40">
                      <td className="py-1 pr-3 text-muted-foreground">
                        {i + 1}
                      </td>
                      {satir.trim().split(/\s+/).map((h, j) => (
                        <td key={j} className="py-1 pr-2 tabular-nums">
                          {h}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[11.5px] leading-relaxed text-muted-foreground">
              Garanti <strong>koşulludur</strong>: ancak gerçek sonuç seçim
              kümesinin içindeyse geçerlidir.
            </p>
          </details>
        ) : null}
      </CardBody>
    </Card>
  );
}
