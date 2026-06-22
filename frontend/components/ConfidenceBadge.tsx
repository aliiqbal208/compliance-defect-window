export default function ConfidenceBadge({ value }: { value: number }) {
  if (value <= 0) {
    return (
      <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-500">
        n/a
      </span>
    );
  }
  const pct = Math.round(value * 100);
  const tone =
    value >= 0.8
      ? "bg-emerald-100 text-emerald-700"
      : value >= 0.5
      ? "bg-amber-100 text-amber-700"
      : "bg-rose-100 text-rose-700";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>
      {pct}%
    </span>
  );
}
