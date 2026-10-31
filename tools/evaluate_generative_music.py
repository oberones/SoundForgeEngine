"""Export reproducible MIDI and events from current or archived engine source.

Use --source-root with an extracted source revision for genuine baseline evidence.
The archive's Python is imported using the current project's virtual environment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

import mido


def write_midi(events, destination, bpm):
    """Render explicit retrigger semantics on channel 1, matching live ownership."""
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
    actions = []
    for token, e in enumerate(events):
        actions += [(round(e['beat'] * 480), 1, token, e),
                    (round((e['beat'] + e['duration']) * 480), 0, token, e)]
    active = {}
    last = 0
    for tick, attack, token, e in sorted(actions, key=lambda a: a[:3]):
        pitch = e['pitch']
        messages = []
        if attack:
            if pitch in active:
                messages.append(mido.Message('note_off', note=pitch, velocity=0))
            messages.append(mido.Message('note_on', note=pitch, velocity=e['velocity']))
            active[pitch] = token
        elif active.get(pitch) == token:
            messages.append(mido.Message('note_off', note=pitch, velocity=0))
            del active[pitch]
        for message in messages:
            message.time = tick - last
            track.append(message)
            last = tick
    midi.save(destination)


def metrics(events):
    """Measure event-level texture; voice-dependent metrics require known ownership."""
    active = {}
    crossings = strong_dissonance = 0
    previous = {}
    intervals = {}
    for e in events:
        active = {v: prior for v, prior in active.items()
                  if prior['beat'] + prior['duration'] > e['beat']}
        if e['voice'] is not None:
            if e['voice'] in previous:
                interval = abs(e['pitch'] - previous[e['voice']])
                intervals[interval] = intervals.get(interval, 0) + 1
            previous[e['voice']] = e['pitch']
            active[e['voice']] = e
        ordered = [active[v]['pitch'] for v in sorted(active)]
        crossings += sum(a < b for i, a in enumerate(ordered) for b in ordered[i + 1:])
        if e['beat'] % 1 == 0:
            strong_dissonance += sum(abs(a - b) % 12 not in (0, 3, 4, 5, 7, 8, 9)
                                    for i, a in enumerate(ordered) for b in ordered[i + 1:])
    known = all(e['voice'] is not None for e in events)
    return dict(melodic_interval_semitones=intervals if known else None, notes=len(events), end_beat=max((e['beat'] + e['duration'] for e in events), default=0),
                mean_velocity=sum(e['velocity'] for e in events) / max(1, len(events)),
                crossing_observations=crossings if known else None,
                strong_beat_dissonance_observations=strong_dissonance if known else None)


def main():
    """Export presets and fugues with emitted voice identities, provenance and settings."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=1729)
    parser.add_argument('--bpm', type=float, default=120)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--revision', default='working-tree')
    parser.add_argument('--comparison-baseline', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source_root / 'src'))
    from scale_mapper import ScaleMapper
    from song import SONG_PATTERNS, SongSequencer
    from state import get_state, reset_state
    from fugue import FugueEngine, FugueParams
    current = (args.source_root / 'src/song_composition.py').exists()
    if current:
        from song_composition import SongRequest, SectionSpec, prepare_song
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = dict(revision=args.revision, seed=args.seed, bpm=args.bpm,
                    scale='major', root=60, division='eighth', files=[],
                    evidence='Offline events and MIDI; listening and physical MIDI not validated',
                    source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted((args.source_root / 'src').glob('*.py'))})

    def save(name, events, metadata):
        """Persist MIDI, event data and auditable metrics under matching names."""
        events.sort(key=lambda e: (e['beat'], e['voice'] if e['voice'] is not None else -1))
        write_midi(events, args.output / f'{name}.mid', args.bpm)
        payload = dict(events=events, metadata=metadata, metrics=metrics(events))
        (args.output / f'{name}.json').write_text(json.dumps(payload, separators=(',', ':')) + '\n')
        manifest['files'].append(dict(name=name, metrics=payload['metrics'],
            midi_sha256=hashlib.sha256((args.output / f'{name}.mid').read_bytes()).hexdigest()))

    for name, pattern in SONG_PATTERNS.items():
        random.seed(args.seed)  # Legacy source uses the global stream; this tool is isolated.
        reset_state()
        state = get_state()
        state.update_multiple(dict(direction_pattern='song', bpm=args.bpm, voices=3,
                                   note_division='eighth', base_velocity=80, base_gate_length=.8))
        mapper = ScaleMapper()
        song = SongSequencer(state, mapper)
        metadata = dict(pattern=name, section_bars=[s.bars for s in pattern.sections])
        if current:
            r = SongRequest(args.seed, name,
                tuple(SectionSpec(s.section_type.value, s.bars, s.density, s.octave_shift,
                                  s.velocity_factor) for s in pattern.sections),
                3, 60, tuple(mapper.current_scale_intervals))
            material = prepare_song(r)
            song._snapshot = lambda: r
            song.preparation.ready = (r, material)
            song.start_new_song()
            metadata.update(harmony=material.harmony, motifs=material.motifs)
        else:
            song.start_new_song()
            song._current_pattern = pattern
            song._apply_section_settings()
        events = []
        origin = 0.0
        for si, section in enumerate(pattern.sections):
            song._current_section_index = si
            song._section_origin = origin
            song._apply_section_settings()
            # Equal-tempo comparison intentionally disables preset tempo multipliers.
            state.set('bpm', args.bpm)
            for step in range(section.bars * 8):
                beat = origin + step * .5
                if current:
                    # Quantized attacks can come from earlier rows. Keep the voice
                    # attached to the actual emitted event after per-voice selection.
                    notes = song.get_next_step_events(step % 8, beat=beat, beats_per_step=.5, bpm=args.bpm)
                else:
                    notes = [(None, pitch, velocity, duration)
                             for pitch, velocity, duration in song.get_next_step_notes(
                                 step % 8, beat=beat, beats_per_step=.5, bpm=args.bpm)]
                for voice, pitch, velocity, duration in notes:
                    events.append(dict(beat=beat, pitch=pitch, velocity=velocity,
                                       duration=duration * args.bpm / 60, voice=voice))
            origin += section.bars * 4
        save(name, events, metadata)
    for voices in (3, 4):
        random.seed(args.seed)
        engine = FugueEngine(ScaleMapper(), seed=args.seed) if current else FugueEngine(ScaleMapper())
        if not current:
            engine._seed = args.seed
        params = FugueParams(n_voices=voices, key_root=60, mode='major')
        score = engine.render_fugue(engine.generate_subject(params), params)
        events = []
        for vi, voice in enumerate(score):
            beat = 0.0
            for note in voice:
                if note['pitch'] is not None:
                    events.append(dict(beat=beat, pitch=note['pitch'], velocity=note['vel'],
                                       duration=note['dur'], voice=vi))
                beat += note['dur']
        save(f'fugue-{voices}', events, dict(counterpoint=engine._score_counterpoint(score, params)[1]))
    if args.comparison_baseline:
        comparison = args.output / 'comparison'
        comparison.mkdir(exist_ok=True)
        records = []
        for entry in manifest['files']:
            name = entry['name']
            old = json.loads((args.comparison_baseline / f'{name}.json').read_text())['events']
            new = json.loads((args.output / f'{name}.json').read_text())['events']
            # Match per-bar onset counts and mean velocity. Retain raw performances;
            # these thinned variants control density/loudness, not phrase quality.
            groups = []
            for events in (old, new):
                bars = {}
                for event in events:
                    bars.setdefault(int(event['beat'] // 4), []).append(event)
                groups.append(bars)
            targets = {bar: min(len(groups[0].get(bar, [])), len(groups[1].get(bar, [])))
                       for bar in groups[0].keys() | groups[1].keys()}
            for label, bars in zip(('baseline', 'current'), groups):
                matched = []
                rng = random.Random(args.seed)
                for bar in sorted(targets):
                    matched.extend(rng.sample(bars.get(bar, []), targets[bar]))
                mean = sum(e['velocity'] for e in matched) / max(1, len(matched))
                matched = [dict(e, velocity=max(1, min(127, round(e['velocity'] * 80 / max(1, mean)))))
                           for e in matched]
                matched.sort(key=lambda e: e['beat'])
                write_midi(matched, comparison / f'{name}-{label}.mid', args.bpm)
                records.append(dict(name=name, version=label, metrics=metrics(matched)))
        (comparison / 'manifest.json').write_text(json.dumps(dict(
            method='Seeded per-bar thinning to common onset count; mean velocity normalized to 80. Diagnostic variants only.',
            seed=args.seed, files=records), indent=2) + '\n')
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
