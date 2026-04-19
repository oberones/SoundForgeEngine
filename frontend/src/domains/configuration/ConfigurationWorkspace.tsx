import { useMemo, useState } from "react";

import { CollectionEditor } from "../../components/editors/CollectionEditor";
import { EnumEditor } from "../../components/editors/EnumEditor";
import { GenericJsonEditor } from "../../components/editors/GenericJsonEditor";
import { MappingEditor } from "../../components/editors/MappingEditor";
import { ScalarEditor } from "../../components/editors/ScalarEditor";
import { ToggleEditor } from "../../components/editors/ToggleEditor";
import { PersistStateBadge } from "../../components/feedback/PersistStateBadge";
import type { ConfigUpdateResponse, ControlDefinition, ControlDomain } from "../../services/types";
import { coerceControlValue, controlIsExternallyChanged } from "../../utils/controls";

interface ConfigurationWorkspaceProps {
  domains: ControlDomain[];
  externalChanges: string[];
  onSubmit: (path: string, value: unknown) => Promise<ConfigUpdateResponse>;
}

function formatDraft(control: ControlDefinition): string {
  if (typeof control.current_value === "string") {
    return control.current_value;
  }
  if (control.control_kind === "mapping" || control.control_kind === "collection") {
    return JSON.stringify(control.current_value ?? (control.control_kind === "mapping" ? {} : []), null, 2);
  }
  if (control.current_value === undefined || control.current_value === null) {
    return "";
  }
  return String(control.current_value);
}

export function ConfigurationWorkspace({ domains, externalChanges, onSubmit }: ConfigurationWorkspaceProps) {
  const [selectedDomainId, setSelectedDomainId] = useState<string>(domains[0]?.id ?? "");
  const [drafts, setDrafts] = useState<Record<string, string | boolean>>({});

  const selectedDomain = useMemo(
    () => domains.find((domain) => domain.id === selectedDomainId) ?? domains[0],
    [domains, selectedDomainId]
  );

  return (
    <section className="panel configuration-workspace">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Configuration</p>
          <h2>All Control Domains</h2>
        </div>
        <p className="panel-copy">Every config group the backend exposes, with a structured editor and a generic fallback.</p>
      </div>

      <div className="domain-tabs" role="tablist" aria-label="Configuration domains">
        {domains.map((domain) => (
          <button
            key={domain.id}
            className={domain.id === selectedDomain?.id ? "domain-tab active" : "domain-tab"}
            onClick={() => setSelectedDomainId(domain.id)}
            role="tab"
            type="button"
          >
            {domain.title}
          </button>
        ))}
      </div>

      {selectedDomain ? (
        <div className="domain-panel">
          <header className="domain-panel-header">
            <div>
              <h3>{selectedDomain.title}</h3>
              <p>{selectedDomain.description}</p>
            </div>
          </header>
          <div className="config-card-list">
            {selectedDomain.controls.map((control) => {
              const draftValue = drafts[control.path];
              const serializedValue =
                draftValue !== undefined && typeof draftValue !== "boolean" ? String(draftValue) : formatDraft(control);
              const externallyChanged = controlIsExternallyChanged(control.path, externalChanges);

              return (
                <form
                  key={control.id}
                  className={externallyChanged ? "config-card external-change" : "config-card"}
                  onSubmit={async (event) => {
                    event.preventDefault();
                    const nextValue =
                      draftValue === undefined ? control.current_value : coerceControlValue(control, draftValue);
                    await onSubmit(control.path, nextValue);
                    setDrafts((current) => {
                      const next = { ...current };
                      delete next[control.path];
                      return next;
                    });
                  }}
                >
                  <div className="control-card-header">
                    <div>
                      <h4>{control.label}</h4>
                      <p>{control.description || control.path}</p>
                    </div>
                    <PersistStateBadge control={control} />
                  </div>
                  {externallyChanged ? <p className="inline-warning">Value changed outside the dashboard.</p> : null}
                  {control.control_kind === "toggle" ? (
                    <ToggleEditor
                      value={Boolean(draftValue ?? control.current_value)}
                      onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))}
                    />
                  ) : control.control_kind === "enum" ? (
                    <EnumEditor
                      control={control}
                      value={serializedValue}
                      onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))}
                    />
                  ) : control.control_kind === "collection" ? (
                    <CollectionEditor
                      value={serializedValue}
                      onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))}
                    />
                  ) : control.control_kind === "mapping" ? (
                    <MappingEditor
                      value={serializedValue}
                      onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))}
                    />
                  ) : control.control_kind === "scalar" ? (
                    <ScalarEditor
                      control={control}
                      value={serializedValue}
                      onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))}
                    />
                  ) : (
                    <GenericJsonEditor
                      value={serializedValue}
                      onChange={(next) => setDrafts((current) => ({ ...current, [control.path]: next }))}
                    />
                  )}
                  <div className="control-card-footer">
                    <span className="meta-label">{control.path}</span>
                    <button className="secondary-button" type="submit">
                      Apply
                    </button>
                  </div>
                </form>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
