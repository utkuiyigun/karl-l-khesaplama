"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { CogsImportResult } from "@/lib/types";

export default function CogsPage() {
  const params = useParams();
  const customerId = Number(params.id);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CogsImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.uploadCogs(customerId, file);
      setResult(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold">COGS (Ürün Maliyeti) Yükle</h2>
        <p className="mt-1 text-sm text-slate-500">
          CSV veya Excel (.xlsx) dosyası yükle. Zorunlu kolonlar:{" "}
          <code>barcode, cogs</code>. Opsiyonel: <code>name</code>.
        </p>
        <a
          href={api.cogsTemplateUrl(customerId)}
          className="mt-2 inline-block text-sm text-emerald-700 hover:underline"
        >
          📥 Şablon CSV indir
        </a>
      </div>

      <div className="rounded-lg border-2 border-dashed border-slate-300 bg-white p-8 text-center">
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => {
            setFile(e.target.files?.[0] || null);
            setResult(null);
            setError(null);
          }}
          className="mx-auto block text-sm"
        />
        {file && (
          <div className="mt-3 text-xs text-slate-600">
            Seçili: <code>{file.name}</code> ({(file.size / 1024).toFixed(1)} KB)
          </div>
        )}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {uploading ? "Yükleniyor…" : "Yükle"}
        </button>
      </div>

      {error && (
        <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {result && (
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h3 className="font-semibold">Sonuç</h3>
          <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded bg-emerald-50 p-3">
              <div className="text-xs text-emerald-700">Yeni eklenen</div>
              <div className="text-2xl font-semibold text-emerald-900">
                {result.created}
              </div>
            </div>
            <div className="rounded bg-blue-50 p-3">
              <div className="text-xs text-blue-700">Güncellenen</div>
              <div className="text-2xl font-semibold text-blue-900">
                {result.updated}
              </div>
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-rose-700">
                Hatalar ({result.errors.length}) — değişiklikler kaydedilmedi
              </div>
              <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-rose-600">
                {result.errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
