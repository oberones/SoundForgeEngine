import { useEffect, useState } from "react";

import { api, getApiErrorMessage } from "../services/api";
import type { SessionResponse } from "../services/types";

const HEARTBEAT_INTERVAL_MS = 10_000;

export function useSession() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let heartbeatId: number | undefined;
    let activeSessionId: string | null = null;

    async function create() {
      try {
        const next = await api.createSession({
          client_name: "SoundForgeEngine Dashboard",
          user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "browser"
        });
        if (cancelled) {
          return;
        }
        activeSessionId = next.session_id;
        setSession(next);
        setError(null);

        heartbeatId = window.setInterval(async () => {
          if (!activeSessionId) {
            return;
          }
          try {
            const heartbeat = await api.heartbeatSession(activeSessionId);
            if (!cancelled) {
              setSession(heartbeat);
            }
          } catch (caught) {
            if (!cancelled) {
              setError(getApiErrorMessage(caught));
            }
          }
        }, HEARTBEAT_INTERVAL_MS);
      } catch (caught) {
        if (!cancelled) {
          setError(getApiErrorMessage(caught));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void create();

    return () => {
      cancelled = true;
      if (heartbeatId) {
        window.clearInterval(heartbeatId);
      }
      if (activeSessionId) {
        void api.closeSession(activeSessionId);
      }
    };
  }, []);

  return {
    session,
    error,
    loading,
    setSession
  };
}
