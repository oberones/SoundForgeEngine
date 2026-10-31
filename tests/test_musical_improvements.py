"""Deterministic musical contracts, output ownership, and preparation boundaries."""
import random
from dataclasses import replace
from unittest.mock import Mock

import pytest
from fugue import FugueEngine, FugueParams
from fugue_preparation import PreparationRequest, prepare_score
from note_scheduler import NoteScheduler
from scale_mapper import ScaleMapper
from song import SONG_PATTERNS, SongSequencer
from song_composition import SongRequest, SectionSpec, prepare_song, harmony_for
from state import get_state, reset_state


def request(pattern='verse_chorus', voices=3, root=60, seed=1729):
    """Create an explicit musical fixture independent of runtime selection."""
    return SongRequest(seed, pattern,
        tuple(SectionSpec(s.section_type.value, s.bars, s.density, s.octave_shift,
                          s.velocity_factor) for s in SONG_PATTERNS[pattern].sections),
        voices, root, (0, 2, 4, 5, 7, 9, 11))


def test_composition_rng_isolation_replay_and_advancement():
    state = random.getstate()
    a = FugueEngine(ScaleMapper(), seed=32)
    b = FugueEngine(ScaleMapper(), seed=32)
    params = FugueParams()
    first = a.generate_subject(params)
    second = a.generate_subject(params)
    assert first == b.generate_subject(params)
    assert second == b.generate_subject(params)
    assert first != second
    assert random.getstate() == state
    r = request()
    assert prepare_song(r) == prepare_song(r)
    assert prepare_song(r) != prepare_song(replace(r, seed=1730))
    assert random.getstate() == state


@pytest.mark.parametrize('draw,choices', [(0, (-1, 1)), (.599999, (-1, 1)),
    (.6, (-2, 2, -3, 3)), (.899999, (-2, 2, -3, 3)), (.9, (-4, 4, -5, 5))])
def test_interval_branch_boundaries(draw, choices):
    engine = FugueEngine(ScaleMapper(), seed=1)
    seen = []
    def choose(values):
        seen.append(tuple(values))
        return values[0]
    engine.rng.choice = choose
    engine.rng.random = lambda: draw
    engine.generate_subject(FugueParams())
    assert choices in seen
    other = {(-1, 1), (-2, 2, -3, 3), (-4, 4, -5, 5)} - {choices}
    assert all(value not in seen for value in other)


def test_worker_seed_replay():
    req = PreparationRequest(0, 1, 60, 'major', .5, (0, 2, 4, 5, 7, 9, 11), 19)
    assert prepare_score(req) == prepare_score(req)
    assert prepare_score(req) != prepare_score(replace(req, seed=20))


@pytest.mark.parametrize('pattern', SONG_PATTERNS)
@pytest.mark.parametrize('voices', [1, 2, 3, 4])
def test_arrangement_duration_registers_and_harmony(pattern, voices):
    req = request(pattern, voices)
    material = prepare_song(req)
    assert len(material.sections) == len(req.sections)
    for si, (spec, section) in enumerate(zip(req.sections, material.sections)):
        assert len(section) == spec.bars * 16
        held = {}
        for tick, group in enumerate(section):
            for n in group:
                assert 0 <= n.pitch <= 127
                assert n.duration >= 0
                held[n.voice] = n.pitch
            ordered = [held[v] for v in sorted(held)]
            assert ordered == sorted(ordered, reverse=True)
            if tick % 16 == 0 and voices > 1:
                bass = [n for n in group if n.voice == voices - 1]
                assert bass
    if pattern == 'minimalist':
        assert all(set(h) == {0} for h in material.harmony)
    if pattern == 'blues_twelve_bar':
        assert material.harmony[1] == (0, 0, 0, 0, 5, 5, 0, 0, 7, 5, 0, 7)
        assert material.harmony[-2][-1] == 0
    final = material.sections[-1][-16]
    assert all(n.pitch % 12 == req.root % 12 for n in final)


