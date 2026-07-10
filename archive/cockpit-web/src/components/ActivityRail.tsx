import { X } from "lucide-react";
import { activityFeed } from "@/lib/data";

export function ActivityRail({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <>
      <div className="activity-backdrop" onClick={onClose} aria-hidden />
      <aside className="activity-rail" role="dialog" aria-label="Activity feed">
        <div className="activity-rail-head">
          <h3>Activity</h3>
          <button type="button" className="btn ghost" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <div className="activity-list">
          {activityFeed.map((item) => (
            <div key={item.id} className="activity-item">
              <span className={`activity-dot ${item.tone}`} />
              <div className="activity-body">
                <strong>{item.title}</strong>
                <p>{item.detail}</p>
                <time dateTime={item.ts}>{item.tsLabel}</time>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
