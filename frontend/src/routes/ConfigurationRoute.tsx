import { StatusBanner } from "../components/feedback/StatusBanner";
import type { ConfigUpdateResponse, ControlDomain, MutationFeedback } from "../services/types";
import { ConfigurationReviewDrawer } from "../domains/configuration/ConfigurationReviewDrawer";
import { ConfigurationWorkspace } from "../domains/configuration/ConfigurationWorkspace";
import { TrustedNetworkNotice } from "../domains/settings/TrustedNetworkNotice";

interface ConfigurationRouteProps {
  domains: ControlDomain[];
  externalChanges: string[];
  configFeedback: MutationFeedback;
  persistFeedback: MutationFeedback;
  onSubmit: (path: string, value: unknown) => Promise<ConfigUpdateResponse>;
  onPersist: () => Promise<unknown>;
}

export function ConfigurationRoute({
  domains,
  externalChanges,
  configFeedback,
  persistFeedback,
  onSubmit,
  onPersist
}: ConfigurationRouteProps) {
  return (
    <div className="route-grid">
      <div className="route-stack">
        <TrustedNetworkNotice />
        <StatusBanner feedback={configFeedback} />
        <ConfigurationWorkspace domains={domains} externalChanges={externalChanges} onSubmit={onSubmit} />
      </div>
      <ConfigurationReviewDrawer domains={domains} onPersist={onPersist} persistFeedback={persistFeedback} />
    </div>
  );
}
