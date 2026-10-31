"""
Tests for Phase 4 features: Scale mapping and probability.
"""

import pytest
import time
from unittest.mock import Mock, call

from state import State, get_state, reset_state
from sequencer import Sequencer, NoteEvent
from scale_mapper import ScaleMapper


@pytest.fixture(autouse=True)
def setup_teardown():
    """Fixture to reset state before each test."""
    reset_state()
    yield


def test_scale_mapper_major_scale():
    mapper = ScaleMapper()
    mapper.set_scale("major", root_note=60)  # C4
    # C, D, E, F, G, A, B
    expected_notes = [60, 62, 64, 65, 67, 69, 71]
    for i, expected in enumerate(expected_notes):
        assert mapper.get_note(i) == expected
    # Test octave
    assert mapper.get_note(7) == 72  # Next C


def test_scale_mapper_pentatonic_minor():
    mapper = ScaleMapper()
    mapper.set_scale("pentatonic_minor", root_note=57)  # A3
    # A, C, D, E, G
    expected_notes = [57, 60, 62, 64, 67]
    notes = mapper.get_notes(5)
    assert notes == expected_notes


def test_sequencer_uses_scale_mapper():
    state = get_state()
    scales = ["pentatonic_minor"]
    state.set('scale_index', 0)
    state.set('root_note', 57)  # A3 to match expected notes
    
    sequencer = Sequencer(state, scales)
    mock_note_callback = Mock()
    sequencer.set_note_callback(mock_note_callback)

    # Force density and probability to 1.0 for deterministic test
    state.set('density', 1.0)
    state.set('note_probability', 1.0)
    
    sequencer.start()
    time.sleep(0.5)  # Let it run for a few steps
    sequencer.stop()

    assert mock_note_callback.call_count > 0
    
    # Expected notes from A minor pentatonic scale starting at A3 (root 57)
    # Sequencer plays on even steps (0, 2, 4, 6), mapping to degrees (0, 1, 2, 3)
    expected_notes = [57, 60, 62, 64] 
    
    for i, mock_call in enumerate(mock_note_callback.call_args_list):
        note_event: NoteEvent = mock_call.args[0]
        assert note_event.note == expected_notes[i]


@pytest.mark.parametrize('sequence_length', [8, 16, 20])
def test_dense_pattern_maps_consecutive_degrees(sequence_length):
    """All-on steps advance scale degrees across full and partial pattern repeats."""
    state = get_state()
    scales = ["pentatonic_minor"]
    state.set('scale_index', 0)
    state.set('root_note', 57)  # A3

    sequencer = Sequencer(state, scales)
    state.set('density', 1.0)
    state.set('note_probability', 1.0)
    state.set('sequence_length', sequence_length)
    sequencer.set_step_pattern(sequencer.get_pattern_preset('all_on'))

    notes = []
    sequencer.set_note_callback(lambda e: notes.append((e.step, e.note)))

    for step in range(sequence_length):
        sequencer._generate_step_note(step)

    # Consecutive A minor pentatonic degrees from A3, spanning four octaves.
    expected_notes = [
        57, 60, 62, 64, 67, 69, 72, 74, 76, 79,
        81, 84, 86, 88, 91, 93, 96, 98, 100, 103,
    ]
    assert notes == list(zip(range(sequence_length), expected_notes[:sequence_length]))
    assert len({note for _, note in notes}) == sequence_length


@pytest.mark.parametrize('sequence_length', [16, 19, 32])
def test_repeated_every_other_matches_default_pattern(sequence_length):
    """The every_other preset and default rhythm produce identical steps and pitches."""
    state = get_state()
    state.set('sequence_length', sequence_length)
    state.set('density', 1.0)
    state.set('note_probability', 1.0)
    sequencer = Sequencer(state, ['major'])

    notes = []
    sequencer.set_note_callback(lambda e: notes.append((e.step, e.note)))
    for step in range(sequence_length):
        sequencer._generate_step_note(step)
    default_notes = notes.copy()
    assert [step for step, _ in default_notes] == list(range(0, sequence_length, 2))

    notes.clear()
    sequencer.set_step_pattern(sequencer.get_pattern_preset('every_other'))
    for step in range(sequence_length):
        sequencer._generate_step_note(step)

    assert notes == default_notes


def test_repeated_sparse_pattern_resets_degrees_at_sequence_boundary():
    """Leading rests and uneven repeats preserve degrees until the sequence wraps."""
    state = get_state()
    state.set('sequence_length', 16)
    state.set('root_note', 57)
    state.set('density', 1.0)
    state.set('note_probability', 1.0)
    sequencer = Sequencer(state, ['pentatonic_minor'])
    sequencer.set_step_pattern([False, True, True])

    notes = []
    sequencer.set_note_callback(lambda e: notes.append((e.step, e.note)))
    state.set('step_position', 15)
    for _ in range(32):
        sequencer._advance_step()

    expected_steps = [1, 2, 4, 5, 7, 8, 10, 11, 13, 14]
    expected_notes = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79]
    assert notes == list(zip(expected_steps, expected_notes)) * 2


def test_density_and_probability_gating():
    state = get_state()
    scales = ["major"]
    sequencer = Sequencer(state, scales)
    mock_note_callback = Mock()
    sequencer.set_note_callback(mock_note_callback)

    # Test with zero density - no notes should be generated
    state.set('density', 0.0)
    state.set('note_probability', 1.0)
    sequencer.start()
    time.sleep(0.5)
    sequencer.stop()
    mock_note_callback.assert_not_called()

    # Test with zero probability - no notes should be generated
    state.set('density', 1.0)
    state.set('note_probability', 0.0)
    sequencer.start()
    time.sleep(0.5)
    sequencer.stop()
    mock_note_callback.assert_not_called()

def test_quantized_scale_change():
    state = get_state()
    scales = ["major", "minor"]
    sequencer = Sequencer(state, scales)
    
    # Set initial scale to major
    state.set('scale_index', 0, source='test')
    sequencer._update_scale_from_state(force=True) # Force immediate update
    assert sequencer.scale_mapper.current_scale_name == "major"

    # Request a change to minor, should be quantized
    state.set('scale_index', 1, source='test')
    assert sequencer._pending_scale_index == 1
    assert sequencer.scale_mapper.current_scale_name == "major" # Still major

    # A pattern wrap is not a musical bar; advance four elapsed quarter notes.
    from sequencer import TickEvent
    for _ in range(4 * sequencer.clock.ppq):
        sequencer._on_tick(TickEvent(0, 0.0))

    # The scale change should have been applied
    assert sequencer._pending_scale_index is None
    assert sequencer.scale_mapper.current_scale_name == "minor"
