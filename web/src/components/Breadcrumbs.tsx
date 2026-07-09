import { Link } from "react-router-dom";

const GROUP: Record<string, string> = {
  "/": "Control",
  "/command": "Control",
  "/manual-control": "Control",
  "/capital": "Control",
  "/wallets": "Control",
  "/pnl": "Control",
  "/risk": "Control",
  "/security": "Control",
  "/ops": "Control",
  "/forge": "Control",
  "/pipelines": "Trading",
  "/promotions": "Trading",
  "/edge": "Trading",
  "/latency": "Trading",
  "/qi-optimizer": "Trading",
  "/flash-loans": "Trading",
  "/memecoin": "Trading",
  "/signing": "Trading",
  "/automations": "Intelligence",
  "/crypto-twitter": "Intelligence",
  "/crypto-news": "Intelligence",
  "/goals": "Intelligence",
  "/identity": "Intelligence",
  "/models": "Intelligence",
  "/ai-log": "Intelligence",
  "/questions": "Intelligence",
  "/skills": "Build",
  "/agents": "Build",
  "/workspace": "Build",
  "/reports": "Governance",
  "/settings": "Governance",
};

export function Breadcrumbs({ pathname, title }: { pathname: string; title: string }) {
  const group = GROUP[pathname] ?? "Agentik";

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <Link to="/">Titan Agentik</Link>
      <span className="sep">/</span>
      <span>{group}</span>
      <span className="sep">/</span>
      <span className="current">{title}</span>
    </nav>
  );
}
