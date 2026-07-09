import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { portfolio } from "@/lib/data";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/command": "Command Center",
  "/forge": "Forge",
  "/ops": "Ops Center",
  "/automations": "Automations",
  "/goals": "Goals Lab",
  "/identity": "Identity",
  "/ai-log": "AI Log",
  "/questions": "Questions",
  "/skills": "Skill Factory",
  "/agents": "Agent Teams",
  "/workspace": "Workspace",
  "/reports": "Reports",
  "/settings": "Settings",
};

export function AppShell() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "TITAN Cockpit";

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main">
        <header className="topbar">
          <h1>{title}</h1>
          <div className="topbar-meta">
            <span className="chip ok">regime · {portfolio.regime}</span>
            <span className={`chip ${portfolio.evolutionFrozen ? "warn" : "ok"}`}>
              evolution · {portfolio.evolutionFrozen ? "frozen" : "open"}
            </span>
            <span className="chip">equity · ${portfolio.equityUsd.toLocaleString()}</span>
            <span className="chip">operator · Hyperion</span>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
