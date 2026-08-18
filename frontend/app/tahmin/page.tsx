"use client";

import * as React from "react";
import { RefreshCw } from "lucide-react";

import { getTahmin } from "@/lib/api";
import type { TahminResponse } from "@/lib/types";
import {
  Button,
  Callout,
  Card,
  CardBody,
  SectionTitle,
  Skeleton,
} from "@/components/ui/primitives";
import {
  IsabetKarti,
  Sinirlar,
  TahminTablosu,
} from "@/components/tahmin/parts";

/**
 * Tahmin sayfası — yaklaşan maçlara olasılık.
 *
 * Sayfanın kuruluşu bir sıralama kararı taşıyor ve karar bilinçlidir:
 * **ölçülmüş isabet, tahmin tablosunun ÜSTÜNDEDİR.** Kullanıcı önce bu
 * tahmincinin 540 maçta ne yaptığını görür, sonra bu haftanın sayılarını.
 * Ters sırada olsaydı isabet bir dipnot olurdu; sayfanın amacı ise onu
 * dipnot olmaktan çıkarmak.
 *
 * Aynı sebeple sınırlar katlanmaz ve "detay" arkasına konmaz. En önemlisi
 * — bu tahminci tek kolonla 14+ tutturamaz — sayfada tam metniyle durur.
 */
export default function TahminSayfasi() {
  const [veri, setVeri] = React.useState<TahminResponse | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = React.useState(true);

  const yukle = React.useCallback((signal?: AbortSignal) => {
    setYukleniyor(true);
    setHata(null);
    getTahmin({}, signal)
      .then((g) => {
        setVeri(g);
        setYukleniyor(false);
      })
      .catch((e: unknown) => {
        if (signal?.aborted) return;
        setHata(e instanceof Error ? e.message : "Tahmin alınamadı");
        setYukleniyor(false);
      });
  }, []);

  React.useEffect(() => {
    const c = new AbortController();
    yukle(c.signal);
    return () => c.abort();
  }, [yukle]);

  return (
    <div className="mx-auto w-full max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Tahmin</h1>
          <p className="mt-1 max-w-[62ch] text-[13px] leading-relaxed text-muted-foreground">
            Yaklaşan maçlar için 1 / 0 / 2 olasılığı. Olasılıklar marj
            arındırılmış piyasa fiyatıdır — bir model değil. Yanında her zaman
            bu tahmincinin <strong>ölçülmüş</strong> isabeti durur.
          </p>
        </div>
        <Button
          tip="ghost"
          onClick={() => yukle()}
          disabled={yukleniyor}
          aria-label="Yenile"
        >
          <RefreshCw size={15} className={yukleniyor ? "animate-spin" : ""} />
          Yenile
        </Button>
      </div>

      {hata ? (
        <Callout ton="danger" baslik="Tahmin alınamadı">
          {hata}
        </Callout>
      ) : null}

      {yukleniyor && !veri ? (
        <div className="space-y-3">
          <Skeleton className="h-[132px] w-full" />
          <Skeleton className="h-[280px] w-full" />
        </div>
      ) : null}

      {veri ? (
        <>
          {/* Isabet ONCE gelir — bkz. dosya basligi. */}
          <IsabetKarti isabet={veri.olculmus_isabet} />

          <div className="space-y-3">
            <SectionTitle
              hint={
                veri.n_mac
                  ? `${veri.n_mac} maç · kaynak: ${veri.kaynaklar.join(", ")}`
                  : undefined
              }
            >
              Yaklaşan maçlar
            </SectionTitle>

            {veri.n_mac ? (
              <Card>
                <CardBody>
                  <TahminTablosu
                    satirlar={veri.tahminler}
                    yildizGoster={veri.tahminler.some((t) => t.olculen_lig)}
                  />
                  {veri.tahminler.some((t) => t.olculen_lig) &&
                  veri.tahminler.some((t) => !t.olculen_lig) ? (
                    <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
                      <span className="text-warning">*</span> Ölçülen isabet bu
                      ligin maçlarına ait değil.
                    </p>
                  ) : null}
                </CardBody>
              </Card>
            ) : (
              <Callout ton="neutral" baslik="Yaklaşan maç yok">
                {veri.bos_sebep}
              </Callout>
            )}
          </div>

          <div className="space-y-3">
            <SectionTitle hint="hiçbiri katlanmaz">Sınırlar</SectionTitle>
            <Sinirlar uyarilar={veri.uyarilar} />
          </div>
        </>
      ) : null}
    </div>
  );
}
