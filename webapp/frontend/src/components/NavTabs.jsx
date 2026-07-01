import { NavLink } from "react-router-dom";
import clsx from "clsx";

export default function NavTabs({ tabs }) {
  return (
    <nav
      className="flex items-center gap-1 rounded-full border border-line-soft bg-white p-1 shadow-sm"
      aria-label="Primary"
    >
      {tabs.map((tab) => (
        <NavLink
          key={tab.path}
          to={tab.path}
          className={({ isActive }) =>
            clsx(
              "rounded-full px-4 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-brand-600 text-white shadow-sm"
                : "text-ink-soft hover:bg-line-soft hover:text-ink",
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
