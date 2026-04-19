---

description: "Task list for Control UI Dashboard implementation"
---

# Tasks: Control UI Dashboard

**Input**: Design documents from `/specs/001-control-ui-dashboard/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks are required for every behavior change, bug fix, or new
feature. Include the narrowest useful mix of unit, integration, and contract
coverage needed to satisfy the constitution.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `src/` for the Python control service, `frontend/src/` for the
  dashboard application, `tests/` for backend tests, `frontend/tests/` for UI
  tests
- Paths below assume the structure captured in `plan.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the new dashboard workspace and test tooling

- [ ] T001 Create the frontend workspace manifest and build scripts in `frontend/package.json`, `frontend/tsconfig.json`, and `frontend/vite.config.ts`
- [ ] T002 [P] Create the frontend entrypoints and base directories in `frontend/src/main.tsx`, `frontend/src/app/App.tsx`, and `frontend/src/styles/index.css`
- [ ] T003 [P] Configure frontend test runners in `frontend/vitest.config.ts`, `frontend/playwright.config.ts`, `frontend/tests/unit/.gitkeep`, and `frontend/tests/e2e/.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core dashboard infrastructure that MUST be complete before ANY
user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create UI catalog builders and shared metadata models in `src/ui_catalog.py`
- [ ] T005 [P] Create revision-aware runtime snapshot support in `src/ui_snapshot.py`
- [ ] T006 [P] Create dashboard session lease tracking in `src/ui_sessions.py`
- [ ] T007 [P] Create explicit config persistence support in `src/ui_persistence.py`
- [ ] T008 Extend the control backend routes and static asset serving in `src/api_server.py` and `src/main.py`
- [ ] T009 [P] Create shared frontend API types and request clients in `frontend/src/services/types.ts` and `frontend/src/services/api.ts`
- [ ] T010 [P] Create shared frontend data hooks in `frontend/src/hooks/useBootstrap.ts`, `frontend/src/hooks/useSnapshot.ts`, and `frontend/src/hooks/useSession.ts`
- [ ] T011 [P] Create the shared dashboard shell and design tokens in `frontend/src/app/AppShell.tsx`, `frontend/src/components/layout/Sidebar.tsx`, and `frontend/src/styles/tokens.css`
- [ ] T012 Configure backend unit test scaffolding for UI support modules in `tests/unit/test_ui_catalog.py`, `tests/unit/test_ui_snapshot.py`, `tests/unit/test_ui_sessions.py`, and `tests/unit/test_ui_persistence.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Operate the Engine Live (Priority: P1) 🎯 MVP

**Goal**: Deliver a polished live dashboard that shows engine status and lets
operators change core musical controls safely during active use

**Independent Test**: Open the dashboard, confirm status and current values
load, change tempo/swing/density/direction/root note, verify the running
engine and UI feedback update correctly without leaving the dashboard, and
confirm a second dashboard receives the unsupported-concurrency warning

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Add the bootstrap, session policy, and single-operator warning contract test in `tests/contract/test_control_surface_bootstrap_api.py`
- [ ] T014 [P] [US1] Add the live-control and second-dashboard session integration test in `tests/integration/test_control_dashboard_live_control.py`
- [ ] T015 [P] [US1] Add the live dashboard and concurrent-operator notice component test in `frontend/tests/unit/live-control-panel.test.tsx`

### Implementation for User Story 1

- [ ] T016 [P] [US1] Implement live-control snapshot shaping and single-operator session warning responses in `src/api_server.py`, `src/ui_snapshot.py`, and `src/ui_sessions.py`
- [ ] T017 [P] [US1] Build the live status, control panel, and concurrent-operator notice components in `frontend/src/domains/live-control/EngineStatusCard.tsx`, `frontend/src/domains/live-control/LiveControlPanel.tsx`, and `frontend/src/components/feedback/ConcurrentOperatorNotice.tsx`
- [ ] T018 [US1] Wire the live dashboard route and live-control mutations in `frontend/src/routes/LiveDashboardRoute.tsx` and `frontend/src/hooks/useLiveControls.ts`
- [ ] T019 [US1] Add pending/success/error/unavailable feedback UI and unsupported-session messaging in `frontend/src/components/feedback/StatusBanner.tsx` and `frontend/src/domains/live-control/ControlMutationState.tsx`
- [ ] T020 [US1] Add browser workflow coverage for dashboard load, core parameter edits, and second-dashboard warnings in `frontend/tests/e2e/live-control.spec.ts`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Configure Every Available Control Surface (Priority: P2)

**Goal**: Expose every configuration domain through structured controls and a
generic fallback editor, with explicit save support for persistable settings