@pytest.mark.parametrize('root', [0, 127])
def test_extreme_roots_remain_valid_without_crossing(root):
    material = prepare_song(request(root=root, voices=4))
    for section in material.sections:
        for group in section:
            assert all(0 <= n.pitch <= 127 for n in group)
            assert [n.pitch for n in group] == sorted((n.pitch for n in group), reverse=True)


def test_repeated_chorus_preserves_first_half_theme():
    r = request('pop_standard')
    m = prepare_song(r)
    choruses = [section for spec, section in zip(r.sections, m.sections) if spec.kind == 'chorus']
    def melody(section, limit):
        return [(tick, n.pitch) for tick, group in enumerate(section[:limit]) for n in group if n.voice == 0]
    # Density can omit weak notes; every shared onset retains the melodic identity.
    first = dict(melody(choruses[0], 32))
    second = dict(melody(choruses[1], 32))
    common = first.keys() & second.keys()
    assert len(common) >= 4
    assert all(first[t] == second[t] for t in common)
    assert melody(choruses[0], 64) != melody(choruses[1], 64)


def test_tonal_cost_distinguishes_resolved_chromatic_neighbor():
    engine = FugueEngine(ScaleMapper(), 1)
    def voice(pitches):
        return [[dict(pitch=p, dur=.5, vel=80) for p in pitches]]
    params = FugueParams()
    assert engine._tonal_cost(voice([72, 73, 72]), params) < engine._tonal_cost(voice([72, 73, 79]), params)
    score = voice([72, 73, 79])
    before = engine._score_counterpoint(score, params)[1]
    after = engine._score_counterpoint(engine._optimize_counterpoint(score, params), params)[1]
    assert after['tonal'] <= before['tonal']


def test_scheduler_retrigger_deadlines_channels_and_broadcast():
    now = [100.0]
    sink = Mock()
    scheduler = NoteScheduler(sink, clock=lambda: now[0])
    scheduler._process((60, 80, 1, 1.0, now[0]))
    now[0] += .5
    scheduler._process((60, 90, 1, 2.0, now[0]))
    assert sink.method_calls[:3] == [
        ('send_note_on', (60, 80, 1), {}), ('send_note_off', (60, 0, 1), {}),
        ('send_note_on', (60, 90, 1), {})]
    now[0] = 101.1
    scheduler._process()
    assert sink.send_note_off.call_count == 1
    scheduler._process((60, 50, 2, 1, now[0]))
    now[0] = 102.5
    scheduler._process()
    assert scheduler._active == {}
    scheduler._process((64, 90, 0, 1, now[0]))
    assert len(scheduler._active) == 16
    scheduler._flush()
    assert scheduler._active == {}


def test_output_queue_is_bounded_and_does_not_send_on_caller():
    sink = Mock()
    scheduler = NoteScheduler(sink)
    for _ in range(2100):
        scheduler.schedule_note(60, 80, 1, 1)
    assert scheduler._commands.qsize() == 2048
    assert scheduler.dropped == 52
    assert scheduler._panic.is_set()
    sink.send_note_on.assert_not_called()


def test_song_waits_for_matching_material_and_adopts_live_scale_at_bar():
    reset_state()
    state = get_state()
    state.set('direction_pattern', 'song')
    mapper = ScaleMapper()
    song = SongSequencer(state, mapper, seed=2)
    assert song.get_next_step_notes(0, beat=0) == []
    assert song._current_pattern is None
    r = song._snapshot()
    song.preparation.ready = (replace(r, seed=r.seed + 1), prepare_song(r))
    assert song.start_new_song() is False
    song.preparation.ready = (r, prepare_song(r))
    assert song.start_new_song()
    mapper.set_scale('minor', 62)
    updated = song._snapshot()
    song.preparation.ready = (updated, prepare_song(updated))
    song.update_transport(3.0)
    assert song._material_request == r
    song.update_transport(4.0)
    assert song._material_request == updated


