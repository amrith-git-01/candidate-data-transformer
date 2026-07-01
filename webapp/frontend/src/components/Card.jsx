export default function Card({ title, description, actions, children }) {
  return (
    <div className="rounded-2xl border border-line-soft bg-white p-6 shadow-[0_1px_2px_rgba(31,22,120,0.04),0_8px_24px_-12px_rgba(31,22,120,0.10)]">
      {(title || actions) && (
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            {title && (
              <h2 className="text-lg font-semibold tracking-tight text-ink">
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-1 text-sm text-ink-soft">{description}</p>
            )}
          </div>
          {actions && (
            <div className="flex shrink-0 items-center gap-2">{actions}</div>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
