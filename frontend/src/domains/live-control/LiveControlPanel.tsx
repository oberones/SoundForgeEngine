import { useMemo, useState } from "react";

import { EnumEditor } from "../../components/editors/EnumEditor";
import { ScalarEditor } from "../../components/editors/ScalarEditor";
import type { ConfigUpdateResponse, ControlDefinition, EngineSnapshot } from "../../services/types";
import { controlIsExternallyChanged, coerceControlValue, getPathValue, isLiveControl } from "../../utils/controls";

interface LiveControlPanelProps {
  controls: ControlDefinition[];
  snapshot: EngineSnapshot | null;
  externalChanges: string[];
  onSubmit: (path: string, value: unknown) => Promise<ConfigUpdateResponse>;
}

export function LiveControlPanel({ controls, snapshot, externalChanges, onSubmit }: LiveControlPanelProps) {
  const liveControls = useMemo(
    () => controls.filter((control) => isLiveControl(control.path)).sort((left, right) => left.label.localeCompare(right.label)),
    [controls]
  );
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Live</p>
          <h2>Performance Controls</h2>
        </div>
        <p className="panel-copy">High-confidence controls for shaping the engine in the moment.</p>
      </div>
      <div className="control-grid">
        {liveControls.map((control) => {
          const currentValue = getPathValue(snapshot?.config_values ?? {}, control.path) ?? control.current_value;
          const value = drafts[control.path] ?? String(currentValue ?? "");
          const externallyChanged = controlIsExternallyChanged(control.path, externalChanges);
          return (
            <form
              key={control.id}
              className={externallyChanged ? "control-card external-change" : "control-card"}
              onSubmit={async (event) => {
                event.preventDefault();
                await onSubmit(control.path, coerceControlValue(control, value));
                setDrafts((current) => {
                  const next = { ...current };
                  delete next[control.path];
                  return next;
                });
              }}
            >
              <div className="control-card-header">
                <div>
                  <h3>{control.label}</h3>
                  <p>{control.description || control.path}</p>
                </div>
                {externallyChanged ? <span className="change-flag">external update</span> : null}
              </div>
              {control.control_kind === "enum" ? (
                <EnumEditor control={control} value={value} onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))} />
              ) : (
                <ScalarEditor
                  control={control}
                  value={value}
                  onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))}
                />
              )}
              <div className="control-card-footer">
                <span className="meta-label">Current: {String(currentValue ?? "unset")}</span>
                <button className="primary-button" type="submit">
                  Apply Live
                </button>
              </div>
            </form>
          );
        })}
      </div>
    </section>
  );
}
