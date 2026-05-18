"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Customer } from "@/lib/types";

const TABS = [
  { href: "", label: "Özet" },
  { href: "/orders", label: "Siparişler" },
  { href: "/products", label: "Ürün Kârlılığı" },
  { href: "/price-simulator", label: "Fiyat Simülatörü" },
  { href: "/simulations", label: "Kampanya Simülatörü" },
  { href: "/cogs", label: "COGS Yükle" },
  { href: "/connections", label: "Bağlantılar" },
];

export default function CustomerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const customerId = Number(params.id);
  const [customer, setCustomer] = useState<Customer | null>(null);

  useEffect(() => {
    if (!Number.isFinite(customerId)) return;
    api.getCustomer(customerId).then(setCustomer).catch(() => setCustomer(null));
  }, [customerId]);

  return (
    <div>
      <div className="mb-6 flex items-baseline justify-between border-b border-slate-200 pb-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Müşteri
          </div>
          <h1 className="text-xl font-semibold tracking-tight">
            {customer?.name ?? "—"}
          </h1>
          <div className="text-sm text-slate-500">{customer?.email}</div>
        </div>
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-900">
          ← Müşteriler
        </Link>
      </div>

      <nav className="mb-6 flex flex-wrap gap-1 border-b border-slate-200">
        {TABS.map((tab) => {
          const href = `/customers/${customerId}${tab.href}`;
          const active = pathname === href;
          return (
            <Link
              key={tab.href}
              href={href}
              className={`-mb-px border-b-2 px-3 py-2 text-sm transition ${
                active
                  ? "border-emerald-500 text-emerald-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}
