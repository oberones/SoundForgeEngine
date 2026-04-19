import { useCallback, useState } from "react";

import { api, getApiErrorMessage } from "../services/api";
import type { ActionInvocationResponse, MutationFeedback } from "../services/types";

export function useActionInvocation(onSuccess?: (response: ActionInvocationResponse) => void) {
  const [feedback, setFeedback] = useState<MutationFeedback>({ state: "idle" });

  const invoke = useCallback(
    async (action: string, value?: string) => {
      setFeedback({ state: "pending", message: `Running ${action}...` });
      try {
        const response = await api.invokeAction(action, value);
        setFeedback({ state: "success", message: response.message });
        onSuccess?.(response);
        return response;
      } catch (caught) {
        setFeedback({ state: "error", message: getApiErrorMessage(caught) });
        throw caught;
      }
    },
    [onSuccess]
  );

  return {
    feedback,
    invoke,
    clearFeedback: () => setFeedback({ state: "idle" })
  };
}
