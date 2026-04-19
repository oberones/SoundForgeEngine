export type ControlKind =
  | "scalar"
  | "toggle"
  | "enum"
  | "mapping"
  | "collection"
  | "action"
  | "readonly";

export interface ControlDefinition {
  id: string;
  path: string;
  control_kind: ControlKind;
  label: string;
  description?: string;
  value_type: string;
  current_value: unknown;
  default_value: unknown;
  constraints: Record<string, unknown>;
  ui_hint?: string;
  availability: "available" | "unavailable" | "unsupported-context";
  persist_behavior: "session-only" | "persistable" | "readonly";
  revision: string;
  dirty_state: "clean" | "dirty" | "conflicted";
}

export interface ControlDomain {
  id: string;
  title: string;
  description?: string;
  sort_order: number;
  controls: ControlDefinition[];
}

export interface ActionDefinition {
  id: string;
  label: string;
  description?: string;
  confirmation_required?: boolean;
  availability: "available" | "unavailable" | "unsupported-context";
  parameter_schema?: Record<string, unknown>;
  result_message_template?: string;
}

export interface EngineSnapshot {
  revision: string;
  captured_at: string;
  status: "running" | "degraded" | "unreachable";
  uptime_seconds?: number;
  config_values: Record<string, unknown>;
  state_values: Record<string, unknown>;
  changed_paths: string[];
  messages: ValidationMessage[];
  active_session_id?: string | null;
}

export interface ValidationMessage {
  scope: "global" | "domain" | "control";
  level: "info" | "warning" | "error";
  code: string;
  text: string;
  affected_paths?: string[];
}

export interface SessionPolicy {
  authentication: "none";
  concurrency_mode: "single-active-operator";
  heartbeat_timeout_seconds: number;
}

export interface BootstrapResponse {
  snapshot: EngineSnapshot;
  domains: ControlDomain[];
  actions: ActionDefinition[];
  session_policy: SessionPolicy;
  persistence: {
    mode: "apply-live-then-explicit-save";
    supported: boolean;
  };
}

export interface SessionResponse {
  session_id: string;
  status: "active" | "expired" | "warning-only";
  conflict_state: "none" | "unsupported-concurrent-use";
  active_session_id?: string | null;
}

export interface ConfigUpdateRequest {
  path: string;
  value: unknown;
  apply_immediately?: boolean;
  expected_revision?: string | null;
  session_id?: string | null;
}

export interface ConfigUpdateResponse {
  success: boolean;
  message: string;
  old_value?: unknown;
  new_value?: unknown;
  applied_to_state: boolean;
  revision: string;
  persisted: boolean;
}

export interface PersistResponse {
  result: "succeeded" | "failed";
  message: string;
  target_path: string;
  persisted_revision?: string;
}

export interface SnapshotResponse {
  snapshot: EngineSnapshot;
}

export interface ActionCatalogResponse {
  actions: ActionDefinition[];
}

export interface ActionInvocationResponse {
  message: string;
  revision?: string;
}

export interface ConflictResponse {
  detail: string;
  current_revision: string;
  current_value: unknown;
  affected_path: string;
}

export interface MutationFeedback {
  state: "idle" | "pending" | "success" | "error";
  message?: string;
}
