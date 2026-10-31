"""Playback regressions from GENERATIVE_ENGINE_REVIEW, driven without hardware."""
from unittest.mock import Mock
import pytest
from state import get_state, reset_state
from sequencer import Sequencer, TickEvent
from song import SongSequencer
from scale_mapper import ScaleMapper
from fugue import FugueEngine, FugueParams


@pytest.fixture
def state():
    reset_state()
    return get_state()


def tick(seq, count):
    """Drive the production clock callback without sleeping."""
    for _ in range(count):
        seq._on_tick(TickEvent(0, 0.0))


def test_song_progresses_with_looping_steps(state):
    song = SongSequencer(state, ScaleMapper())
    song.start_new_song()
    for i in range(4096):
        song.get_next_step_notes(i % 8)
        if song._between_songs or song._current_section_index > 0:
            return
    pytest.fail('Song never advanced')


def test_song_pause_expires_once(state, monkeypatch):
    song = SongSequencer(state, ScaleMapper())
    monkeypatch.setattr('song.time.perf_counter', lambda: 10.0)
    song._start_between_songs()
    monkeypatch.setattr('song.time.perf_counter', lambda: 14.999)
    assert song.get_next_step_notes(0) == []
    monkeypatch.setattr('song.time.perf_counter', lambda: 15.0)
    song.get_next_step_notes(0)
    assert not song._between_songs
    pattern = song._current_pattern
    song.start_new_song = Mock(side_effect=AssertionError('duplicate restart'))
    song.get_next_step_notes(1)
    assert song._current_pattern is pattern


def test_whole_note_gate(state):
    for key, value in dict(bpm=120, note_division='whole', density=1.0,
                           step_probabilities=[1.0], step_pattern=[True],
                           base_gate_length=0.8, gate_length_range=0.0).items():
        state.set(key, value)
    seq = Sequencer(state, ['major'])
    notes = []
    seq.set_note_callback(notes.append)
    seq._generate_step_note(0)
    assert notes[0].duration == pytest.approx(1.6)
    assert seq.clock.bpm == 120


def test_crossing_penalty_matches_register_order():
    engine = FugueEngine(ScaleMapper())
    def cost(a, b):
        score = [[dict(pitch=p, dur=2.0, vel=80)] for p in (a, b)]
        return engine._score_counterpoint(score, FugueParams())[1]
    assert cost(76, 67)['cross'] == 0
    assert cost(67, 76)['cross'] > 0


@pytest.mark.parametrize('direction', ['forward', 'backward', 'ping_pong', 'random'])
def test_scale_quantization_uses_elapsed_bar(state, direction):
    state.set('note_division', 'sixteenth')
    state.set('sequence_length', 8)
    state.set('direction_pattern', direction)
    seq = Sequencer(state, ['major', 'minor'])
    state.set('scale_index', 1)
    tick(seq, 95)
    assert seq.scale_mapper.current_scale_name == 'major'
    tick(seq, 1)
    assert seq.scale_mapper.current_scale_name == 'minor'


def prepared(seq, voices):
    """Install a fixed worker result to isolate timing from composition randomness."""
    from fugue_preparation import compile_score
    fugue = seq._fugue_sequencer
    fugue.preparation.ready = (fugue._snapshot(), compile_score(voices))


def note(pitch, dur=1.0):
    """Build a fixed score note or rest."""
    return dict(pitch=pitch, vel=80, dur=dur)


@pytest.mark.parametrize('division,beats', [('whole', 4), ('half', 2), ('quarter', 1),
                                          ('eighth', .5), ('sixteenth', .25)])
