"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { formatTL, profitColor } from "@/lib/format";
import type { SimulationResponse } from "@/lib/types";

export default function SimulationsPage() {
  const params = useParams();
  const customerId = Number(params.id);
  const [discountPct, setDiscountPct] = useState("0.15");
  const [upliftPct, setUpliftPct] = useState("0");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.simulate(customerId, {
        discount_pct: discountPct,
        volume_uplift_pct: upliftPct,
      });
      setResult(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Kampanya Simülatörü</h2>
        <p className="mt-1 text-sm text-slate-500">
          Geçmiş kalemler üzerinde "şu indirimi yapsaydım" hesabı.
        </p>
      </div>

      <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
        <Field
          label="İndirim oranı (örn: 0.15 = %15)"
          value={discountPct}
          onChange={(e) => setDiscountPct(e.target.value)}
          step="0.01"
          min="0"
          max="1"
        />
        <Field
          label="Hacim artışı varsayımı (örn: 0.20 = %20 daha fazla satış)"
          value={upliftPct}
          onChange={(e) => setUpliftPct(e.target.value)}
          step="0.01"
          min="0"
        />
        <button
          onClick={run}
          disabled={running}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {running ? "Hesaplanıyor…" : "Simüle Et"}
        </button>
      </div>

      {error && (
        <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {result && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Şu anki net kâr" value={formatTL(result.base_net_profit)} />
          <Stat
            label="Simüle edilen net kâr"
            value={formatTL(result.simulated_net_profit)}
            colorClass={profitColor(result.simulated_net_profit)}
          />
          <Stat
            label="Fark"
            value={
              (parseFloat(result.delta) >= 0 ? "+" : "") +
              formatTL(result.delta)
            }
            colorClass={profitColor(result.delta)}
            big
          />
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  ...rest
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        type="number"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        {...rest}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  colorClass,
  big,
}: {
  label: string;
  value: string;
  colorClass?: string;
  big?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div
        className={`mt-1 font-semibold tabular-nums ${
          big ? "text-3xl" : "text-xl"
        } ${colorClass ?? ""}`}
      >
        {value}
      </div>
    </div>
  );
}
