"""Song attacks survive live step-phase changes through the production transport."""
from collections import Counter
from dataclasses import replace

import pytest

from sequencer import Sequencer, TickEvent
from song import SONG_PATTERNS, SongPattern, SongSection, SectionType
from song_composition import SongMaterial, SongNote, prepare_song
from state import get_state, reset_state


def tick(seq, count):
    """Advance the production callback without starting a wall-clock thread."""
    for _ in range(count):
        seq._on_tick(TickEvent(0, 0.0))


def prepared_sequencer(monkeypatch, pattern, voices=3):
    """Prepare a deterministic song outside the clock callback, as a worker would."""
    monkeypatch.setattr('song.SONG_PATTERNS', {'fixture': pattern})
    reset_state()
    state = get_state()
    state.update_multiple(dict(direction_pattern='song', note_division='sixteenth',
                               bpm=120, voices=voices, base_gate_length=.8))
    seq = Sequencer(state, ['major'])
    song = seq._song_sequencer
    song._next_seed = 1729
    request = song._snapshot()
    song.preparation.ready = (request, prepare_song(request))
    events = []
    seq.set_note_callback(lambda event: events.append((seq._transport_ticks, event)))
    seq._started_once = True
    return state, seq, song, events


@pytest.mark.parametrize('division,interval', [('eighth', 12), ('quarter', 24),
                                              ('half', 48), ('whole', 96)])
@pytest.mark.parametrize('change_tick', [6, 18, 42, 90])
@pytest.mark.parametrize('voices', [3, 4])
def test_live_division_preserves_attacks_across_song_sections(monkeypatch, division,
                                                            interval, change_tick, voices):
    """Off-grid division changes keep the intro, verse and chorus audible."""
    state, seq, song, events = prepared_sequencer(monkeypatch, SONG_PATTERNS['verse_chorus'], voices)
    seq._generate_step_note(0)
    assert len(events) == 3
    tick(seq, change_tick - 1)
    state.set('note_division', division)
    assert seq._active_division == 'sixteenth'
    tick(seq, 1)
    assert seq._active_division == division
    tick(seq, 100 * 24 - change_tick)
    assert song._current_section_index == 2  # Intro -> verse -> chorus.
    # Every subsequent bar retains its bass anchor, including section starts.
    for bar in range(1, 25):
        assert any(bar * 96 <= t < (bar + 1) * 96 and event.note < 48
                   for t, event in events), f'Missing bass in bar {bar}'
    assert all((t - change_tick) % interval == 0 for t, _ in events if t >= change_tick)
    assert max(Counter(t for t, _ in events).values()) <= voices
    assert all(event.duration > 0 for _, event in events)


def install_rows(song, rows):
    """Replace worker material with a small, auditable attack timeline."""
    request, _ = song.preparation.ready
    tables = tuple(tuple(tuple(rows.get(row, ())) for row in range(section.bars * 16))
                   for section in request.sections)
    song.preparation.ready = (request, SongMaterial(tables, (), ()))


def test_coarse_to_fine_change_consumes_crossed_attacks_once(monkeypatch):
    """The shorter new division must not discard the preceding long interval."""
    pattern = SongPattern('fixture', [SongSection(SectionType.VERSE, 1, 1.0),
                                     SongSection(SectionType.CHORUS, 1, 1.0)], 1)
    state, seq, song, events = prepared_sequencer(monkeypatch, pattern, voices=2)
    install_rows(song, {
        0: [SongNote(0, 72, 1, 0), SongNote(1, 60, 1, 4)],
        2: [SongNote(0, 74, 1, 0)],
        3: [SongNote(0, 75, 1, 0)],
        4: [SongNote(1, 62, 1, 2)],
        5: [SongNote(0, 77, 1, 0)],
    })
    seq._generate_step_note(0)
    tick(seq, 1)
    state.set('note_division', 'quarter')
    tick(seq, 5)
    assert len(events) == 2  # No replay of the initial attacks at beat .25.
    tick(seq, 1)
    state.set('note_division', 'sixteenth')
    tick(seq, 23)
    assert [(t, e.note) for t, e in events] == [(0, 72), (0, 60), (30, 77), (30, 62)]
    assert events[2][1].duration == pytest.approx(.1)  # Newly active sixteenth gate.
    assert events[3][1].duration == pytest.approx(.8)
    tick(seq, 6)
    assert len(events) == 4  # Empty row after the handoff stays silent.
    tick(seq, 60)
    assert [(t, e.note) for t, e in events[-2:]] == [(96, 72), (96, 60)]


def test_forced_sections_reset_attack_cursor_and_mask(monkeypatch):
    """A forced section starts a fresh attack window and an active mask step."""
    section = SongSection(SectionType.VERSE, 1, 1.0, step_pattern='every_other')
    pattern = SongPattern('fixture', [section, replace(section)], 1)
    state, seq, song, events = prepared_sequencer(monkeypatch, pattern, voices=1)
    install_rows(song, {0: [SongNote(0, 72, 1, 0)], 2: [SongNote(0, 74, 1, 0)]})
    seq._generate_step_note(0)
    tick(seq, 1)
    state.set('note_division', 'quarter')
    tick(seq, 29)  # Active step 2 consumes the attack at beat .5.
    assert [(t, e.note) for t, e in events] == [(0, 72), (30, 74)]
    song.force_next_section()
    tick(seq, 24)  # The new section's first callback consumes its opening attacks.
    assert [(t, e.note) for t, e in events] == [(0, 72), (30, 74), (54, 74)]
    count = len(events)
    tick(seq, 24)
    tick(seq, 24)
    assert len(events) == count  # Rest rows do not repeat the previous attack.


def test_masked_attacks_are_not_deferred(monkeypatch):
    """Crossed attacks on a masked step are discarded before the next active step."""
    section = SongSection(SectionType.VERSE, 2, 1.0, step_pattern='every_other')
    state, seq, song, events = prepared_sequencer(
        monkeypatch, SongPattern('fixture', [section], 1), voices=1)
    install_rows(song, {0: [SongNote(0, 72, 1, 0)], 6: [SongNote(0, 74, 1, 0)]})
    seq._generate_step_note(0)
    tick(seq, 1)
    state.set('note_division', 'quarter')
    tick(seq, 77)  # Beat 1.5 falls in masked step 3, then active step 4 is empty.
    assert [(t, e.note) for t, e in events] == [(0, 72)]


def test_forced_off_grid_section_does_not_emit_future_attacks(monkeypatch):
    """A section forced between sixteenths must wait until each attack is due."""
    section = SongSection(SectionType.VERSE, 1, 1.0)
    _, seq, song, events = prepared_sequencer(
        monkeypatch, SongPattern('fixture', [section, replace(section)], 1), voices=1)
    install_rows(song, {0: [SongNote(0, 72, 1, 0)], 1: [SongNote(0, 74, 1, 0)]})
    seq._generate_step_note(0)
    tick(seq, 2)
    song.force_next_section()
    tick(seq, 4)
    assert [(t, e.note) for t, e in events] == [(0, 72), (6, 72)]
    tick(seq, 6)
    assert [(t, e.note) for t, e in events] == [(0, 72), (6, 72), (12, 74)]
