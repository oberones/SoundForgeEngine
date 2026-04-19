# Research: Control UI Dashboard

## Decision: Keep one Python control service and extend the existing FastAPI app

**Decision**: Build the dashboard backend features into the existing FastAPI
service instead of creating a separate control backend.

**Rationale**:
- The current project already exposes runtime control through `src/api_server.py`
  and starts that service from the main engine lifecycle.
- A single service keeps deployment simple on Raspberry Pi and avoids syncing
  state between multiple backend processes.
- The feature requires full parity with the application control interface, so
  extending the current control surface is lower-risk than introducing a second
  source of truth.

**Alternatives considered**:
- A separate backend-for-frontend service: rejected because it adds deployment,
  state synchronization, and operational overhead for a single-instance LAN app.
- A frontend that reads files directly: rejected because it breaks API parity
  and bypasses runtime validation/state behavior.

## Decision: Use a dedicated frontend workspace with a typed SPA

**Decision**: Implement the operator dashboard as a TypeScript React SPA in a
new `frontend/` workspace and serve built assets from the existing FastAPI app.

**Rationale**:
- The UI must support rich, domain-grouped controls, stale-value highlighting,
  overwrite warnings, and generic editors for arbitrarily shaped config.
- A typed component model is easier to maintain than handcrafted imperative DOM
  code for dozens of controls across many configuration domains.
- Serving the built assets from FastAPI preserves a single deployable artifact
  in production while still allowing fast frontend iteration in development.

**Alternatives considered**:
- Vanilla JavaScript: rejected because the metadata-driven form complexity and
  state synchronization requirements would become harder to maintain.
- Server-rendered templates/HTMX: rejected because the dashboard needs
  long-lived client state for dirty fields, stale conflict warnings, and
  responsive live-control interactions.

## Decision: Add a dedicated UI bootstrap/catalog contract instead of teaching the UI to assemble itself from raw schema endpoints

**Decision**: Add a UI-specific bootstrap contract that returns control domains,
action metadata, persistence capabilities, session policy, and the latest engine
snapshot in one response.

**Rationale**:
- The existing `/config/schema`, `/config/mappings`, `/config`, and `/state`
  endpoints are useful primitives, but they do not describe UI grouping,
  display hints, supported actions, persistence affordances, or session policy.
- The dashboard needs a consistent, API-driven control catalog for both custom
  controls and generic fallbacks.
- A dedicated bootstrap contract preserves parity while keeping presentation
  metadata explicit and versionable.

**Alternatives considered**:
- Build the UI directly on `/config/mappings` and `/config/schema`: rejected
  because the current metadata is too low-level for a polished, complete UI.
- Hardcode every control in the frontend: rejected because it would drift from
  the control surface and make future config additions expensive.

## Decision: Use revision-aware polling instead of WebSockets/SSE for v1 sync

**Decision**: Synchronize the dashboard with the running engine using
revision-aware polling and delta snapshots rather than introducing persistent
streaming channels in the first release.

**Rationale**:
- The clarified scope is a trusted LAN UI with one active operator, so polling
  is sufficient and simpler to reason about operationally.
- Revision tokens and delta responses are enough to highlight external changes
  and protect dirty fields from accidental overwrite.
- Polling keeps the backend implementation straightforward and avoids adding
  event-stream state management to the existing API server.

**Alternatives considered**:
- WebSockets: rejected because the scope does not require collaborative
  real-time editing and the added complexity is not justified.
- Server-Sent Events: rejected because it still adds a second sync mode when
  polling can satisfy the current latency target.
- Manual refresh only: rejected because it contradicts the clarified stale-data
  behavior.

## Decision: Separate live apply from explicit persistence

**Decision**: Treat runtime edits and persisted saves as distinct operations.
Config edits apply to the running session immediately, and a separate explicit
persist action writes supported settings back to the active config file.

**Rationale**:
- This matches the clarification decisions and reduces the risk of accidental
  permanent changes during live operation.
- The backend can validate persisted writes atomically and report save status
  independently from live-apply success.
- The UI can show unsaved-versus-active differences clearly.

**Alternatives considered**:
- Autosave every edit: rejected because it is too risky for live performance.
- Session-only changes with no persistence: rejected because the feature needs
  supported save workflows.

## Decision: Represent unsupported concurrent use with a lightweight session lease

**Decision**: Introduce a small UI session registry with create/heartbeat/expire
behavior so the system can detect when a second dashboard is opened and present
the clarified “unsupported concurrent active operation” warning.

**Rationale**:
- The feature explicitly requires one active operator at a time and a clear UI
  indication when that assumption is broken.
- A lease model satisfies that requirement without adding authentication or
  collaborative locking.
- The same session identity can scope heartbeat logs and persist operations.

**Alternatives considered**:
- Ignore concurrent dashboards entirely: rejected because it would not satisfy
  the clarified spec.
- Enforce a hard editing lock: rejected because the clarification only requires
  unsupported-use signaling, not a full concurrency-control system.
- Add user accounts/roles: rejected because the first release explicitly avoids
  in-app authentication.

## Decision: Test the feature across backend contracts, frontend behavior, and browser workflows

**Decision**: Use pytest for backend unit/contract/integration tests, Vitest for
frontend component behavior, and Playwright for end-to-end dashboard workflows.

**Rationale**:
- The constitution requires tests for new behavior and a clear user journey.
- The backend changes are contract-heavy and benefit from direct API coverage.
- The frontend needs browser-level verification for stale updates, persistence,
  operator conflict warnings, and responsive control flows.

**Alternatives considered**:
- Manual QA only: rejected because it does not satisfy the constitution.
- Backend-only automated tests: rejected because the primary user value is in
  the UI workflow.
