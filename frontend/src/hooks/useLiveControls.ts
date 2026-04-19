import { useMemo } from "react";

import type { ConfigUpdateResponse, ControlDefinition, EngineSnapshot, SessionResponse } from "../services/types";
import { useConflictAwareMutation } from "./useConflictAwareMutation";

interface LiveControlsOptions {
  controls: ControlDefinition[];
  snapshot: EngineSnapshot | null;
  session: SessionResponse | null;
  onUpdate: (response: ConfigUpdateResponse) => void;
}

export function useLiveControls({ controls, snapshot, session, onUpdate }: LiveControlsOptions) {
  const controlMap = useMemo(() => {
    return new Map(controls.map((control) => [control.path, control]));
  }, [controls]);

  const mutation = useConflictAwareMutation({
    revision: snapshot?.revision,
    sessionId: session?.session_id,
    onSuccess: onUpdate
  });

  return {
    controlsByPath: controlMap,
    submitLiveChange: mutation.mutate,
    feedback: mutation.feedback,
    conflict: mutation.conflict,
    clearConflict: mutation.clearConflict,
    clearFeedback: mutation.clearFeedback
  };
}
