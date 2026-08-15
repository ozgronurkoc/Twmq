"use client";

import { useMemo, useState } from "react";
import { solve } from "@/lib/api";

const DEFAULT: string[][] = [
  ["1"], ["1", "0"], ["1"], ["1", "2"], ["0"],
  ["1", "0"], ["2"], ["1", "0"], ["1"], ["1", "2"],
  ["0", "2"], ["1"], ["1", "0"], ["2"], ["1", "0"],
];

type Row = { cells: string[]; cost: number };

const MODES = [
  { id: "fix16", label: "Fix-16" },
  { id: "auto", label: "Otomatik" },
  { id: "heuristic", label: "Sezgisel" },
  { id: "butce", label: "Bütçe" },
  { id: "maxcov", label: "Max kapsama" },
] as const;

export default function FormulaPage() {
  const [matches, setMatches] = useState(DEFAULT);
  const [mode, setMode] = useState("fix16");
  const [budget, setBudget] = useState(32);
  const [variant, setVariant] = useState(0);
  const [useBayes, setUseBayes] = useState(false);
  const [prior, setPrior] = useState(1);
  const [evidence, setEvidence] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [log, setLog] = useState("");
  const [copied, setCopied] = useState(false);
  const [logCopied, setLogCopied] = useState(false);

  const needsBudget = mode === "butce" || mode === "maxcov";

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

  async function onSolve() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body: Parameters<typeof solve>[0] = {
        matches,
        mode,
        variant,
        use_bayes: useBayes,
        prior_strength: prior,
        evidence_strength: evidence,
      };
      if (needsBudget) body.budget = budget;
      const data = await solve(body);
      if (!data.ok) {
        setError(data.error || "Hata");
        setResult(null);
      } else {
        setResult(data.result || null);
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
    const header = `#\t${Array.from({ length: 15 }, (_, i) => `M${i + 1}`).join("\t")}\tFiyat`;
    const lines = rows.map((r, i) => `${i + 1}\t${r.cells.join("\t")}\t${r.cost}`);
    navigator.clipboard.writeText([header, ...lines].join("\n")).then(() => {
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
  const advanced = result?.advanced as Record<string, any> | undefined;
  const bayes = result?.bayes as Record<string, any> | undefined;
  const markov = result?.markov as Record<string, any> | undefined;
  const dist = (result?.dist as any[]) || [];

  return (
    <div className="max-w-5xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Formül Üret</h1>
          <p className="text-sm text-muted mt-1">Next.js UI · Python API · tüm motorlar</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs text-muted">Mod</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="h-9 rounded-xl border border-line bg-white px-3 text-sm"
          >
            {MODES.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
          {needsBudget && (
            <>
              <label className="text-xs text-muted">Bütçe</label>
              <input
                type="number"
                min={1}
                max={9999}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value) || 1)}
                className="h-9 w-20 rounded-xl border border-line px-2 text-sm"
              />
            </>
          )}
          {mode === "fix16" && (
            <>
              <label className="text-xs text-muted">Varyant</label>
              <input
                type="number"
                min={0}
                value={variant}
                onChange={(e) => setVariant(Number(e.target.value) || 0)}
                className="h-9 w-16 rounded-xl border border-line px-2 text-sm"
              />
            </>
          )}
        </div>
      </header>

      <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h2 className="text-sm font-semibold">Maç seçimleri</h2>
          <div className="flex flex-wrap gap-1.5">
            <button type="button" onClick={() => fillAll(["1", "0", "2"])} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Tüm üçlü</button>
            <button type="button" onClick={() => fillAll(["1", "0"])} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Tüm 1/0</button>
            <button type="button" onClick={() => fillAll(["0", "2"])} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Tüm 0/2</button>
            <button type="button" onClick={() => setMatches(DEFAULT.map((r) => [...r]))} className="text-xs px-2.5 py-1 rounded-full border border-line hover:bg-soft">Örnek</button>
          </div>
        </div>

        <div className="space-y-1.5">
          {matches.map((row, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="w-10 text-xs text-muted font-medium">M{i + 1}</span>
              {(["1", "0", "2"] as const).map((sym) => {
                const on = row.includes(sym);
                const color =
                  sym === "1" ? "bg-blue-500 border-blue-500"
                  : sym === "0" ? "bg-amber-500 border-amber-500"
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

        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm border-t border-line pt-4">
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={useBayes} onChange={(e) => setUseBayes(e.target.checked)} className="rounded" />
            <span>Bayes (Dirichlet)</span>
          </label>
          {useBayes && (
            <>
              <label className="text-xs text-muted">α
                <input type="number" step={0.5} min={0.1} value={prior} onChange={(e) => setPrior(Number(e.target.value) || 1)}
                  className="ml-1 h-8 w-16 rounded-lg border border-line px-2 text-sm" />
              </label>
              <label className="text-xs text-muted">n
                <input type="number" min={0} value={evidence} onChange={(e) => setEvidence(Number(e.target.value) || 0)}
                  className="ml-1 h-8 w-16 rounded-lg border border-line px-2 text-sm" />
              </label>
              <span className="text-[11px] text-muted">Not: Bayes için probs gerekir; şimdilik sadece bayes bayrağı gönderilir (uniform seçim kümesi).</span>
            </>
          )}
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

      {result && (
        <section className="rounded-2xl border border-line bg-white p-5 shadow-sm space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">{(result.baslik as string) || "Sonuç"}</h2>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
              guaranteed
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : "bg-red-50 text-red-600 border border-red-200"
            }`}>
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

          {Array.isArray(result.notlar) && (result.notlar as string[]).length > 0 && (
            <ul className="text-xs text-muted space-y-1">
              {(result.notlar as string[]).map((n, i) => <li key={i}>• {n}</li>)}
            </ul>
          )}

          {rows.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold">Kupona yazılacak {rows.length} satır</h3>
                <button type="button" onClick={copyTable}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                    copied ? "bg-emerald-50 border-emerald-300 text-emerald-700" : "border-line hover:bg-soft"
                  }`}>{copied ? "Kopyalandı" : "Tabloyu kopyala"}</button>
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
                          <td key={ci} className={`py-1.5 px-1 text-center font-semibold ${
                            c === "1" ? "text-blue-600" : c === "0" ? "text-amber-600" : "text-red-500"
                          }`}>{c}</td>
                        ))}
                        <td className="py-1.5 px-2 text-center">
                          <span className="font-semibold">{r.cost}</span>
                          {r.cost > 1 && <span className="ml-1 text-[10px] bg-amber-50 text-amber-700 px-1 rounded">×{r.cost}</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {dist.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Kapsama dağılımı</h3>
              <div className="space-y-1.5">
                {dist.map((d) => (
                  <div key={d.d} className="grid grid-cols-[60px_80px_1fr_48px] items-center gap-2 text-xs">
                    <span className="font-semibold">d={d.d}</span>
                    <span className="text-muted">{d.label}</span>
                    <div className="h-1.5 bg-soft rounded overflow-hidden">
                      <div className="h-full bg-brand rounded" style={{ width: `${Math.min(100, Number(d.pct) || 0)}%` }} />
                    </div>
                    <span className="text-right text-muted">%{d.pct}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {advanced && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Gelişmiş olasılık ({String(advanced.source || "")})</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center text-sm">
                {advanced.exact && Object.entries(advanced.exact).map(([k, v]) => (
                  <div key={k} className="rounded-xl bg-soft p-3">
                    <div className="font-semibold">{String(v)}</div>
                    <div className="text-[11px] text-muted">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {bayes && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Bayes posterior</h3>
              <p className="text-xs text-muted mb-2">α={bayes.prior_strength} · n={bayes.evidence_strength}</p>
              <div className="overflow-x-auto rounded-xl border border-line text-xs">
                <table className="w-full">
                  <thead><tr className="bg-soft text-muted text-left">
                    <th className="p-2">Maç</th><th className="p-2">Posterior 1/0/2</th><th className="p-2">KL</th><th className="p-2">Yorum</th>
                  </tr></thead>
                  <tbody>
                    {(bayes.matches || []).map((m: any) => (
                      <tr key={m.mac} className="border-t border-line">
                        <td className="p-2">M{m.mac}</td>
                        <td className="p-2">{m.posterior?.["1"]}/{m.posterior?.["0"]}/{m.posterior?.["2"]}</td>
                        <td className="p-2">{Number(m.kl).toFixed(4)}</td>
                        <td className="p-2">{m.kl_label || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {markov?.summary && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Markov özeti</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-center text-sm">
                {["p_kume_ici", "p_garanti_path", "p0", "p1", "p2plus"].map((k) => (
                  <div key={k} className="rounded-xl bg-soft p-3">
                    <div className="font-semibold">
                      {markov.summary[k] != null ? `%${(100 * Number(markov.summary[k])).toFixed(2)}` : "—"}
                    </div>
                    <div className="text-[11px] text-muted">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className={`text-sm rounded-xl px-3 py-2 border ${
            guaranteed
              ? "text-emerald-700 bg-emerald-50 border-emerald-100"
              : "text-amber-800 bg-amber-50 border-amber-100"
          }`}>
            {guaranteed
              ? "En kötü mesafe ≤ 1 — 14-Garanti doğrulandı."
              : `En kötü mesafe ${String(result.worst)} — 14-garanti yok.`}
          </p>
        </section>
      )}

      {log && (
        <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold">Çalışma logu</h2>
            <button type="button" onClick={copyLog}
              className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                logCopied ? "bg-emerald-50 border-emerald-300 text-emerald-700" : "border-line hover:bg-soft"
              }`}>{logCopied ? "Kopyalandı" : "Logu kopyala"}</button>
          </div>
          <pre className="text-xs bg-soft rounded-xl p-3 overflow-auto max-h-56 whitespace-pre-wrap font-mono leading-relaxed">{log}</pre>
        </section>
      )}
    </div>
  );
}
