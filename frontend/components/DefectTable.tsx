import { CheckResult } from "@/lib/types";
import ConfidenceBadge from "./ConfidenceBadge";
import StatusPill from "./StatusPill";

export default function DefectTable({ checks }: { checks: CheckResult[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-2.5 font-medium">Rule</th>
            <th className="px-4 py-2.5 font-medium">Required</th>
            <th className="px-4 py-2.5 font-medium">Actual</th>
            <th className="px-4 py-2.5 font-medium">Status</th>
            <th className="px-4 py-2.5 font-medium">Conf.</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {checks.map((c) => (
            <tr key={c.rule_id} className="align-top">
              <td className="px-4 py-3">
                <div className="font-medium text-slate-800">{c.label}</div>
                {c.message && (
                  <div className="mt-0.5 text-xs text-rose-600">{c.message}</div>
                )}
              </td>
              <td className="px-4 py-3 text-slate-600">{c.required}</td>
              <td className="px-4 py-3 text-slate-800">
                {c.actual ?? "—"}
              </td>
              <td className="px-4 py-3">
                <StatusPill status={c.status} />
              </td>
              <td className="px-4 py-3">
                <ConfidenceBadge value={c.confidence} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
