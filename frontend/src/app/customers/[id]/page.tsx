"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { formatDate, formatTL, profitColor } from "@/lib/format";
import type { OrderSummary, PlatformConnection } from "@/lib/types";

export default function CustomerOverviewPage() {
  const params = useParams();
  const customerId = Number(params.id);
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!Number.isFinite(customerId)) return;
    Promise.all([
      api.listConnections(customerId),
      api.listOrders(customerId, 10),
    ])
      .then(([c, o]) => {
        setConnections(c);
        setOrders(o.items);
      })
      .finally(() => setLoading(false));
  }, [customerId]);

  if (loading) return <p className="text-slate-500">Yükleniyor…</p>;

  const totalNet = orders.reduce(
    (sum, o) => sum + parseFloat(o.profit.net_profit),
    0
  );

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Aktif Bağlantı"
          value={String(connections.filter((c) => c.is_active).length)}
          href={`/customers/${customerId}/connections`}
        />
        <StatCard
          label="Son 10 Siparişin Net Kârı"
          value={formatTL(totalNet)}
          colorClass={profitColor(String(totalNet))}
        />
        <StatCard
          label="Toplam Sipariş"
          value={String(orders.length)}
          href={`/customers/${customerId}/orders`}
        />
      </div>

      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="font-semibold">Son Siparişler</h2>
          <Link
            href={`/customers/${customerId}/orders`}
            className="text-xs text-emerald-700 hover:underline"
          >
            Tümünü gör →
          </Link>
        </div>
        {orders.length === 0 ? (
          <div className="rounded border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
            Henüz sipariş yok. Bağlantı kurulduktan sonra worker 5 dk içinde çeker.
          </div>
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {orders.slice(0, 5).map((o) => (
              <li key={o.id}>
                <Link
                  href={`/customers/${customerId}/orders/${o.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-slate-50"
                >
                  <div>
                    <div className="font-medium">{o.external_id}</div>
                    <div className="text-xs text-slate-500">
                      {formatDate(o.order_date)}
                    </div>
                  </div>
                  <div className={`text-sm font-medium ${profitColor(o.profit.net_profit)}`}>
                    {formatTL(o.profit.net_profit)}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
  href,
  colorClass,
}: {
  label: string;
  value: string;
  href?: string;
  colorClass?: string;
}) {
  const inner = (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${colorClass ?? ""}`}>{value}</div>
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}
