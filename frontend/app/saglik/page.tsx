"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, XCircle } from "lucide-react";

import { getHealth } from "@/lib/api";
import type { HealthReport } from "@/lib/types";
import { cn, sure } from "@/lib/utils";
import {
  Badge,
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";

export default function SaglikPage() {
  const [rapor, setRapor] = React.useState<HealthReport | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = React.useState(true);

  const yukle = React.useCallback(async (signal?: AbortSignal) => {
    setYukleniyor(true);
    setHata(null);
    try {
      setRapor(await getHealth(signal));
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setHata(e instanceof Error ? e.message : String(e));
    } finally {
      setYukleniyor(false);
    }
  }, []);

  React.useEffect(() => {
    const ac = new AbortController();
    void yukle(ac.signal);
    return () => ac.abort();
  }, [yukle]);

  const saglikli = rapor?.ok ?? false;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-[30px] italic leading-tight">
            Sistem sağlığı
          </h1>
          <p className="mt-1 max-w-2xl text-[13.5px] leading-relaxed text-muted-foreground">
            Motorun 14 değişmezi (invariant). Bunlar testten farklıdır: çalışan
            sürümün 14-garantiyi, olasılık ve Bayes hattını gerçekten
            koruduğunu her çağrıda yeniden doğrular.
          </p>
        </div>
        <Button
          tip="outline"
          boyut="sm"
          onClick={() => void yukle()}
          disabled={yukleniyor}
        >
          <RefreshCw size={14} className={cn(yukleniyor && "animate-spin")} />
          Yeniden çalıştır
        </Button>
      </header>

      {hata ? (
        <Callout ton="danger" baslik="Sağlık raporu alınamadı">
          {hata}
        </Callout>
      ) : null}

      {yukleniyor && !rapor ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : null}

      {rapor ? (
        <>
          <Card
            className={cn(
              "overflow-hidden",
              saglikli ? "border-success/30" : "border-danger/40",
            )}
          >
            <CardBody className="flex flex-wrap items-center gap-5">
              <span
                className={cn(
                  "grid h-14 w-14 shrink-0 place-items-center rounded-2xl",
                  saglikli
                    ? "bg-success-soft text-success"
                    : "bg-danger-soft text-danger",
                )}
              >
                {saglikli ? <CheckCircle2 size={26} /> : <XCircle size={26} />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[19px] font-semibold tracking-tight">
                    {saglikli ? "HEALTHY" : "UNHEALTHY"}
                  </span>
                  <Badge ton={saglikli ? "success" : "danger"}>
                    {rapor.passed}/{rapor.total} geçti
                  </Badge>
                  <Badge>v{rapor.version}</Badge>
                  <Badge ton={rapor.summary?.has_scipy ? "primary" : "warning"}>
                    scipy {rapor.summary?.has_scipy ? "var" : "yok"}
                  </Badge>
                </div>
                <p className="tnum mt-1 text-[12px] text-muted-foreground">
                  {new Date(rapor.timestamp).toLocaleString("tr-TR")}
                </p>
              </div>
            </CardBody>
          </Card>

          {!rapor.summary?.has_scipy ? (
            <Callout ton="warning" baslik="scipy kurulu değil">
              Araç çalışır, yalnızca kesin çözücü (ILP) devre dışıdır —{" "}
              <strong>exact</strong> modu kullanılamaz.
            </Callout>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-3">
            <Stat etiket="Geçen" deger={rapor.passed} ton="success" />
            <Stat
              etiket="Kalan"
              deger={rapor.failed}
              ton={rapor.failed ? "danger" : "neutral"}
            />
            <Stat
              etiket="Toplam süre"
              deger={sure(
                rapor.checks.reduce((a, c) => a + (c.duration_ms || 0), 0),
              )}
            />
          </div>

          <Card>
            <CardHeader
              title="Değişmezler"
              hint="Her satır bağımsız bir kontrol. Detay sütunu, kontrolün o çalışmada ölçtüğü gerçek değerleri gösterir."
            />
            <CardBody className="space-y-1.5">
              {rapor.checks.map((c) => (
                <div
                  key={c.name}
                  className={cn(
                    "flex items-start gap-3 rounded-xl border px-3 py-2.5",
                    c.ok
                      ? "border-line bg-elevated"
                      : "border-danger/40 bg-danger-soft",
                  )}
                >
                  <span className={cn("mt-0.5 shrink-0", c.ok ? "text-success" : "text-danger")}>
                    {c.ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="font-mono text-[12.5px] font-medium">{c.name}</div>
                    {c.detail ? (
                      <div className="tnum mt-0.5 break-words font-mono text-[11.5px] text-muted-foreground">
                        {c.detail}
                      </div>
                    ) : null}
                  </div>
                  <span className="tnum shrink-0 text-[11.5px] text-muted-foreground">
                    {c.duration_ms.toFixed(1)} ms
                  </span>
                </div>
              ))}
            </CardBody>
          </Card>

          {rapor.summary?.ornek_kupon ? (
            <Card>
              <CardHeader title="Kontrollerde kullanılan örnek kupon" />
              <CardBody>
                <code className="tnum block break-all rounded-lg bg-muted px-3 py-2 font-mono text-[12.5px]">
                  {rapor.summary.ornek_kupon}
                </code>
              </CardBody>
            </Card>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
