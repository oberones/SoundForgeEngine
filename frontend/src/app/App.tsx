import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "./AppShell";
import { useActionCatalog } from "../hooks/useActionCatalog";
import { useActionInvocation } from "../hooks/useActionInvocation";
import { useBootstrap } from "../hooks/useBootstrap";
import { useConflictAwareMutation } from "../hooks/useConflictAwareMutation";
import { usePersistConfig } from "../hooks/usePersistConfig";
import { useSession } from "../hooks/useSession";
import { useSnapshot } from "../hooks/useSnapshot";
import { useSnapshotPolling } from "../hooks/useSnapshotPolling";
import { ActionCenter } from "../domains/actions/ActionCenter";
import { ConfigurationRoute } from "../routes/ConfigurationRoute";
import { LiveDashboardRoute } from "../routes/LiveDashboardRoute";
import { StatusBanner } from "../components/feedback/StatusBanner";
import { mergeDomainValues } from "../utils/controls";

export default function App() {
  const [route, setRoute] = useState<"live" | "config" | "actions">("live");
  const [externalChanges, setExternalChanges] = useState<string[]>([]);
  const { bootstrap, loading: bootstrapLoading, error: bootstrapError, refetch } = useBootstrap();
  const { session, error: sessionError } = useSession();
  const { snapshot, setSnapshot } = useSnapshot(bootstrap?.snapshot ?? null);
  const { actions } = useActionCatalog(bootstrap?.actions ?? []);

  useEffect(() => {
    if (bootstrap?.snapshot) {
      setSnapshot(bootstrap.snapshot);
    }
  }, [bootstrap, setSnapshot]);

  const mergedDomains = useMemo(() => mergeDomainValues(bootstrap?.domains ?? [], snapshot), [bootstrap?.domains, snapshot]);
  const liveControls = useMemo(() => mergedDomains.flatMap((domain) => domain.controls), [mergedDomains]);

  const refreshBootstrap = useCallback(async () => {
    const payload = await refetch();
    setSnapshot(payload.snapshot);
    if (payload.snapshot.changed_paths.length > 0) {
      setExternalChanges((current) => Array.from(new Set([...current, ...payload.snapshot.changed_paths])));
    }
  }, [refetch, setSnapshot]);

  const configMutation = useConflictAwareMutation({
    revision: snapshot?.revision,
    sessionId: session?.session_id,
    onSuccess: async () => {
      await refreshBootstrap();
    }
  });

  const persistMutation = usePersistConfig({
    revision: snapshot?.revision,
    sessionId: session?.session_id,
    onSuccess: async () => {
      await refreshBootstrap();
    }
  });

  const actionMutation = useActionInvocation(async () => {
    await refreshBootstrap();
  });

  useSnapshotPolling({
    enabled: Boolean(session),
    revision: snapshot?.revision,
    onSnapshot: (nextSnapshot) => {
      setSnapshot(nextSnapshot);
      if (nextSnapshot.changed_paths.length > 0) {
        setExternalChanges((current) => Array.from(new Set([...current, ...nextSnapshot.changed_paths])));
      }
    }
  });

  if (bootstrapLoading && !bootstrap) {
    return (
      <main className="loading-screen">
        <p className="eyebrow">SoundForgeEngine</p>
        <h1>Loading control surface…</h1>
      </main>
    );
  }

  if (!bootstrap) {
    return (
      <main className="loading-screen">
        <h1>Dashboard unavailable</h1>
        <p>{bootstrapError ?? sessionError ?? "The dashboard could not load its bootstrap payload."}</p>
      </main>
    );
  }

  return (
    <AppShell
      route={route}
      onRouteChange={setRoute}
      domainCount={mergedDomains.length}
      actionCount={actions.length}
      snapshot={snapshot}
    >
      {bootstrapError || sessionError ? (
        <StatusBanner feedback={{ state: "error", message: bootstrapError ?? sessionError ?? undefined }} />
      ) : null}

      {route === "live" ? (
        <LiveDashboardRoute
          controls={liveControls}
          snapshot={snapshot}
          session={session}
          externalChanges={externalChanges}
          feedback={configMutation.feedback}
          onSubmit={configMutation.mutate}
        />
      ) : null}

      {route === "config" ? (
        <ConfigurationRoute
          domains={mergedDomains}
          externalChanges={externalChanges}
          configFeedback={configMutation.feedback}
          persistFeedback={persistMutation.feedback}
          onSubmit={configMutation.mutate}
          onPersist={persistMutation.persist}
        />
      ) : null}

      {route === "actions" ? (
        <ActionCenter
          actions={actions}
          snapshot={snapshot}
          feedbackState={actionMutation.feedback}
          onInvoke={actionMutation.invoke}
        />
      ) : null}
    </AppShell>
  );
}
