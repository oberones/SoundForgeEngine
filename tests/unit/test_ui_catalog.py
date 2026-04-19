from config import RootConfig
from ui_catalog import build_action_catalog, build_control_domains
from ui_persistence import UIPersistenceManager


def test_build_control_domains_covers_all_top_level_sections(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("sequencer:\n  bpm: 110.0\n", encoding="utf-8")
    config = RootConfig()
    persistence = UIPersistenceManager(lambda: config, str(config_path))

    domains = build_control_domains(config, "r1", persistence)

    domain_ids = {domain.id for domain in domains}
    assert {"sequencer", "midi", "hid", "mutation", "idle", "logging", "api"}.issubset(domain_ids)
    sequencer = next(domain for domain in domains if domain.id == "sequencer")
    control_paths = {control.path for control in sequencer.controls}
    assert "sequencer.bpm" in control_paths
    assert "sequencer.direction_pattern" in control_paths


def test_build_action_catalog_exposes_semantic_actions():
    actions = build_action_catalog()
    action_ids = {action.id for action in actions}
    assert "trigger_step" in action_ids
    assert "set_direction_pattern" in action_ids
    assert "reload_cc_profile" in action_ids
