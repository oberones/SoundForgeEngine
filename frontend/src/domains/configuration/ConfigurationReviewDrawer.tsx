import type { ControlDomain, MutationFeedback } from "../../services/types";
import { StatusBanner } from "../../components/feedback/StatusBanner";

interface ConfigurationReviewDrawerProps {
  domains: ControlDomain[];
  onPersist: () => Promise<unknown>;
  persistFeedback: MutationFeedback;
}

export function ConfigurationReviewDrawer({ domains, onPersist, persistFeedback }: ConfigurationReviewDrawerProps) {
  const totalControls = domains.reduce((sum, domain) => sum + domain.controls.length, 0);
  const dirtyControls = domains.flatMap((domain) => domain.controls).filter((control) => control.dirty_state === "dirty");

  return (
    <aside className="review-drawer panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Review</p>
          <h2>Persist Changes</h2>
        </div>
      </div>
      <p className="panel-copy">
        The running engine applies edits immediately. Use the explicit save action below when you want those changes to
        become the new default configuration.
      </p>
      <div className="review-metrics">
        <div>
          <span className="meta-label">Visible controls</span>
          <strong>{totalControls}</strong>
        </div>
        <div>
          <span className="meta-label">Differs from saved</span>
          <strong>{dirtyControls.length}</strong>
        </div>
      </div>
      <StatusBanner feedback={persistFeedback} />
      <button className="primary-button persist-button" onClick={() => void onPersist()} type="button">
        Save Supported Settings
      </button>
      {dirtyControls.length > 0 ? (
        <ul className="dirty-list">
          {dirtyControls.slice(0, 8).map((control) => (
            <li key={control.id}>
              <strong>{control.label}</strong>
              <span>{control.path}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="quiet-copy">The current runtime config matches the saved file for persistable settings.</p>
      )}
    </aside>
  );
}
