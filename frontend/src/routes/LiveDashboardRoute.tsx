import { ConcurrentOperatorNotice } from "../components/feedback/ConcurrentOperatorNotice";
import type { ConfigUpdateResponse, ControlDefinition, EngineSnapshot, MutationFeedback, SessionResponse } from "../services/types";
import { EngineStatusCard } from "../domains/live-control/EngineStatusCard";
import { LiveControlPanel } from "../domains/live-control/LiveControlPanel";
import { ControlMutationState } from "../domains/live-control/ControlMutationState";

interface LiveDashboardRouteProps {
  controls: ControlDefinition[];
  snapshot: EngineSnapshot | null;
  session: SessionResponse | null;
  externalChanges: string[];
  feedback: MutationFeedback;
  onSubmit: (path: string, value: unknown) => Promise<ConfigUpdateResponse>;
}

export function LiveDashboardRoute({
  controls,
  snapshot,
  session,
  externalChanges,
  feedback,
  onSubmit
}: LiveDashboardRouteProps) {
  return (
    <div className="route-stack">
      <ConcurrentOperatorNotice session={session} snapshot={snapshot} />
      <EngineStatusCard snapshot={snapshot} />
      <ControlMutationState feedback={feedback} />
      <LiveControlPanel controls={controls} snapshot={snapshot} externalChanges={externalChanges} onSubmit={onSubmit} />
    </div>
  );
}
