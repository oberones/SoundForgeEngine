import { useCallback, useState } from "react";

import { api, getApiErrorMessage, getConflictDetail } from "../services/api";
import type { ConfigUpdateResponse, MutationFeedback } from "../services/types";

interface ConflictAwareMutationOptions {
  revision?: string | null;
  sessionId?: string | null;
  onSuccess?: (response: ConfigUpdateResponse) => void;
}

export function useConflictAwareMutation({ revision, sessionId, onSuccess }: ConflictAwareMutationOptions) {
  const [feedback, setFeedback] = useState<MutationFeedback>({ state: "idle" });
  const [conflict, setConflict] = useState<Record<string, unknown> | null>(null);

  const mutate = useCallback(
    async (path: string, value: unknown) => {
      setFeedback({ state: "pending", message: `Updating ${path}...` });
      setConflict(null);
      try {
        const response = await api.updateConfig({
          path,
          value,
          apply_immediately: true,
          expected_revision: revision ?? undefined,
          session_id: sessionId ?? undefined
        });
        setFeedback({ state: "success", message: response.message });
        onSuccess?.(response);
        return response;
      } catch (caught) {
        const conflictDetail = getConflictDetail(caught);
        if (conflictDetail) {
          setConflict(conflictDetail);
        }
        setFeedback({ state: "error", message: getApiErrorMessage(caught) });
        throw caught;
      }
    },
    [onSuccess, revision, sessionId]
  );

  return {
    feedback,
    conflict,
    mutate,
    clearConflict: () => setConflict(null),
    clearFeedback: () => setFeedback({ state: "idle" })
  };
}
