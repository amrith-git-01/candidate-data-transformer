import clsx from "clsx";

export default function Toggle({ checked, onChange, label, description }) {
  return (
    <label className="flex items-start gap-3 py-1">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={clsx(
          "relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-200",
          checked ? "bg-brand-600" : "bg-line-soft",
        )}
      >
        <span
          className={clsx(
            "inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-6" : "translate-x-1",
          )}
        />
      </button>
      <span>
        <span className="block text-sm font-medium text-ink">{label}</span>
        {description && (
          <span className="block text-xs text-ink-soft">{description}</span>
        )}
      </span>
    </label>
  );
}
