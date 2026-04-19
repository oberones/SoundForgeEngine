import { useEffect, useState } from "react";

import { api, getApiErrorMessage } from "../services/api";
import type { ActionDefinition } from "../services/types";

export function useActionCatalog(initialActions: ActionDefinition[] = []) {
  const [actions, setActions] = useState<ActionDefinition[]>(initialActions);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActions(initialActions);
  }, [initialActions]);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const payload = await api.actionCatalog();
        if (!cancelled) {
          setActions(payload.actions);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(getApiErrorMessage(caught));
        }
      }
    }

    void refresh();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    actions,
    error,
    setActions
  };
}
