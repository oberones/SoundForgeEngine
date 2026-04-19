import type { ControlDefinition } from "../../services/types";

interface PersistStateBadgeProps {
  control: ControlDefinition;
}

export function PersistStateBadge({ control }: PersistStateBadgeProps) {
  if (control.persist_behavior !== "persistable") {
    return <span className="persist-badge readonly">Session only</span>;
  }

  if (control.dirty_state === "dirty") {
    return <span className="persist-badge dirty">Differs from saved</span>;
  }

  if (control.dirty_state === "conflicted") {
    return <span className="persist-badge conflicted">Conflict</span>;
  }

  return <span className="persist-badge clean">Saved</span>;
}
