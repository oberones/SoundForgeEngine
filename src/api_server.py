"""Dynamic control-surface API server for SoundForgeEngine."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, ValidationError

from config import RootConfig
from events import SemanticEvent
from state import get_state
from ui_catalog import build_action_catalog, build_control_domains
from ui_persistence import UIPersistenceManager
from ui_sessions import UISessionRegistry
from ui_snapshot import UISnapshotTracker


log = logging.getLogger(__name__)


class ConfigUpdateRequest(BaseModel):
    """Request model for updating configuration values."""

    path: str = Field(..., description="Dot-separated path to the config value (e.g. 'sequencer.bpm').")
    value: Any = Field(..., description="New value to set.")
    apply_immediately: bool = Field(True, description="Apply the change to the running system immediately.")
    expected_revision: Optional[str] = Field(None, description="Last revision seen by the client.")
    session_id: Optional[str] = Field(None, description="Optional dashboard session identifier.")


class ConfigUpdateResponse(BaseModel):
    """Response model for configuration updates."""

    success: bool
    message: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    applied_to_state: bool = False
    revision: str
    persisted: bool = False


class ConfigGetResponse(BaseModel):
    """Response model for getting configuration values."""

    path: str
    value: Any
    exists: bool = True


class SystemStatusResponse(BaseModel):
    """Response model for system status."""

    status: str
    uptime_seconds: float
    config_version: str = "0.1.0"
    api_version: str = "2.0.0"


class CreateSessionRequest(BaseModel):
    client_name: Optional[str] = None
    user_agent: Optional[str] = None


class PersistRequest(BaseModel):
    revision: str
    session_id: Optional[str] = None


class APIServer:
    """FastAPI server for configuration, control, and dashboard metadata."""

    def __init__(
        self,
        config: RootConfig,
        semantic_event_handler=None,
        config_path: Optional[str] = None,
    ):
        self.config = config
        self.semantic_event_handler = semantic_event_handler
        self.config_path = config_path
        self.start_time = time.time()
        self._server = None
        self._thread = None
        self._running = False
        self._root_schema: Dict[str, Any] = {}

        self.ui_sessions = UISessionRegistry()
        self.ui_persistence = UIPersistenceManager(lambda: self.config, config_path=config_path)
        self.ui_snapshot = UISnapshotTracker(
            config_provider=lambda: self.config,
            state_provider=get_state,
            active_session_provider=self.ui_sessions.active_session_id,
            start_time=lambda: self.start_time,
        )

        self.app = FastAPI(
            title="SoundForgeEngine API",
            description="Dynamic configuration and control API for SoundForgeEngine.",
            version="2.0.0",
            lifespan=self.lifespan,
        )

        self._setup_routes()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        log.info("api_server_starting")
        yield
        log.info("api_server_stopping")

    def _setup_routes(self) -> None:
        @self.app.get("/", response_model=Dict[str, str])
        async def root():
            return {
                "name": "SoundForgeEngine API",
                "version": "2.0.0",
                "status": "running",
                "docs": "/docs",
                "dashboard": "/ui",
            }

        @self.app.get("/ui", response_class=HTMLResponse)
        async def get_dashboard_shell():
            index_path = self._frontend_dist_dir() / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return HTMLResponse(
                """
                <!doctype html>
                <html lang="en">
                <head>
                  <meta charset="utf-8" />
                  <title>SoundForgeEngine Dashboard</title>
                  <meta name="viewport" content="width=device-width, initial-scale=1" />
                  <style>
                    body { font-family: sans-serif; margin: 0; background: #101414; color: #f2f1eb; }
                    main { max-width: 720px; margin: 5rem auto; padding: 2rem; }
                    code { background: rgba(255,255,255,0.08); padding: 0.2rem 0.4rem; border-radius: 0.4rem; }
                    a { color: #9bd0ff; }
                  </style>
                </head>
                <body>
                  <main>
                    <h1>Dashboard Assets Not Built</h1>
                    <p>The backend UI endpoints are ready, but the bundled frontend assets are missing.</p>
                    <p>From the repository root, run <code>cd frontend && npm install && npm run build</code>.</p>
                    <p>You can still inspect and exercise the dashboard API through <a href="/docs">/docs</a>.</p>
                  </main>
                </body>
                </html>
                """,
                status_code=503,
            )

        @self.app.get("/ui/assets/{asset_path:path}")
        async def get_dashboard_asset(asset_path: str):
            dist_dir = self._frontend_dist_dir() / "assets"
            candidate = (dist_dir / asset_path).resolve()
            if not str(candidate).startswith(str(dist_dir.resolve())) or not candidate.exists():
                raise HTTPException(status_code=404, detail="Dashboard asset not found")
            return FileResponse(candidate)

        @self.app.get("/status", response_model=SystemStatusResponse)
        async def get_status():
            return SystemStatusResponse(
                status="running",
                uptime_seconds=time.time() - self.start_time,
            )

        @self.app.get("/config", response_model=Dict[str, Any])
        async def get_full_config():
            return self.config.model_dump()

        @self.app.get("/config/schema")
        async def get_config_schema():
            return RootConfig.model_json_schema()

        @self.app.get("/config/mappings")
        async def get_supported_mappings():
            schema = RootConfig.model_json_schema()
            self._root_schema = schema
            return self._extract_schema_paths(schema)

        @self.app.get("/config/{config_path:path}", response_model=ConfigGetResponse)
        async def get_config_value(config_path: str):
            try:
                value = self._get_config_value(config_path)
                return ConfigGetResponse(path=config_path, value=value)
            except KeyError:
                return ConfigGetResponse(path=config_path, value=None, exists=False)

        @self.app.post("/config", response_model=ConfigUpdateResponse)
        async def update_config(request: ConfigUpdateRequest):
            try:
                if self.ui_snapshot.has_conflict(request.expected_revision, request.path):
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "detail": "The requested field changed after the client began editing it.",
                            "current_revision": self.ui_snapshot.current_revision(),
                            "current_value": self._get_config_value(request.path),
                            "affected_path": request.path,
                        },
                    )

                try:
                    old_value = self._get_config_value(request.path)
                except KeyError:
                    old_value = None

                self._set_config_value(request.path, request.value)

                applied_to_state = False
                message = f"Configuration updated successfully: {request.path}"
                if request.apply_immediately:
                    self._apply_config_to_system(request.path, request.value)
                    applied_to_state = True
                    message += " and applied to running system"

                revision = self.ui_snapshot.mark_paths_changed([request.path])

                log.info("ui_config_update path=%s revision=%s session_id=%s", request.path, revision, request.session_id)
                return ConfigUpdateResponse(
                    success=True,
                    message=message,
                    old_value=old_value,
                    new_value=request.value,
                    applied_to_state=applied_to_state,
                    revision=revision,
                    persisted=not self.ui_persistence.differs_from_persisted(request.path),
                )
            except HTTPException:
                raise
            except ValidationError as exc:
                raise HTTPException(status_code=400, detail=f"Validation error: {exc}") from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Value error: {exc}") from exc
            except Exception as exc:  # pragma: no cover - defensive fallback
                log.error("config_update_failed path=%s error=%s", request.path, exc)
                raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc

        @self.app.post("/config/persist")
        async def persist_config(request: PersistRequest):
            try:
                result = self.ui_persistence.persist(
                    revision=request.revision,
                    current_revision=self.ui_snapshot.current_revision(),
                    session_id=request.session_id,
                )
                log.info("ui_persist_success revision=%s session_id=%s", request.revision, request.session_id)
                return result
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @self.app.get("/state", response_model=Dict[str, Any])
        async def get_system_state():
            return get_state().get_all()

        @self.app.post("/state/reset")
        async def reset_system_state():
            from state import reset_state

            reset_state()
            self.ui_snapshot = UISnapshotTracker(
                config_provider=lambda: self.config,
                state_provider=get_state,
                active_session_provider=self.ui_sessions.active_session_id,
                start_time=lambda: self.start_time,
            )
            self.ui_snapshot.mark_paths_changed(["state.reset"])
            return {"message": "System state reset successfully"}

        @self.app.get("/actions/catalog")
        async def get_action_catalog():
            return {"actions": [action.model_dump() for action in build_action_catalog()]}

        @self.app.post("/actions/semantic")
        async def trigger_semantic_event(action: str, value: Optional[str] = None, source: str = "api"):
            if not self.semantic_event_handler:
                raise HTTPException(status_code=503, detail="Semantic event handler not available")

            try:
                event = SemanticEvent(type=action, value=value, source=source)
                self.semantic_event_handler(event)
                revision = self.ui_snapshot.mark_paths_changed(self._affected_paths_for_action(action))
                log.info("ui_action_triggered action=%s revision=%s", action, revision)
                return {
                    "message": f"Semantic event '{action}' triggered successfully",
                    "revision": revision,
                }
            except Exception as exc:  # pragma: no cover - defensive fallback
                log.error("semantic_action_failed action=%s error=%s", action, exc)
                raise HTTPException(status_code=500, detail=f"Error triggering event: {exc}") from exc

        @self.app.get("/ui/bootstrap")
        async def ui_bootstrap():
            snapshot = self.ui_snapshot.build_snapshot()
            revision = snapshot["revision"]
            domains = build_control_domains(self.config, revision, self.ui_persistence)
            actions = build_action_catalog()
            return {
                "snapshot": snapshot,
                "domains": [domain.model_dump() for domain in domains],
                "actions": [action.model_dump() for action in actions],
                "session_policy": self.ui_sessions.session_policy(),
                "persistence": self.ui_persistence.persistence_metadata(),
            }

        @self.app.post("/ui/sessions", status_code=201)
        async def create_ui_session(request: CreateSessionRequest):
            result = self.ui_sessions.create_session(
                client_name=request.client_name,
                user_agent=request.user_agent,
            )
            self.ui_snapshot.mark_paths_changed(["ui.session"])
            return result

        @self.app.post("/ui/sessions/{session_id}/heartbeat")
        async def heartbeat_ui_session(session_id: str):
            try:
                result = self.ui_sessions.heartbeat(session_id)
                self.ui_snapshot.mark_paths_changed(["ui.session"])
                return result
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="Unknown or expired session") from exc

        @self.app.delete("/ui/sessions/{session_id}", status_code=204)
        async def close_ui_session(session_id: str):
            self.ui_sessions.close(session_id)
            self.ui_snapshot.mark_paths_changed(["ui.session"])
            return Response(status_code=204)

        @self.app.get("/ui/snapshot")
        async def ui_snapshot(since_revision: Optional[str] = None):
            return {"snapshot": self.ui_snapshot.build_snapshot(since_revision=since_revision)}

    def _frontend_dist_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "frontend" / "dist"

    def _affected_paths_for_action(self, action: str) -> List[str]:
        mapping = {
            "trigger_step": ["state.step_position"],
            "tempo_up": ["sequencer.bpm"],
            "tempo_down": ["sequencer.bpm"],
            "direction_left": ["sequencer.direction_pattern"],
            "direction_right": ["sequencer.direction_pattern"],
            "set_direction_pattern": ["sequencer.direction_pattern"],
            "set_step_pattern": ["sequencer.step_pattern"],
            "reload_cc_profile": ["midi.cc_profile.active_profile"],
        }
        return mapping.get(action, [f"action.{action}"])

    def _get_config_value(self, path: str) -> Any:
        current = self.config.model_dump()
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"Configuration path not found: {path}")
        return current

    def _set_config_value(self, path: str, value: Any) -> None:
        keys = path.split(".")
        config_dict = self.config.model_dump()
        current = config_dict
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

        try:
            self.config = RootConfig(**config_dict)
        except ValidationError as exc:
            raise ValueError(f"Configuration validation failed: {exc}") from exc

    def _apply_config_to_system(self, path: str, value: Any) -> None:
        state = get_state()
        path_mappings = {
            "sequencer.bpm": "bpm",
            "sequencer.swing": "swing",
            "sequencer.density": "density",
            "sequencer.steps": "sequence_length",
            "sequencer.root_note": "root_note",
            "sequencer.gate_length": "gate_length",
            "sequencer.voices": "voices",
            "idle.smooth_bpm_transitions": "smooth_idle_transitions",
            "idle.bpm_transition_duration_s": "idle_transition_duration_s",
        }

        if path in path_mappings:
            state_key = path_mappings[path]
            state.set(state_key, value, source="api")
            log.info("config_applied_to_state state_key=%s", state_key)

        if path == "sequencer.direction_pattern" and self.semantic_event_handler:
            self.semantic_event_handler(SemanticEvent(type="set_direction_pattern", value=value, source="api"))
        elif path == "sequencer.step_pattern" and self.semantic_event_handler:
            self.semantic_event_handler(SemanticEvent(type="set_step_pattern", value=value, source="api"))
        elif path.startswith("midi.cc_profile") and self.semantic_event_handler:
            self.semantic_event_handler(SemanticEvent(type="reload_cc_profile", value=None, source="api"))

    def _extract_schema_paths(self, schema: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        paths: Dict[str, Any] = {}

        def resolve_ref(ref_schema: Dict[str, Any], root_schema: Dict[str, Any]) -> Dict[str, Any]:
            if "$ref" in ref_schema:
                ref_path = ref_schema["$ref"]
                if ref_path.startswith("#/$defs/"):
                    def_name = ref_path[8:]
                    return root_schema.get("$defs", {}).get(def_name, {})
            return ref_schema

        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                current_path = f"{prefix}.{prop_name}" if prefix else prop_name
                resolved_schema = resolve_ref(prop_schema, schema if not prefix else self._root_schema)
                if resolved_schema.get("type") == "object" and "properties" in resolved_schema:
                    paths.update(self._extract_schema_paths(resolved_schema, current_path))
                else:
                    paths[current_path] = {
                        "type": resolved_schema.get("type", "unknown"),
                        "description": resolved_schema.get("description", ""),
                        "default": resolved_schema.get("default"),
                        "enum": resolved_schema.get("enum"),
                        "minimum": resolved_schema.get("minimum"),
                        "maximum": resolved_schema.get("maximum"),
                    }
        return paths

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True, name="api-server")
        self._thread.start()
        log.info("api_server_started port=%s", self.config.api.port)

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5.0)
        log.info("api_server_stopped")

    def _run_server(self) -> None:
        try:
            config = uvicorn.Config(
                self.app,
                host=self.config.api.host,
                port=self.config.api.port,
                log_level="info" if log.isEnabledFor(logging.INFO) else "warning",
                access_log=True,
            )
            self._server = uvicorn.Server(config)
            self._server.run()
        except Exception as exc:  # pragma: no cover - defensive fallback
            log.error("api_server_error error=%s", exc)
            self._running = False


def create_api_server(
    config: RootConfig,
    semantic_event_handler=None,
    config_path: Optional[str] = None,
) -> Optional[APIServer]:
    if not config.api.enabled:
        log.info("api_server_disabled")
        return None
    try:
        return APIServer(config, semantic_event_handler, config_path=config_path)
    except Exception as exc:  # pragma: no cover - defensive fallback
        log.error("api_server_creation_failed error=%s", exc)
        return None
