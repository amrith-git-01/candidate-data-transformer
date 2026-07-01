import clsx from "clsx";

export default function Tabs({ tabs, active, onChange }) {
  return (
    <nav
      className="flex items-center gap-1 rounded-full border border-line-soft bg-white p-1 shadow-sm"
      aria-label="Tabs"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={clsx(
              "rounded-full px-4 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-brand-600 text-white shadow-sm"
                : "text-ink-soft hover:bg-line-soft hover:text-ink",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
