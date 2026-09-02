"use client";

import * as React from "react";

import { SEMBOLLER, type DataQuality } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { ResultStrip } from "@/components/ui/symbol";
import { isaretli } from "./viz";
import { adreseYaz, adrestenOku } from "@/lib/adres";

const ARALIK_PARAM = "last";

/**
 * Filtreyi URL'den okur (`?last=12`). Sunucuda ve ilk render'da null
 * doner; deger bir EFEKTTE uygulanir, cunku statik olarak on-render edilen
 * sayfada render sirasinda `window`'a bakmak hidrasyon uyusmazligi yapar.
 */
export function aralikUrldenOku(): number | null {
  const ham = adrestenOku(ARALIK_PARAM);
  if (!ham || ham === "all") return null;
  const n = Number(ham);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : null;
}

/**
 * Filtreyi adres cubuguna yazar — `/istatistik?last=12` paylasilabilir
 * olsun diye.
 *
 * `router.replace` DEGIL, dogrudan `history.replaceState`: router uzerinden
 * gidildiginde ayni rotaya yapilan replace sayfa bilesenini yeniden
 * bagliyor, `veri` sifirlaniyor ve her filtre tikinda iskelet parliyordu.
 * Arama parametresini ayni yolda degistirmek router'in bilmesi gereken bir
 * sey degil. Olculdu: replaceState ile tablo tikta ayakta kaliyor ve
 * yalnizca beklenen tek `/api/stats` istegi atiliyor.
 */
export function aralikUrleYaz(deger: number | null): void {
  adreseYaz(ARALIK_PARAM, deger && deger > 0 ? String(deger) : null);
}

const SEZON_PARAM = "sezon";

/** Secili sezonu URL'den okur (`?sezon=2023_24`); yoksa null (varsayilan). */
export function sezonUrldenOku(): string | null {
  const ham = adrestenOku(SEZON_PARAM);
  return ham && ham.trim() ? ham.trim() : null;
}

/** Secili sezonu adrese yazar — `aralikUrleYaz` ile ayni gerekce. */
export function sezonUrleYaz(deger: string | null): void {
  adreseYaz(SEZON_PARAM, deger || null);
}

/** "2023_24" -> "2023/24". */
function sezonEtiketi(anahtar: string): string {
  const [bas, son] = anahtar.split("_");
  return son ? `${bas}/${son}` : anahtar;
}

/**
 * Sezon secici.
 *
 * Ilk secenek "Varsayilan" ve bu bir sezon ADI DEGIL: varsayilan kayit
 * (`st_history_2025_26.json`, 41 hafta) ile listedeki `2025_26` (resmi
 * bultenden okunan 29 hafta) AYNI sezonun iki farkli kaydidir. Ikisini
 * "2025/26" diye yan yana koymak hangisinin secildigini belirsizlestirirdi;
 * bu yuzden varsayilan kendi adiyla durur ve rozet kokeni yazar.
 */
export function SeasonFilter({
  deger,
  secenekler,
  onChange,
  mesgul,
}: {
  deger: string | null;
  secenekler: string[];
  onChange: (v: string | null) => void;
  mesgul?: boolean;
}) {
  if (!secenekler.length) return null;
  const hepsi: Array<{ deger: string | null; etiket: string }> = [
    { deger: null, etiket: "Varsayılan" },
    ...secenekler.map((s) => ({ deger: s, etiket: sezonEtiketi(s) })),
  ];
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Sezon">
      {hepsi.map((o) => {
        const secili = o.deger === deger;
        return (
          <Button
            key={String(o.deger)}
            type="button"
            tip={secili ? "primary" : "outline"}
            boyut="sm"
            aria-pressed={secili}
            onClick={() => onChange(o.deger)}
            disabled={mesgul}
          >
            {o.etiket}
          </Button>
        );
      })}
    </div>
  );
}

