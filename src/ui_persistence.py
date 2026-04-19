"""Explicit persistence support for the dashboard UI."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any, Callable, Dict, Optional

import yaml


def _lookup_path(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for segment in path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return None
    return current


class UIPersistenceManager:
    """Persist the current config model back to the active YAML file."""

    def __init__(self, config_provider: Callable[[], Any], config_path: Optional[str] = None):
        self._config_provider = config_provider
        self._config_path = Path(config_path).resolve() if config_path else None
        self._persisted_data = self._read_persisted_data()

    @property
    def config_path(self) -> Optional[Path]:
        return self._config_path

    def is_supported(self) -> bool:
        return self._config_path is not None

    def persistence_metadata(self) -> Dict[str, object]:
        return {
            "mode": "apply-live-then-explicit-save",
            "supported": self.is_supported(),
        }

    def differs_from_persisted(self, path: str) -> bool:
        current = self._config_provider().model_dump()
        return _lookup_path(current, path) != _lookup_path(self._persisted_data, path)

    def persist(self, revision: str, current_revision: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        if not self._config_path:
            raise ValueError("Persistence is not supported for this runtime configuration")

        # Persist the server's current config model rather than coupling saves to the
        # latest global UI snapshot revision. Runtime-only state changes can advance the
        # snapshot token without changing the config that should be written to disk.
        data = self._config_provider().model_dump()
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(self._config_path.parent),
            prefix=f"{self._config_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)
            temp_path = Path(handle.name)

        temp_path.replace(self._config_path)
        self._persisted_data = data
        return {
            "result": "succeeded",
            "message": "Configuration persisted successfully.",
            "target_path": str(self._config_path),
            "persisted_revision": current_revision,
            "session_id": session_id,
        }

    def _read_persisted_data(self) -> Dict[str, Any]:
        if not self._config_path or not self._config_path.exists():
            current = self._config_provider()
            return current.model_dump() if current else {}

        with self._config_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
