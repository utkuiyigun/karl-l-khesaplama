"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Customer } from "@/lib/types";

export default function HomePage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCustomers()
      .then((res) => setCustomers(res.items))
      .catch((err: ApiError) => setError(err.detail))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Müşteriler</h1>
          <p className="text-sm text-slate-500">
            Bir müşteriyi seç veya yeni müşteri ekle.
          </p>
        </div>
        <Link
          href="/customers/new"
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          + Yeni Müşteri
        </Link>
      </div>

      {loading && <p className="text-slate-500">Yükleniyor…</p>}
      {error && (
        <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          API'ye ulaşılamadı: {error}
          <div className="mt-2 text-xs text-rose-600">
            Backend çalışıyor mu? <code>cd backend && .venv/bin/uvicorn app.main:app --reload</code>
          </div>
        </div>
      )}
      {!loading && !error && customers.length === 0 && (
        <div className="rounded border border-dashed border-slate-300 p-12 text-center text-slate-500">
          Henüz müşteri yok. Yukarıdan ilk müşteriyi ekle.
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {customers.map((c) => (
          <Link
            key={c.id}
            href={`/customers/${c.id}`}
            className="rounded-lg border border-slate-200 bg-white p-5 transition hover:border-emerald-400 hover:shadow-sm"
          >
            <div className="font-medium text-slate-900">{c.name}</div>
            <div className="mt-0.5 text-sm text-slate-500">{c.email}</div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
              <span className="rounded bg-slate-100 px-2 py-0.5">
                {c.is_vat_registered ? "KDV mükellefi" : "Mükellef değil"}
              </span>
              {parseFloat(c.stopaj_rate) > 0 && (
                <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-800">
                  Stopaj %{(parseFloat(c.stopaj_rate) * 100).toFixed(2)}
                </span>
              )}
            </div>
            <div className="mt-3 text-xs text-slate-400">
              Oluşturulma: {formatDate(c.created_at)}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
