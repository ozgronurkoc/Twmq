"use client";

import * as React from "react";
import { Check, Copy, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";

import type { ButcePlan, SolveResult } from "@/lib/types";
import { cn, panoyaKopyala, sayi } from "@/lib/utils";
import {
  Badge,
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  SectionTitle,
  Stat,
} from "@/components/ui/primitives";
import { CouponCell, SymbolLegend } from "@/components/ui/symbol";

/** Garanti uc ayri durumdur ve asla belirsiz birakilmaz. */
function garantiDurumu(r: SolveResult) {
  if (r.acik > 0 || r.worst > 1) {
    return {
      ton: "danger" as const,
      icon: <ShieldX size={22} />,
      baslik: "14-garanti YOK",
      detay:
        r.acik > 0
          ? `${sayi(r.acik)} nokta kapsanmıyor (en kötü durum ${r.worst} hata). ` +
            `Bu formül seçim kümenin tamamını korumaz.`
          : `En kötü durumda ${r.worst} hata. 14-garanti kırık.`,
    };
  }
  return {
    ton: "success" as const,
    icon: <ShieldCheck size={22} />,
    baslik: "14-garanti VAR",
    detay:
      "En kötü durumda 1 hata. Bu garanti yalnızca gerçek sonuç seçim kümenin " +
      "içindeyse geçerlidir; küme dışı bir sonuç zaten kapsanmaz.",
  };
}

export function OzetPanel({
  r,
  onPlanSec,
}: {
  r: SolveResult;
  onPlanSec?: (plan: ButcePlan) => void;
}) {
  const g = garantiDurumu(r);
  return (
    <div className="space-y-4">
      <Card className={cn(g.ton === "success" ? "border-success/30" : "border-danger/40")}>
        <CardBody className="flex flex-wrap items-start gap-4">
          <span
            className={cn(
              "grid h-12 w-12 shrink-0 place-items-center rounded-xl",
              g.ton === "success"
                ? "bg-success-soft text-success"
                : "bg-danger-soft text-danger",
            )}
          >
            {g.icon}
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-[17px] font-semibold tracking-tight">{g.baslik}</div>
            <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
              {g.detay}
            </p>
          </div>
        </CardBody>
      </Card>

      {/* satir != kolon: bu ikisi asla ayri gosterilmez */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          etiket="Kupon satırı"
          deger={sayi(r.satir_sayisi)}
          alt="elle doldurulacak satır"
        />
        <Stat
          etiket="Kolon bedeli"
          deger={sayi(r.kolon_bedeli)}
          ton="primary"
          alt="ÖDENECEK TUTAR budur"
        />
        <Stat
          etiket="Küre-kaplama alt sınırı"
          deger={sayi(r.alt_sinir)}
          alt="bu sayının altı matematiksel olarak imkânsız"
        />
        <Stat
          etiket="Değişken uzay"
          deger={sayi(r.total_space)}
          alt={`${r.match_count} maç`}
        />
      </div>

      <Callout ton="warning" baslik="Satır ≠ kolon">
        Bir maça çifte işaretlersen o satır <strong>2 kolon</strong> üretir ve 2
        kolon bedeli ödersin. Yukarıda <strong>{sayi(r.satir_sayisi)} satır</strong>{" "}
        var ama ödeyeceğin tutar <strong>{sayi(r.kolon_bedeli)} kolon</strong>.
      </Callout>

      {r.notlar?.length ? (
        <Card>
          <CardHeader title="Motor notları" />
          <CardBody className="space-y-1.5">
            {r.notlar.map((n, i) => (
              <p key={i} className="text-[12.5px] leading-relaxed text-muted-foreground">
                {n}
              </p>
            ))}
          </CardBody>
        </Card>
      ) : null}

      {r.uyarilar?.length ? (
        <Callout ton="warning" baslik="Girdi uyarıları">
          <ul className="list-inside list-disc space-y-1">
            {r.uyarilar.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </Callout>
      ) : null}

      {r.butce_planlari?.length ? (
        <Card>
          <CardHeader
            title="Bütçe planları"
            hint="Motor, bütçene sığması için hangi maçları kısabileceğini sıraladı. Uygulanan plan işaretli."
          />
          <CardBody className="space-y-2">
            {r.butce_planlari.map((p) => (
              <button
                key={p.index}
                type="button"
                onClick={() => onPlanSec?.(p)}
                disabled={!onPlanSec || p.secili}
                className={cn(
                  "flex w-full flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border px-3 py-2.5 text-left",
                  "transition-colors duration-200 ease-smooth",
                  p.secili
                    ? "border-primary/50 bg-accent"
                    : "border-line bg-elevated hover:border-primary/30 enabled:hover:bg-accent/50",
                )}
              >
                <span className="tnum w-6 shrink-0 text-[12px] font-semibold">
                  {p.index}.
                </span>
                <span className="tnum w-24 shrink-0 text-[12.5px] font-semibold">
                  {sayi(p.bedel)} kolon
                </span>
                <span className="min-w-0 flex-1 text-[12px] text-muted-foreground">
                  {p.degisiklikler.length
                    ? p.degisiklikler.join(" · ")
                    : "değişiklik yok"}
                </span>
                {p.p_kume_ici !== null ? (
                  <span className="tnum shrink-0 text-[11.5px] text-muted-foreground">
                    {/* Zaten yuzde (bkz. types.ts:ButcePlan). Ham
                        basiliyordu: sunucudan 3 basamak geldigi icin
                        "%2.309" gibi, arayuzun geri kalaniyla uyumsuz. */}
                    küme içi %{p.p_kume_ici.toFixed(2)}
                  </span>
                ) : null}
                {p.secili ? <Badge ton="primary">uygulandı</Badge> : null}
              </button>
            ))}
          </CardBody>
        </Card>
      ) : null}

      {r.stat_lines?.length ? (
        <Card>
          <CardHeader title="Kupon geometrisi" />
          <CardBody>
            <div className="space-y-1">
              {r.stat_lines.map((s, i) => (
                <p
                  key={i}
                  className="tnum whitespace-pre-wrap font-mono text-[12px] text-muted-foreground"
                >
                  {s}
                </p>
              ))}
            </div>
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}

export function KuponPanel({
  r,
  labels = [],
}: {
  r: SolveResult;
  /** 15 maç adı; boş olanlar M1…M15 olarak yazılır. */
  labels?: string[];
}) {
  const [kopyalandi, setKopyalandi] = React.useState(false);

  /*
    Kopyalanan metnin baslik satiri adlari tasir. Tabloyu bir hesap
    tablosuna yapistirip kuponu elle doldururken "M7" hangi macti sorusunun
    cevabi orada olmali; sutun numarasi tek basina isi ekrana geri
    donmeye birakiyordu. Sekme ayraci oldugu icin ad icindeki bosluklar
    sorun degil.
  */
  const metin = React.useMemo(() => {
    const basliklar = [
      "#",
      ...Array.from({ length: r.match_count }, (_, i) => labels[i] || `M${i + 1}`),
      "Kolon",
    ].join("\t");
    const satirlar = r.rows.map((row, i) =>
      [i + 1, ...row.cells, row.cost].join("\t"),
    );
    return [basliklar, ...satirlar].join("\n");
  }, [r, labels]);

  async function kopyala() {
    try {
      await panoyaKopyala(metin);
      setKopyalandi(true);
      setTimeout(() => setKopyalandi(false), 1800);
    } catch {
      /* pano yoksa sessiz gec */
    }
  }

  return (
    <Card>
      <CardHeader
        title={`Kupona yazılacak — ${sayi(r.satir_sayisi)} satır`}
        hint={`Toplam ${sayi(r.kolon_bedeli)} kolon bedeli. Çok işaretli satırlar birden fazla kolon üretir.`}
        action={
          <Button tip="outline" boyut="sm" onClick={kopyala}>
            {kopyalandi ? <Check size={14} /> : <Copy size={14} />}
            {kopyalandi ? "Kopyalandı" : "Tabloyu kopyala"}
          </Button>
        }
      />
      <CardBody>
        <SymbolLegend className="mb-3" />
        <div className="scroll-slim overflow-x-auto">
          <table className="w-full border-separate border-spacing-0">
            <thead>
              <tr>
                <th className="sticky left-0 z-10 bg-card pb-2 pr-3 text-left text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                  #
                </th>
                {Array.from({ length: r.match_count }, (_, i) => (
                  <th
                    key={i}
                    // Tablo 15 sutun genis; ad sigmaz ama kaybolmasin da.
                    title={labels[i] || undefined}
                    className={cn(
                      "px-0.5 pb-2 text-center text-[10px] font-semibold text-muted-foreground",
                      labels[i] && "cursor-help underline decoration-dotted underline-offset-2",
                    )}
                  >
                    {i + 1}
                  </th>
                ))}
                <th className="pb-2 pl-3 text-right text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                  Kolon
                </th>
              </tr>
            </thead>
            <tbody>
              {r.rows.map((row, i) => (
                <tr
                  key={i}
                  className={cn(
                    // 4'erli gruplama: 16-32 satiri elle gecirirken goz kaymasin
                    i > 0 && i % 4 === 0 && "border-t",
                  )}
                >
                  <td
                    className={cn(
                      "tnum sticky left-0 z-10 bg-card py-1 pr-3 text-right font-mono text-[11.5px] text-muted-foreground",
                      i > 0 && i % 4 === 0 && "border-t border-line",
                    )}
                  >
                    {i + 1}
                  </td>
                  {row.cells.map((cell, j) => (
                    <td
                      key={j}
                      className={cn(
                        "px-0.5 py-1 text-center",
                        i > 0 && i % 4 === 0 && "border-t border-line",
                      )}
                    >
                      <CouponCell value={cell} />
                    </td>
                  ))}
                  <td
                    className={cn(
                      "tnum py-1 pl-3 text-right font-mono text-[12px]",
                      row.cost > 1 ? "font-semibold text-primary" : "text-muted-foreground",
                      i > 0 && i % 4 === 0 && "border-t border-line",
                    )}
                  >
                    {row.cost}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td
                  colSpan={r.match_count + 1}
                  className="border-t border-line-strong pt-2 text-right text-[12px] font-medium"
                >
                  Toplam kolon bedeli
                </td>
                <td className="tnum border-t border-line-strong pl-3 pt-2 text-right font-mono text-[13px] font-bold text-primary">
                  {sayi(r.kolon_bedeli)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}

export function DagilimPanel({ r }: { r: SolveResult }) {
  const enBuyuk = Math.max(...r.dist.map((d) => d.count), 1);
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Kapsama dağılımı"
          hint="Değişken uzaydaki her noktanın en yakın kolona uzaklığı. d=0 tam isabet, d=1 bir hata."
        />
        <CardBody className="space-y-2">
          {r.dist.map((d) => (
            <div key={d.d} className="flex items-center gap-3">
              <span className="tnum w-20 shrink-0 text-[12px] font-medium">
                {d.label}
              </span>
              <span className="tnum w-8 shrink-0 text-[11px] text-muted-foreground">
                d={d.d}
              </span>
              <div className="h-6 min-w-0 flex-1 overflow-hidden rounded-md bg-muted">
                <div
                  className={cn(
                    "h-full rounded-md transition-all duration-500 ease-ios",
                    d.d === 0 ? "bg-primary" : d.d === 1 ? "bg-primary/55" : "bg-danger/60",
                  )}
                  style={{ width: `${(d.count / enBuyuk) * 100}%` }}
                />
              </div>
              <span className="tnum w-20 shrink-0 text-right font-mono text-[11.5px]">
                {sayi(d.count)}
              </span>
              <span className="tnum w-16 shrink-0 text-right font-mono text-[11.5px] text-muted-foreground">
                %{d.pct}
              </span>
            </div>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Uniform varsayım altında"
          hint="Tüm sonuçlar eşit olasılıklıysa — yani hiçbir tahmin bilgisi kullanılmazsa — kaç doğru tutturursun."
        />
        <CardBody>
          <div className="grid gap-3 sm:grid-cols-4">
            {(["15", "14", "13", "12"] as const).map((k) => (
              <Stat
                key={k}
                etiket={`${k} doğru`}
                deger={`%${r.probs[k]?.pct ?? "0.00"}`}
                alt={`${sayi(r.probs[k]?.count ?? 0)} nokta`}
                ton={k === "15" ? "primary" : "neutral"}
              />
            ))}
          </div>
          <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
            Bu tablo <strong>kombinatoryaldır</strong> — senin tahminlerine değil,
            yalnızca formülün geometrisine bağlıdır. Kendi olasılıklarını girersen
            &ldquo;Olasılık&rdquo; sekmesinde gerçek tahminlerine göre hesap yapılır.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}

export function EksikVeri({ baslik, aciklama }: { baslik: string; aciklama: string }) {
  return (
    <Card>
      <CardBody className="flex items-start gap-3 py-8">
        <ShieldAlert size={18} className="mt-0.5 shrink-0 text-muted-foreground" />
        <div>
          <SectionTitle>{baslik}</SectionTitle>
          <p className="text-[12.5px] leading-relaxed text-muted-foreground">
            {aciklama}
          </p>
        </div>
      </CardBody>
    </Card>
  );
}
