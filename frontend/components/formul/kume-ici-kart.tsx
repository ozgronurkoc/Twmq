"use client";

import * as React from "react";
import { Plus, TriangleAlert } from "lucide-react";

import {
  birdeKac,
  kumeIciHesapla,
  olasilikYaz,
  type Oneri,
} from "@/lib/kume-ici";
import type { ProbRow, Sembol } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { SEMBOL_ADI } from "@/components/ui/symbol";

/**
 * Uretmeden ONCE gorulen kosul: secim kumen dogru sonucu iceriyor mu.
 *
 * Bu kart bir tahmin uretmez ve bir tavsiye vermez; kullanicinin KENDI
 * girdigi olasiliklarin carpimini gosterir. Degeri, 14-garantinin kosulunu
 * isaretleri degistirirken gorunur kilmasindadir — motoru calistirmak
 * gerekmez.
 */
export function KumeIciKart({
  matches,
  probs,
  acik,
  onAc,
  onEsitle,
}: {
  matches: Sembol[][];
  probs: ProbRow[];
  acik: boolean;
  onAc: () => void;
  onEsitle: () => void;
}) {
  const h = React.useMemo(() => kumeIciHesapla(matches, probs), [matches, probs]);

  if (!acik) {
    return (
      <Card>
        <CardBody className="py-3.5">
          <p className="text-[12px] leading-relaxed text-muted-foreground">
            14-garanti <strong>koşulludur</strong>: ancak gerçek sonuç seçim
            kümenin içindeyse devreye girer.{" "}
            <button
              type="button"
              onClick={onAc}
              className="font-medium text-primary underline underline-offset-2 hover:no-underline"
            >
              Olasılık girişini aç
            </button>{" "}
            — o koşulun olasılığını burada, üretmeden önce ve işaretleri
            değiştirdikçe canlı görürsün.
          </p>
        </CardBody>
      </Card>
    );
  }

  const oran = birdeKac(h.p);
  const enBuyukKutle = Math.max(...h.kutleler, 1);

  return (
    <Card className={h.p > 0 ? undefined : "border-danger/40"}>
      <CardHeader
        title="Seçim kümen doğru sonucu içeriyor mu"
        hint="14-garantinin geçerli olması için gereken koşul. Kazanma olasılığı DEĞİLDİR: ikramiye, kolon bedeli ve kaç kişinin tutturduğu bu hesaba girmez."
      />
      <CardBody className="space-y-4">
        {h.imkansizlar.length ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger-soft px-3 py-2.5">
            <TriangleAlert size={16} className="mt-0.5 shrink-0 text-danger" />
            <p className="text-[12px] leading-relaxed">
              <strong>
                {h.imkansizlar.map((i) => i + 1).join(", ")}. maçta
              </strong>{" "}
              işaretlediğin sembollerin olasılığı sıfır. Bu tahminlerle seçim
              kümen doğru sonucu <strong>hiçbir ihtimalle</strong> içeremez —
              formül ne kadar iyi olursa olsun 14-garanti devreye girmez.
            </p>
          </div>
        ) : h.bilgiYok ? (
          /*
            Varsayilan olasilik satirlari tum kutleyi ZATEN isaretli
            sembollere veriyor (uniformProb), yani kume-ici tanim geregi
            %100 cikiyor. O sayiyi basmak "secimin kesin tutar" demek
            olurdu — burada sayi yerine sebebi yazilir.
          */
          <div className="rounded-xl border border-warning/30 bg-warning-soft px-3 py-2.5">
            <p className="text-[12px] leading-relaxed">
              <strong>Henüz tahmin girilmedi.</strong> Olasılık satırları tüm
              kütleyi işaretlediğin sembollere veriyor, o yüzden bu koşul
              tanım gereği %100 çıkıyor ve hiçbir şey anlatmıyor. Aşağıdaki
              olasılık ızgarasına kendi tahminlerini gir — ya da{" "}
              <button
                type="button"
                onClick={onEsitle}
                className="font-medium text-primary underline underline-offset-2 hover:no-underline"
              >
                hepsini eşit (1/3) yap
              </button>{" "}
              da bilgisiz taban çizgisini gör.
            </p>
          </div>
        ) : (
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="tnum font-mono text-[30px] font-semibold leading-none tracking-tight">
              {olasilikYaz(h.p)}
            </span>
            {oran ? (
              <span className="tnum text-[13px] text-muted-foreground">~{oran}</span>
            ) : null}
          </div>
        )}

        {/* Mac basina kutle. Izgarayla ayni sirada durur ki hangi maci
            degistirecegini aramak zorunda kalmayasin. */}
        <div>
          <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
            Maç başına küme-içi kütle
          </div>
          <div className="flex items-end gap-[3px]">
            {h.kutleler.map((kutle, i) => {
              const zayif = h.zayiflar.includes(i);
              return (
                <div key={i} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                  <div
                    className="flex h-12 w-full items-end rounded-[3px] bg-muted"
                    title={`${i + 1}. maç — küme-içi kütle ${(kutle * 100).toFixed(1)}%`}
                  >
                    <div
                      className={cn(
                        "w-full rounded-[3px] transition-all duration-300 ease-ios",
                        kutle <= 0 ? "bg-danger" : zayif ? "bg-warning" : "bg-primary",
                      )}
                      style={{ height: `${Math.max(3, (kutle / enBuyukKutle) * 100)}%` }}
                    />
                  </div>
                  <span
                    className={cn(
                      "tnum text-[9.5px] leading-none",
                      zayif ? "font-semibold text-warning" : "text-muted-foreground",
                    )}
                  >
                    {i + 1}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
            Kütle = o maçta işaretlediğin sembollerin olasılık toplamı.
            Çarpımları yukarıdaki sayıyı verir
            {h.zayiflar.length ? (
              <>
                ; <span className="text-warning">sarı</span> olan üçü toplamı en
                çok aşağı çeken maçlardır
              </>
            ) : null}
            .
          </p>
        </div>

        {h.oneriler.length ? (
          <div>
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              En verimli ekleme
            </div>
            <div className="space-y-1.5">
              {h.oneriler.map((o) => (
                <OneriSatiri key={`${o.mac}-${o.sembol}`} o={o} />
              ))}
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
              Sıralama <strong>verime</strong> göre: küme-içi kazancın bedel
              artışına oranı. Bir sembol eklemek o maçın kolon çarpanını
              büyütür — kararı bu ikisini birlikte görerek ver.
            </p>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

function OneriSatiri({ o }: { o: Oneri }) {
  const sonsuz = !Number.isFinite(o.kumeCarpani);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-line bg-elevated px-3 py-2">
      <span className="flex shrink-0 items-center gap-1.5 text-[12.5px] font-medium">
        <span className="tnum text-muted-foreground">{o.mac + 1}.</span>
        <Plus size={12} className="text-muted-foreground" />
        <span className="font-mono font-semibold">{o.sembol}</span>
        <span className="text-[11.5px] font-normal text-muted-foreground">
          {SEMBOL_ADI[o.sembol]}
        </span>
      </span>
      <span className="tnum shrink-0 text-[12px]">
        küme-içi{" "}
        <strong className="text-success">
          {sonsuz ? "0'dan çıkar" : `×${o.kumeCarpani.toFixed(2)}`}
        </strong>
      </span>
      <span className="tnum shrink-0 text-[12px] text-muted-foreground">
        bedel <strong>×{o.bedelCarpani.toFixed(2)}</strong>
      </span>
      {!sonsuz ? (
        <Badge ton={o.verim >= 1 ? "success" : "neutral"} className="ml-auto shrink-0">
          verim ×{o.verim.toFixed(2)}
        </Badge>
      ) : null}
    </div>
  );
}
