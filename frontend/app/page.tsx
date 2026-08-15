"use client";

import { useMemo, useState } from "react";
import { solve } from "@/lib/api";

const DEFAULT: string[][] = [
  ["1"], ["1", "0"], ["1"], ["1", "2"], ["0"],
  ["1", "0"], ["2"], ["1", "0"], ["1"], ["1", "2"],
  ["0", "2"], ["1"], ["1", "0"], ["2"], ["1", "0"],
];

type Row = { cells: string[]; cost: number };

export default function FormulaPage() {
  const [matches, setMatches] = useState(DEFAULT);
  const [mode, setMode] = useState("fix16");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [log, setLog] = useState("");
  const [copied, setCopied] = useState(false);
  const [logCopied, setLogCopied] = useState(false);

  const live = useMemo(() => {
    let banko = 0, cifte = 0, uclu = 0, space = 1;
    for (const row of matches) {
      const n = row.length || 3;
      if (n === 1) banko++;
      else if (n === 2) cifte++;
      else uclu++;
      space *= n;
    }
    let bedel = space;
    if (mode === "fix16" && cifte >= 7) bedel = Math.round(space / 8);
    return { banko, cifte, uclu, space, bedel };
  }, [matches, mode]);

  function toggle(i: number, sym: string) {
    setMatches((prev) => {
      const next = prev.map((row) => [...row]);
      const row = next[i];
      if (row.includes(sym)) {
        if (row.length === 1) return prev;
        next[i] = row.filter((s) => s !== sym);
      } else {
        const order: Record<string, number> = { "1": 0, "0": 1, "2": 2 };
        next[i] = [...row, sym].sort((a, b) => order[a] - order[b]);
      }
      return next;
    });
  }

  function fillAll(syms: string[]) {
    setMatches(Array.from({ length: 15 }, () => [...syms]));
  }

  function loadExample() {
    setMatches(DEFAULT.map((r) => [...r]));
  }

  async function onSolve() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await solve({ matches, mode, variant: 0 });
      if (!data.ok) {
        setError(data.error || "Hata");
        setResult(null);
      } else {
        setResult(data.result);
      }
      setLog(data.run_log_text || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setLog("");
    } finally {
      setLoading(false);
    }
  }

  function copyTable() {
    if (!result?.rows) return;
    const rows = result.rows as Row[];
    const lines = rows.map((r, i) =>
      `${i + 1}\t${r.cells.join("\t")}\t${r.cost}`
    );
    const header = `#\t${Array.from({ length: 15 }, (_, i) => `M${i + 1}`).join("\t")}\tFiyat`;
    const text = [header, ...lines].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    });
  }

  function copyLog() {
    if (!log) return;
    navigator.clipboard.writeText(log).then(() => {
      setLogCopied(true);
      setTimeout(() => setLogCopied(false), 1600);
    });
  }

  const rows = (result?.rows as Row[] | undefined) || [];
  const guaranteed = Boolean(result?.guaranteed);

  return (
    <div className="max-w-5xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Formül Üret</h1>
          <p className="text-sm text-muted mt-1">Next.js UI · JSON API · Fix-16 motor</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted">Mod</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="h-9 rounded-xl border border-line bg-white px-3 text-sm"
          >
            <option value="fix16">Fix-16</option>
            <option value="auto">Otomatik</option>
            <option value="heuristic">Sezgisel</option>
          </select>
        </div>
      </header>

      {/* Maç seçimleri */}
      <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h2 className="text-sm font-semibold">Maç seçimleri</h2>
          <div className="flex flex-wrap gap-1.5">
            <button type="button" onClick={() => fillAll(["1", "0", "2"])} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Tüm üçlü</button>
            <button type="button" onClick={() => fillAll(["1", "0"])} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Tüm 1/0</button>
            <button type="button" onClick={() => fillAll(["0", "2"])} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Tüm 0/2</button>
            <button type="button" onClick={loadExample} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Örnek</button>
          </div>
        </div>

        <div className="space-y-1.5">
          {matches.map((row, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="w-10 text-xs text-muted font-medium">M{i + 1}</span>
              {(["1", "0", "2"] as const).map((sym) => {
                const on = row.includes(sym);
                const color =
                  sym === "1"
                    ? "bg-blue-500 border-blue-500"
                    : sym === "0"
                    ? "bg-amber-500 border-amber-500"
                    : "bg-red-500 border-red-500";
                return (
                  <button
                    key={sym}
                    type="button"
                    onClick={() => toggle(i, sym)}
                    className={`h-9 w-11 rounded-lg border text-sm font-semibold transition active:scale-95 ${
                      on ? color + " text-white" : "border-line bg-white text-muted"
                    }`}
                  >
                    {sym}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Canlı istatistik */}
        <div className="mt-5 grid grid-cols-5 gap-2 border-t border-line pt-4">
          {[
            { label: "Banko", value: live.banko },
            { label: "Çifte", value: live.cifte },
            { label: "Üçlü", value: live.uclu },
            { label: "Uzay", value: live.space >= 1000 ? `${(live.space / 1000).toFixed(1)}k` : live.space },
            { label: "Tahmini bedel", value: live.bedel >= 1000 ? `${(live.bedel / 1000).toFixed(1)}k` : live.bedel, accent: true },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className={`text-lg font-semibold ${s.accent ? "text-brand" : ""}`}>{s.value}</div>
              <div className="text-[11px] text-muted">{s.label}</div>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={onSolve}
          disabled={loading}
          className="mt-5 h-11 w-full sm:w-auto rounded-xl bg-brand px-8 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-60 transition"
        >
          {loading ? "Hesaplanıyor…" : "Formül Üret"}
        </button>

        {error && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2 border border-red-100">{error}</p>
        )}
      </section>

      {/* Sonuç özeti */}
      {result && (
        <section className="rounded-2xl border border-line bg-white p-5 shadow-sm space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">{(result.baslik as string) || "Sonuç"}</h2>
            <span
              className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                guaranteed
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "bg-red-50 text-red-600 border border-red-200"
              }`}
            >
              {guaranteed ? "14-Garanti ✓" : "Garanti yok"}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
            <div className="rounded-xl bg-soft p-3">
              <div className="text-xl font-semibold">{String(result.satir_sayisi ?? "—")}</div>
              <div className="text-[11px] text-muted mt-0.5">Kupon satırı</div>
            </div>
            <div className="rounded-xl bg-soft p-3">
              <div className="text-xl font-semibold text-brand">{String(result.kolon_bedeli ?? "—")}</div>
              <div className="text-[11px] text-muted mt-0.5">Toplam bedel</div>
            </div>
            <div className="rounded-xl bg-soft p-3">
              <div className="text-xl font-semibold">{String(result.alt_sinir ?? "—")}</div>
              <div className="text-[11px] text-muted mt-0.5">Alt sınır</div>
            </div>
            <div className="rounded-xl bg-soft p-3">
              <div className={`text-xl font-semibold ${guaranteed ? "text-emerald-600" : "text-red-500"}`}>
                {String(result.worst ?? "—")}
              </div>
              <div className="text-[11px] text-muted mt-0.5">En kötü mesafe</div>
            </div>
          </div>

          {/* Satır tablosu */}
          {rows.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold">Kupona yazılacak {rows.length} satır</h3>
                <button
                  type="button"
                  onClick={copyTable}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                    copied
                      ? "bg-emerald-50 border-emerald-300 text-emerald-700"
                      : "border-line hover:bg-soft"
                  }`}
                >
                  {copied ? "Kopyalandı" : "Tabloyu kopyala"}
                </button>
              </div>
              <div className="overflow-x-auto rounded-xl border border-line">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-soft text-left text-[11px] text-muted">
                      <th className="py-2 px-2 font-semibold">#</th>
                      {Array.from({ length: 15 }, (_, i) => (
                        <th key={i} className="py-2 px-1 text-center font-semibold">M{i + 1}</th>
                      ))}
                      <th className="py-2 px-2 text-center font-semibold">Fiyat</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, idx) => (
                      <tr key={idx} className="border-t border-line hover:bg-soft/60">
                        <td className="py-1.5 px-2 text-muted text-xs">{idx + 1}</td>
                        {r.cells.map((c, ci) => (
                          <td
                            key={ci}
                            className={`py-1.5 px-1 text-center font-semibold ${
                              c === "1" ? "text-blue-600" : c === "0" ? "text-amber-600" : "text-red-500"
                            }`}
                          >
                            {c}
                          </td>
                        ))}
                        <td className="py-1.5 px-2 text-center">
                          <span className="font-semibold">{r.cost}</span>
                          {r.cost > 1 && (
                            <span className="ml-1 text-[10px] bg-amber-50 text-amber-700 px-1 rounded">×{r.cost}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {guaranteed ? (
            <p className="text-sm text-emerald-700 bg-emerald-50 rounded-xl px-3 py-2 border border-emerald-100">
              En kötü mesafe ≤ 1 — <strong>14-Garanti doğrulandı</strong>. Seçim kümesi içinde doğru sonuç varsa en az bir kolon en fazla 1 maç hatalı kalır.
            </p>
          ) : (
            <p className="text-sm text-amber-800 bg-amber-50 rounded-xl px-3 py-2 border border-amber-100">
              En kötü mesafe {String(result.worst)} — <strong>14-garanti yok</strong>. Fix-16 veya bütçeyi yükseltin.
            </p>
          )}
        </section>
      )}

      {/* Çalışma logu */}
      {log && (
        <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold">Çalışma logu</h2>
            <button
              type="button"
              onClick={copyLog}
              className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                logCopied
                  ? "bg-emerald-50 border-emerald-300 text-emerald-700"
                  : "border-line hover:bg-soft"
              }`}
            >
              {logCopied ? "Kopyalandı" : "Logu kopyala"}
            </button>
          </div>
          <pre className="text-xs bg-soft rounded-xl p-3 overflow-auto max-h-56 whitespace-pre-wrap font-mono leading-relaxed">
            {log}
          </pre>
        </section>
      )}
    </div>
  );
}
