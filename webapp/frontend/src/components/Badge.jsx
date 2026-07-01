import clsx from "clsx";

const TONES = {
  slate: "bg-line-soft text-ink-soft",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-rose-50 text-rose-700",
  brand: "bg-brand-100 text-brand-700",
};

export function Badge({ tone = "slate", children }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}

export function ConfidenceBadge({ value }) {
  if (value === null || value === undefined)
    return <span className="text-ink-soft/50">—</span>;
  const pct = Math.round(value * 100);
  const tone = value >= 0.85 ? "green" : value >= 0.6 ? "amber" : "red";
  return <Badge tone={tone}>{pct}%</Badge>;
}