@pytest.mark.parametrize('length', [8, 16])
def test_parent_complete_song_and_restart(state, monkeypatch, division, beats, length):
    from song import SongPattern, SongSection, SectionType
    pattern = SongPattern('fixture', [SongSection(SectionType.VERSE, 1, 1.0),
                                     SongSection(SectionType.CHORUS, 1, 1.0)], 1.0)
    monkeypatch.setattr('song.SONG_PATTERNS', {'fixture': pattern})
    wall = [100.0]
    monkeypatch.setattr('song.time.perf_counter', lambda: wall[0])
    for key, value in dict(bpm=120, note_division=division, direction_pattern='song',
                           sequence_length=length, base_gate_length=.8).items():
        state.set(key, value)
    seq = Sequencer(state, ['major'])
    events = []
    seq.set_note_callback(events.append)
    seq._generate_step_note(0)
    assert events[0].duration == pytest.approx(beats * .5 * .8)
    tick(seq, 95)
    assert seq._song_sequencer._current_section_index == 0
    tick(seq, 1)
    assert seq._song_sequencer._current_section_index == 1
    tick(seq, 96)
    assert seq._song_sequencer._between_songs
    count = len(events)
    wall[0] += 4.999
    tick(seq, 96)
    assert len(events) == count
    wall[0] += .001
    tick(seq, 96)
    assert not seq._song_sequencer._between_songs
    assert len(events) > count


@pytest.mark.parametrize('division', ['whole', 'half', 'quarter', 'eighth', 'sixteenth'])
def test_fugue_score_onsets_ignore_pattern_division(state, division):
    state.set('direction_pattern', 'fugue')
    state.set('note_division', division)
    state.set('bpm', 120)
    seq = Sequencer(state, ['major'])
    prepared(seq, [[note(60), note(62)], [note(None, .5), note(67, 1.5)]])
    events = []
    seq.set_note_callback(lambda event: events.append((seq._transport_ticks, event)))
    seq._generate_step_note(0)
    tick(seq, 24)
    assert [(t, e.note) for t, e in events] == [(0, 60), (12, 67), (24, 62)]
    assert events[0][1].duration == .5
    assert seq._fugue_sequencer._active_fugue is not None
    tick(seq, 24)
    assert seq._fugue_sequencer._active_fugue is None


def test_live_controls_preserve_transport_and_latch_division(state):
    state.set('note_division', 'quarter')
    state.set('bpm', 120)
    seq = Sequencer(state, ['major'])
    seq._started_once = True
    tick(seq, 12)
    state.set('note_division', 'whole')
    state.set('bpm', 90)
    assert seq._ticks_per_step == 24
    assert seq.clock.bpm == 90
    tick(seq, 12)
    assert seq._current_step == 1
    assert seq._ticks_per_step == 96
    assert seq._transport_ticks == 24
    tick(seq, 95)
    assert seq._current_step == 1
    tick(seq, 1)
    assert seq._current_step == 2


def test_fugue_late_stale_results_and_bar_handoff(state, monkeypatch):
    state.set('direction_pattern', 'fugue')
    seq = Sequencer(state, ['major'])
    fugue = seq._fugue_sequencer
    notes = []
    seq.set_note_callback(notes.append)
    # There is no synchronous generation fallback.
    monkeypatch.setattr(FugueEngine, 'render_fugue', Mock(side_effect=AssertionError('render on clock')))
    seq._generate_step_note(0)
    tick(seq, 5)
    prepared(seq, [[note(60)]])
    old = fugue.preparation.ready
    state.set('voices', 4)
    tick(seq, 91)
    assert not notes  # Stale result rejected at beat four.
    prepared(seq, [[note(62)]])
    tick(seq, 96)
    assert [n.note for n in notes] == [62]
    assert fugue.preparation.consumed is not old


def test_restart_does_not_duplicate_initial_event(state, monkeypatch):
    seq = Sequencer(state, ['major'])
    monkeypatch.setattr(seq.clock, 'start', Mock())
    monkeypatch.setattr(seq.clock, 'stop', Mock())
    monkeypatch.setattr(seq._fugue_sequencer, 'start_preparation', Mock())
    monkeypatch.setattr(seq._fugue_sequencer, 'stop_preparation', Mock())
    generate = Mock()
    monkeypatch.setattr(seq, '_generate_step_note', generate)
    seq.start()
    tick(seq, 3)
    seq.stop()
    seq.start()
    assert generate.call_count == 1
    assert seq._transport_ticks == 3


@pytest.mark.parametrize('ranges', [None, [(72, 84), (60, 72)]])
def test_optimizer_preserves_ordered_fixture(ranges):
    engine = FugueEngine(ScaleMapper())
    params = FugueParams(n_voices=2, ranges=ranges)
    score = [[note(76, 2), note(77, 2)], [note(67, 2), note(69, 2)]]
    optimized = engine._optimize_counterpoint(score, params)
    assert engine._score_counterpoint(optimized, params)[1]['cross'] == 0


