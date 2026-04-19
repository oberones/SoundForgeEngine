import type { EngineSnapshot, SessionResponse } from "../../services/types";

interface ConcurrentOperatorNoticeProps {
  session: SessionResponse | null;
  snapshot: EngineSnapshot | null;
}

export function ConcurrentOperatorNotice({ session, snapshot }: ConcurrentOperatorNoticeProps) {
  if (!session || session.conflict_state !== "unsupported-concurrent-use") {
    return null;
  }

  return (
    <div className="warning-callout" role="alert">
      <strong>Concurrent active operation is unsupported.</strong>
      <p>
        Another dashboard is already acting as the primary operator surface. This session can still observe the engine,
        but you should avoid conflicting edits until the active session releases control.
      </p>
      {snapshot?.active_session_id ? <p className="callout-meta">Active session: {snapshot.active_session_id}</p> : null}
    </div>
  );
}
