import { AnalyzeResponse } from "@/lib/types";

export default function SummaryBanner({ result }: { result: AnalyzeResponse }) {
  const { summary, compliant, backend } = result;
  const tone = compliant
    ? "border-emerald-200 bg-emerald-50"
    : summary.failed > 0
    ? "border-rose-200 bg-rose-50"
    : "border-amber-200 bg-amber-50";
  const headline = compliant
    ? "Compliant — no defects found"
    : summary.failed > 0
    ? `${summary.failed} compliance ${summary.failed === 1 ? "failure" : "failures"}`
    : "Incomplete — some values could not be determined";

  return (
    <div className={`rounded-xl border p-4 ${tone}`}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-slate-800">{headline}</h2>
        <span className="rounded-md bg-white/70 px-2 py-1 text-xs font-medium text-slate-500">
          extractor: {backend}
        </span>
      </div>
      <div className="mt-2 flex gap-4 text-sm text-slate-600">
        <span>
          <strong className="text-emerald-700">{summary.passed}</strong> passed
        </span>
        <span>
          <strong className="text-rose-700">{summary.failed}</strong> failed
        </span>
        <span>
          <strong className="text-amber-700">{summary.unknown}</strong> unknown
        </span>
      </div>
    </div>
  );
}
