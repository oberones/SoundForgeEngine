# AGENTS.md

SoundForgeEngine: real-time generative MIDI music engine (Python/FastAPI backend in `src/`, React/Vite/TS dashboard in `frontend/`). Older docs and scripts still say "Mystery Music Machine/Engine" (`mme-cli`, Makefile) — same project.

## Environment & commands

- All Python MUST run inside `.venv/` (project constitution requirement). Use `.venv/bin/python`, `.venv/bin/pytest`, or `make` targets which enforce it.
- Setup: `make setup` (creates `.venv`, installs `requirements.txt` + pytest).
- Run engine: `make run` (= `.venv/bin/python src/main.py --config config.yaml --log-level INFO`). API + dashboard on `:8080`.
- Backend tests: `.venv/bin/pytest tests -q` from repo root. `tests/conftest.py` puts `src/` on `sys.path`.
- Frontend: `cd frontend && npm test` (Vitest unit), `npm run build` (runs `tsc --noEmit` first, then Vite build), `npm run test:e2e` (Playwright).
- UI dev loop: run the engine, then `cd frontend && npm run dev`; open `http://127.0.0.1:5173/ui/`. Vite proxies `/config`, `/actions`, `/state`, `/status`, `/ui/*` to `127.0.0.1:8080`.

## Architecture facts that are easy to get wrong

- `src/` is a flat module dir, not a package. Imports are top-level (`import config`, `from state import get_state`); there is no `src.` prefix and no `__init__.py`. Entrypoint is `src/main.py`.
- Runtime state is a global singleton in `src/state.py` (`get_state()`/`reset_state()`). Tests that touch it call `reset_state()` first — follow that pattern.
- All config is defined in `src/config.py` (`RootConfig`); `config.yaml` at root is the working example. Dashboard/API edits are live in memory only; writing back to disk is an explicit separate action (`POST /config/persist`).
- The engine serves the dashboard from `frontend/dist` at `/ui` (Vite `base: "/ui/"`). Until `npm run build` has run, `/ui` shows a setup page — API works fine without the bundle.
- `./mme-cli` (bash wrapper around `mme-cli.py`) talks to the HTTP API; the engine must be running on `:8080` for it to work.
- `ansible/` deploys to Raspberry Pi; not needed for local dev. No MIDI/HID hardware is required for dev or tests.

## Testing quirks

- Backend suite: 310 tests, no hardware or live server needed. `tests/unit|contract|integration/` use FastAPI `TestClient` in-process.
- `pygame` is optional and NOT in `requirements.txt`; pygame-specific HID tests auto-skip when it's missing. The default HID backend is `hidapi`.
- `make test-integration` only runs `tests/test_integration_phase2.py` — it does NOT run the `tests/integration/` directory. Use `pytest tests/integration -q` for that.
- Playwright e2e (`npm run test:e2e`) has no `webServer` autostart; the engine must already be running at `http://127.0.0.1:8080`.
- Broken Makefile targets: `make verify` and `make spec` reference missing files (`verify_setup.sh`, `docs/AI/SPEC.md`). Don't use them.

## Conventions

- SpecKit workflow: `.specify/memory/constitution.md` is the binding project constitution; feature specs/plans/tasks live under `specs/NNN-name/`. Key hard rules: tests are mandatory for any behavior change ("tests define done"); performance budgets are requirements — sub-10 ms button response, <2 ms sequencer tick jitter, no blocking I/O or heavy work on timing-sensitive paths (input handling, sequencer, MIDI routing).
- Commits: Conventional Commits via Commitizen (`.cz.json`, semver, `cz bump` updates `CHANGELOG.md`, tags are bare versions like `0.2.0`).
- API and CLI naming must stay aligned (constitution); semantic action vocabulary is documented in `docs/reference/SEMANTIC_ACTIONS_REFERENCE.md`, architecture in `docs/reference/ARCHITECTURE.md`.
