import { useCallback, useEffect, useState } from "react";

import { api, getApiErrorMessage } from "../services/api";
import type { BootstrapResponse } from "../services/types";

export function useBootstrap() {
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await api.bootstrap();
      setBootstrap(payload);
      setError(null);
      return payload;
    } catch (caught) {
      setError(getApiErrorMessage(caught));
      throw caught;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    bootstrap,
    loading,
    error,
    refetch: load,
    setBootstrap
  };
}
