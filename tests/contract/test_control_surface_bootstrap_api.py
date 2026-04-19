from fastapi.testclient import TestClient

from api_server import APIServer
from config import RootConfig
from state import reset_state


def test_ui_bootstrap_contract_includes_snapshot_domains_actions(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    response = client.get("/ui/bootstrap")

    assert response.status_code == 200
    data = response.json()
    assert "snapshot" in data
    assert "domains" in data
    assert "actions" in data
    assert data["session_policy"]["concurrency_mode"] == "single-active-operator"
    assert data["persistence"]["supported"] is True


def test_ui_session_contract_warns_on_second_dashboard(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    first = client.post("/ui/sessions", json={"client_name": "A", "user_agent": "ua"})
    second = client.post("/ui/sessions", json={"client_name": "B", "user_agent": "ub"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["status"] == "active"
    assert second.json()["status"] == "warning-only"
