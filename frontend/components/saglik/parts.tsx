"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Info,
  MinusCircle,
  WifiOff,
  XCircle,
} from "lucide-react";

import type { HealthCheck, HealthKategori, HealthReport } from "@/lib/types";
import { cn, sure } from "@/lib/utils";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";

// ─── Durum ────────────────────────────────────────────────────────────────

export type Durum = "saglikli" | "kisitli" | "bozuk";

export function durumu(rapor: HealthReport): Durum {
  if (!rapor.ok) return "bozuk";
  return rapor.degraded ? "kisitli" : "saglikli";
}

export const DURUM_METNI: Record<Durum, string> = {
  saglikli: "HEALTHY",
  kisitli: "DEGRADED",
  bozuk: "UNHEALTHY",
};

export const DURUM_TONU: Record<Durum, "success" | "warning" | "danger"> = {
  saglikli: "success",
  kisitli: "warning",
  bozuk: "danger",
};

export function DurumIkonu({ durum, size = 26 }: { durum: Durum; size?: number }) {
  if (durum === "bozuk") return <XCircle size={size} />;
  if (durum === "kisitli") return <AlertTriangle size={size} />;
  return <CheckCircle2 size={size} />;
}

/**
 * Kontrolun ikonu uc durumu ayirir: gecti, kritik dustu, bilgi amacli
 * kontrol dustu. Ucuncusu kirmizi DEGILDIR — servis calisiyordur.
 */
function KontrolIkonu({ check }: { check: HealthCheck }) {
  if (check.ok) return <CheckCircle2 size={16} className="text-success" />;
  if (!check.critical) return <MinusCircle size={16} className="text-warning" />;
  return <AlertTriangle size={16} className="text-danger" />;
}

// ─── Zaman ────────────────────────────────────────────────────────────────

/**
 * "14 sn once" — sunucuda hesaplanirsa hydration uyusmazligi olur, bu
 * yuzden `simdi` disaridan (mount sonrasi) verilir; null ise sabit metin.
 */
export function goreliZaman(iso: string, simdi: number | null): string {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return "—";
  if (simdi === null) return new Date(t).toLocaleTimeString("tr-TR");
  const sn = Math.max(0, Math.round((simdi - t) / 1000));
  if (sn < 5) return "az önce";
  if (sn < 60) return `${sn} sn önce`;
  const dk = Math.round(sn / 60);
  if (dk < 60) return `${dk} dk önce`;
  return new Date(t).toLocaleString("tr-TR");
}

// ─── Kontrol satiri ───────────────────────────────────────────────────────

export function KontrolSatiri({
  check,
  enUzunMs,
}: {
  check: HealthCheck;
  /** Rapordaki en uzun sure; sure cubugu buna gore olceklenir. */
  enUzunMs: number;
}) {
  const oran = enUzunMs > 0 ? Math.min(1, check.duration_ms / enUzunMs) : 0;
  const kirik = !check.ok && check.critical;

  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-2.5",
        kirik
          ? "border-danger/40 bg-danger-soft"
          : !check.ok
            ? "border-warning/40 bg-warning-soft"
            : "border-line bg-elevated",
      )}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 shrink-0">
          <KontrolIkonu check={check} />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-mono text-[12.5px] font-medium">{check.name}</span>
            {!check.critical ? (
              <Badge ton="neutral" className="gap-1">
                <Info size={11} />
                bilgi
              </Badge>
            ) : null}
          </div>

          <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
            {check.aciklama}
          </p>

          {check.detail ? (
            <div
              className={cn(
                "tnum mt-1.5 break-words rounded-lg px-2 py-1 font-mono text-[11.5px]",
                kirik
                  ? "bg-danger/10 text-danger"
                  : "bg-muted text-muted-foreground",
              )}
            >
              {check.detail}
            </div>
          ) : null}
        </div>

        <span className="tnum shrink-0 pt-0.5 text-[11.5px] text-muted-foreground">
          {check.duration_ms.toFixed(1)} ms
        </span>
      </div>

      {/* Sure cubugu: hangi kontrolun raporu yavaslattigini gozle secmek icin. */}
      <div className="mt-2 h-[3px] overflow-hidden rounded-full bg-line">
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-500 ease-smooth",
            kirik ? "bg-danger" : "bg-primary/50",
          )}
          style={{ width: `${Math.max(1, oran * 100)}%` }}
        />
      </div>
    </div>
  );
}

