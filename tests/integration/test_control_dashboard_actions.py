from fastapi.testclient import TestClient

from api_server import APIServer
from config import RootConfig
from state import reset_state


def test_action_invocation_returns_revision_and_calls_handler(tmp_path):
    reset_state()
    events = []

    def handle(event):
        events.append((event.type, event.value))

    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(
        RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}),
        semantic_event_handler=handle,
        config_path=str(config_path),
    )
    client = TestClient(server.app)

    response = client.post("/actions/semantic", params={"action": "trigger_step"})

    assert response.status_code == 200
    assert response.json()["revision"].startswith("r")
    assert events == [("trigger_step", None)]
