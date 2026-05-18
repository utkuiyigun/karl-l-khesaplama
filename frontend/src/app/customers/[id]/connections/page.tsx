"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { PlatformConnection } from "@/lib/types";

export default function ConnectionsPage() {
  const params = useParams();
  const customerId = Number(params.id);
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const list = await api.listConnections(customerId);
    setConnections(list);
  }

  useEffect(() => {
    if (Number.isFinite(customerId)) refresh();
  }, [customerId]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget; // React event pooling — async sonra null olmasın diye baştan al
    const form = new FormData(formEl);
    setSubmitting(true);
    setError(null);
    try {
      await api.createConnection(customerId, {
        platform: "trendyol",
        seller_id: String(form.get("seller_id")),
        api_key: String(form.get("api_key")),
        api_secret: String(form.get("api_secret")),
      });
      formEl.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Bağlantıyı silmek istiyor musun?")) return;
    await api.deleteConnection(customerId, id);
    await refresh();
  }

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div>
        <h2 className="font-semibold">Mevcut Bağlantılar</h2>
        {connections.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Henüz yok.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {connections.map((c) => (
              <li key={c.id} className="flex items-center justify-between p-4">
                <div>
                  <div className="font-medium uppercase">{c.platform}</div>
                  <div className="text-sm text-slate-600">
                    Seller ID: <code>{c.seller_id}</code>
                  </div>
                  <div className="mt-1 flex gap-2 text-xs text-slate-500">
                    <span
                      className={`rounded px-2 py-0.5 ${
                        c.is_active
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {c.is_active ? "Aktif" : "Pasif"}
                    </span>
                    <span>
                      Son sync:{" "}
                      {c.last_sync_at ? formatDate(c.last_sync_at) : "henüz yok"}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(c.id)}
                  className="text-xs text-rose-600 hover:underline"
                >
                  Sil
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h2 className="font-semibold">Yeni Trendyol Bağlantısı</h2>
        <form onSubmit={handleSubmit} className="mt-3 space-y-3">
          <Field label="Seller ID" name="seller_id" required />
          <Field label="API Key" name="api_key" type="password" required />
          <Field label="API Secret" name="api_secret" type="password" required />
          {error && (
            <div className="rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? "Kuruluyor…" : "Bağlantı Kur"}
          </button>
          <p className="text-xs text-slate-500">
            🔒 API key ve secret sunucuda Fernet ile şifrelenir. Asla geri
            okunmaz.
          </p>
        </form>
      </div>
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
