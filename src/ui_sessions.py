"""Session tracking for the operator dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
import uuid
from typing import Dict, Optional


@dataclass
class DashboardSession:
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_heartbeat_at: float = field(default_factory=time.time)
    status: str = "active"
    client_name: Optional[str] = None
    user_agent: Optional[str] = None
    mode: str = "active-operator"
    conflict_state: str = "none"


class UISessionRegistry:
    """Track lightweight dashboard sessions for unsupported concurrency warnings."""

    def __init__(self, heartbeat_timeout_seconds: int = 30):
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self._lock = threading.RLock()
        self._sessions: Dict[str, DashboardSession] = {}
        self._active_session_id: Optional[str] = None

    def _prune_expired(self) -> None:
        now = time.time()
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session.last_heartbeat_at > self.heartbeat_timeout_seconds
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)
            if self._active_session_id == session_id:
                self._active_session_id = None
        if self._active_session_id is None:
            self._promote_oldest_waiting()

    def _promote_oldest_waiting(self) -> None:
        waiting = sorted(self._sessions.values(), key=lambda session: session.created_at)
        if not waiting:
            return
        promoted = waiting[0]
        promoted.status = "active"
        promoted.conflict_state = "none"
        self._active_session_id = promoted.session_id
        for session in waiting[1:]:
            session.status = "warning-only"
            session.conflict_state = "unsupported-concurrent-use"

    def create_session(self, client_name: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Optional[str]]:
        with self._lock:
            self._prune_expired()
            session_id = uuid.uuid4().hex
            session = DashboardSession(
                session_id=session_id,
                client_name=client_name,
                user_agent=user_agent,
            )
            if self._active_session_id is None:
                self._active_session_id = session_id
                session.status = "active"
                session.conflict_state = "none"
            else:
                session.status = "warning-only"
                session.conflict_state = "unsupported-concurrent-use"
            self._sessions[session_id] = session
            return self._serialize(session)

    def heartbeat(self, session_id: str) -> Dict[str, Optional[str]]:
        with self._lock:
            self._prune_expired()
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(session_id)
            session.last_heartbeat_at = time.time()
            if self._active_session_id is None:
                self._active_session_id = session_id
                session.status = "active"
                session.conflict_state = "none"
            elif self._active_session_id != session_id:
                session.status = "warning-only"
                session.conflict_state = "unsupported-concurrent-use"
            else:
                session.status = "active"
                session.conflict_state = "none"
            return self._serialize(session)

    def close(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            if self._active_session_id == session_id:
                self._active_session_id = None
            self._prune_expired()

    def active_session_id(self) -> Optional[str]:
        with self._lock:
            self._prune_expired()
            return self._active_session_id

    def session_policy(self) -> Dict[str, object]:
        return {
            "authentication": "none",
            "concurrency_mode": "single-active-operator",
            "heartbeat_timeout_seconds": self.heartbeat_timeout_seconds,
        }

    def _serialize(self, session: DashboardSession) -> Dict[str, Optional[str]]:
        return {
            "session_id": session.session_id,
            "status": session.status,
            "conflict_state": session.conflict_state,
            "active_session_id": self._active_session_id,
        }
