"use client";

import { useEffect, useState } from "react";
import { getStats } from "@/lib/api";
import Link from "next/link";

export default function StatsPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getStats().then(setData).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);
  if (err) return <p className="text-red-600 text-sm bg-red-50 rounded-xl p-4">{err}</p>;
  if (!data) return <p className="text-muted text-sm">Yükleniyor…</p>;
  const t = data.totals || {};
  const avg = data.weekly_avg || {};
  const meta = data.meta || {};
  return (
    <div className="max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Tarihsel 1 / 0 / 2</h1>
        <p className="text-sm text-muted mt-1">{String(meta.season ?? "")} · {String(meta.weeks ?? "")} hafta · {String(meta.matches ?? "")} maç</p>
      </header>
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {["1", "0", "2"].map((k) => (
          <div key={k} className="rounded-2xl border border-line bg-white p-4 text-center shadow-sm">
            <div className="text-[11px] text-muted">{k}</div>
            <div className="text-xl font-semibold mt-1">{String(t[k] ?? "—")}</div>
          </div>
        ))}
        <div className="rounded-2xl border border-line bg-white p-4 text-center shadow-sm">
          <div className="text-[11px] text-muted">Haftalık ort.</div>
          <div className="text-lg font-semibold mt-1">{Number(avg["1"]||0).toFixed(1)} / {Number(avg["0"]||0).toFixed(1)} / {Number(avg["2"]||0).toFixed(1)}</div>
        </div>
      </section>
      <section className="rounded-2xl border border-line bg-white p-5 shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-muted text-xs"><th className="py-2">Hf</th><th>1</th><th>0</th><th>2</th><th>Kod</th></tr></thead>
          <tbody>
            {(data.weeks || []).map((w: any) => (
              <tr key={String(w.week)} className="border-t border-line">
                <td className="py-2"><Link className="text-brand" href={`/stats/${w.week}`}>{String(w.week)}</Link></td>
                <td>{String(w.n1)}</td><td>{String(w.n0)}</td><td>{String(w.n2)}</td>
                <td className="font-mono text-xs">{String(w.results)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
