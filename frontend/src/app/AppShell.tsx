import type { ReactNode } from "react";

import type { EngineSnapshot } from "../services/types";
import { Sidebar } from "../components/layout/Sidebar";

interface AppShellProps {
  route: "live" | "config" | "actions";
  onRouteChange: (route: "live" | "config" | "actions") => void;
  domainCount: number;
  actionCount: number;
  snapshot: EngineSnapshot | null;
  children: ReactNode;
}

export function AppShell({ route, onRouteChange, domainCount, actionCount, snapshot, children }: AppShellProps) {
  return (
    <div className="app-frame">
      <Sidebar route={route} onRouteChange={onRouteChange} domainCount={domainCount} actionCount={actionCount} />
      <div className="main-shell">
        <header className="top-bar">
          <div>
            <p className="eyebrow">Dashboard</p>
            <h2>Operator Surface</h2>
          </div>
          <div className="top-bar-meta">
            <span className="meta-chip">Revision {snapshot?.revision ?? "Unknown"}</span>
            <span className="meta-chip">{snapshot?.status ?? "offline"}</span>
          </div>
        </header>
        <main className="content-shell">{children}</main>
      </div>
    </div>
  );
}
