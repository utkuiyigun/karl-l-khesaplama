"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { formatDate, formatTL, profitColor } from "@/lib/format";
import type { OrderSummary } from "@/lib/types";

export default function OrdersListPage() {
  const params = useParams();
  const customerId = Number(params.id);
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  useEffect(() => {
    if (!Number.isFinite(customerId)) return;
    api.listOrders(customerId, limit, offset).then((page) => {
      setOrders(page.items);
      setTotal(page.total);
    });
  }, [customerId, offset]);

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">Siparişler ({total})</h2>
        <div className="text-xs text-slate-500">
          {offset + 1}–{Math.min(offset + limit, total)} / {total}
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-2">Sipariş No</th>
              <th className="px-4 py-2">Tarih</th>
              <th className="px-4 py-2 text-right">Brüt Gelir</th>
              <th className="px-4 py-2 text-right">Komisyon</th>
              <th className="px-4 py-2 text-right">COGS</th>
              <th className="px-4 py-2 text-right">Net Kâr</th>
              <th className="px-4 py-2 text-center">Durum</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {orders.map((o) => (
              <tr key={o.id} className="hover:bg-slate-50">
                <td className="px-4 py-2">
                  <Link
                    href={`/customers/${customerId}/orders/${o.id}`}
                    className="font-medium text-emerald-700 hover:underline"
                  >
                    {o.external_id}
                  </Link>
                </td>
                <td className="px-4 py-2 text-slate-600">
                  {formatDate(o.order_date)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {formatTL(o.profit.gross_revenue)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums text-slate-500">
                  −{formatTL(o.profit.commission)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums text-slate-500">
                  −{formatTL(o.profit.total_cogs)}
                </td>
                <td
                  className={`px-4 py-2 text-right font-semibold tabular-nums ${profitColor(o.profit.net_profit)}`}
                >
                  {formatTL(o.profit.net_profit)}
                </td>
                <td className="px-4 py-2 text-center">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      o.profit.is_realized
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {o.profit.is_realized ? "Tahsil" : "Beklemede"}
                  </span>
                </td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  Sipariş bulunamadı.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {total > limit && (
        <div className="flex justify-center gap-2">
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-50"
          >
            ← Önceki
          </button>
          <button
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
            className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-50"
          >
            Sonraki →
          </button>
        </div>
      )}
    </div>
  );
}
