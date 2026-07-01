export default function StatChip({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line-soft bg-canvas px-4 py-3">
      {Icon && (
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
          <Icon size={18} strokeWidth={2} />
        </span>
      )}
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">
          {label}
        </p>
        <p className="text-base font-semibold text-ink">{value}</p>
      </div>
    </div>
  );
}
