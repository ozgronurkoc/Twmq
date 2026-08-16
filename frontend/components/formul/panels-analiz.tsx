"use client";

import * as React from "react";
import { AlertTriangle } from "lucide-react";

import { SEMBOLLER, type SolveResult } from "@/lib/types";
import { cn, ondalik, sayi } from "@/lib/utils";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Stat,
} from "@/components/ui/primitives";

// ─── Olasilik (exact + Monte Carlo) ───────────────────────────────────────

export function OlasilikPanel({ r }: { r: SolveResult }) {
  const a = r.advanced;
  if (!a) return null;
  const mc = a.monte_carlo;

  const satirlar = [
    { id: "kume_ici", etiket: "Tüm sonuçlar seçim kümende", exact: a.exact.p_kume_ici, mc: mc.kume_ici },
    { id: "p15", etiket: "15 tutturma", exact: a.exact.p_15, mc: mc.p15 },
    { id: "p14", etiket: "Tam 14 tutturma", exact: a.exact.p_14, mc: mc.p14 },
    { id: "p13", etiket: "13 tutturma", exact: null, mc: mc.p13 },
    { id: "p12", etiket: "12 tutturma", exact: null, mc: mc.p12 },
  ];

  return (
    <div className="space-y-4">
      <Callout ton="primary" baslik="Bu bölüm senin tahminlerine bağlıdır">
        Aşağıdaki sayılar girdiğin olasılıklardan hesaplanır ve{" "}
        <strong>kombinatoryal 14-garanti kadar kesin değildir</strong>. Kaynak:{" "}
        <Badge ton={a.source === "bayes_posterior" ? "primary" : "neutral"}>
          {a.source === "bayes_posterior" ? "Bayes posterior" : "doğrudan girdin"}
        </Badge>
      </Callout>

      <Card>
        <CardHeader
          title="Exact vs Monte Carlo"
          hint={`Monte Carlo ${sayi(mc.n_samples)} denemeyle simüle edildi; ± değerleri %95 güven aralığıdır. İki sütunun yakın olması hesabın tutarlı olduğunu gösterir.`}
        />
        <CardBody className="scroll-slim overflow-x-auto">
          <table className="w-full min-w-[520px] text-[12.5px]">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
                <th className="pb-2 pr-3 font-medium">Olay</th>
                <th className="pb-2 pr-3 text-right font-medium">Exact</th>
                <th className="pb-2 pr-3 text-right font-medium">Monte Carlo</th>
                <th className="pb-2 pr-3 text-right font-medium">±%95</th>
                <th className="pb-2 text-right font-medium">Örnek</th>
              </tr>
            </thead>
            <tbody className="tnum">
              {satirlar.map((s) => (
                <tr key={s.id} className="border-t border-line">
                  <td className="py-2.5 pr-3">{s.etiket}</td>
                  <td className="py-2.5 pr-3 text-right font-mono font-semibold">
                    {s.exact === null ? "—" : `%${s.exact.toFixed(3)}`}
                  </td>
                  <td className="py-2.5 pr-3 text-right font-mono">
                    %{s.mc.pct.toFixed(3)}
                  </td>
                  <td className="py-2.5 pr-3 text-right font-mono text-muted-foreground">
                    ±{s.mc.ci95.toFixed(3)}
                  </td>
                  <td className="py-2.5 text-right font-mono text-muted-foreground">
                    {sayi(s.mc.count)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      {mc.warning ? (
        <Callout ton="warning" baslik="Monte Carlo uyarısı">
          {mc.warning}
        </Callout>
      ) : null}

      <Card>
        <CardHeader title="Sistem oynamak tek kolona göre ne kazandırıyor?" />
        <CardBody className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Stat
              etiket="Sistemle 15 tutturma"
              deger={`%${a.exact.p_15.toFixed(3)}`}
              ton="primary"
            />
            <Stat
              etiket="En olası TEK kolonla 15"
              deger={`%${a.exact.p_tek.toFixed(3)}`}
            />
          </div>
          <Callout ton="neutral">
            Sistemin değeri <strong>14-garantidir</strong>, 15 şansını artırmak
            değil. Kaplama kodu 15 olasılığını değil <strong>kapsamayı</strong>{" "}
            maksimize eder; en olası tek nokta formülün kolonları arasında
            olmayabilir — bu yüzden üstteki sayı alttakinden küçük çıkabilir ve bu
            bir hata değildir.
          </Callout>
          <Callout ton="warning">
            Bunlar <strong>beklenen-değer veya kâr hesabı değildir</strong>.
            İkramiye havuzu ve kolon bedeli hesaba katılmaz.
          </Callout>
        </CardBody>
      </Card>
    </div>
  );
}

// ─── Bayes ────────────────────────────────────────────────────────────────

export function BayesPanel({ r }: { r: SolveResult }) {
  const b = r.bayes;
  if (!b) return null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Dirichlet güncellemesi"
          hint="Seçim kümene dayalı prior, girdiğin olasılıklarla (evidence) birleştirilir. Sonuç exact ve Monte Carlo motorlarına verilir."
          action={
            <div className="flex gap-2">
              <Badge>α = {b.prior_strength}</Badge>
              <Badge>n = {b.evidence_strength}</Badge>
              {r.bayes_preset ? <Badge ton="primary">{r.bayes_preset}</Badge> : null}
            </div>
          }
        />
        <CardBody className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Stat
              etiket="Ortalama KL kayması"
              deger={ondalik(b.summary.mean_kl_prior_post, 4)}
              alt={b.summary.mean_kl_label}
              ton={
                b.summary.mean_kl_prior_post > 0.7
                  ? "warning"
                  : b.summary.mean_kl_prior_post > 0.3
                    ? "primary"
                    : "neutral"
              }
            />
            <Stat etiket="Güncellenen maç" deger={b.summary.n} />
          </div>
          <Callout ton="neutral" baslik="Bayes 14-garantiyi değiştirmez">
            Yalnızca exact/Monte Carlo motorlarına giden olasılık ağırlıklarını
            günceller. Garanti kombinatoryaldır ve olasılıkla güçlendirilemez.
          </Callout>
        </CardBody>
      </Card>

      {b.summary.top_shifts?.length ? (
        <Card>
          <CardHeader
            title="En çok kayan maçlar"
            hint="Prior ile evidence'ın en çok çatıştığı maçlar. Yüksek KL, tahmininin seçim kümenden belirgin şekilde ayrıştığı anlamına gelir."
          />
          <CardBody className="space-y-2">
            {b.summary.top_shifts.map((t) => (
              <div
                key={t.mac}
                className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-line bg-elevated px-3 py-2.5"
              >
                <span className="tnum w-10 shrink-0 text-[12.5px] font-semibold">
                  {t.mac}.
                </span>
                <span className="tnum w-20 shrink-0 font-mono text-[12px]">
                  {ondalik(t.kl, 4)}
                </span>
                <Badge
                  ton={t.kl > 0.7 ? "warning" : t.kl > 0.3 ? "primary" : "neutral"}
                >
                  {t.kl_label}
                </Badge>
                <span className="tnum ml-auto font-mono text-[11.5px] text-muted-foreground">
                  {SEMBOLLER.map((s) => `${s}:${t.posterior[s].toFixed(2)}`).join("  ")}
                </span>
              </div>
            ))}
          </CardBody>
        </Card>
      ) : null}

      <Card>
        <CardHeader title="Maç bazlı prior → posterior" />
        <CardBody className="scroll-slim overflow-x-auto">
          <table className="w-full min-w-[760px] text-[12px]">
            <thead>
              <tr className="text-left text-[10.5px] uppercase tracking-[0.06em] text-muted-foreground">
                <th className="pb-2 pr-3 font-medium">Maç</th>
                <th className="pb-2 pr-3 font-medium" colSpan={3}>
                  Prior
                </th>
                <th className="pb-2 pr-3 font-medium" colSpan={3}>
                  Evidence
                </th>
                <th className="pb-2 pr-3 font-medium" colSpan={3}>
                  Posterior
                </th>
                <th className="pb-2 pr-3 text-right font-medium">KL</th>
                <th className="pb-2 font-medium">Yorum</th>
              </tr>
              <tr className="text-[10px] text-muted-foreground">
                <th />
                {(["prior", "evidence", "posterior"] as const).map((grup) =>
                  SEMBOLLER.map((s) => (
                    <th key={`${grup}-${s}`} className="pb-1.5 pr-1 text-right font-mono font-normal">
                      {s}
                    </th>
                  )),
                )}
                <th />
                <th />
              </tr>
            </thead>
            <tbody className="tnum">
              {b.matches.map((m) => (
                <tr key={m.mac} className="border-t border-line">
                  <td className="py-2 pr-3 font-semibold">{m.mac}</td>
                  {(["prior", "evidence", "posterior"] as const).map((grup) =>
                    SEMBOLLER.map((s) => (
                      <td
                        key={`${grup}-${s}`}
                        className={cn(
                          "py-2 pr-1 text-right font-mono",
                          grup === "posterior" ? "font-semibold" : "text-muted-foreground",
                        )}
                      >
                        {m[grup][s].toFixed(3)}
                      </td>
                    )),
                  )}
                  <td className="py-2 pr-3 text-right font-mono">{ondalik(m.kl, 4)}</td>
                  <td className="py-2 text-[11px] text-muted-foreground">{m.kl_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="α / n / KL kılavuzu" />
        <CardBody className="space-y-2 text-[12.5px] leading-relaxed text-muted-foreground">
          <p>{b.summary.guide.alpha}</p>
          <p>{b.summary.guide.n}</p>
          <p>{b.summary.guide.kl}</p>
        </CardBody>
      </Card>
    </div>
  );
}

// ─── Markov ───────────────────────────────────────────────────────────────

/**
 * Hata butcesi + kume-ici cozulme egrisi.
 *
 * Onceki surumde burada bir de MAC BAZLI gecis tablosu vardi (p_stay /
 * p_exit). Kaldirildi, cunku ayni sayilardi: sunucuda
 * `p_stay = Σ_{s∈sec} p(s)`, yani girdi kartindaki kutle cubugunun tam
 * kendisi — ve `p_survive` de onlarin carpimi, yani kume-ici kosulu.
 * Ayni sayiyi ikinci kez, üstelik yalnizca motor calistiktan SONRA
 * gostermek bilgi eklemiyordu; girdi kartindaki hali hem canli hem de
 * yaninda ne yapilacagini soyluyor.
 */
export function HataButcesiPanel({ r }: { r: SolveResult }) {
  const m = r.markov;
  if (!m) return null;
  const eb = m.error_budget;
  const kapsamaEksik = eb.tam_kaplama === false;

  return (
    <div className="space-y-4">
      {kapsamaEksik ? (
        <Callout ton="danger" baslik="Kapsama tam değil">
          Bu formülde {sayi(eb.acik_nokta ?? 0)} nokta kapsanmıyor. Aşağıdaki
          &ldquo;garanti&rdquo; olasılığı yalnızca kapsanan bölge içindir —
          14-garanti bu formülde geçerli değildir.
        </Callout>
      ) : null}

      <Card>
        <CardHeader
          title="Hata bütçesi zinciri"
          hint="Seçim kümesi içinde kalındığı varsayımıyla, en yakın kolona göre birikmiş hata. 2+ durumu emicidir: garanti dışıdır."
          action={<Badge>{eb.method}</Badge>}
        />
        <CardBody className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat
              etiket="0 hata (15 doğru)"
              deger={`%${(eb.p_final["0"] * 100).toFixed(3)}`}
              ton="primary"
            />
            <Stat
              etiket="1 hata (14 doğru)"
              deger={`%${(eb.p_final["1"] * 100).toFixed(3)}`}
            />
            <Stat
              etiket="2+ hata (garanti dışı)"
              deger={`%${(eb.p_final["2+"] * 100).toFixed(3)}`}
              ton={eb.p_final["2+"] > 0 ? "danger" : "neutral"}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Stat
              etiket="Küme içi kalma"
              deger={`%${(eb.p_kume_ici * 100).toFixed(3)}`}
              alt="14-garanti ancak burada devreye girer"
            />
            <Stat
              etiket="Küme içi VE en fazla 1 hata"
              deger={`%${(eb.p_garanti * 100).toFixed(3)}`}
              ton={kapsamaEksik ? "warning" : "success"}
            />
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Küme-içi çözülme"
          hint="Maç maç ilerlerken sonucun hâlâ seçim kümende olma olasılığı. Bir kez çıkıldığında geri dönüş yoktur (emici durum)."
        />
        <CardBody className="space-y-3">
          {/*
            Olcek bilerek 0–100'de sabit. Kalma olasiligi yuksekken tum
            cubuklar dolu gorunur; bu dogrudur. Ekseni veri araligina
            germek kucucuk dususleri dramatik gosterirdi — yaniltici olurdu.
          */}
          <div className="flex h-[92px] items-end gap-[3px] border-b border-line">
            {m.survival.p_in_after.map((p, i) => (
              <div
                key={i}
                className="flex-1"
                title={`${i} maç sonra: %${(p * 100).toFixed(3)}`}
              >
                <div
                  className="rounded-t bg-gradient-to-t from-primary/45 to-primary/85 transition-all duration-500 ease-ios"
                  style={{ height: `${Math.max(2, p * 90)}px` }}
                />
              </div>
            ))}
          </div>
          <div className="flex gap-[3px]">
            {m.survival.p_in_after.map((_, i) => (
              <span
                key={i}
                className="tnum flex-1 text-center text-[9.5px] text-muted-foreground"
              >
                {i}
              </span>
            ))}
          </div>
          <div className="flex justify-between text-[10.5px] text-muted-foreground">
            <span>kaç maç oynandı (ölçek %0–100)</span>
            <span className="tnum">
              15 maç sonra %{(m.survival.p_survive * 100).toFixed(3)}
            </span>
          </div>

          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Eğrinin <strong>yatay ekseni kupon sırasıdır</strong>, bir zaman
            değil: maçlar bağımsız olduğu için son değer sıralamadan
            etkilenmez, yalnızca inişin şekli değişir. Maç bazlı kalma
            olasılıkları soldaki{" "}
            <strong>&ldquo;seçim kümen doğru sonucu içeriyor mu&rdquo;</strong>{" "}
            kartındaki kütle çubuklarının ta kendisidir — orada canlı, üstelik
            hangi maçı değiştireceğini de söylüyor.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}

// ─── Hata frekansi ────────────────────────────────────────────────────────

export function HataFrekansPanel({ r }: { r: SolveResult }) {
  const ef = r.error_freq;
  if (!ef) return null;

  const bolum = (
    baslik: string,
    hint: string,
    items: typeof ef.d1,
    toplam: number,
  ) => {
    const enBuyuk = Math.max(...items.map((i) => i.count), 1);
    return (
      <Card>
        <CardHeader title={baslik} hint={hint} action={<Badge>{sayi(toplam)} nokta</Badge>} />
        <CardBody className="space-y-1.5">
          {items.length === 0 ? (
            <p className="text-[12.5px] text-muted-foreground">Bu katmanda nokta yok.</p>
          ) : (
            items.map((it) => (
              <div key={it.mac} className="flex items-center gap-3">
                <span className="tnum w-10 shrink-0 text-[12px] font-medium">
                  {it.mac}.
                </span>
                <div className="h-5 min-w-0 flex-1 overflow-hidden rounded bg-muted">
                  <div
                    className="h-full rounded bg-primary/60 transition-all duration-500 ease-ios"
                    style={{ width: `${(it.count / enBuyuk) * 100}%` }}
                  />
                </div>
                <span className="tnum w-16 shrink-0 text-right font-mono text-[11.5px]">
                  {sayi(it.count)}
                </span>
                <span className="tnum w-14 shrink-0 text-right font-mono text-[11.5px] text-muted-foreground">
                  %{it.pct.toFixed(1)}
                </span>
              </div>
            ))
          )}
        </CardBody>
      </Card>
    );
  };

  return (
    <div className="space-y-4">
      <Callout ton="neutral">
        Uniform varsayım altında, hata olduğunda <strong>hangi maçta</strong>{" "}
        olduğunu gösterir. Yüksek pay alan maçlar formülün en kırılgan
        noktalarıdır — o maçı bankoya çekmek riski en çok düşüren hamledir.
      </Callout>
      {bolum(
        "d = 1 katmanı (14 doğru)",
        "En yakın kolona 1 hata uzaklıktaki noktalarda hata hangi maçta çıkıyor.",
        ef.d1,
        ef.n1,
      )}
      {ef.n2 > 0
        ? bolum(
            "d = 2 katmanı (13 doğru)",
            "Garanti dışı katman. Tam kaplamada burası boş olmalıdır.",
            ef.d2,
            ef.n2,
          )
        : null}
    </div>
  );
}

// ─── Calisma logu ─────────────────────────────────────────────────────────

export function LogPanel({ metin }: { metin?: string }) {
  if (!metin) return null;
  return (
    <Card>
      <CardHeader
        title="Çalışma logu"
        hint="Motorun adım adım ne yaptığı ve her adımın süresi."
      />
      <CardBody>
        <pre className="tnum scroll-slim overflow-x-auto whitespace-pre rounded-xl bg-muted px-4 py-3 font-mono text-[11.5px] leading-relaxed">
          {metin}
        </pre>
      </CardBody>
    </Card>
  );
}

export function BosPanel({
  baslik,
  children,
}: {
  baslik: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardBody className="flex items-start gap-3 py-10">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-muted-foreground" />
        <div className="min-w-0">
          <div className="text-[14px] font-semibold">{baslik}</div>
          <div className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
            {children}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
