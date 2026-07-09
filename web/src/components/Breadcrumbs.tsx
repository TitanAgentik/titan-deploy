import { Link } from "react-router-dom";

const GROUP: Record<string, string> = {
  "/": "Control",
  "/command": "Control",
  "/capital": "Control",
  "/risk": "Control",
  "/security": "Control",
  "/ops": "Control",
  "/forge": "Control",
  "/pipelines": "Trading",
  "/promotions": "Trading",
  "/edge": "Trading",
  "/signing": "Trading",
  "/automations": "Intelligence",
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
  const group = GROUP[pathname] ?? "Cockpit";

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <Link to="/">TITAN</Link>
      <span className="sep">/</span>
      <span>{group}</span>
      <span className="sep">/</span>
      <span className="current">{title}</span>
    </nav>
  );
}
