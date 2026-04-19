"""Revision-aware snapshot support for the dashboard UI."""

from __future__ import annotations

from datetime import datetime, UTC
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from state import StateChange


STATE_TO_PATH = {
    "bpm": "sequencer.bpm",
    "swing": "sequencer.swing",
    "density": "sequencer.density",
    "sequence_length": "sequencer.steps",
    "root_note": "sequencer.root_note",
    "gate_length": "sequencer.gate_length",
    "voices": "sequencer.voices",
    "note_division": "sequencer.note_division",
    "step_position": "state.step_position",
    "idle_mode": "state.idle_mode",
    "filter_cutoff": "state.filter_cutoff",
    "reverb_mix": "state.reverb_mix",
    "master_volume": "state.master_volume",
}


class UISnapshotTracker:
    """Track a revisioned view of config/state changes for UI polling."""

    def __init__(
        self,
        config_provider: Callable[[], Any],
        state_provider: Callable[[], Any],
        active_session_provider: Callable[[], Optional[str]],
        start_time: Callable[[], float],
    ):
        self._config_provider = config_provider
        self._state_provider = state_provider
        self._active_session_provider = active_session_provider
        self._start_time = start_time
        self._lock = threading.RLock()
        self._revision = 1
        self._history: List[tuple[int, Set[str]]] = [(self._revision, set())]
        self._last_changed_paths: Set[str] = set()

        state = self._state_provider()
        state.add_listener(self._handle_state_change)

    def _handle_state_change(self, change: StateChange) -> None:
        path = STATE_TO_PATH.get(change.parameter, f"state.{change.parameter}")
        self.mark_paths_changed([path])

    def _token(self, revision: int) -> str:
        return f"r{revision}"

    def current_revision(self) -> str:
        with self._lock:
            return self._token(self._revision)

    def mark_paths_changed(self, paths: Iterable[str]) -> str:
        normalized = {path for path in paths if path}
        with self._lock:
            self._revision += 1
            self._last_changed_paths = normalized
            self._history.append((self._revision, normalized))
            self._history = self._history[-512:]
            return self._token(self._revision)

    def has_conflict(self, expected_revision: Optional[str], path: str) -> bool:
        if not expected_revision:
            return False
        return path in self.changed_paths_since(expected_revision)

    def changed_paths_since(self, revision_token: Optional[str]) -> Set[str]:
        with self._lock:
            if not revision_token:
                return set(self._last_changed_paths)
            try:
                target = int(revision_token.lstrip("r"))
            except ValueError:
                return set(self._last_changed_paths)

            if target >= self._revision:
                return set()

            changed: Set[str] = set()
            for revision, paths in self._history:
                if revision > target:
                    changed.update(paths)
            return changed

    def build_snapshot(self, since_revision: Optional[str] = None, status: str = "running") -> Dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        revision = self.current_revision()
        current_config = self._config_provider().model_dump()
        current_state = self._state_provider().get_all()
        return {
            "revision": revision,
            "captured_at": now,
            "status": status,
            "uptime_seconds": max(0.0, time.time() - self._start_time()),
            "config_values": current_config,
            "state_values": current_state,
            "changed_paths": sorted(self.changed_paths_since(since_revision)),
            "messages": [],
            "active_session_id": self._active_session_provider(),
        }
