import { AnalyzeResponse, FIELD_LABELS } from "@/lib/types";
import ConfidenceBadge from "./ConfidenceBadge";

export default function ExtractedValues({
  result,
}: {
  result: AnalyzeResponse;
}) {
  const order = Object.keys(FIELD_LABELS).filter((k) => k in result.fields);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">
        Extracted Values
      </h3>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
        {order.map((key) => {
          const f = result.fields[key];
          const determined = f.value !== null;
          return (
            <div
              key={key}
              className="flex items-center justify-between border-b border-slate-50 py-1.5"
            >
              <dt className="text-sm text-slate-500">{FIELD_LABELS[key]}</dt>
              <dd className="flex items-center gap-2">
                <span
                  className={`text-sm font-medium ${
                    determined ? "text-slate-800" : "italic text-slate-400"
                  }`}
                  title={f.note ?? undefined}
                >
                  {determined
                    ? `${f.value}${f.unit && f.unit !== "count" ? " " + f.unit : ""}`
                    : "Unable to determine"}
                </span>
                <ConfidenceBadge value={f.confidence} />
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