**Independent Test**: Browse every configuration domain in the dashboard, edit
representative settings across all groups, confirm unsupported shapes still use
a generic editor, verify live apply plus explicit save behavior end-to-end, and
confirm external changes are highlighted before an overwrite is allowed

### Tests for User Story 2 ⚠️

- [ ] T021 [P] [US2] Add the control catalog and persistence contract test in `tests/contract/test_control_catalog_api.py`
- [ ] T022 [P] [US2] Add the apply-live, explicit-persist, and stale-write protection integration test in `tests/integration/test_control_dashboard_persistence.py`
- [ ] T023 [P] [US2] Add the configuration workspace, stale-highlight, and overwrite-warning component test in `frontend/tests/unit/config-workspace.test.tsx`

### Implementation for User Story 2

- [ ] T024 [P] [US2] Extend the control catalog to cover every config domain in `src/ui_catalog.py` and `src/config.py`
- [ ] T025 [P] [US2] Implement the explicit persistence endpoint, revision-conflict responses, and safe YAML writes in `src/api_server.py` and `src/ui_persistence.py`
- [ ] T026 [P] [US2] Build the configuration route and workspace container in `frontend/src/routes/ConfigurationRoute.tsx` and `frontend/src/domains/configuration/ConfigurationWorkspace.tsx`
- [ ] T027 [P] [US2] Build the editor set and persist indicators in `frontend/src/components/editors/ToggleEditor.tsx`, `frontend/src/components/editors/ScalarEditor.tsx`, `frontend/src/components/editors/EnumEditor.tsx`, `frontend/src/components/editors/CollectionEditor.tsx`, `frontend/src/components/editors/MappingEditor.tsx`, `frontend/src/components/editors/GenericJsonEditor.tsx`, and `frontend/src/components/feedback/PersistStateBadge.tsx`
- [ ] T028 [US2] Wire explicit save actions, automatic snapshot refresh, stale-field highlighting, overwrite warnings, conflict-aware config mutations, and review-mode UX in `frontend/src/hooks/usePersistConfig.ts`, `frontend/src/hooks/useSnapshotPolling.ts`, `frontend/src/hooks/useConflictAwareMutation.ts`, and `frontend/src/domains/configuration/ConfigurationReviewDrawer.tsx`
- [ ] T029 [US2] Add browser workflow coverage for config browsing, explicit persistence, stale value highlighting, and overwrite warnings in `frontend/tests/e2e/configuration-workspace.spec.ts`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Drive the Application Through One Control Contract (Priority: P3)

**Goal**: Preserve one API-driven control contract by adding supported action
catalogs and proving that dashboard-triggered workflows use the same backend
surface as automation and other control clients

**Independent Test**: Trigger supported semantic actions from the UI, confirm
the same tasks are available through the backend contract, and verify action
results update the state view without any UI-only shortcut behavior

### Tests for User Story 3 ⚠️

- [ ] T030 [P] [US3] Add the action catalog and contract-parity test in `tests/contract/test_control_contract_api.py`
- [ ] T031 [P] [US3] Add the action invocation and parity integration test in `tests/integration/test_control_dashboard_actions.py`
- [ ] T032 [P] [US3] Add the action center and contract-driven rendering component test in `frontend/tests/unit/control-contract-parity.test.tsx`

### Implementation for User Story 3

