"use client";

import * as React from "react";
import { RefreshCw } from "lucide-react";

import { getTakimlar } from "@/lib/api";
import { useIstek } from "@/lib/istek";
import type { KucultulmusOlcu, TakimSatiri } from "@/lib/types";
import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
} from "@/components/ui/primitives";

const OLCU_BASLIK: Record<string, string> = {
  puan: "Puan",
  gol_at: "Attığı",
  gol_ye: "Yediği",
};

/**
 * Küçültme oranının **görsel** karşılığı. Sayının yanında bir çubuk
 * durması, "%74'ü takımın kendi verisi" cümlesini okumadan da anlaşılır
 * kılıyor — ve bu sayfanın var olma sebebi tam olarak o cümledir.
 */
function KucultmeCubugu({ b }: { b: number }) {
  return (
    <span
      className="inline-flex h-1.5 w-10 overflow-hidden rounded-full bg-border align-middle"
      title={`Sayının %${(100 * b).toFixed(0)}'i takımın kendi verisi`}
      aria-label={`küçültme ${(100 * b).toFixed(0)} yüzde`}
    >
      <span
        className="h-full bg-foreground/60"
        style={{ width: `${Math.round(100 * b)}%` }}
      />
    </span>
  );
}

function OlcuHucresi({ o, basamak = 2 }: { o: KucultulmusOlcu; basamak?: number }) {
  return (
    <td className="py-2 pr-3 text-right tabular-nums">
      <span className="font-medium">{o.kucultulmus.toFixed(basamak)}</span>
      <span className="ml-1 text-[11px] text-muted-foreground">
        [{o.alt.toFixed(basamak)}, {o.ust.toFixed(basamak)}]
      </span>
    </td>
  );
}

function LigTablosu({
  lig,
  takimlar,
  kucultmeYapildi,
}: {
  lig: string;
  takimlar: TakimSatiri[];
  kucultmeYapildi: boolean;
}) {
  return (
    <Card>
      <CardHeader
        title={lig}
        hint={`${takimlar.length} takım${
          kucultmeYapildi ? "" : " · küçültme yapılamadı (az takım)"
        }`}
      />
      <CardBody>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-[13px]">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border/60 text-left">
                <th className="py-2 pr-3 font-medium">Takım</th>
                <th className="py-2 pr-3 text-right font-medium">Maç</th>
                <th className="py-2 pr-3 text-right font-medium">Kendi verisi</th>
                <th className="py-2 pr-3 text-right font-medium">
                  {OLCU_BASLIK.puan}
                </th>
                <th className="py-2 pr-3 text-right font-medium">
                  {OLCU_BASLIK.gol_at}
                </th>
                <th className="py-2 pr-3 text-right font-medium">
                  {OLCU_BASLIK.gol_ye}
                </th>
              </tr>
            </thead>
            <tbody>
              {takimlar.map((t) => (
                <tr key={t.takim} className="border-b border-border/30">
                  <td className="py-2 pr-3">{t.takim}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{t.n}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    <KucultmeCubugu b={t.puan.kucultme} />
                    <span className="ml-2 text-[11px] text-muted-foreground">
                      %{(100 * t.puan.kucultme).toFixed(0)}
                    </span>
                  </td>
                  <OlcuHucresi o={t.puan} />
                  <OlcuHucresi o={t.gol_at} />
                  <OlcuHucresi o={t.gol_ye} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}

/**
 * Takım bazlı istatistik.
 *
 * Bu sayfa uzun süre **yasaktı** ve gerekçesi `ISTATISTIK_YOL_HARITASI.md`
 * §7'de yazılıydı: *"216 takım, Süper Lig takımları bile 32 maç. Çıkacak
 * sayı güvenilir görünür ama gürültüdür."* Teşhis doğruydu, çare yanlıştı:
 * az örnekli bir ortalamanın gürültülü olması onu **yasaklamayı** değil,
 * ne kadarının gürültü olduğunu **göstermeyi** gerektirir.
 *
 * Sayfanın bütün kuruluşu bu cümleden çıkıyor. Her satırda maç sayısı,
 * küçültme oranı ve %95 aralık durur; küçültme oranı bir çubukla ayrıca
 * görünür. Az maçlı takımın sayısı lig ortalamasına yaklaşır ve **bunu
 * kendisi söyler**.
 */
export default function TakimlarSayfasi() {
  const [lig, setLig] = React.useState<string>("");
  const [sezon, setSezon] = React.useState<string>("");
  const { veri, hata, yukleniyor, yenile } = useIstek(
    (signal) => getTakimlar(lig || undefined, sezon || undefined, signal),
    [lig, sezon],
    { varsayilanHata: "Takım verisi alınamadı" },
  );

  // Lig ve sezon listeleri SUZULMEMIS govdeden gelmeli; suzulmus govdede
  // yalnizca secili olan bulunur ve acilir menu kendini kilitler.
  const [ligler, setLigler] = React.useState<string[]>([]);
  React.useEffect(() => {
    if (!lig && veri) setLigler(veri.ligler.map((g) => g.lig));
  }, [lig, veri]);

  return (
    <div className="mx-auto w-full max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Takımlar</h1>
          <p className="mt-1 max-w-[64ch] text-[13px] leading-relaxed text-muted-foreground">
            Her sayı <strong>küçültülmüştür</strong>: lig ortalamasına doğru,
            maç sayısına bağlı olarak çekilir. Az maçlı bir takım otomatik
            olarak lig ortalamasına düşer — <em>&quot;kendi verisi&quot;</em>{" "}
            sütunu bunu doğrudan gösterir.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Lig"
            className="h-9 rounded-md border border-border bg-background px-2 text-[13px]"
            value={lig}
            onChange={(e) => setLig(e.target.value)}
          >
            <option value="">Tüm ligler</option>
            {ligler.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <input
            aria-label="Sezon"
            placeholder="sezon (2425)"
            className="h-9 w-[130px] rounded-md border border-border bg-background px-2 text-[13px]"
            value={sezon}
            onChange={(e) => setSezon(e.target.value.trim())}
          />
          <Button tip="ghost" onClick={yenile} aria-label="Yenile">
            <RefreshCw size={15} />
          </Button>
        </div>
      </div>

      {hata ? <Callout ton="danger" baslik="Hata">{hata}</Callout> : null}

      {veri ? (
        <Callout ton="warning" baslik="Bu sayılar nasıl okunur">
          {veri.kural}
        </Callout>
      ) : null}

      {yukleniyor && !veri ? <Skeleton className="h-96 w-full" /> : null}

      {veri && veri.ligler.length === 0 ? (
        <Callout ton="primary" baslik="Veri yok">
          Bu süzgeçle en az {veri.en_az_mac} maç oynamış takım bulunamadı.
        </Callout>
      ) : null}

      {veri?.ligler.map((g) => (
        <LigTablosu
          key={g.lig}
          lig={g.lig}
          takimlar={g.takimlar}
          kucultmeYapildi={g.kucultme_yapildi}
        />
      ))}

      {veri ? (
        <p className="text-[12px] leading-relaxed text-muted-foreground">
          Aralık, <strong>küçültülmüş</strong> tahminin %95 aralığıdır — ham
          ortalamanın değil. Ham ortalamanın aralığı 5 maçlık bir takımda o
          kadar geniştir ki hiçbir şey söylemez. Takımlar arası yayılımın
          (<code>τ</code>) kendi belirsizliği aralığa dahil değildir; az
          takımlı liglerde gerçek aralık buradakinden geniştir.
        </p>
      ) : null}
    </div>
  );
}
