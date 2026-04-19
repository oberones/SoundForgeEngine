from fastapi.testclient import TestClient

from api_server import APIServer
from config import RootConfig
from state import get_state, reset_state


def test_live_control_update_changes_runtime_state(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    response = client.post(
        "/config",
        json={
            "path": "sequencer.bpm",
            "value": 124.0,
            "apply_immediately": True,
            "expected_revision": server.ui_snapshot.current_revision(),
        },
    )

    assert response.status_code == 200
    assert response.json()["applied_to_state"] is True
    assert get_state().get("bpm") == 124.0


def test_second_dashboard_is_warning_only(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    first = client.post("/ui/sessions", json={"client_name": "A"})
    second = client.post("/ui/sessions", json={"client_name": "B"})

    assert first.json()["status"] == "active"
    assert second.json()["conflict_state"] == "unsupported-concurrent-use"
