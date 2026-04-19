# Data Model: Control UI Dashboard

## Overview

The feature adds a UI-facing control model on top of the existing runtime config
and state models. These entities describe how the backend exposes dashboard
metadata, runtime snapshots, persistence state, and unsupported concurrent-use
warnings.

## Entities

### ControlDomain

Represents a user-facing grouping of related controls.

**Fields**
- `id`: stable slug such as `live-performance`, `sequencer`, `midi`, `idle`
- `title`: operator-facing label
- `description`: short help text for the group
- `sort_order`: integer ordering for UI layout
- `visibility`: `always` | `contextual`
- `sections`: ordered collection of nested subgroups or panels

**Validation**
- `id` must be unique across the catalog
- `sort_order` must be deterministic so the UI does not reorder between loads

### ControlDefinition

Describes one configurable or triggerable element shown in the dashboard.

**Fields**
- `id`: unique stable identifier
- `domain_id`: owning `ControlDomain`
- `path`: config path or action identifier
- `control_kind`: `scalar` | `toggle` | `enum` | `mapping` | `collection` | `action` | `readonly`
- `label`: operator-facing name
- `description`: help text
- `value_type`: `integer` | `float` | `string` | `boolean` | `object` | `array`
- `default_value`: baseline value if defined
- `current_value`: latest effective runtime value
- `constraints`: min/max/step/pattern/enum metadata
- `ui_hint`: preferred input presentation such as slider, segmented select, key-value editor, button, or badge
- `persist_behavior`: `session-only` | `persistable` | `readonly`
- `availability`: `available` | `unavailable` | `unsupported-context`
- `dirty_state`: `clean` | `dirty` | `conflicted`
- `last_changed_revision`: revision token for stale-change detection

**Validation**
- `path` must be unique when `control_kind` is not `action`
- `constraints` must match `value_type`
- `persist_behavior` cannot be `persistable` for values the backend cannot save

### ActionDefinition

Describes a command-style interaction exposed to the dashboard.

**Fields**
- `id`: stable semantic action identifier
- `label`: operator-facing action name
- `description`: action purpose
- `parameter_schema`: optional argument metadata
- `confirmation_required`: boolean
- `availability`: `available` | `unavailable` | `unsupported-context`
- `result_message_template`: success or warning copy hints

**Validation**
- `id` must be unique across actions
- `parameter_schema` is empty for parameterless actions

### EngineSnapshot

Represents the current runtime view consumed by the dashboard.

**Fields**
- `revision`: monotonically increasing token or version string
- `captured_at`: timestamp
- `status`: `running` | `degraded` | `unreachable`
- `uptime_seconds`: numeric uptime
- `config_values`: key/value map of effective config
- `state_values`: key/value map of live runtime state
- `changed_paths`: paths changed since the previous revision
- `messages`: list of `ValidationMessage`
- `active_session_id`: current UI session if any

**Validation**
- `revision` must advance whenever a UI-relevant value changes
- `changed_paths` must be empty only for full snapshots or no-op refreshes

### DashboardSession

Represents a browser dashboard instance for unsupported-concurrency detection.

**Fields**
- `session_id`: unique opaque identifier
- `created_at`: timestamp
- `last_heartbeat_at`: timestamp
- `status`: `active` | `expired` | `warning-only`
- `client_name`: optional operator-provided label
- `user_agent`: optional client metadata
- `mode`: `active-operator`
- `conflict_state`: `none` | `unsupported-concurrent-use`

**Validation**
- Only one session may be marked as the active operator at a time
- Expired sessions are ignored for active-use warnings after timeout

**State Transitions**
- `active` -> `warning-only` when another dashboard opens concurrently
- `active` -> `expired` when heartbeat timeout elapses
- `warning-only` -> `expired` when heartbeat timeout elapses

### PersistOperation

Represents an explicit save of supported config to disk.

**Fields**
- `operation_id`: unique identifier
- `requested_by_session_id`: optional `DashboardSession`
- `started_at`: timestamp
- `completed_at`: optional timestamp
- `target_path`: config file path
- `input_revision`: revision being persisted
- `result`: `pending` | `succeeded` | `failed`
- `message`: operator-facing summary

**Validation**
- `input_revision` must refer to a known snapshot
- `target_path` must resolve to the active runtime config path

### ValidationMessage

Structured feedback returned to the UI.

**Fields**
- `scope`: `global` | `domain` | `control`
- `level`: `info` | `warning` | `error`
- `code`: stable machine-readable identifier
- `text`: operator-facing message
- `affected_paths`: optional list of impacted config paths or action IDs

**Validation**
- `affected_paths` must be present for control-level conflicts
- `text` must be safe to render directly in the dashboard

## Relationships

- One `ControlDomain` has many `ControlDefinition` records.
- One `EngineSnapshot` references many `ControlDefinition.current_value` states.
- One `DashboardSession` may create many `PersistOperation` records.
- One `EngineSnapshot` may contain many `ValidationMessage` items.
- `ActionDefinition` records are exposed alongside `ControlDomain` catalog data
  but are not children of `ControlDefinition`.

## Derived Rules

- A dashboard edit becomes `dirty` once local value != latest effective value.
- A dashboard edit becomes `conflicted` when the same control receives a newer
  backend revision before the local dirty value is submitted.
- Persist actions are enabled only for `persistable` controls and only after
  the running session has no unresolved validation errors for the pending save.