@pytest.mark.parametrize('division', ['whole', 'half', 'quarter', 'eighth', 'sixteenth'])
@pytest.mark.parametrize('length', [8, 16])
def test_bar_changes_with_any_division_and_length(state, division, length):
    state.update_multiple(dict(note_division=division, sequence_length=length))
    seq = Sequencer(state, ['major', 'minor'])
    state.set('scale_index', 1)
    tick(seq, 95)
    assert seq.scale_mapper.current_scale_name == 'major'
    tick(seq, 1)
    assert seq.scale_mapper.current_scale_name == 'minor'


def test_fugue_live_tempo_division_and_off_grid_event(state):
    state.update_multiple(dict(direction_pattern='fugue', bpm=120, note_division='whole'))
    seq = Sequencer(state, ['major'])
    prepared(seq, [[note(None, .1), note(60, .9), note(62, 1)]] )
    events = []
    seq.set_note_callback(lambda event: events.append((seq._transport_ticks, event)))
    seq._generate_step_note(0)
    tick(seq, 2)
    assert not events
    tick(seq, 1)
    assert events[0][0] == 3  # ceil(.1 * 24), not whole-note quantization
    assert events[0][1].duration == pytest.approx(.45)
    state.set('bpm', 60)
    state.set('note_division', 'sixteenth')
    tick(seq, 21)
    assert events[1][0] == 24
    assert events[1][1].duration == 1.0


def test_fugue_final_rest_and_pause_boundary(state, monkeypatch):
    state.set('direction_pattern', 'fugue')
    seq = Sequencer(state, ['major'])
    fugue = seq._fugue_sequencer
    wall = [100.0]
    monkeypatch.setattr('fugue.time.perf_counter', lambda: wall[0])
    prepared(seq, [[note(60), note(None, 3)]])
    seq.set_note_callback(Mock())
    seq._generate_step_note(0)
    tick(seq, 95)
    assert fugue._active_fugue is not None
    tick(seq, 1)
    assert fugue._active_fugue is None
    assert fugue._last_fugue_end == 100.0
    prepared(seq, [[note(62)]])
    wall[0] = 109.999
    tick(seq, 96)
    assert fugue._active_fugue is None
    wall[0] = 110.0
    tick(seq, 95)
    assert fugue._active_fugue is None
    tick(seq, 1)
    assert fugue._active_fugue is not None


def test_forced_song_section_establishes_new_origin(state):
    song = SongSequencer(state, ScaleMapper())
    song.start_new_song()
    song.update_transport(1.5)
    song.force_next_section()
    index = song._current_section_index
    bars = song._current_pattern.sections[index].bars
    song.update_transport(1.5 + bars * 4 - 1/24)
    assert song._current_section_index == index
    song.update_transport(1.5 + bars * 4)
    assert song._current_section_index == index + 1


def test_song_initial_tempo_factor_sets_gate(state, monkeypatch):
    from song import SongPattern, SongSection, SectionType
    monkeypatch.setattr('song.SONG_PATTERNS', {'fixture': SongPattern(
        'fixture', [SongSection(SectionType.VERSE, 1, 1, tempo_factor=.5)], 1)})
    state.update_multiple(dict(bpm=120, direction_pattern='song', note_division='quarter'))
    seq = Sequencer(state, ['major'])
    notes = []
    seq.set_note_callback(notes.append)
    seq._generate_step_note(0)
    assert seq.clock.bpm == 60
    assert notes[0].duration == pytest.approx(.8)


@pytest.fixture(autouse=True)
def prepared_song_fixture(monkeypatch):
    """Prepare controlled songs outside callbacks; worker lateness is tested separately."""
    from song_composition import prepare_song
    original = SongSequencer.start_new_song
    def start(song):
        request = song._snapshot()
        if request is None:
            song.state.set('direction_pattern', 'song')
            request = song._snapshot()
        song.preparation.ready = (request, prepare_song(request))
        return original(song)
    monkeypatch.setattr(SongSequencer, 'start_new_song', start)
