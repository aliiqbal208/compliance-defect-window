"use client";

import { useState } from "react";
import DefectTable from "@/components/DefectTable";
import ExtractedValues from "@/components/ExtractedValues";
import PdfViewer from "@/components/PdfViewer";
import SummaryBanner from "@/components/SummaryBanner";
import UploadZone from "@/components/UploadZone";
import { AnalyzeResponse } from "@/lib/types";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  async function analyze(file: File) {
    setLoading(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/analyze", { method: "POST", body });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Compliance Defect Window
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a site-plan PDF to check it against zoning bylaws.
        </p>
      </header>

      <UploadZone onFile={analyze} loading={loading} />

      {error && (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-6">
          <SummaryBanner result={result} />

          {result.warnings.length > 0 && (
            <ul className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
              {result.warnings.map((w, i) => (
                <li key={i}>⚠ {w}</li>
              ))}
            </ul>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="space-y-6">
              <DefectTable checks={result.checks} />
              <ExtractedValues result={result} />
            </div>
            <PdfViewer url={result.annotated_pdf_url} />
          </div>
        </div>
      )}
    </main>
  );
}
