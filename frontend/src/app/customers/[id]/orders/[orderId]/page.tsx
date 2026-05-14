"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { formatDate, formatTL, profitColor } from "@/lib/format";
import type { OrderDetail } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  delivered: "bg-emerald-100 text-emerald-800",
  shipped: "bg-blue-100 text-blue-800",
  pending: "bg-amber-100 text-amber-800",
  cancelled: "bg-slate-200 text-slate-700",
  returned: "bg-rose-100 text-rose-800",
};

export default function OrderDetailPage() {
  const params = useParams();
  const customerId = Number(params.id);
  const orderId = Number(params.orderId);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(orderId)) return;
    api
      .getOrder(customerId, orderId)
      .then(setOrder)
      .catch((err) => setError(err.detail || String(err)));
  }, [customerId, orderId]);

  if (error)
    return (
      <div className="rounded border border-rose-200 bg-rose-50 p-4 text-rose-700">
        {error}
      </div>
    );
  if (!order) return <p className="text-slate-500">Yükleniyor…</p>;

  const p = order.profit;
  const items = [
    { label: "Brüt Gelir", value: p.gross_revenue, negative: false },
    { label: "Komisyon", value: p.commission, negative: true },
    { label: "Satış KDV", value: p.sale_vat, negative: true },
    { label: "Hizmet Bedeli (paket)", value: p.service_fee, negative: true },
    { label: "Kargo", value: p.shipping_cost, negative: true },
    { label: "COGS", value: p.total_cogs, negative: true },
    { label: "Stopaj", value: p.stopaj, negative: true },
  ];

  return (
    <div className="space-y-8">
      <Link
        href={`/customers/${customerId}/orders`}
        className="text-sm text-slate-500 hover:text-slate-900"
      >
        ← Siparişler
      </Link>

      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Sipariş
          </div>
          <h1 className="text-2xl font-semibold">{order.external_id}</h1>
          <div className="text-sm text-slate-500">
            {formatDate(order.order_date)}
          </div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-5 py-3 text-right">
          <div className="text-xs uppercase tracking-wider text-emerald-700">
            Net Kâr
          </div>
          <div className={`text-2xl font-bold ${profitColor(p.net_profit)}`}>
            {formatTL(p.net_profit)}
          </div>
          <div className="text-xs text-slate-500">
            {p.is_realized ? "Tahsil edildi" : "Beklemede"}
          </div>
        </div>
      </div>

      <section>
        <h2 className="mb-3 font-semibold">Kâr Dökümü</h2>
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {items.map((item) => (
            <li
              key={item.label}
              className="flex items-center justify-between px-4 py-3 text-sm"
            >
              <span className="text-slate-700">{item.label}</span>
              <span
                className={`font-mono ${
                  item.negative ? "text-rose-600" : "text-slate-900"
                }`}
              >
                {item.negative ? "−" : "+"}
                {formatTL(item.value)}
              </span>
            </li>
          ))}
          <li className="flex items-center justify-between bg-slate-50 px-4 py-3 text-sm font-semibold">
            <span>Net Kâr</span>
            <span className={`font-mono text-base ${profitColor(p.net_profit)}`}>
              {formatTL(p.net_profit)}
            </span>
          </li>
        </ul>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">Paketler ({order.packages.length})</h2>
        <div className="space-y-4">
          {order.packages.map((pkg) => (
            <div
              key={pkg.id}
              className="rounded-lg border border-slate-200 bg-white"
            >
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div>
                  <div className="font-medium">Paket #{pkg.external_id}</div>
                  <div className="text-xs text-slate-500">
                    Hizmet bedeli {formatTL(pkg.package_service_fee)} · Kargo{" "}
                    {formatTL(pkg.shipping_cost)}
                  </div>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs ${
                    STATUS_COLORS[pkg.status] || "bg-slate-100 text-slate-700"
                  }`}
                >
                  {pkg.status}
                </span>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-2">Barkod</th>
                    <th className="px-4 py-2 text-right">Adet</th>
                    <th className="px-4 py-2 text-right">İade</th>
                    <th className="px-4 py-2 text-right">Birim Fiyat</th>
                    <th className="px-4 py-2 text-right">Komisyon</th>
                    <th className="px-4 py-2 text-right">COGS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {pkg.items.map((it) => (
                    <tr key={it.id}>
                      <td className="px-4 py-2 font-mono text-xs">{it.barcode}</td>
                      <td className="px-4 py-2 text-right">{it.quantity}</td>
                      <td className="px-4 py-2 text-right text-slate-500">
                        {it.return_quantity}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatTL(it.unit_sale_price)}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-500">
                        %{(parseFloat(it.commission_rate) * 100).toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-500">
                        {formatTL(it.cogs_snapshot)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
