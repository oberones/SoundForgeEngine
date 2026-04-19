from fastapi.testclient import TestClient

from api_server import APIServer
from config import RootConfig
from state import reset_state


def test_action_catalog_and_invocation_contract(tmp_path):
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

    catalog = client.get("/actions/catalog")
    invoke = client.post("/actions/semantic", params={"action": "set_direction_pattern", "value": "random"})

    assert catalog.status_code == 200
    assert any(action["id"] == "set_direction_pattern" for action in catalog.json()["actions"])
    assert invoke.status_code == 200
    assert events == [("set_direction_pattern", "random")]
