from config import RootConfig
from state import get_state, reset_state
from ui_snapshot import UISnapshotTracker


def test_snapshot_tracker_marks_state_changes():
    reset_state()
    tracker = UISnapshotTracker(
        config_provider=lambda: RootConfig(),
        state_provider=get_state,
        active_session_provider=lambda: None,
        start_time=lambda: 0.0,
    )

    get_state().set("bpm", 130.0, source="test")
    snapshot = tracker.build_snapshot()

    assert snapshot["revision"].startswith("r")
    assert "sequencer.bpm" in snapshot["changed_paths"]


def test_snapshot_tracker_detects_path_conflicts():
    reset_state()
    tracker = UISnapshotTracker(
        config_provider=lambda: RootConfig(),
        state_provider=get_state,
        active_session_provider=lambda: None,
        start_time=lambda: 0.0,
    )
    first_revision = tracker.current_revision()
    tracker.mark_paths_changed(["sequencer.bpm"])

    assert tracker.has_conflict(first_revision, "sequencer.bpm") is True
    assert tracker.has_conflict(first_revision, "sequencer.swing") is False
