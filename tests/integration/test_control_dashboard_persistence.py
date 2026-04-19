from fastapi.testclient import TestClient

from api_server import APIServer
from config import RootConfig
from state import get_state, reset_state


def test_persist_endpoint_writes_current_config(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    revision = server.ui_snapshot.current_revision()
    update = client.post(
        "/config",
        json={"path": "sequencer.bpm", "value": 128.0, "apply_immediately": True, "expected_revision": revision},
    )
    persist = client.post("/config/persist", json={"revision": update.json()["revision"]})

    assert persist.status_code == 200
    assert "sequencer:" in config_path.read_text(encoding="utf-8")
    assert update.json()["persisted"] is False


def test_persist_succeeds_after_runtime_only_revision_change(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    revision = server.ui_snapshot.current_revision()
    update = client.post(
        "/config",
        json={"path": "sequencer.bpm", "value": 128.0, "apply_immediately": True, "expected_revision": revision},
    )

    get_state().set("step_position", 1, source="sequencer")

    persist = client.post("/config/persist", json={"revision": update.json()["revision"]})

    assert persist.status_code == 200
    assert persist.json()["persisted_revision"] == server.ui_snapshot.current_revision()


def test_conflicting_write_returns_409(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    stale_revision = server.ui_snapshot.current_revision()
    client.post("/config", json={"path": "sequencer.bpm", "value": 126.0, "apply_immediately": True, "expected_revision": stale_revision})
    conflict = client.post("/config", json={"path": "sequencer.bpm", "value": 122.0, "apply_immediately": True, "expected_revision": stale_revision})

    assert conflict.status_code == 409
