# Implementation Plan: Control UI Dashboard

**Branch**: `001-control-ui-dashboard` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-control-ui-dashboard/spec.md`

## Summary

Build a full control dashboard for SoundForgeEngine by extending the existing
FastAPI control service with a metadata-driven UI backend layer and adding a
dedicated frontend workspace for a responsive operator dashboard. The plan keeps
one deployable Python service, serves built UI assets from the existing API
server, adds revision-aware snapshot and persistence workflows, and introduces
lightweight session tracking so the UI can warn about unsupported concurrent
operators without changing the clarified first-release scope.

## Technical Context

**Language/Version**: Python 3.11 backend; TypeScript 5.x frontend  
**Primary Dependencies**: FastAPI, Pydantic, Uvicorn, React, Vite, TanStack Query  
**Storage**: Existing YAML config file, in-memory runtime state, ephemeral UI session registry  
**Testing**: pytest with FastAPI/TestClient for backend contract and integration tests; Vitest + Testing Library for frontend unit tests; Playwright for browser workflow coverage  
**Target Platform**: Raspberry Pi-hosted Linux service accessed from modern desktop and tablet browsers on trusted local/LAN networks  
**Project Type**: Web application layered onto the existing Python control service  
**Performance Goals**: Visible UI feedback within 250 ms locally; snapshot refresh cadence fast enough to surface external changes within 1 s; no regression to existing engine goals of sub-10 ms perceptual button response and under 2 ms sequencer tick jitter  
**Constraints**: One active operator at a time, no in-app authentication, edits apply live by default with separate explicit persistence, responsive desktop/tablet layouts, metadata-driven full config coverage, Python work stays in `.venv`, timing-sensitive code paths must remain non-blocking  
**Scale/Scope**: Single engine instance, ~10 control domains, dozens of config fields plus supported semantic actions, one active dashboard session, trusted operator environment only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code quality approach**: PASS. Backend work is isolated to API and UI-support
  modules adjacent to `src/api_server.py`; frontend work lives in a dedicated
  `frontend/` workspace so engine sequencing logic remains untouched except for
  clearly scoped integration points.
- **Test plan**: PASS. Backend gets unit, contract, and integration coverage for
  metadata, persistence, session, and revision behavior; frontend gets unit and
  browser-level workflow coverage for live control, stale updates, and
  persistence flows.
- **User experience consistency**: PASS. The dashboard uses the existing
  terminology from config, semantic actions, and docs/reference; live controls,
  advanced configuration, status states, and warnings follow one shared
  interaction model.
- **Performance impact**: PASS. UI synchronization uses revision-aware polling
  and dedicated API-side bookkeeping so no blocking work is introduced into the
  timing-critical sequencer and MIDI paths.
- **Observability updates**: PASS. The design includes structured logs for UI
  session lifecycle, config persistence, stale-write warnings, and API metadata
  generation, plus quickstart coverage for operator workflows.

**Post-Design Check**: PASS. Research, data model, contracts, and quickstart
all preserve the constitution requirements without requiring any explicit
exception or waiver.

## Project Structure

### Documentation (this feature)

```text
specs/001-control-ui-dashboard/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── control-surface-api.yaml
```

### Source Code (repository root)

```text
src/
├── api_server.py
├── config.py
├── main.py
├── state.py
├── ui_catalog.py
├── ui_persistence.py
├── ui_sessions.py
└── ui_snapshot.py

frontend/
├── package.json
├── vite.config.ts
├── src/
│   ├── app/
│   ├── components/
│   ├── domains/
│   ├── hooks/
│   ├── routes/
│   ├── services/
│   └── styles/
└── tests/
    ├── e2e/
    └── unit/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep the existing Python backend in `src/` and add a
new `frontend/` workspace for the control dashboard. This avoids a backend
relayout while giving the UI its own build/test boundary. Python API contract
and integration tests stay under the existing `tests/` hierarchy, while browser
and component tests live with the frontend workspace.

## Complexity Tracking

No constitution check violations identified.
