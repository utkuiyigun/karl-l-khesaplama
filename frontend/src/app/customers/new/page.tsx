"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";

export default function NewCustomerPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setSubmitting(true);
    setError(null);
    try {
      const customer = await api.createCustomer({
        email: String(form.get("email")),
        name: String(form.get("name")),
        is_vat_registered: form.get("is_vat_registered") === "on",
        stopaj_rate: String(form.get("stopaj_rate") || "0"),
        default_shipping_cost: String(form.get("default_shipping_cost") || "0"),
      });
      router.push(`/customers/${customer.id}/connections`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : String(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold tracking-tight">Yeni Müşteri</h1>
      <p className="mt-1 text-sm text-slate-500">
        Müşteriyi ekledikten sonra Trendyol bağlantısı kuracaksın.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <Field label="E-mail" name="email" type="email" required />
        <Field label="İsim" name="name" required />
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_vat_registered"
            name="is_vat_registered"
            defaultChecked
            className="h-4 w-4"
          />
          <label htmlFor="is_vat_registered" className="text-sm text-slate-700">
            KDV mükellefi
          </label>
        </div>
        <Field
          label="Stopaj oranı (örn: 0.05 = %5)"
          name="stopaj_rate"
          type="number"
          step="0.0001"
          defaultValue="0"
          min="0"
          max="1"
        />
        <Field
          label="Varsayılan kargo maliyeti (TL)"
          name="default_shipping_cost"
          type="number"
          step="0.01"
          defaultValue="0"
          min="0"
        />

        {error && (
          <div className="rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? "Oluşturuluyor…" : "Müşteri Oluştur"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="text-sm text-slate-500 hover:text-slate-900"
          >
            İptal
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  name,
  ...rest
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; name: string }) {
  return (
    <div>
      <label htmlFor={name} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={name}
        name={name}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        {...rest}
      />
    </div>
  );
}
