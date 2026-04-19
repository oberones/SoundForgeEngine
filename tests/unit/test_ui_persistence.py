from pathlib import Path

from config import RootConfig
from ui_persistence import UIPersistenceManager


def test_persistence_manager_writes_yaml(tmp_path):
    config_path = tmp_path / "config.yaml"
    config = RootConfig()
    manager = UIPersistenceManager(lambda: config, str(config_path))

    result = manager.persist("r1", "r1")

    assert result["result"] == "succeeded"
    assert Path(result["target_path"]).exists()


def test_persistence_manager_detects_saved_difference(tmp_path):
    config_path = tmp_path / "config.yaml"
    config = RootConfig()
    manager = UIPersistenceManager(lambda: config, str(config_path))
    manager.persist("r1", "r1")
    config.sequencer.bpm = 123.0

    assert manager.differs_from_persisted("sequencer.bpm") is True


def test_persistence_manager_treats_empty_file_as_unsaved_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    config = RootConfig()
    manager = UIPersistenceManager(lambda: config, str(config_path))

    assert manager.differs_from_persisted("sequencer.bpm") is True
