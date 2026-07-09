import { useCallback, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Bell, Search } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { CommandPalette } from "./CommandPalette";
import { ActivityRail } from "./ActivityRail";
import { Breadcrumbs } from "./Breadcrumbs";
import { ToastStack, useToasts } from "./interactive";
import { portfolio, pnl, formatPnl } from "@/lib/data";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/command": "Command Center",
  "/manual-control": "Manual Control",
  "/capital": "Capital & Wallets",
  "/wallets": "Wallet Tracker",
  "/pnl": "PnL",
  "/risk": "Risk & Circuit Breakers",
  "/security": "Security Ops",
  "/forge": "Forge",
  "/ops": "Ops Center",
  "/pipelines": "Pipelines",
  "/promotions": "Promotions",
  "/edge": "Edge Mesh",
  "/latency": "Latency",
  "/qi-optimizer": "QI Optimizer",
  "/flash-loans": "Flash Loans",
  "/memecoin": "Memecoin Trench",
  "/signing": "Signing Node",
  "/automations": "Automations",
  "/crypto-twitter": "Crypto Twitter",
  "/crypto-news": "Crypto News",
  "/goals": "Goals Lab",
  "/identity": "Identity",
  "/models": "Model Tiers",
  "/ai-log": "AI Log",
  "/questions": "Questions",
  "/skills": "Skill Factory",
  "/agents": "Agent Teams",
  "/workspace": "Workspace",
  "/reports": "Reports",
  "/settings": "Settings",
};

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function AppShell() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "Titan Agentik";
  const clock = useClock();
  const { toasts, push, dismiss } = useToasts();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);

  const onPaletteAction = useCallback(
    (msg: string, tone: "ok" | "warn" | "danger" = "ok") => {
      push(msg, tone);
    },
    [push],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
      if (e.key === "Escape") {
        setPaletteOpen(false);
        setActivityOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const mode = portfolio.killActive ? "HALTED" : portfolio.capitalProfile.toUpperCase();

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main">
        <header className="topbar">
          <div>
            <h1>{title}</h1>
            <Breadcrumbs pathname={pathname} title={title} />
          </div>
          <div className="topbar-meta">
            <button
              type="button"
              className="palette-trigger"
              onClick={() => setPaletteOpen(true)}
            >
              <Search size={14} />
              Search
              <span className="kbd">⌘K</span>
            </button>
            <span className="topbar-clock">{clock}</span>
            <button
              type="button"
              className="activity-trigger"
              onClick={() => setActivityOpen(true)}
              aria-label="Open activity feed"
            >
              <Bell size={16} />
              <span className="badge" />
            </button>
            <span className="chip ok">regime · {portfolio.regime}</span>
            <span className={`chip ${portfolio.evolutionFrozen ? "warn" : "ok"}`}>
              evolution · {portfolio.evolutionFrozen ? "frozen" : "open"}
            </span>
            <span className="chip">equity · ${portfolio.equityUsd.toLocaleString()}</span>
            <span className={`chip ${pnl.weeklyUsd >= 0 ? "ok" : "danger"}`}>
              WTD PnL · {formatPnl(pnl.weeklyUsd)}
            </span>
            <span className={`chip ${portfolio.killActive ? "danger" : ""}`}>
              kernel · {mode}
            </span>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onAction={onPaletteAction}
      />
      <ActivityRail open={activityOpen} onClose={() => setActivityOpen(false)} />
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
