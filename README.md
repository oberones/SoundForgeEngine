# SoundForgeEngine

SoundForgeEngine is a real-time generative music engine for performance rigs, hardware controllers, and external synthesizers. It combines a scale-aware sequencer, mutation and idle behaviors, MIDI and HID input handling, external CC profile routing, and multiple operator control surfaces: physical hardware, a REST API, a CLI, and a browser dashboard.

## Highlights

- Real-time sequencer with BPM, swing, density, gate length, root note, scale, step pattern, and direction control
- Direction modes including `forward`, `backward`, `ping_pong`, `random`, `fugue`, and `song`
- MIDI input from controller hardware plus optional HID arcade-button and joystick input
- MIDI output and CC profile support for external synths
- Idle-mode transitions and automatic mutation for long-running ambient behavior
- FastAPI control surface with Swagger docs at `/docs`
- Browser dashboard served by the engine at `/ui`
- CLI client for scripting, monitoring, and remote control

## Control Surfaces

| Surface | Purpose | Entry Point |
|---------|---------|-------------|
| Hardware input | Live control from MIDI controllers and optional HID arcade controls | `midi`, `hid`, and `mapping` sections in `config.yaml` |
| Dashboard | Visual live control, configuration editing, action triggering, and explicit persistence | `http://localhost:8080/ui` |
| REST API | Automation, scripting, and integration with external tools | `http://localhost:8080/docs` |
| CLI | Terminal-friendly status, config, state, and action commands | `./mme-cli` |

## Quick Start

### Prerequisites