/**
 * Tum gorselleri kapsayan TEK filtre satiri. Kart icine filtre koymuyoruz:
 * secim degisince butun bloklar ayni dilim uzerinden yeniden hesaplanir,
 * boylece iki gorsel asla farkli veriyi anlatmaz.
 */
export function RangeFilter({
  deger,
  onChange,
  secenekler,
  mesgul,
}: {
  deger: number | null;
  onChange: (v: number | null) => void;
  secenekler: Array<{ deger: number | null; etiket: string }>;
  mesgul?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Hafta aralığı">
      {secenekler.map((o) => {
        const secili = o.deger === deger;
        return (
          <Button
            key={String(o.deger)}
            type="button"
            tip={secili ? "primary" : "outline"}
            boyut="sm"
            aria-pressed={secili}
            onClick={() => onChange(o.deger)}
          >
            {o.etiket}
          </Button>
        );
      })}
      <span
        aria-live="polite"
        className={cn(
          "text-[11.5px] text-muted-foreground transition-opacity duration-200",
          mesgul ? "opacity-100" : "opacity-0",
        )}
      >
        güncelleniyor…
      </span>
    </div>
  );
}

/** [32,33,35,36,…] → ["34", "43–49"] biçiminde eksik aralıklar. */
function eksikAraliklar(numaralar: number[]): string[] {
  // Sinirlar YEREL degiskene alinir. `length < 2` kontrolu indekslerin
  // varligini kanitlar ama tip sistemi bunu goremez; `!` koymak yerine
  // degeri bir kez okuyup daraltmak hem dogru hem okunur.
  const ilk = numaralar[0];
  const son = numaralar[numaralar.length - 1];
  if (numaralar.length < 2 || ilk === undefined || son === undefined) return [];

  const set = new Set(numaralar);
  const eksik: number[] = [];
  for (let n = ilk; n <= son; n++) {
    if (!set.has(n)) eksik.push(n);
  }
  const parcalar: string[] = [];
  let i = 0;
  while (i < eksik.length) {
    let j = i;
    // Ardisik blogu buyut: `eksik[j + 1] === eksik[j] + 1` oldugu surece.
    for (;;) {
      const suanki = eksik[j];
      const sonraki = eksik[j + 1];
      if (suanki === undefined || sonraki === undefined || sonraki !== suanki + 1) break;
      j++;
    }
    const bas = eksik[i];
    const bit = eksik[j];
    if (bas === undefined || bit === undefined) break;
    parcalar.push(i === j ? String(bas) : `${bas}–${bit}`);
    i = j + 1;
  }
  return parcalar;
}

/**
 * Filtrenin altindaki tek satirlik acıklama: hangi haftalar hesaba giriyor.
 * Filtre veriyi kirpmaz, kesit secer — bu satir secimi somutlastirir.
 */
export function SliceNote({
  weeks,
  matches,
  sliced,
}: {
  weeks: number[];
  matches: number;
  sliced: boolean;
}) {
  if (!weeks.length) return null;
  const ilk = weeks[0];
  const son = weeks[weeks.length - 1];
  const bosluk = eksikAraliklar(weeks);

  return (
    <p className="mt-2 text-[11.5px] leading-relaxed text-muted-foreground">
      <span className="tnum">
        Seçili kesit: <span className="font-medium text-foreground">{ilk}–{son}. haftalar</span>
        {" · "}
        {weeks.length} hafta · {matches} maç
      </span>
      {sliced ? " — veri setindeki son " + weeks.length + " hafta." : " — tüm sezon."}
      {bosluk.length > 0 ? (
        <>
          {" "}
          Aradaki <span className="tnum">{bosluk.join(", ")}</span>. haftalar veri setinde yok:
          15 maçı tam kapanmadığı için hiç girmediler.
        </>
      ) : null}
    </p>
  );
}

