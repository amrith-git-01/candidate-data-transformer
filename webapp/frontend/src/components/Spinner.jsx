export default function Spinner({ label }) {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-soft">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line-soft border-t-brand-600" />
      {label && <span>{label}</span>}
    </div>
  );
}
