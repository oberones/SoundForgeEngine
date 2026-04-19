import type { ControlDefinition, ControlDomain, EngineSnapshot } from "../services/types";

export function getPathValue(source: Record<string, unknown>, path: string): unknown {
  const parts = path.split(".");
  let current: unknown = source;
  for (const part of parts) {
    if (current && typeof current === "object" && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return current;
}

export function mergeControlValue(control: ControlDefinition, snapshot: EngineSnapshot | null): ControlDefinition {
  if (!snapshot) {
    return control;
  }
  const fromConfig = getPathValue(snapshot.config_values, control.path);
  const fromState = control.path.startsWith("state.")
    ? getPathValue(snapshot.state_values, control.path.replace(/^state\./, ""))
    : undefined;
  const currentValue = fromState ?? fromConfig ?? control.current_value;
  return { ...control, current_value: currentValue };
}

export function mergeDomainValues(domains: ControlDomain[], snapshot: EngineSnapshot | null): ControlDomain[] {
  return domains.map((domain) => ({
    ...domain,
    controls: domain.controls.map((control) => mergeControlValue(control, snapshot))
  }));
}

export function coerceControlValue(control: ControlDefinition, rawValue: unknown): unknown {
  if (control.control_kind === "toggle") {
    return Boolean(rawValue);
  }

  if (control.control_kind === "collection" || control.control_kind === "mapping") {
    if (typeof rawValue === "string") {
      try {
        return JSON.parse(rawValue);
      } catch {
        return rawValue;
      }
    }
    return rawValue;
  }

  if (control.value_type === "integer") {
    return Number.parseInt(String(rawValue), 10);
  }
  if (control.value_type === "float" || control.value_type === "number") {
    return Number.parseFloat(String(rawValue));
  }
  return rawValue;
}

export function formatUptime(seconds?: number): string {
  if (!seconds && seconds !== 0) {
    return "Unknown";
  }
  const whole = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(whole / 3600);
  const mins = Math.floor((whole % 3600) / 60);
  const secs = whole % 60;
  if (hrs > 0) {
    return `${hrs}h ${mins}m ${secs}s`;
  }
  if (mins > 0) {
    return `${mins}m ${secs}s`;
  }
  return `${secs}s`;
}

export function controlIsExternallyChanged(path: string, changedPaths: string[]) {
  return changedPaths.includes(path);
}

export function isLiveControl(path: string): boolean {
  return [
    "sequencer.bpm",
    "sequencer.swing",
    "sequencer.density",
    "sequencer.direction_pattern",
    "sequencer.root_note",
    "sequencer.gate_length"
  ].includes(path);
}
