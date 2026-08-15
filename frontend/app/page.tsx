"use client";

import { useState } from "react";
import { solve } from "@/lib/api";

const DEFAULT: string[][] = [
  ["1"], ["1", "0"], ["1"], ["1", "2"], ["0"],
  ["1", "0"], ["2"], ["1", "0"], ["1"], ["1", "2"],
  ["0", "2"], ["1"], ["1", "0"], ["2"], ["1", "0"],
];

export default function FormulaPage() {
  const [matches, setMatches] = useState(DEFAULT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [log, setLog] = useState("");

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

  async function onSolve() {
    setLoading(true);
    setError(null);
    try {
      const data = await solve({ matches, mode: "fix16", variant: 0 });
      if (!data.ok) {
        setError(data.error || "Hata");
        setResult(null);
      } else setResult(data.result);
      setLog(data.run_log_text || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Formül Üret</h1>
        <p className="text-sm text-muted mt-1">Next.js UI · JSON API · Fix-16 motor</p>
      </header>
      <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold mb-3">Maç seçimleri</h2>
        <div className="space-y-2">
          {matches.map((row, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="w-10 text-xs text-muted">M{i + 1}</span>
              {(["1", "0", "2"] as const).map((sym) => {
                const on = row.includes(sym);
                const color = sym === "1" ? "bg-blue-500 border-blue-500" : sym === "0" ? "bg-amber-500 border-amber-500" : "bg-red-500 border-red-500";
                return (
                  <button key={sym} type="button" onClick={() => toggle(i, sym)}
                    className={`h-9 w-11 rounded-lg border text-sm font-semibold ${on ? color + " text-white" : "border-line bg-white text-muted"}`}>
                    {sym}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
        <button type="button" onClick={onSolve} disabled={loading}
          className="mt-5 h-11 rounded-xl bg-brand px-6 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-60">
          {loading ? "Hesaplanıyor…" : "Formül Üret"}
        </button>
        {error && <p className="mt-3 text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{error}</p>}
      </section>
      {result && (
        <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold mb-2">{(result.baslik as string) || "Sonuç"}</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 text-center">
            <div className="rounded-xl bg-soft p-3"><div className="text-lg font-semibold">{String(result.satir_sayisi ?? "—")}</div><div className="text-[11px] text-muted">Satır</div></div>
            <div className="rounded-xl bg-soft p-3"><div className="text-lg font-semibold">{String(result.kolon_bedeli ?? "—")}</div><div className="text-[11px] text-muted">Bedel</div></div>
            <div className="rounded-xl bg-soft p-3"><div className="text-lg font-semibold">{result.guaranteed ? "Evet" : "Hayır"}</div><div className="text-[11px] text-muted">Garanti</div></div>
            <div className="rounded-xl bg-soft p-3"><div className="text-lg font-semibold">{String(result.worst ?? "—")}</div><div className="text-[11px] text-muted">Worst d</div></div>
          </div>
          <pre className="text-xs bg-soft rounded-xl p-3 overflow-auto max-h-64">{JSON.stringify(result.rows, null, 2)}</pre>
        </section>
      )}
      {log && (
        <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold mb-2">Çalışma logu</h2>
          <pre className="text-xs bg-soft rounded-xl p-3 overflow-auto max-h-48 whitespace-pre-wrap">{log}</pre>
        </section>
      )}
    </div>
  );
}
