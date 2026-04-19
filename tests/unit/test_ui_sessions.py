from ui_sessions import UISessionRegistry


def test_session_registry_warns_for_second_operator():
    registry = UISessionRegistry(heartbeat_timeout_seconds=60)

    first = registry.create_session("A", "ua")
    second = registry.create_session("B", "ub")

    assert first["status"] == "active"
    assert second["status"] == "warning-only"
    assert second["conflict_state"] == "unsupported-concurrent-use"
    assert second["active_session_id"] == first["session_id"]


def test_session_registry_promotes_waiting_session_when_active_closes():
    registry = UISessionRegistry(heartbeat_timeout_seconds=60)

    first = registry.create_session()
    second = registry.create_session()
    registry.close(first["session_id"])

    promoted = registry.heartbeat(second["session_id"])
    assert promoted["status"] == "active"
    assert promoted["conflict_state"] == "none"
