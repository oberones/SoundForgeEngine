"""Measure local timing during repeated spawned score generation, without MIDI hardware.

Run with .venv/bin/python tools/check_generative_timing.py --seconds 15.
Forced endings shorten compositions for load testing; production rests stay unchanged.
"""
import argparse
import json
import logging
import platform
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from action_handler import ActionHandler
from events import SemanticEvent
from sequencer import Sequencer
from state import get_state, reset_state
from note_scheduler import NoteScheduler


def distribution(values):
    """Summarize measured seconds in milliseconds, without discarding outliers."""
    values = sorted(value * 1000 for value in values)
    if not values:
        return {'count': 0}
    return {'count': len(values), 'p50_ms': values[len(values) // 2],
            'p95_ms': values[min(len(values) - 1, int(len(values) * .95))],
            'p99_ms': values[min(len(values) - 1, int(len(values) * .99))],
            'max_ms': max(values)}


def measure(seconds, voices, generation=True, mode="fugue", spin_seconds=.0005):
    """Exercise clock dispatch, real process preparation, handoff, and button handling."""
    reset_state()
    state = get_state()
    state.update_multiple(dict(bpm=200, swing=0.0, voices=voices,
                               note_division='quarter', direction_pattern=mode))
    seq = Sequencer(state, ['minor', 'major'])
    class Sink:
        """Nonblocking fake MIDI device; queue latency is measured by the scheduler."""
        def send_note_on(self, *args):
            pass
        def send_note_off(self, *args):
            pass
    scheduler = NoteScheduler(Sink())
    scheduler.start()
    seq.set_note_callback(lambda event: scheduler.schedule_note(
        event.note, event.velocity, 1, event.duration) if event.note >= 0 else None)
    seq.clock.spin_seconds = spin_seconds
    handler = ActionHandler(state, seq)
    handler.set_note_callback(seq._note_callback)
    fugue = seq._fugue_sequencer
    song = seq._song_sequencer
    composition = fugue if mode == "fugue" else song
    # Shorten only the benchmark's lifecycle to obtain repeated measured handoffs.
    fugue._rest_duration = 0.0
    callbacks, lateness, inputs = [], [], []
    consumed = None
    handoffs = 0
    original = seq._on_tick

    def record(event):
        """Capture deadline error separately from application callback duration."""
        start = time.perf_counter()
        lateness.append(abs(event.timestamp - event.scheduled_timestamp))
        original(event)
        callbacks.append(time.perf_counter() - start)

    seq.clock.set_tick_callback(record)
    if not generation:
        fugue.start_preparation = lambda: None
        song.start_preparation = lambda: None
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    seq.start()
    deadline = time.perf_counter() + seconds
    try:
        while time.perf_counter() < deadline:
            start = time.perf_counter()
            handler.handle_semantic_event(SemanticEvent('trigger_step', 'button', value=100, raw_note=60))
            inputs.append(time.perf_counter() - start)
            if composition.preparation.consumed is not consumed:
                consumed = composition.preparation.consumed
                handoffs += 1
            if fugue._active_fugue is not None and fugue._fugue_musical_time >= 2:
                fugue._active_fugue = None
                fugue._last_fugue_end = float('-inf')
            if mode == 'song' and song._current_pattern is not None and song._musical_position - song._section_origin >= 2:
                song._current_pattern = None
                song._between_songs = False
            time.sleep(.02)
    finally:
        seq.stop()
        scheduler.stop()
    return dict(mode=mode, spin_seconds=spin_seconds,
                parent_cpu_percent=100 * (time.process_time() - cpu_start) / (time.perf_counter() - wall_start),
                midi_queue_max_ms=scheduler.max_queue_latency * 1000, midi_dropped=scheduler.dropped,
                voices=voices, bpm=seq.clock.bpm, ppq=seq.clock.ppq, swing=seq.clock.swing,
                generation=generation, seconds=seconds, handoffs=handoffs,
                callback=distribution(callbacks), deadline_error=distribution(lateness),
                button_dispatch=distribution(inputs),
                budgets_met=max(lateness, default=0) < .002 and max(inputs, default=0) + scheduler.max_queue_latency < .010 and scheduler.dropped == 0)


def main():
    """Print reproducible environment details and unfiltered local timing results."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--spin-ms', type=float, default=.5, choices=(0, .5))
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    results = [measure(args.seconds, voices, not args.baseline, mode, args.spin_ms / 1000)
               for mode in ('fugue', 'song') for voices in (3, 4)]
    print(json.dumps(dict(platform=platform.platform(), python=sys.version, results=results), indent=2))
    return 0 if all(r['budgets_met'] and (args.baseline or r['handoffs'] >= 2) for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
