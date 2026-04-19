from fastapi.testclient import TestClient

from api_server import APIServer
from config import RootConfig
from state import reset_state


def test_control_catalog_contract_exposes_domain_metadata(tmp_path):
    reset_state()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    server = APIServer(RootConfig(api={"enabled": True, "port": 8181, "host": "127.0.0.1"}), config_path=str(config_path))
    client = TestClient(server.app)

    response = client.get("/ui/bootstrap")
    domains = response.json()["domains"]

    sequencer = next(domain for domain in domains if domain["id"] == "sequencer")
    controls = {control["path"]: control for control in sequencer["controls"]}
    assert "sequencer.bpm" in controls
    assert "sequencer.direction_pattern" in controls
    assert controls["sequencer.bpm"]["persist_behavior"] == "persistable"
