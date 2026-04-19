# Quickstart: Control UI Dashboard

## Goal

Verify that the dashboard can drive the running engine through the control
interface, reflect external changes, and persist supported settings explicitly.

## Prerequisites

1. Activate the project virtual environment from the repository root:
   ```bash
   source .venv/bin/activate
   ```
2. Install existing Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install frontend dependencies in the new UI workspace:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

## Development Run

1. Start the engine and API with the desired config:
   ```bash
   python src/main.py --config config.yaml --log-level INFO
   ```
2. In a second terminal, start the frontend development server:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open the dashboard in a browser using the frontend dev URL.

## Production-Style Run

1. Build the frontend assets:
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
2. Start the engine and open the dashboard from the FastAPI-served `/ui`
   route.

## Verification Scenarios

### 1. Core Live Control

1. Open the dashboard and confirm engine status, uptime, and current values are
   visible.
2. Change tempo, swing, density, and direction.
3. Confirm the engine applies the new values and the UI reports success within
   the local feedback budget.

### 2. Full Configuration Coverage

1. Visit each control domain shown in the catalog.
2. Confirm every domain from the runtime config model is represented.
3. Verify that unsupported custom shapes still render through the generic
   editor instead of disappearing.

### 3. External Change Highlighting

1. Leave the dashboard open.
2. Change a value through hardware input, a second control client, or a direct
   API call.
3. Confirm the dashboard refreshes automatically, highlights the changed field,
   and warns before overwriting a field currently being edited.

### 4. Explicit Persistence

1. Change one or more persistable settings from the dashboard.
2. Confirm the values apply live immediately.
3. Use the explicit save action.
4. Confirm the save succeeds, the UI reflects the persisted state, and the
   running/persisted difference indicator clears.

### 5. Unsupported Concurrent Operator Warning

1. Open the dashboard in one browser window.
2. Open the same dashboard in a second window or browser profile.
3. Confirm the second dashboard surfaces the unsupported concurrent-use warning
   defined by the spec.

## Automated Test Targets

Run backend tests:

```bash
pytest tests/unit tests/contract tests/integration -q
```

Run frontend tests:

```bash
cd frontend
npm test
```

Run browser workflow coverage:

```bash
cd frontend
npm run test:e2e
```
