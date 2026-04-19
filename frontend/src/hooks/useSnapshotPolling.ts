import { useEffect } from "react";

import { api } from "../services/api";
import type { EngineSnapshot } from "../services/types";

const POLL_INTERVAL_MS = 1_000;

interface SnapshotPollingOptions {
  enabled: boolean;
  revision?: string;
  onSnapshot: (snapshot: EngineSnapshot) => void;
}

export function useSnapshotPolling({ enabled, revision, onSnapshot }: SnapshotPollingOptions) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const payload = await api.snapshot(revision);
        onSnapshot(payload.snapshot);
      } catch {
        // Leave error presentation to the calling routes; background polling
        // should stay quiet unless the main fetch path also fails.
      }
    }, POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [enabled, onSnapshot, revision]);
}