- [ ] T033 [US3] Implement the action catalog and action-invocation parity responses in `src/api_server.py` and `src/ui_catalog.py`
- [ ] T034 [P] [US3] Build the action center and action feedback components in `frontend/src/domains/actions/ActionCenter.tsx` and `frontend/src/components/feedback/ActionResultBanner.tsx`
- [ ] T035 [US3] Wire action catalog loading and invocation hooks in `frontend/src/hooks/useActionCatalog.ts` and `frontend/src/hooks/useActionInvocation.ts`
- [ ] T036 [US3] Add browser workflow coverage for actions and control-contract parity in `frontend/tests/e2e/control-contract-parity.spec.ts`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T037 [P] Update operator-facing documentation in `README.md` and `docs/API_DOCUMENTATION.md`
- [ ] T038 Refactor shared dashboard and backend code for clarity in `src/api_server.py` and `frontend/src/app/App.tsx`
- [ ] T039 Add performance validation coverage and notes in `tests/integration/test_control_dashboard_performance.py` and `specs/001-control-ui-dashboard/quickstart.md`
- [ ] T040 [P] Add extra shared-state unit coverage in `tests/unit/test_ui_snapshot.py` and `frontend/tests/unit/session-state.test.tsx`
- [ ] T041 Harden trusted-LAN exposure messaging in `src/api_server.py` and `frontend/src/domains/settings/TrustedNetworkNotice.tsx`
- [ ] T042 Review and tune UX consistency across the dashboard in `frontend/src/styles/index.css` and `frontend/src/app/AppShell.tsx`
- [ ] T043 Add observability for dashboard sessions, persistence, and conflicts in `src/api_server.py` and `src/ui_sessions.py`
- [ ] T044 Run the quickstart validation scenarios in `specs/001-control-ui-dashboard/quickstart.md` and record any fixes in `specs/001-control-ui-dashboard/research.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel if separate contributors own disjoint files
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Reuses shared dashboard foundation but does not require User Story 1 completion
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Reuses shared dashboard foundation but does not require User Story 1 or 2 completion

### Within Each User Story

- Tests MUST be written and FAIL before implementation when practical
- Backend contract/integration coverage before route completion
- Shared data/hooks before route wiring
- Route wiring before end-to-end validation
- Story complete before moving to next priority checkpoint

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- Foundational backend service tasks `T005`, `T006`, and `T007` can run in parallel
- Foundational frontend shared-shell tasks `T009`, `T010`, and `T011` can run in parallel
- User Story 1 tests `T013`, `T014`, and `T015` can run in parallel
- User Story 2 editor and catalog tasks `T024`, `T026`, and `T027` can run in parallel
- User Story 3 UI/backend split tasks `T034` and `T035` can run in parallel after `T033` begins exposing the needed contract

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Add the bootstrap, session policy, and single-operator warning contract test in tests/contract/test_control_surface_bootstrap_api.py"
Task: "Add the live-control and second-dashboard session integration test in tests/integration/test_control_dashboard_live_control.py"
Task: "Add the live dashboard and concurrent-operator notice component test in frontend/tests/unit/live-control-panel.test.tsx"

# Launch implementation tasks that touch different files:
Task: "Implement live-control snapshot shaping and single-operator session warning responses in src/api_server.py, src/ui_snapshot.py, and src/ui_sessions.py"
Task: "Build the live status, control panel, and concurrent-operator notice components in frontend/src/domains/live-control/EngineStatusCard.tsx, frontend/src/domains/live-control/LiveControlPanel.tsx, and frontend/src/components/feedback/ConcurrentOperatorNotice.tsx"
```

## Parallel Example: User Story 2

```bash
# Launch tests for User Story 2 together:
Task: "Add the control catalog and persistence contract test in tests/contract/test_control_catalog_api.py"
Task: "Add the apply-live, explicit-persist, and stale-write protection integration test in tests/integration/test_control_dashboard_persistence.py"
Task: "Add the configuration workspace, stale-highlight, and overwrite-warning component test in frontend/tests/unit/config-workspace.test.tsx"

# Launch implementation tasks that touch different files:
Task: "Extend the control catalog to cover every config domain in src/ui_catalog.py and src/config.py"
Task: "Build the configuration route and workspace container in frontend/src/routes/ConfigurationRoute.tsx and frontend/src/domains/configuration/ConfigurationWorkspace.tsx"
Task: "Build the editor set and persist indicators in frontend/src/components/editors/ToggleEditor.tsx, frontend/src/components/editors/ScalarEditor.tsx, frontend/src/components/editors/EnumEditor.tsx, frontend/src/components/editors/CollectionEditor.tsx, frontend/src/components/editors/MappingEditor.tsx, frontend/src/components/editors/GenericJsonEditor.tsx, and frontend/src/components/feedback/PersistStateBadge.tsx"
```

## Parallel Example: User Story 3

```bash
# Launch tests for User Story 3 together:
Task: "Add the action catalog and contract-parity test in tests/contract/test_control_contract_api.py"
Task: "Add the action invocation and parity integration test in tests/integration/test_control_dashboard_actions.py"
Task: "Add the action center and contract-driven rendering component test in frontend/tests/unit/control-contract-parity.test.tsx"

# Launch implementation tasks that touch different files:
Task: "Build the action center and action feedback components in frontend/src/domains/actions/ActionCenter.tsx and frontend/src/components/feedback/ActionResultBanner.tsx"
Task: "Wire action catalog loading and invocation hooks in frontend/src/hooks/useActionCatalog.ts and frontend/src/hooks/useActionInvocation.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Demo the live operator dashboard before expanding scope

### Incremental Delivery

1. Complete Setup + Foundational → foundation ready
2. Add User Story 1 → Test independently → Demo MVP
3. Add User Story 2 → Test independently → Demo full configuration coverage
4. Add User Story 3 → Test independently → Demo one-control-contract parity
5. Finish cross-cutting polish, docs, observability, and quickstart validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Rejoin for Phase 6 polish and performance validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable once Foundational work is done
- Verify tests fail before implementing where practical
- Include docs, observability, UX consistency, and performance validation work as part of done
- Avoid same-file parallel edits unless the assigned tasks are clearly coordinated
