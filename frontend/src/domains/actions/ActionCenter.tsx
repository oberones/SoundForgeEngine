import { useState } from "react";

import { ActionResultBanner } from "../../components/feedback/ActionResultBanner";
import type { ActionDefinition, ActionInvocationResponse, EngineSnapshot } from "../../services/types";

interface ActionCenterProps {
  actions: ActionDefinition[];
  snapshot: EngineSnapshot | null;
  feedbackState: { state: "idle" | "pending" | "success" | "error"; message?: string };
  onInvoke: (action: string, value?: string) => Promise<ActionInvocationResponse>;
}

export function ActionCenter({ actions, snapshot, feedbackState, onInvoke }: ActionCenterProps) {
  const [inputs, setInputs] = useState<Record<string, string>>({});

  return (
    <section className="panel action-center">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Actions</p>
          <h2>Semantic Workflows</h2>
        </div>
        <p className="panel-copy">Command-style interactions exposed through the same API surface as every other client.</p>
      </div>
      <ActionResultBanner feedback={feedbackState} />
      <div className="action-grid">
        {actions.map((action) => {
          const inputValue = inputs[action.id] ?? "";
          const requiresValue = Boolean(action.parameter_schema && Object.keys(action.parameter_schema).length > 0);
          const enumValues = Array.isArray(action.parameter_schema?.enum)
            ? (action.parameter_schema?.enum as string[])
            : null;

          return (
            <form
              key={action.id}
              className="action-card"
              onSubmit={async (event) => {
                event.preventDefault();
                await onInvoke(action.id, requiresValue ? inputValue : undefined);
              }}
            >
              <div className="control-card-header">
                <div>
                  <h3>{action.label}</h3>
                  <p>{action.description}</p>
                </div>
                {action.confirmation_required ? <span className="change-flag">confirm first</span> : null}
              </div>
              {requiresValue ? (
                enumValues ? (
                  <select
                    className="control-input"
                    value={inputValue}
                    onChange={(event) => setInputs((current) => ({ ...current, [action.id]: event.target.value }))}
                  >
                    <option value="">Select a value</option>
                    {enumValues.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    className="control-input"
                    value={inputValue}
                    onChange={(event) => setInputs((current) => ({ ...current, [action.id]: event.target.value }))}
                    placeholder="Optional action value"
                  />
                )
              ) : (
                <p className="quiet-copy">No additional parameters are required for this action.</p>
              )}
              <div className="control-card-footer">
                <span className="meta-label">Revision: {snapshot?.revision ?? "Unknown"}</span>
                <button className="secondary-button" type="submit">
                  Run Action
                </button>
              </div>
            </form>
          );
        })}
      </div>
    </section>
  );
}