- Python 3 with `venv`
- `pip`
- Node.js and `npm` only if you want to build the dashboard assets locally
- MIDI or HID hardware is optional for development and testing

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional: install pygame for the alternate HID joystick backend
pip install pygame
```

`pygame` is optional. The engine, API, dashboard backend, and MIDI-only workflows run without it. Install it only if you want the original pygame-based HID backend in addition to the `hidapi` path.

### Build the Dashboard

The API works without frontend assets, but the browser dashboard at `/ui` expects a built bundle.

```bash
cd frontend
npm install
npm run build
cd ..
```

### Local UI Development

For the fastest local testing loop, run the engine and the Vite dev server side by side.

Terminal 1:

```bash
source .venv/bin/activate
python src/main.py --config config.yaml --log-level INFO
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Then open [http://127.0.0.1:5173/ui/](http://127.0.0.1:5173/ui/).

The Vite dev server proxies dashboard API requests to the engine on `127.0.0.1:8080`, so this is the best setup for day-to-day UI work. For a more production-like smoke test, build the frontend and use the engine-served dashboard at `/ui`.

### Run the Engine

```bash
source .venv/bin/activate
python src/main.py --config config.yaml --log-level INFO
```

With the default `config.yaml`, the control surfaces are:

- Dashboard: [http://localhost:8080/ui](http://localhost:8080/ui)
- API docs: [http://localhost:8080/docs](http://localhost:8080/docs)
- API status: [http://localhost:8080/status](http://localhost:8080/status)

If the frontend bundle has not been built yet, `/ui` returns a setup page explaining how to build it.

## Using SoundForgeEngine

### 1. Configure the Engine

The engine loads YAML configuration from the file passed to `--config`. The repository root includes a working example at [config.yaml](config.yaml).

Typical workflow:

1. Copy or edit `config.yaml`
2. Set MIDI ports, channels, and CC profile
3. Configure sequencer behavior
4. Optionally map HID buttons and joystick directions
5. Enable the API if you want the dashboard, CLI, or remote control

### 2. Start the Engine

```bash
source .venv/bin/activate
python src/main.py --config config.yaml --log-level INFO
```

The engine loads the config, initializes MIDI output, starts the API server if enabled, starts hybrid input, and begins sequencing.

### 3. Choose a Control Surface

#### Browser Dashboard

Open `/ui` to:

- Monitor current engine status
- Adjust live parameters
- Browse all configuration domains
- Trigger supported semantic actions
- Review pending configuration changes
- Persist supported settings explicitly back to the config file

Dashboard edits update the running session first. Persistence is an explicit separate action.

#### CLI

The repo includes a wrapper script and a Python CLI client:

- [mme-cli](mme-cli)
- [mme-cli.py](mme-cli.py)

Examples:

```bash
./mme-cli status
./mme-cli config get sequencer.bpm
./mme-cli quick bpm 128
./mme-cli event trigger set_direction_pattern random
./mme-cli monitor
```

#### REST API

Examples:

```bash
curl http://localhost:8080/status

curl http://localhost:8080/config/sequencer.bpm

curl -X POST http://localhost:8080/config \
  -H "Content-Type: application/json" \
  -d '{"path":"sequencer.bpm","value":124,"apply_immediately":true}'

curl -X POST "http://localhost:8080/actions/semantic?action=set_direction_pattern&value=ping_pong"
```

For custom clients:

- `POST /config` updates the in-memory config, can apply changes immediately, and returns a revision token
- `POST /config/persist` writes the current config back to disk using a current revision token
- `GET /actions/catalog` lists supported operator actions
- `GET /ui/bootstrap` and `GET /ui/snapshot` expose dashboard metadata and revision-aware snapshots

## Configuration Reference

All supported configuration is defined in [src/config.py](src/config.py). The top-level sections are `logging`, `midi`, `hid`, `mapping`, `sequencer`, `scales`, `mutation`, `idle`, `synth`, `api`, and `cc_profiles`.

### Logging

| Key | Values | Purpose |
|-----|--------|---------|
| `logging.level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Engine log verbosity |

### MIDI

| Key | Values | Purpose |
|-----|--------|---------|
| `midi.input_port` | Port name or `auto` | MIDI input source |
| `midi.output_port` | Port name or `null` | External synth/output destination |
| `midi.input_channel` | Integer channel | MIDI input channel filter |
| `midi.output_channel` | Integer channel | MIDI output channel |
| `midi.clock.enabled` | `true` / `false` | Enable MIDI clock output |
| `midi.clock.send_start_stop` | `true` / `false` | Send transport start/stop |
| `midi.clock.send_song_position` | `true` / `false` | Send song-position messages |
| `midi.cc_profile.active_profile` | String profile name | Active CC mapping profile for external hardware |
| `midi.cc_profile.parameter_smoothing` | `true` / `false` | Smooth parameter changes before sending CC |
| `midi.cc_profile.cc_throttle_ms` | Integer milliseconds | Minimum time between outgoing CC messages |

### HID Input

| Key | Values | Purpose |
|-----|--------|---------|
| `hid.device_name` | String | HID device name match |
| `hid.button_mapping` | Button index to action map | Map arcade/gamepad buttons to semantic actions |
| `hid.joystick_mapping` | Direction to action map | Map joystick directions to semantic actions |

Default joystick actions are `tempo_up`, `tempo_down`, `direction_left`, and `direction_right`. You can map these controls to other semantic actions documented in [docs/reference/SEMANTIC_ACTIONS_REFERENCE.md](docs/reference/SEMANTIC_ACTIONS_REFERENCE.md).

### MIDI-to-Action Mapping

| Key | Values | Purpose |
|-----|--------|---------|
| `mapping.buttons` | MIDI note or note-range to action map | Map incoming note events to semantic actions |
| `mapping.ccs` | MIDI CC number to action map | Map incoming CC messages to semantic actions |

Examples:

```yaml
mapping:
  buttons:
    "60-69": trigger_step
  ccs:
    "27": tempo
    "21": filter_cutoff
```

### Sequencer

| Key | Values | Purpose |
|-----|--------|---------|
| `sequencer.steps` | Integer | Number of steps in the sequence |
| `sequencer.bpm` | Float | Tempo |
| `sequencer.swing` | `0.0` to `0.5` | Swing amount |
| `sequencer.density` | `0.0` to `1.0` | Global probability gate |
| `sequencer.root_note` | MIDI note `0` to `127` | Scale root |
| `sequencer.gate_length` | `0.1` to `1.0` | Note duration as a fraction of step length |
| `sequencer.quantize_scale_changes` | `bar` or `immediate` | When scale changes take effect |
| `sequencer.step_pattern` | Preset name or `null` | Named step pattern preset |
| `sequencer.direction_pattern` | `forward`, `backward`, `ping_pong`, `random`, `fugue`, `song` | Playback mode |
| `sequencer.voices` | `1` to `4` | Voice count for multi-voice modes |
| `sequencer.note_division` | `whole`, `half`, `quarter`, `eighth`, `sixteenth` | Step timing division |

### Scales

| Key | Values | Purpose |
|-----|--------|---------|
| `scales` | Non-empty list of scale names | Scales available to the sequencer |

Example values used in the repo include `major`, `minor`, `blues`, `pentatonic_major`, `pentatonic_minor`, `mixolydian`, `dorian`, and `locrian`.

### Mutation and Idle Behavior

| Key | Values | Purpose |
|-----|--------|---------|
| `mutation.interval_min_s` | Integer seconds | Minimum delay between mutation cycles |
| `mutation.interval_max_s` | Integer seconds | Maximum delay between mutation cycles |
| `mutation.max_changes_per_cycle` | Integer | Maximum parameter changes per cycle |
| `idle.timeout_ms` | Integer milliseconds | Idle timeout before ambient behavior begins |
| `idle.ambient_profile` | String profile name | Ambient profile to activate while idle |
| `idle.fade_in_ms` | Integer milliseconds | Idle-entry fade duration |
| `idle.fade_out_ms` | Integer milliseconds | Idle-exit fade duration |
| `idle.smooth_bpm_transitions` | `true` / `false` | Smooth BPM changes during idle transitions |
| `idle.bpm_transition_duration_s` | Float seconds | Idle BPM transition duration |

The repository config uses profiles such as `slow_fade`, `meditative`, and `rhythmic`.

### Synth and External Profiles

| Key | Values | Purpose |
|-----|--------|---------|
| `synth.backend` | Currently `supercollider` | Synth backend identifier |
| `synth.voices` | Integer | Voice-allocation count |
| `cc_profiles` | Mapping of profile names to arbitrary config objects | Custom external synth CC profile definitions |

### API

| Key | Values | Purpose |
|-----|--------|---------|
| `api.enabled` | `true` / `false` | Enable the API server |
| `api.port` | Integer port | HTTP port for API and dashboard |
| `api.host` | Host string such as `127.0.0.1` or `0.0.0.0` | Network binding |
| `api.log_level` | Uvicorn/FastAPI log level string | API server logging |

If the API is exposed beyond localhost, place it behind a trusted LAN or reverse proxy. There is no in-app authentication layer.

## Supported Runtime Surfaces

### Dashboard and API

- Dashboard shell: `/ui`
- Dashboard metadata: `/ui/bootstrap`
- Dashboard snapshot polling: `/ui/snapshot`
- Swagger/OpenAPI docs: `/docs`
- Health/status: `/status`
- Config inspection and updates: `/config`, `/config/{path}`, `/config/schema`, `/config/mappings`
- Persistence: `/config/persist`
- State inspection/reset: `/state`, `/state/reset`
- Actions: `/actions/catalog`, `/actions/semantic`

### Semantic Actions Exposed by the Dashboard

The current dashboard action catalog includes:

- `trigger_step`
- `tempo_up`
- `tempo_down`
- `direction_left`
- `direction_right`
- `set_direction_pattern`
- `set_step_pattern`
- `reload_cc_profile`

For broader action vocabulary and hardware-mapping ideas, see [docs/reference/SEMANTIC_ACTIONS_REFERENCE.md](docs/reference/SEMANTIC_ACTIONS_REFERENCE.md).

## Testing

### Python Test Suite

Run the full backend test suite:

```bash
source .venv/bin/activate
pytest tests -q
```

Useful focused commands:

```bash
pytest tests/test_config.py -v
pytest tests/test_sequencer.py -v
pytest tests/test_hid_input.py -v
pytest tests/unit tests/contract tests/integration tests/test_api_server.py -q
```

Notes:

- `tests/conftest.py` adds `src/` to `PYTHONPATH`, so tests run from the repo root
- The pygame-specific HID tests skip automatically if `pygame` is not installed
- Core unit and integration tests do not require physical hardware, but live rig validation is still recommended before performance use

### Frontend Tests

```bash
cd frontend
npm test
npm run build
```

The frontend workspace also includes Playwright specs under `frontend/tests/e2e/`.

For interactive UI testing during development, use `npm run dev` with the engine running locally and open `http://127.0.0.1:5173/ui/`.

## Project Layout

| Path | Purpose |
|------|---------|
| [src](src) | Python engine, API server, and runtime components |
| [frontend](frontend) | React/Vite dashboard |
| [config.yaml](config.yaml) | Example runtime configuration |
| [tests](tests) | Backend unit, contract, and integration tests |
| [docs](docs) | Extended API, CLI, architecture, and implementation docs |

## Further Documentation

- [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)
- [docs/CLI_DOCUMENTATION.md](docs/CLI_DOCUMENTATION.md)
- [docs/reference/ARCHITECTURE.md](docs/reference/ARCHITECTURE.md)
- [docs/reference/SEMANTIC_ACTIONS_REFERENCE.md](docs/reference/SEMANTIC_ACTIONS_REFERENCE.md)
