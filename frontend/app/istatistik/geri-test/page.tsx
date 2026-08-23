"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { getBacktest } from "@/lib/api";
import { useIstek } from "@/lib/istek";
import { cn, ondalik, sayi } from "@/lib/utils";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  SectionTitle,
  Skeleton,
} from "@/components/ui/primitives";
import {
  BacktestStats,
  BacktestWeeks,
  HoldoutPanel,
  OverfitWarning,
  StrategyPicker,
  SweepTable,
  WeekCoupon,
} from "@/components/istatistik/backtest";
import {
  RangeFilter,
  aralikUrldenOku,
  aralikUrleYaz,
} from "@/components/istatistik/parts";

const ARALIKLAR: Array<{ deger: number | null; etiket: string }> = [
  { deger: null, etiket: "Tüm sezon" },
  { deger: 24, etiket: "Son 24" },
  { deger: 12, etiket: "Son 12" },
];

export default function GeriTestPage() {
  const [last, setLast] = React.useState<number | null>(null);
  const [esik, setEsik] = React.useState<{ banko: number; uclu: number } | null>(null);
  const [urlOkundu, setUrlOkundu] = React.useState(false);

  React.useEffect(() => {
    setLast(aralikUrldenOku());
    setUrlOkundu(true);
  }, []);

  function aralikSec(v: number | null) {
    setLast(v);
    aralikUrleYaz(v);
  }

  const {
    veri,
    hata,
    yukleniyor: mesgul,
  } = useIstek(
    (signal) => getBacktest({ last, banko: esik?.banko, uclu: esik?.uclu }, signal),
    [last, esik?.banko, esik?.uclu],
    { hazir: urlOkundu, varsayilanHata: "Geri test alınamadı" },
  );

  if (hata) {
    return (
      <div className="space-y-4">
        <Link
          href="/istatistik"
          className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft size={15} />
          İstatistik
        </Link>
        <Callout ton="danger" baslik="Geri test alınamadı">
          {hata}
        </Callout>
      </div>
    );
  }

  if (!veri) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  const calisan = veri.weeks.filter((h) => !h.skipped);
  const ornek = calisan.length ? calisan[calisan.length - 1] : null;
  const secili = { banko: veri.strategy.banko, uclu: veri.strategy.uclu };

  return (
    <div className="space-y-6">
      <Link
        href="/istatistik"
        className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft size={15} />
        İstatistik
      </Link>

      <header>
        <h1 className="font-display text-[30px] italic leading-tight">Geri test</h1>
        <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
          “Bu strateji geçen sezon ne yapardı?” Her hafta için kapanış oranlarından bir kupon
          üretilir, 14-garantili kaplama motoru çalıştırılır ve <strong>gerçekleşen sonucun</strong>{" "}
          o kupona ne yaptığı ölçülür. Sonuç bir kâr vaadi değil, stratejinin geçmişteki
          bedelinin ve isabetinin kaydıdır.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge ton="primary">{veri.meta.weeks_used} hafta çalıştırıldı</Badge>
          <Badge>{veri.meta.weeks_available} hafta veri setinde</Badge>
          {veri.meta.weeks_dropped.length ? (
            <Badge ton="warning">{veri.meta.weeks_dropped.length} hafta elendi (oran eksik)</Badge>
          ) : null}
        </div>
        <div className="mt-4">
          <RangeFilter deger={last} onChange={aralikSec} secenekler={ARALIKLAR} mesgul={mesgul} />
          {/* İstatistik sayfasının SliceNote'u burada YANLIŞ olurdu: oradaki
              boşluklar "15 maçı tam kapanmamış hafta", buradakiler ise
              "oranı eksik hafta". Aynı görünen iki eksiklik değil. */}
          <p className="tnum mt-2 text-[11.5px] leading-relaxed text-muted-foreground">
            Seçili kesit:{" "}
            <span className="font-medium text-foreground">
              {veri.weeks.length ? `${veri.weeks[0].week}–${veri.weeks[veri.weeks.length - 1].week}. haftalar` : "—"}
            </span>{" "}
            · {veri.meta.weeks_used} hafta · {veri.meta.weeks_used * veri.meta.match_count} maç
            {last === null ? " — tüm sezon." : ` — veri setindeki son ${last} hafta.`}
            {veri.meta.weeks_dropped.length ? (
              <>
                {" "}
                Hesaba girmeyen{" "}
                <span className="font-medium text-foreground">
                  {veri.meta.weeks_dropped.map((d) => d.week).join(", ")}. hafta
                </span>
                : 15 maçın hepsinde oran yok (milli maç haftalarında kaynak oran yayınlamıyor),
                eksik oran tamamlanmadığı için hafta tamamen elenir.
              </>
            ) : null}
          </p>
        </div>
      </header>

      <OverfitWarning metin={veri.warning} />

      <div className={cn("space-y-6 transition-opacity duration-200", mesgul && "opacity-60")}>
        <Card>
          <CardHeader
            title="Strateji"
            hint={veri.strategy.explain}
            action={
              <Badge>
                %{(veri.strategy.banko * 100).toFixed(0)} /{" "}
                {veri.strategy.uclu === 0 ? "üçlü yok" : `%${(veri.strategy.uclu * 100).toFixed(0)}`}
              </Badge>
            }
          />
          <CardBody className="space-y-5">
            <StrategyPicker
              banko={veri.strategy.banko}
              uclu={veri.strategy.uclu}
              grid={veri.grid}
              onChange={(banko, uclu) => setEsik({ banko, uclu })}
              mesgul={mesgul}
            />
            <BacktestStats season={veri.season} />
            {ornek ? (
              <div>
                <SectionTitle hint="Seçili eşiklerin son çalıştırılan haftada ürettiği kupon.">
                  Örnek kupon
                </SectionTitle>
                <WeekCoupon hafta={ornek} />
              </div>
            ) : null}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Aşırı uyum sağlaması (hold-out)"
            hint="Bir hafta dışarıda bırakılır, eşik kalan haftalarda seçilir, dışarıdaki haftada ölçülür. Karara esas alınacak sayı budur."
          />
          <CardBody>
            <HoldoutPanel holdout={veri.holdout} best={veri.sweep_best} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title={`Eşik taraması (${veri.sweep.length} strateji)`}
            hint="Her satır bir eşik çifti. En iyi satır bu sezona en iyi uyan stratejidir — gelecek sezonun en iyisi değil."
          />
          <CardBody>
            <SweepTable
              rows={veri.sweep}
              best={veri.sweep_best}
              secili={secili}
              onSec={(banko, uclu) => setEsik({ banko, uclu })}
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Hafta hafta"
            hint="Seçili stratejinin her haftada ne yaptığı. “En iyi”, üretilen kolonlar içinde en çok tutturanın doğru sayısıdır."
          />
          <CardBody>
            <BacktestWeeks weeks={veri.weeks} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Yöntem" hint="Sayının nereden geldiği belirsiz kalmamalı." />
          <CardBody className="space-y-2 text-[12.5px] leading-relaxed text-muted-foreground">
            <p>
              <strong className="text-foreground">Olasılık.</strong> Maç sonucu (1/0/2) kapanış
              oranları marj arındırılarak 1’e normalize edilir. {veri.meta.note}.
            </p>
            <p>
              <strong className="text-foreground">Seçim.</strong> {veri.strategy.explain}. 15 maçın
              tamamı bu kuralla işaretlenir; elle müdahale yoktur.
            </p>
            <p>
              <strong className="text-foreground">Kaplama.</strong> Kupon, formül sayfasındaki
              motorun aynısıyla çözülür ve kaplama bağımsız olarak doğrulanır — açık nokta bırakan
              bir çözüm rapora girmez.
            </p>
            <p>
              <strong className="text-foreground">Skor.</strong> “En iyi”, üretilen kolonlar içinde
              gerçekleşen sonuca en çok uyanın doğru sayısıdır. Küme içi kalan hafta 14-garanti
              gereği en az 14 tutturur; küme dışı her maç o haftanın tavanını bir düşürür.
            </p>
            <p>
              <strong className="text-foreground">Elenen hafta.</strong> 15 maçın hepsinde oranı
              olmayan hafta hesaba hiç girmez, tamamlanmaz.{" "}
              {veri.meta.weeks_dropped.length
                ? `Elenen: ${veri.meta.weeks_dropped.map((d) => `${d.week}. (${d.missing} maç)`).join(", ")}.`
                : "Bu dilimde elenen hafta yok."}
            </p>
            <p>
              <strong className="text-foreground">Sınır.</strong> Seçim uzayı{" "}
              {sayi(veri.meta.space_limit)} noktayı aşan hafta çözülmez: doğrulayamadığımız bir
              bedel raporlanmaz. Sezon ortalaması {ondalik(veri.season.rows_avg, 1)} kupon satırı.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
