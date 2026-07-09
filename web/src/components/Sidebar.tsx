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
} from "lucide-react";
import { portfolio } from "@/lib/data";

const NAV = [
  {
    label: "Control",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/command", icon: Command, label: "Command Center" },
      { to: "/forge", icon: Hammer, label: "Forge" },
      { to: "/ops", icon: Radar, label: "Ops Center" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/automations", icon: Workflow, label: "Automations" },
      { to: "/goals", icon: Target, label: "Goals Lab" },
      { to: "/identity", icon: Fingerprint, label: "Identity" },
      { to: "/ai-log", icon: ScrollText, label: "AI Log" },
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

export function Sidebar() {
  const mode = portfolio.killActive ? "HALTED" : portfolio.capitalProfile.toUpperCase();
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">T</div>
        <div className="brand-text">
          <strong>TITAN COCKPIT</strong>
          <span>institutional control plane</span>
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
        <div className="status-pill">
          <span className={`dot${portfolio.killActive ? " danger" : ""}`} />
          <span>
            Kernel · <span className="mono">{mode}</span>
          </span>
        </div>
      </div>
    </aside>
  );
}