// ─── Kategori karti ───────────────────────────────────────────────────────

/** Düşenler özetinden ilgili karta atlamak için (§7.17). */
export function kategoriAnkraji(kategoriId: string): string {
  return `saglik-kat-${kategoriId}`;
}

export function KategoriKarti({
  kategori,
  checks,
  enUzunMs,
  calisiyor,
  onCalistir,
}: {
  kategori: HealthKategori;
  checks: HealthCheck[];
  enUzunMs: number;
  calisiyor: boolean;
  onCalistir: (kategoriId: string) => void;
}) {
  if (!checks.length) return null;
  const dusen = kategori.total - kategori.passed;

  return (
    <Card
      id={kategoriAnkraji(kategori.id)}
      className={cn("scroll-mt-24", !kategori.ok && "border-danger/40")}
    >
      <CardHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {kategori.label}
            <Badge ton={!kategori.ok ? "danger" : dusen ? "warning" : "success"}>
              {kategori.passed}/{kategori.total}
            </Badge>
            <span className="tnum text-[11.5px] font-normal text-muted-foreground">
              {sure(kategori.duration_ms)}
            </span>
          </span>
        }
        hint={kategori.aciklama}
        action={
          <button
            type="button"
            disabled={calisiyor}
            onClick={() => onCalistir(kategori.id)}
            className={cn(
              "rounded-lg border border-line-strong px-2.5 py-1.5 text-[11.5px] font-medium",
              "transition-colors duration-200 ease-smooth hover:bg-muted",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60",
              "disabled:pointer-events-none disabled:opacity-50",
            )}
          >
            Yalnızca bunu çalıştır
          </button>
        }
      />
      <CardBody className="space-y-1.5">
        {checks.map((c) => (
          <KontrolSatiri key={c.name} check={c} enUzunMs={enUzunMs} />
        ))}
      </CardBody>
    </Card>
  );
}

// ─── Calisma gecmisi ──────────────────────────────────────────────────────

export interface GecmisKaydi {
  id: number;
  zaman: string;
  ok: boolean;
  degraded: boolean;
  passed: number;
  total: number;
  duration_ms: number;
  kismi: boolean;
  /** Rapor sunucudaki kısa TTL önbelleğinden geldiyse: yeni ölçüm değildir. */
  onbellekten?: boolean;
  /** Dolu ise koşu hiç tamamlanamadı (backend'e ulaşılamadı). */
  hata?: string;
}

/**
 * Oturum ici calisma gecmisi. Kalici degildir; amaci ARADA BIR dusen
 * kontrolu (ornegin Monte Carlo orneklemesi) tek calistirmaya bakarak
 * kacirmamaktir.
 *
 * Ulasilamayan kosular da buraya duser: zaman cizelgesinde en cok gormek
 * isteyecegin olay tam odur, ve yalnizca basarili kosulari kaydeden bir
 * gecmis "iyi gunlerin" kaydina donusur.
 */
