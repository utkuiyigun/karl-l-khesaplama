"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { formatTL, profitColor } from "@/lib/format";
import type { PriceSimulatorResponse } from "@/lib/types";

const PRESETS = [
  { label: "Komisyon %12 + KDV %20 (otomotiv)", commission: "0.12", vat: "0.20" },
  { label: "Komisyon %20 + KDV %20 (giyim)", commission: "0.20", vat: "0.20" },
  { label: "Komisyon %15 + KDV %10 (gıda)", commission: "0.15", vat: "0.10" },
];

export default function PriceSimulatorPage() {
  const params = useParams();
  const customerId = Number(params.id);

  const [salePrice, setSalePrice] = useState("100");
  const [vatRate, setVatRate] = useState("0.20");
  const [commissionRate, setCommissionRate] = useState("0.18");
  const [cogs, setCogs] = useState("0");
  const [quantity, setQuantity] = useState("1");
  const [campaignDiscount, setCampaignDiscount] = useState("0");
  const [serviceFee, setServiceFee] = useState("13.19");
  const [shippingCost, setShippingCost] = useState("0");

  const [result, setResult] = useState<PriceSimulatorResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const r = await api.simulatePrice(customerId, {
        sale_price: salePrice,
        vat_rate: vatRate,
        commission_rate: commissionRate,
        cogs,
        quantity: parseInt(quantity, 10) || 1,
        campaign_discount: campaignDiscount,
        package_service_fee: serviceFee,
        shipping_cost: shippingCost,
      });
      setResult(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : String(err));
      setResult(null);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Fiyat Simülatörü</h2>
          <p className="mt-1 text-sm text-slate-500">
            Bir ürünü şu fiyata satarsam ne kadar kâr ederim? Tüm kesintilerle
            (komisyon, KDV, hizmet bedeli, kargo, COGS, stopaj) hesaplar.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => {
                setCommissionRate(p.commission);
                setVatRate(p.vat);
              }}
              className="rounded border border-slate-300 bg-white px-3 py-1 text-xs text-slate-600 hover:border-emerald-400"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Satış fiyatı (KDV dahil, TL)"
            value={salePrice}
            onChange={(e) => setSalePrice(e.target.value)}
            step="0.01"
            min="0"
            full
          />
          <Field
            label="Adet"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            step="1"
            min="1"
          />
          <Field
            label="Komisyon oranı (0.12 = %12)"
            value={commissionRate}
            onChange={(e) => setCommissionRate(e.target.value)}
            step="0.001"
            min="0"
            max="1"
          />
          <Field
            label="KDV oranı"
            value={vatRate}
            onChange={(e) => setVatRate(e.target.value)}
            step="0.01"
            min="0"
            max="1"
          />
          <Field
            label="Birim COGS (TL)"
            value={cogs}
            onChange={(e) => setCogs(e.target.value)}
            step="0.01"
            min="0"
          />
          <Field
            label="Kampanya indirimi (TL)"
            value={campaignDiscount}
            onChange={(e) => setCampaignDiscount(e.target.value)}
            step="0.01"
            min="0"
          />
          <Field
            label="Hizmet bedeli (paket)"
            value={serviceFee}
            onChange={(e) => setServiceFee(e.target.value)}
            step="0.01"
            min="0"
          />
          <Field
            label="Kargo (TL)"
            value={shippingCost}
            onChange={(e) => setShippingCost(e.target.value)}
            step="0.01"
            min="0"
          />
        </div>

        <button
          onClick={run}
          disabled={running}
          className="w-full rounded-md bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {running ? "Hesaplanıyor…" : "Hesapla"}
        </button>

        {error && (
          <div className="rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        )}
      </div>

      {result && (
        <div className="space-y-4">
          <ResultTable r={result} />
          <Summary r={result} />
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  full,
  ...rest
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; full?: boolean }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <label className="mb-1 block text-xs font-medium text-slate-600">
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

function ResultTable({ r }: { r: PriceSimulatorResponse }) {
  const rows = [
    { label: "Brüt Gelir (etiket × adet)", value: r.gross_revenue, kind: "positive" },
    { label: "Kampanya İndirimi", value: r.campaign_discount, kind: "negative" },
    { label: "Net Satış (brüt − kampanya)", value: r.net_sale, kind: "subtotal" },
    { label: "Trendyol Komisyonu", value: r.commission, kind: "negative" },
    { label: "Platform Hizmet Bedeli", value: r.service_fee, kind: "negative" },
    { label: "Kargo", value: r.shipping_cost, kind: "negative" },
    { label: "Satış KDV'si", value: r.sale_vat, kind: "negative" },
    { label: "COGS (Ürün Maliyeti)", value: r.total_cogs, kind: "negative" },
    { label: "Stopaj", value: r.stopaj, kind: "negative" },
  ];

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h3 className="font-semibold">Kesinti Dökümü</h3>
      </div>
      <ul className="divide-y divide-slate-100 text-sm">
        {rows.map((row) => (
          <li
            key={row.label}
            className={`flex items-center justify-between px-4 py-2.5 ${
              row.kind === "subtotal" ? "bg-slate-50 font-medium" : ""
            }`}
          >
            <span className="text-slate-700">{row.label}</span>
            <span
              className={`font-mono ${
                row.kind === "negative"
                  ? "text-rose-600"
                  : row.kind === "subtotal"
                    ? "text-slate-900"
                    : "text-slate-900"
              }`}
            >
              {row.kind === "negative" && parseFloat(row.value) > 0 ? "−" : ""}
              {formatTL(row.value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Summary({ r }: { r: PriceSimulatorResponse }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="text-xs uppercase tracking-wider text-slate-500">
          Trendyol'dan Tahsilat
        </div>
        <div className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
          {formatTL(r.seller_payout)}
        </div>
        <div className="mt-1 text-xs text-slate-500">
          KDV dahil, satıcı hesabına yatan
        </div>
      </div>
      <div
        className={`rounded-lg border-2 p-4 ${
          parseFloat(r.net_profit) >= 0
            ? "border-emerald-300 bg-emerald-50"
            : "border-rose-300 bg-rose-50"
        }`}
      >
        <div className="text-xs uppercase tracking-wider text-slate-700">
          Net Kâr
        </div>
        <div
          className={`mt-1 text-2xl font-bold tabular-nums ${profitColor(r.net_profit)}`}
        >
          {formatTL(r.net_profit)}
        </div>
        <div className="mt-1 text-xs text-slate-600">
          Vergi + COGS dahil
        </div>
      </div>
    </div>
  );
}
