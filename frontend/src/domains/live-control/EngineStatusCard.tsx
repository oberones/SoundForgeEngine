import type { EngineSnapshot } from "../../services/types";
import { formatUptime } from "../../utils/controls";

interface EngineStatusCardProps {
  snapshot: EngineSnapshot | null;
}

export function EngineStatusCard({ snapshot }: EngineStatusCardProps) {
  return (
    <section className="panel hero-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Engine</p>
          <h2>Runtime Status</h2>
        </div>
        <span className={`status-chip ${snapshot?.status ?? "unreachable"}`}>{snapshot?.status ?? "offline"}</span>
      </div>
      <div className="status-grid">
        <div>
          <span className="meta-label">Revision</span>
          <strong>{snapshot?.revision ?? "Unknown"}</strong>
        </div>
        <div>
          <span className="meta-label">Uptime</span>
          <strong>{formatUptime(snapshot?.uptime_seconds)}</strong>
        </div>
        <div>
          <span className="meta-label">Last capture</span>
          <strong>{snapshot ? new Date(snapshot.captured_at).toLocaleTimeString() : "Unknown"}</strong>
        </div>
      </div>
    </section>
  );
}