export function GecmisSeridi({
  gecmis,
  simdi,
}: {
  gecmis: GecmisKaydi[];
  simdi: number | null;
}) {
  if (gecmis.length < 2) return null;
  const enUzun = Math.max(...gecmis.map((g) => g.duration_ms), 1);

  return (
    <Card>
      <CardHeader
        title="Bu oturumdaki çalışmalar"
        hint="Arada bir düşen bir kontrol tek çalıştırmada görünmez; sütunlar en yeniden en eskiye doğru sıralıdır."
      />
      <CardBody>
        <div className="flex flex-wrap gap-2">
          {gecmis.map((g) => {
            const durum: Durum = !g.ok ? "bozuk" : g.degraded ? "kisitli" : "saglikli";
            const ulasilamadi = Boolean(g.hata);
            return (
              <div
                key={g.id}
                title={
                  ulasilamadi
                    ? `ulaşılamadı — ${g.hata}`
                    : `${g.passed}/${g.total} · ${sure(g.duration_ms)}${
                        g.kismi ? " · kısmi" : ""
                      }${g.onbellekten ? " · önbellekten" : ""}`
                }
                className={cn(
                  "min-w-[92px] flex-1 rounded-xl border px-2.5 py-2",
                  durum === "bozuk"
                    ? "border-danger/40 bg-danger-soft"
                    : durum === "kisitli"
                      ? "border-warning/40 bg-warning-soft"
                      : "border-line bg-elevated",
                  ulasilamadi && "border-dashed",
                )}
              >
                <div className="flex items-center justify-between gap-1">
                  <span
                    className={cn(
                      "tnum text-[12px] font-semibold",
                      durum === "bozuk"
                        ? "text-danger"
                        : durum === "kisitli"
                          ? "text-warning"
                          : "text-success",
                    )}
                  >
                    {ulasilamadi ? (
                      <span className="inline-flex items-center gap-1">
                        <WifiOff size={11} />
                        yok
                      </span>
                    ) : (
                      `${g.passed}/${g.total}`
                    )}
                  </span>
                  {g.kismi ? (
                    <span
                      aria-hidden
                      title="kısmi çalıştırma"
                      className="h-1.5 w-1.5 rounded-full bg-muted-foreground"
                    />
                  ) : null}
                </div>
                <div className="tnum mt-0.5 text-[10.5px] text-muted-foreground">
                  {ulasilamadi
                    ? "ulaşılamadı"
                    : g.onbellekten
                      ? `${sure(g.duration_ms)} · önbellek`
                      : sure(g.duration_ms)}
                </div>
                <div className="mt-1 h-[3px] overflow-hidden rounded-full bg-line">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      ulasilamadi ? "bg-danger/50" : "bg-primary/40",
                    )}
                    style={{
                      width: ulasilamadi
                        ? "100%"
                        : `${(g.duration_ms / enUzun) * 100}%`,
                    }}
                  />
                </div>
                <div className="mt-1 text-[10px] text-muted-foreground">
                  {goreliZaman(g.zaman, simdi)}
                </div>
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}

// ─── Ortam ────────────────────────────────────────────────────────────────

export function OrtamKarti({ rapor }: { rapor: HealthReport }) {
  const env = rapor.summary.env;
  const satirlar: Array<[string, string]> = [
    ["Motor sürümü", `v${rapor.version}`],
    ["Python", env?.python || "—"],
    ["Platform", env?.platform || "—"],
    ["numpy", env?.numpy || "yok"],
    ["scipy", env?.scipy || "yok"],
    ["flask", env?.flask || "yok"],
  ];

  return (
    <Card>
      <CardHeader
        title="Çalışan ortam"
        hint="Rapor bu sürümlerle üretildi — “bende çalışıyordu” tartışmasını kapatır."
      />
      <CardBody className="space-y-3">
        <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
          {satirlar.map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between gap-3 border-b border-line pb-1.5">
              <dt className="text-[12px] text-muted-foreground">{k}</dt>
              <dd className="tnum truncate font-mono text-[12px]">{v}</dd>
            </div>
          ))}
        </dl>

        {rapor.summary.ornek_kupon ? (
          <div>
            <div className="text-[12px] text-muted-foreground">
              Kontrollerde kullanılan örnek kupon
            </div>
            <code className="tnum mt-1 block break-all rounded-lg bg-muted px-3 py-2 font-mono text-[12.5px]">
              {rapor.summary.ornek_kupon}
            </code>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}
