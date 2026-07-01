import clsx from "clsx";

export default function SegmentedControl({
  options,
  value,
  onChange,
  size = "md",
}) {
  const padding = size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm";

  return (
    <div
      className="inline-flex items-center gap-1 rounded-full border border-line-soft bg-canvas p-1 shadow-sm"
      role="radiogroup"
    >
      {options.map((option) => {
        const isActive = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => onChange(option.value)}
            className={clsx(
              "rounded-full font-medium transition-colors",
              padding,
              isActive
                ? "bg-brand-600 text-white shadow-sm"
                : "text-ink-soft hover:bg-line-soft hover:text-ink",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
