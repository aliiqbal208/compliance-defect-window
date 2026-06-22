import { Status } from "@/lib/types";

const STYLES: Record<Status, string> = {
  PASS: "bg-emerald-100 text-emerald-700 ring-emerald-200",
  FAIL: "bg-rose-100 text-rose-700 ring-rose-200",
  UNKNOWN: "bg-amber-100 text-amber-700 ring-amber-200",
};

export default function StatusPill({ status }: { status: Status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}
