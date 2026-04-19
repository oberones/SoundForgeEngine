import { useEffect, useState } from "react";

import type { EngineSnapshot } from "../services/types";

export function useSnapshot(initialSnapshot: EngineSnapshot | null) {
  const [snapshot, setSnapshot] = useState<EngineSnapshot | null>(initialSnapshot);

  useEffect(() => {
    if (initialSnapshot) {
      setSnapshot((current) => current ?? initialSnapshot);
    }
  }, [initialSnapshot]);

  return {
    snapshot,
    setSnapshot
  };
}
