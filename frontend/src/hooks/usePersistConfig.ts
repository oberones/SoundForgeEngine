import { useCallback, useState } from "react";

import { api, getApiErrorMessage } from "../services/api";
import type { MutationFeedback, PersistResponse } from "../services/types";

interface PersistConfigOptions {
  revision?: string | null;
  sessionId?: string | null;
  onSuccess?: (response: PersistResponse) => void;
}

export function usePersistConfig({ revision, sessionId, onSuccess }: PersistConfigOptions) {
  const [feedback, setFeedback] = useState<MutationFeedback>({ state: "idle" });

  const persist = useCallback(async () => {
    if (!revision) {
      setFeedback({ state: "error", message: "No revision is available to persist yet." });
      return null;
    }
    setFeedback({ state: "pending", message: "Persisting current configuration..." });
    try {
      const response = await api.persistConfig({
        revision,
        session_id: sessionId ?? undefined
      });
      setFeedback({ state: "success", message: response.message });
      onSuccess?.(response);
      return response;
    } catch (caught) {
      setFeedback({ state: "error", message: getApiErrorMessage(caught) });
      throw caught;
    }
  }, [onSuccess, revision, sessionId]);

  return {
    feedback,
    persist,
    clearFeedback: () => setFeedback({ state: "idle" })
  };
}