/** Sayi kutusu — Stat'in sembol rozetli ve farkli surumu. */
export function DeltaStat({
  etiket,
  deger,
  alt,
  delta,
  deltaNot,
  rozet,
  rozetSinif,
}: {
  etiket: string;
  deger: string;
  alt?: string;
  delta?: number;
  deltaNot?: string;
  rozet?: string;
  rozetSinif?: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-elevated px-4 py-3">
      <div className="flex items-center gap-1.5">
        {rozet ? (
          <span
            className={cn(
              "tnum grid h-5 w-5 place-items-center rounded font-mono text-[11px] font-bold text-white",
              rozetSinif,
            )}
          >
            {rozet}
          </span>
        ) : null}
        <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          {etiket}
        </span>
      </div>
      <div className="tnum mt-1 text-[24px] font-semibold leading-tight">{deger}</div>
      {alt ? <div className="tnum mt-0.5 text-[11.5px] text-muted-foreground">{alt}</div> : null}
      {delta !== undefined ? (
        <div className="mt-1.5 text-[11.5px] text-muted-foreground">
          <span className="tnum font-medium text-foreground">{isaretli(delta)}</span>
          {deltaNot ? ` ${deltaNot}` : ""}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Veri kalitesi. Dosyadaki hazir sayim ile 15 karakterlik dizi
 * catistiginda fark burada acikca listelenir — sessizce yutulmaz.
 */
export function DataQualityPanel({ dq }: { dq: DataQuality }) {
  const catisma = dq.count_conflicts ?? [];
  const kopya = dq.duplicate_results ?? [];
  const eksik = dq.incomplete_weeks ?? [];

  if (dq.ok) {
    return (
      <p className="flex items-start gap-2 text-[13px] text-muted-foreground">
        <span aria-hidden className="text-success">
          ✓
        </span>
        <span>
          {dq.weeks_total} haftanın tamamı tutarlı: her hafta 15 maçlık listesini taşıyor, sonuç
          dizisi bu listeden türüyor ve sayımlar ikisiyle de birebir örtüşüyor.
        </span>
      </p>
    );
  }

  return (
    <div className="space-y-3 text-[13px]">
      <p className="flex items-start gap-2">
        <span aria-hidden className="text-warning">
          ⚠
        </span>
        <span>
          <strong className="font-semibold">Veri uyarısı.</strong> Sayımlar 15 karakterlik{" "}
          <code className="text-[12px]">results</code> dizisinden türetilir; dosyadaki hazır{" "}
          <code className="text-[12px]">n1/n0/n2</code> alanları çeliştiğinde aşağıda listelenir.
        </span>
      </p>

      {catisma.length > 0 ? (
        <div>
          <div className="mb-1.5 text-muted-foreground">Sayım çelişkisi: {catisma.length} hafta</div>
          <ul className="tnum space-y-1">
            {catisma.map((c) => (
              <li key={c.week}>
                <span className="font-medium">{c.week}. hafta</span>{" "}
                <span className="text-muted-foreground">
                  dosya {SEMBOLLER.map((s) => c.reported?.[s] ?? 0).join("/")} · dizi{" "}
                  {SEMBOLLER.map((s) => c.derived[s]).join("/")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {kopya.length > 0 ? (
        <div>
          <div className="mb-1.5 text-muted-foreground">Aynı sonuç dizisi tekrar eden haftalar</div>
          <ul className="space-y-2">
            {kopya.map((d) => (
              <li key={d.results} className="flex flex-wrap items-center gap-2">
                <span className="tnum">{d.weeks.join(" · ")}. hafta</span>
                <ResultStrip results={d.results} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {dq.match_conflicts?.length ? (
        <div className="text-muted-foreground">
          Maç listesi sonuç dizisiyle örtüşmeyen hafta: {dq.match_conflicts.join(", ")}
        </div>
      ) : null}

      {dq.weeks_without_matches?.length ? (
        <div className="text-muted-foreground">
          Maç listesi taşımayan hafta: {dq.weeks_without_matches.join(", ")}
        </div>
      ) : null}

      {eksik.length > 0 ? (
        <div className="text-muted-foreground">
          Eksik hafta (15 maçtan az): {eksik.join(", ")}
        </div>
      ) : null}
    </div>
  );
}
