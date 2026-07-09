import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Command,
  Hammer,
  Radar,
  Workflow,
  Target,
  Fingerprint,
  ScrollText,
  MessageCircleQuestion,
  Factory,
  Users,
  FolderOpen,
  FileBarChart2,
  Settings,
  Wallet,
  ScanLine,
  ShieldAlert,
  GitBranch,
  Globe2,
  KeyRound,
  Rocket,
  Cpu,
  Shield,
  Zap,
  TrendingUp,
  Megaphone,
  Newspaper,
  Flame,
  Timer,
  Atom,
  SlidersHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  HeartPulse,
  ClipboardCheck,
  Gauge,
  BatteryCharging,
  BookMarked,
} from "lucide-react";
import { portfolio, pnl, formatPnl } from "@/lib/data";

export const NAV = [
  {
    label: "Control",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/command", icon: Command, label: "Command Center" },
      { to: "/manual-control", icon: SlidersHorizontal, label: "Manual Control" },
      { to: "/capital", icon: Wallet, label: "Capital & Wallets" },
      { to: "/wallets", icon: ScanLine, label: "Wallet Tracker" },
      { to: "/pnl", icon: TrendingUp, label: "PnL" },
      { to: "/risk", icon: ShieldAlert, label: "Risk & CBs" },
      { to: "/dms", icon: HeartPulse, label: "Dead Man's Switch" },
      { to: "/security", icon: Shield, label: "Security Ops", badge: 2 },
      { to: "/ops", icon: Radar, label: "Ops Center" },
      { to: "/health", icon: ClipboardCheck, label: "Health & Verify" },
      { to: "/power", icon: BatteryCharging, label: "Power & UPS" },
      { to: "/forge", icon: Hammer, label: "Forge" },
    ],
  },
  {
    label: "Trading",
    items: [
      { to: "/pipelines", icon: GitBranch, label: "Pipelines" },
      { to: "/qi-optimizer", icon: Atom, label: "QI Optimizer" },
      { to: "/tca", icon: Gauge, label: "TCA & Allocator" },
      { to: "/promotions", icon: Rocket, label: "Promotions", badge: 3 },
      { to: "/memecoin", icon: Flame, label: "Memecoin Trench" },
      { to: "/edge", icon: Globe2, label: "Edge Mesh" },
      { to: "/latency", icon: Timer, label: "Latency" },
      { to: "/flash-loans", icon: Zap, label: "Flash Loans" },
      { to: "/signing", icon: KeyRound, label: "Signing" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/automations", icon: Workflow, label: "Automations" },
      { to: "/crypto-news", icon: Newspaper, label: "Crypto News" },
      { to: "/crypto-twitter", icon: Megaphone, label: "Crypto Twitter" },
      { to: "/goals", icon: Target, label: "Goals Lab" },
      { to: "/identity", icon: Fingerprint, label: "Identity" },
      { to: "/models", icon: Cpu, label: "Model Tiers" },
      { to: "/ai-log", icon: ScrollText, label: "AI Log" },
      { to: "/decisions", icon: BookMarked, label: "Decision Log" },
      { to: "/questions", icon: MessageCircleQuestion, label: "Questions", badge: 3 },
    ],
  },
  {
    label: "Build",
    items: [
      { to: "/skills", icon: Factory, label: "Skill Factory" },
      { to: "/agents", icon: Users, label: "Agent Teams" },
      { to: "/workspace", icon: FolderOpen, label: "Workspace" },
    ],
  },
  {
    label: "Governance",
    items: [
      { to: "/reports", icon: FileBarChart2, label: "Reports" },
      { to: "/settings", icon: Settings, label: "Settings" },
    ],
  },
];

export function Sidebar({
  collapsed,
  onToggleCollapsed,
  dirty,
  onSaveShell,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  dirty: boolean;
  onSaveShell: () => void;
}) {
  const mode = portfolio.killActive ? "HALTED" : portfolio.capitalProfile.toUpperCase();
  return (
    <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
      <div className="brand">
        <div className="brand-mark">T</div>
        <div className="brand-text">
          <strong>Titan Agentik</strong>
          <span>crypto control plane</span>
        </div>
      </div>

      <nav className="nav-group">
        {NAV.map((group) => (
          <div key={group.label}>
            <div className="nav-label">{group.label}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                title={item.label}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
              >
                <item.icon />
                <span>{item.label}</span>
                {"badge" in item && item.badge ? (
                  <span className="nav-badge">{item.badge}</span>
                ) : null}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="mini-stats">
          <div className="mini-stat">
            <div className="k">Equity</div>
            <div className="v">${(portfolio.equityUsd / 1000).toFixed(1)}k</div>
          </div>
          <div className="mini-stat">
            <div className="k">WTD PnL</div>
            <div className="v">{formatPnl(pnl.weeklyUsd)}</div>
          </div>
        </div>
        <div className="status-pill">
          <span className={`dot${portfolio.killActive ? " danger" : ""}`} />
          <span>
            Kernel · <span className="mono">{mode}</span>
          </span>
        </div>
        <button
          type="button"
          className="sidebar-collapse-btn"
          onClick={onToggleCollapsed}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          {!collapsed ? <span>Collapse</span> : null}
        </button>
        {dirty ? (
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={onSaveShell}
            title="Save sidebar layout locally"
          >
            <span>{collapsed ? "Save" : "Save layout (local)"}</span>
          </button>
        ) : null}
      </div>
    </aside>
  );
}
