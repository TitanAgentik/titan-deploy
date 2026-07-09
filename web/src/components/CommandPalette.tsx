import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  CornerDownLeft,
  ArrowDownUp,
  Skull,
  HeartPulse,
  Snowflake,
  ArrowDownToLine,
  ArrowUpFromLine,
  Vault,
  Shield,
  type LucideIcon,
} from "lucide-react";
import { NAV } from "./Sidebar";

export type PaletteEntry = {
  id: string;
  group: string;
  label: string;
  hint?: string;
  icon: LucideIcon;
  run: (navigate: (to: string) => void) => string | void;
};

function buildEntries(onAction: (msg: string, tone: "ok" | "warn" | "danger") => void): PaletteEntry[] {
  const nav: PaletteEntry[] = NAV.flatMap((group) =>
    group.items.map((item) => ({
      id: `nav:${item.to}`,
      group: "Go to",
      label: item.label,
      hint: item.to,
      icon: item.icon,
      run: (navigate) => navigate(item.to),
    })),
  );

  const actions: PaletteEntry[] = [
    {
      id: "act:heartbeat",
      group: "Actions",
      label: "Send DMS heartbeat",
      hint: "dead man's switch",
      icon: HeartPulse,
      run: (navigate) => {
        onAction("Heartbeat sent — DMS timer reset (demo)", "ok");
        navigate("/command");
      },
    },
    {
      id: "act:kill",
      group: "Actions",
      label: "Open kill switch",
      hint: "requires confirm",
      icon: Skull,
      run: (navigate) => {
        onAction("Kill switch requires confirmation in Command Center", "warn");
        navigate("/command");
      },
    },
    {
      id: "act:freeze",
      group: "Actions",
      label: "Toggle evolution freeze",
      hint: "shadow-only deploys",
      icon: Snowflake,
      run: (navigate) => {
        onAction("Evolution freeze is managed from Command Center", "warn");
        navigate("/command");
      },
    },
    {
      id: "act:lockdown",
      group: "Actions",
      label: "Security lockdown",
      hint: "impenetrable · predatory",
      icon: Shield,
      run: (navigate) => {
        onAction("Open Security Ops → lockdown confirm", "warn");
        navigate("/security");
      },
    },
    {
      id: "act:deposit",
      group: "Actions",
      label: "New deposit",
      hint: "capital ledger",
      icon: ArrowDownToLine,
      run: (navigate) => navigate("/capital"),
    },
    {
      id: "act:withdraw",
      group: "Actions",
      label: "New withdrawal",
      hint: "operator YES",
      icon: ArrowUpFromLine,
      run: (navigate) => navigate("/capital"),
    },
    {
      id: "act:sweep",
      group: "Actions",
      label: "Run Trezor Safe 7 sweep check",
      hint: "R23 · 20% weekly",
      icon: Vault,
      run: (navigate) => {
        onAction("Sweep eligibility evaluated — see Capital & Wallets", "ok");
        navigate("/capital");
      },
    },
    {
      id: "act:rebalance",
      group: "Actions",
      label: "Review lane allocations",
      hint: "capital allocator",
      icon: ArrowDownUp,
      run: (navigate) => navigate("/pipelines"),
    },
  ];

  return [...nav, ...actions];
}

export function CommandPalette({
  open,
  onClose,
  onAction,
}: {
  open: boolean;
  onClose: () => void;
  onAction: (msg: string, tone: "ok" | "warn" | "danger") => void;
}) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const entries = useMemo(() => buildEntries(onAction), [onAction]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return entries;
    return entries.filter(
      (e) =>
        e.label.toLowerCase().includes(q) ||
        e.group.toLowerCase().includes(q) ||
        (e.hint ?? "").toLowerCase().includes(q),
    );
  }, [entries, query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelected(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    setSelected(0);
  }, [query]);

  if (!open) return null;

  const runEntry = (entry: PaletteEntry) => {
    onClose();
    entry.run((to) => navigate(to));
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && filtered[selected]) {
      e.preventDefault();
      runEntry(filtered[selected]);
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  let lastGroup = "";

  return (
    <div className="cmdk-root" onClick={onClose}>
      <div className="cmdk-panel" onClick={(e) => e.stopPropagation()}>
        <div className="cmdk-input">
          <Search size={17} />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search sections and actions…"
            spellCheck={false}
          />
          <span className="kbd">esc</span>
        </div>
        <div className="cmdk-list">
          {filtered.length === 0 && <div className="empty">No matches for “{query}”</div>}
          {filtered.map((entry, i) => {
            const showGroup = entry.group !== lastGroup;
            lastGroup = entry.group;
            return (
              <div key={entry.id}>
                {showGroup && <div className="cmdk-group">{entry.group}</div>}
                <button
                  className={`cmdk-item${i === selected ? " selected" : ""}`}
                  onMouseEnter={() => setSelected(i)}
                  onClick={() => runEntry(entry)}
                >
                  <entry.icon />
                  <span>{entry.label}</span>
                  {entry.hint && <span className="hint">{entry.hint}</span>}
                </button>
              </div>
            );
          })}
        </div>
        <div className="cmdk-foot">
          <span>
            <span className="kbd">↑↓</span> navigate
          </span>
          <span>
            <CornerDownLeft size={11} style={{ verticalAlign: "-1px" }} /> select
          </span>
          <span>
            <span className="kbd">Ctrl</span> + <span className="kbd">K</span> toggle
          </span>
        </div>
      </div>
    </div>
  );
}
