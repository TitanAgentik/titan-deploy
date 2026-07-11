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
import {
  dataModeLabel,
  envDataMode,
  useDataMode,
  type DataMode,
} from "@/lib/providers";

type ThemeId = "light" | "dark";

function readTheme(): ThemeId {
  const stored = localStorage.getItem("titan-theme");
  if (stored === "dark" || stored === "classic") return "dark";
  if (stored === "light" || stored === "fable") return "light";
  return "light";
}

export function Settings() {
  const { toasts, push, dismiss } = useToasts();
  const { mode, setMode } = useDataMode();
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

  const applyMode = (next: DataMode) => {
    setMode(next);
    push(`Data mode → ${dataModeLabel(next)}`, "ok");
  };

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Settings"
        subtitle="Remote access, auth, appearance, data providers, and Agentik connectivity. Prefer Tailscale / SSH tunnel — never expose unsigned admin UI publicly."
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

        <Card title="Data providers">
          <p className="muted small" style={{ marginBottom: 12 }}>
            Cockpit reads through <span className="mono">lib/providers</span>. Mock uses fixtures
            in <span className="mono">data.ts</span>. Live calls Vite{" "}
            <span className="mono">/api/*</span> proxies and soft-fails to fixtures until your
            backends exist. Env default:{" "}
            <span className="mono">VITE_DATA_MODE={envDataMode()}</span>.
          </p>
          <div className="option-grid">
            <button
              type="button"
              className={`option-tile${mode === "mock" ? " active" : ""}`}
              onClick={() => applyMode("mock")}
            >
              <strong>Mock</strong>
              <span>fixtures · advisory</span>
            </button>
            <button
              type="button"
              className={`option-tile${mode === "live" ? " active" : ""}`}
              onClick={() => applyMode("live")}
            >
              <strong>Live</strong>
              <span>API stubs · soft-fail</span>
            </button>
          </div>
          <p className="muted small" style={{ marginTop: 12, marginBottom: 0 }}>
            Active: <Tag kind={mode === "live" ? "watch" : "neutral"}>{dataModeLabel(mode)}</Tag>
            {" · "}session override (not persisted to disk)
          </p>
        </Card>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
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
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
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
                {(
                  [
                    ["/api/risk", "http://127.0.0.1:19001"],
                    ["/api/recon", "http://127.0.0.1:19002"],
                    ["/api/status", "http://127.0.0.1:19003"],
                    ["/api/portfolio", "http://127.0.0.1:19004"],
                    ["/api/dms", "http://127.0.0.1:19005"],
                    ["/api/allocator", "http://127.0.0.1:19006"],
                    ["/api/tca", "http://127.0.0.1:19007"],
                    ["/api/security", "http://127.0.0.1:19008"],
                    ["/api/signing", "http://127.0.0.1:19003 (halt via control plane)"],
                    [
                      "/api/sign",
                      "optional legacy :19010 (default signing is in-process titan-safety)",
                    ],
                  ] as const
                ).map(([a, b]) => (
                  <tr key={a}>
                    <td>{a}</td>
                    <td>{b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
