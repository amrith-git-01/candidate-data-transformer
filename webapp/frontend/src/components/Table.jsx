function formatCell(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function Table({ columns, rows, emptyMessage = "No data" }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="py-16 text-center text-sm text-ink-soft">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-line-soft">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-line-soft">
            {columns.map((col) => (
              <th
                key={col.key}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-ink-soft whitespace-nowrap"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id ?? i}
              className="border-b border-line-soft last:border-b-0 hover:bg-canvas"
            >
              {columns.map((col) => {
                const content = col.render
                  ? col.render(row)
                  : formatCell(row[col.key]);

                if (col.scroll) {
                  return (
                    <td key={col.key} className="px-4 py-3 align-top text-ink">
                      <div className="thin-scroll max-h-28 w-72 overflow-y-auto whitespace-pre-wrap break-words pr-2">
                        {content}
                      </div>
                    </td>
                  );
                }

                return (
                  <td
                    key={col.key}
                    className="max-w-[280px] truncate px-4 py-3 text-ink"
                    title={formatCell(
                      col.render ? col.render(row) : row[col.key],
                    )}
                  >
                    {content}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
