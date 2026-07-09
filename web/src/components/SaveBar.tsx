import { Save } from "lucide-react";
import { Btn } from "@/components/ui";

export function SaveBar({
  dirty,
  lastSavedAt,
  onSave,
  onDiscard,
  onResetDefaults,
  disabled,
  label = "Saved locally (cockpit)",
}: {
  dirty: boolean;
  lastSavedAt?: string | null;
  onSave: () => void;
  onDiscard: () => void;
  onResetDefaults?: () => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <div className={`cockpit-save-bar${dirty ? " dirty" : ""}`}>
      <div className="cockpit-save-bar-meta">
        <span className={`chip ${dirty ? "warn" : "ok"}`}>
          {dirty ? "Unsaved changes" : label}
        </span>
        <span className="muted small">
          Browser localStorage · not live API
          {lastSavedAt ? ` · last save ${lastSavedAt.slice(11, 19)}Z` : " · no save yet"}
        </span>
      </div>
      <div className="cockpit-save-bar-actions">
        <Btn variant="ghost" disabled={!dirty || disabled} onClick={onDiscard}>
          Discard
        </Btn>
        {onResetDefaults ? (
          <Btn variant="ghost" disabled={disabled} onClick={onResetDefaults}>
            Reset defaults
          </Btn>
        ) : null}
        <Btn variant="primary" disabled={!dirty || disabled} onClick={onSave}>
          <Save size={14} /> Save
        </Btn>
      </div>
    </div>
  );
}
