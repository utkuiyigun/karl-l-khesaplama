"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { formatTL, profitColor } from "@/lib/format";
import type { ProductProfitabilityRow } from "@/lib/types";

export default function ProductsPage() {
  const params = useParams();
  const customerId = Number(params.id);
  const [rows, setRows] = useState<ProductProfitabilityRow[]>([]);

  useEffect(() => {
    if (!Number.isFinite(customerId)) return;
    api.productProfitability(customerId).then(setRows);
  }, [customerId]);

  return (
    <div>
      <h2 className="text-lg font-semibold">Ürün Bazlı Kârlılık</h2>
      <p className="mt-1 text-sm text-slate-500">
        Net kâra göre azalan sıra. Item-level hesap (paket bedeli ve kargo dahil değil).
      </p>

      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-2">Barkod</th>
              <th className="px-4 py-2 text-right">Satılan</th>
              <th className="px-4 py-2 text-right">İade</th>
              <th className="px-4 py-2 text-right">Brüt Gelir</th>
              <th className="px-4 py-2 text-right">Komisyon</th>
              <th className="px-4 py-2 text-right">COGS</th>
              <th className="px-4 py-2 text-right">Net Kâr</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => (
              <tr key={r.barcode} className="hover:bg-slate-50">
                <td className="px-4 py-2 font-mono text-xs">{r.barcode}</td>
                <td className="px-4 py-2 text-right">{r.units_sold}</td>
                <td className="px-4 py-2 text-right text-slate-500">
                  {r.units_returned}
                </td>
                <td className="px-4 py-2 text-right">
                  {formatTL(r.gross_revenue)}
                </td>
                <td className="px-4 py-2 text-right text-slate-500">
                  −{formatTL(r.commission)}
                </td>
                <td className="px-4 py-2 text-right text-slate-500">
                  −{formatTL(r.total_cogs)}
                </td>
                <td
                  className={`px-4 py-2 text-right font-semibold ${profitColor(r.item_net_profit)}`}
                >
                  {formatTL(r.item_net_profit)}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  Ürün verisi yok. Önce sipariş çek + COGS yükle.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
