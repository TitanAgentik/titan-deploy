import { useEffect, useState } from "react";
import { PageHeader, Card, Btn, Tag } from "@/components/ui";
import { ToastStack, useToasts } from "@/components/interactive";
import {
  clearHmacToken,
  getHmacToken,
  setHmacToken,
} from "@/lib/auth";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";

type ThemeId = "light" | "dark";

function readTheme(): ThemeId {
  const stored = localStorage.getItem("titan-theme");
  if (stored === "dark" || stored === "classic") return "dark";
  if (stored === "light" || stored === "fable") return "light";
  return "light";
}

export function Settings() {
  const { toasts, push, dismiss } = useToasts();
  const {
    draft: settingsPrefs,
    update: updateSettings,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("settings", { bind: "0.0.0.0" });
  const bind = settingsPrefs.bind;
  const setBind = (v: string) => updateSettings({ bind: v });
  const [token, setToken] = useState("");
  const [hmacSaved, setHmacSaved] = useState(() => Boolean(getHmacToken()));
  const [theme, setTheme] = useState<ThemeId>(readTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("titan-theme", theme);
  }, [theme]);

  useEffect(() => {
    setHmacSaved(Boolean(getHmacToken()));
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Settings"
        subtitle="Remote access, auth, appearance, and Agentik connectivity. Prefer Tailscale / SSH tunnel — never expose unsigned admin UI publicly."
      />

      <SaveBar
        dirty={dirty}
        lastSavedAt={lastSavedAt}
        onSave={() => {
          save();
          push("Saved locally", "ok");
        }}
        onDiscard={discard}
        onResetDefaults={resetDefaults}
      />

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Appearance">
          <p className="muted small" style={{ marginBottom: 12 }}>
            <strong>Signal</strong> — cool slate light theme with cyan accent (default).{" "}
            <strong>Night</strong> — deep dark mode with teal accent for low-light ops.
          </p>
          <div className="option-grid">
            <button
              type="button"
              className={`option-tile${theme === "light" ? " active" : ""}`}
              onClick={() => setTheme("light")}
            >
              <strong>Signal</strong>
              <span>slate · cyan · sora</span>
            </button>
            <button
              type="button"
              className={`option-tile${theme === "dark" ? " active" : ""}`}
              onClick={() => setTheme("dark")}
            >
              <strong>Night</strong>
              <span>deep · teal · space grotesk</span>
            </button>
          </div>
        </Card>

        <Card title="Keyboard shortcuts">
          <div className="table-wrap">
            <table className="data">
              <tbody>
                <tr>
                  <td>
                    <span className="kbd">Ctrl</span> + <span className="kbd">K</span>
                  </td>
                  <td>Command palette — navigate sections and run actions</td>
                </tr>
                <tr>
                  <td>
                    <span className="kbd">Esc</span>
                  </td>
                  <td>Close palette, modals, drawers, activity rail</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Remote access">
          <div className="form-row">
            <div className="field" style={{ flex: 1 }}>
              <label>Bind</label>
              <select value={bind} onChange={(e) => setBind(e.target.value)}>
                <option value="127.0.0.1">127.0.0.1 (local only)</option>
                <option value="0.0.0.0">0.0.0.0 (LAN / reverse proxy)</option>
              </select>
            </div>
            <div className="field">
              <label>Port</label>
              <input defaultValue="5173" />
            </div>
          </div>
          <p className="muted small" style={{ marginTop: 12 }}>
            Anywhere access: Tailscale Serve, Cloudflare Tunnel, or{" "}
            <span className="kbd">ssh -L 5173:127.0.0.1:5173</span>. OpenClaw Control UI pattern —
            token in sessionStorage, strip from URL.
          </p>
          <div style={{ marginTop: 10 }}>
            <Tag kind={hmacSaved ? "healthy" : "watch"}>
              {hmacSaved
                ? "HMAC session active"
                : "HMAC not set — mutating calls will 401"}
            </Tag>
          </div>
        </Card>

        <Card title="Control-plane HMAC">
          <div className="field">
            <label>Operator token (session)</label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="X-Titan-Auth secret — not persisted to disk"
            />
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <Btn
              variant="primary"
              onClick={() => {
                setHmacToken(token.trim());
                const saved = Boolean(getHmacToken());
                setHmacSaved(saved);
                if (!saved) setToken("");
              }}
            >
              Save session
            </Btn>
            <Btn
              variant="ghost"
              onClick={() => {
                clearHmacToken();
                setToken("");
                setHmacSaved(false);
              }}
            >
              Clear
            </Btn>
            <Tag kind={hmacSaved ? "healthy" : "neutral"}>
              {hmacSaved ? "HMAC session saved" : "no token"}
            </Tag>
          </div>
        </Card>
      </div>

      <Card title="API proxy map (Vite)">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>UI path</th>
                <th>Upstream</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["/api/risk", ":19001"],
                ["/api/recon", ":19002"],
                ["/api/status", ":19003"],
                ["/api/portfolio", ":19004"],
                ["/api/dms", ":19005"],
                ["/api/allocator", ":19006"],
                ["/api/tca", ":19007"],
                ["/api/security", ":19008"],
                ["/api/sign", "in-process"],
              ].map(([a, b]) => (
                <tr key={a}>
                  <td>{a}</td>
                  <td>http://127.0.0.1{b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
