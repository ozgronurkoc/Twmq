"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

export default function HealthPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getHealth().then(setData).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);
  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Sistem sağlığı</h1>
      {err && <p className="text-sm text-red-600 bg-red-50 rounded-xl p-3">{err}</p>}
      <pre className="text-xs bg-white border border-line rounded-2xl p-4 overflow-auto">
        {data ? JSON.stringify(data, null, 2) : "Yükleniyor…"}
      </pre>
    </div>
  );
}