def test_masks_reset_and_follow_elapsed_steps():
    reset_state()
    state = get_state()
    state.set('direction_pattern', 'song')
    song = SongSequencer(state, ScaleMapper(), seed=2)
    # Force a preset with a sparse intro, independent of random preset selection.
    r = request('minimalist', 1)
    song._next_seed = r.seed
    song._snapshot = lambda: r
    song.preparation.ready = (r, prepare_song(r))
    song.start_new_song()
    onsets = []
    for i in range(8):
        if song.get_next_step_notes(7 - i, beat=i / 4):
            onsets.append(i)
    assert set(onsets) <= {0, 6}
    assert 0 in onsets
    song.force_next_section()
    assert song._section_step == 0
    song._current_section_index = 2
    song._apply_section_settings()
    assert state.get('song_step_pattern') == 'all_on'


def test_standard_probability_does_not_change_expression(monkeypatch):
    from sequencer import Sequencer
    reset_state()
    state = get_state()
    state.update_multiple(dict(density=1, step_pattern=[True], step_probabilities=[.1]))
    seq = Sequencer(state, ['major'])
    notes = []
    seq.set_note_callback(notes.append)
    monkeypatch.setattr('sequencer.random.random', lambda: .05)
    monkeypatch.setattr('sequencer.random.uniform', lambda a, b: .1)
    seq._generate_step_note(0)
    state.set('step_probabilities', [.9])
    seq._generate_step_note(0)
    assert len(notes) == 2
    assert notes[0].velocity == notes[1].velocity
    assert notes[0].duration == notes[1].duration


def test_clock_absolute_deadlines_and_bounded_late_recovery(monkeypatch):
    from sequencer import HighResClock
    from types import SimpleNamespace
    now = [0.0]
    sleeps = []
    events = []
    clock = HighResClock(bpm=120, spin_seconds=0)
    clock._running = True
    def sleep(delay):
        sleeps.append(delay)
        now[0] += delay
        if len(sleeps) == 2:
            now[0] += .2  # A severely late host wakeup must not cause catch-up bursts.
    def callback(event):
        events.append(event)
        if len(events) == 4:
            clock._running = False
    clock.set_tick_callback(callback)
    monkeypatch.setattr('sequencer.time', SimpleNamespace(perf_counter=lambda: now[0], sleep=sleep))
    clock._clock_thread()
    interval = 60 / (120 * 24)
    assert len(sleeps) == 4
    assert events[0].scheduled_timestamp == pytest.approx(interval)
    assert events[1].scheduled_timestamp == pytest.approx(interval * 2)
    assert events[2].scheduled_timestamp == pytest.approx(events[1].timestamp + interval)
    assert all(delay > 0 for delay in sleeps)
    assert HighResClock(spin_seconds=1).spin_seconds == .0005


def test_scheduler_ignores_wall_clock_changes(monkeypatch):
    now = [0.0]
    scheduler = NoteScheduler(Mock(), clock=lambda: now[0])
    scheduler._process((60, 80, 1, 1, 0))
    monkeypatch.setattr('time.time', lambda: -100000)
    now[0] = 1.0
    scheduler._process()
    scheduler.midi_output.send_note_off.assert_called_once_with(60, 0, 1)


def test_exported_midi_uses_live_retrigger_ownership(tmp_path):
    import importlib.util
    from pathlib import Path
    import mido
    spec = importlib.util.spec_from_file_location('music_export',
        Path(__file__).resolve().parents[1] / 'tools/evaluate_generative_music.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    events = [dict(beat=0, duration=2, pitch=60, velocity=80),
              dict(beat=1, duration=2, pitch=60, velocity=90)]
    destination = tmp_path / 'retrigger.mid'
    exporter.write_midi(events, destination, 120)
    tick = 0
    observed = []
    for message in mido.MidiFile(destination).tracks[0]:
        tick += message.time
        if message.type in ('note_on', 'note_off'):
            observed.append((tick, message.type, message.velocity))
    assert observed == [(0, 'note_on', 80), (480, 'note_off', 0),
                        (480, 'note_on', 90), (1440, 'note_off', 0)]
