import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Inbox,
  FileText,
  Info,
  Shield,
} from "lucide-react";
import { cn } from "../../lib/cn.js";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/tickets", label: "Tickets", icon: Inbox },
  { to: "/audit", label: "Audit Log", icon: FileText },
  { to: "/about", label: "About", icon: Info },
];

export function Sidebar() {
  return (
    <aside className="w-[240px] shrink-0 border-r border-border bg-surface flex flex-col h-screen sticky top-0">
      <div className="px-5 h-14 flex items-center gap-2 border-b border-border">
        <div className="w-7 h-7 rounded-md bg-accent flex items-center justify-center">
          <Shield className="w-4 h-4 text-black" strokeWidth={2.5} />
        </div>
        <div className="leading-tight">
          <div className="text-text font-semibold text-sm">Sentinel</div>
          <div className="text-text-muted text-[10px] uppercase tracking-wider">
            Support Agent
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-0.5">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 px-3 h-8 rounded-md text-sm transition-colors duration-150",
                isActive
                  ? "bg-surface-2 text-text"
                  : "text-text-muted hover:bg-surface-2 hover:text-text"
              )
            }
          >
            <Icon className="w-4 h-4" aria-hidden />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-border">
        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">
          Hackathon
        </div>
        <div className="text-xs text-text-dim leading-tight">
          Ksolves Agentic AI
          <br />
          Hackathon 2026
        </div>
      </div>
    </aside>
  );
}
