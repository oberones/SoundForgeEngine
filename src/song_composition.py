"""Pure, seeded song rendering. All arrangement work runs in a preparation worker."""
from dataclasses import dataclass
import random


@dataclass(frozen=True)
class SectionSpec:
    """Serializable section settings copied from a preset."""
    kind: str
    bars: int
    density: float
    octave: int
    velocity: float


@dataclass(frozen=True)
class SongRequest:
    """Complete immutable musical input; seed also identifies a composition."""
    seed: int
    pattern: str
    sections: tuple[SectionSpec, ...]
    voices: int
    root: int
    intervals: tuple[int, ...]


@dataclass(frozen=True)
class SongNote:
    """Prepared voice event; zero duration means use the active step division."""
    voice: int
    pitch: int
    velocity: float
    duration: float


@dataclass(frozen=True)
class SongMaterial:
    """Quarter-beat lookup tables plus auditable harmony and motif metadata."""
    sections: tuple[tuple[tuple[SongNote, ...], ...], ...]
    harmony: tuple[tuple[int, ...], ...]
    motifs: tuple[tuple[str, tuple[int, ...]], ...]


def harmony_for(request: SongRequest, section_index: int) -> tuple[int, ...]:
    """Return scale-degree roots per bar; blues uses explicit semitone roots."""
    section = request.sections[section_index]
    if request.pattern == 'minimalist' or section.kind == 'intro':
        return (0,) * section.bars
    if request.pattern == 'blues_twelve_bar' and section.bars == 12:
        roots = [0, 0, 0, 0, 5, 5, 0, 0, 7, 5, 0, 7]
        if section_index == len(request.sections) - 2:
            roots[-1] = 0
        return tuple(roots)
    if request.pattern == 'blues_twelve_bar':
        return tuple((0, 5, 7, 0)[i % 4] for i in range(section.bars))
    progression = {'chorus': (0, 4, 5, 3), 'bridge': (5, 3, 1, 4)}.get(
        section.kind, (0, 3, 4, 0))
    return tuple(progression[i % 4] for i in range(section.bars))


def prepare_song(request: SongRequest) -> SongMaterial:
    """Render bounded voices with shared chords, recurring themes and phrase shape.

    Separate random streams prevent expression changes from rewriting themes.
    Non-heptatonic scales interpret degrees cyclically in their supplied scale.
    Register windows never overlap, even at extreme configured MIDI roots.
    """
    motif_rng = random.Random(f'{request.seed}:motif')
    rhythm_rng = random.Random(f'{request.seed}:rhythm')
    expression_rng = random.Random(f'{request.seed}:expression')
    motifs = {kind: tuple([0] + [motif_rng.choice((0, 1, 2, 4)) for _ in range(6)] + [0])
              for kind in ('intro', 'verse', 'chorus', 'bridge', 'instrumental', 'outro')}
    rhythms = {kind: rhythm_rng.choice(((True, False, True, True, False, True, True, False),
                                       (True, True, False, True, True, False, True, False)))
               for kind in motifs}
    intervals = request.intervals

    def degree_pitch(degree):
        """Map an unbounded degree to a pitch without MIDI clipping distortion."""
        return request.root + intervals[degree % len(intervals)] + 12 * (degree // len(intervals))

    center = min(84, max(24, request.root))
    ranges = [(center + 12, center + 23)]
    if request.voices == 2:
        ranges += [(center - 12, center - 1)]
    elif request.voices >= 3:
        ranges += [(center, center + 11)]
        if request.voices == 4:
            ranges += [(center - 12, center - 1)]
        ranges += [(center - 24, center - 13)]
    rendered, harmony = [], []
    occurrences = {}
    for section_index, section in enumerate(request.sections):
        roots = harmony_for(request, section_index)
        harmony.append(roots)
        occurrence = occurrences.get(section.kind, 0)
        occurrences[section.kind] = occurrence + 1
        motif = motifs[section.kind]
        previous = [sum(bounds) // 2 for bounds in ranges]
        steps = []
        for tick in range(section.bars * 16):
            beat = tick / 4
            bar = tick // 16
            phrase_tick = tick % 64
            chord_root = roots[bar]
            blues = request.pattern == 'blues_twelve_bar'
            root_pitch = request.root + chord_root if blues else degree_pitch(chord_root)
            chord = ({(root_pitch + offset) % 12 for offset in (0, 4, 7, 10)} if blues else
                     {degree_pitch(chord_root + offset) % 12 for offset in (0, 2, 4)})
            group = []
            final_bar = section.kind == 'outro' and bar == section.bars - 1
            for voice, (lo, hi) in enumerate(ranges):
                bass = request.voices > 1 and voice == request.voices - 1
                # Bass anchors bars, inner voices answer on beats 0/2 and 1/3.
                if bass and tick % 16:
                    continue
                if voice not in (0, request.voices - 1) and tick % 8 != (0 if voice == 1 else 4):
                    continue
                if voice == 0 and tick % 16:
                    slot = (tick // 2) % 8
                    if phrase_tick >= 32 and occurrence % 3 == 1:
                        slot = (slot + 1) % 8  # Displace only the developed half.
                    ornament = phrase_tick >= 32 and occurrence % 3 == 2
                    if (tick % 2 and not ornament) or not rhythms[section.kind][slot]:
                        continue
                if voice == 0 and phrase_tick >= 60:
                    continue  # Leave one beat of phrase-ending space.
                if tick % 16 and rhythm_rng.random() > section.density:
                    continue
                motif_index = (tick // 2) % 8
                degree = motif[motif_index]
                # Returning themes keep the first half; develop only the second.
                if phrase_tick >= 32:
                    degree += (occurrence + tick // 64) % 3 - 1
                target = degree_pitch(degree) + 12 + section.octave * 12
                pcs = chord
                if bass or final_bar:
                    pcs = {root_pitch % 12} if bass else {request.root % 12}
                candidates = [p for p in range(lo, hi + 1) if p % 12 in pcs]
                # Each twelve-semitone window contains every pitch class.
                pitch = min(candidates, key=lambda p: (abs(p - target) if voice == 0 else abs(p - previous[voice]), p))
                previous[voice] = pitch
                accent = 1.10 if tick % 16 == 0 else .94 if tick % 4 == 0 else .84
                shape = 1.0 + .08 * min(phrase_tick, 48) / 48 - .18 * max(0, phrase_tick - 48) / 16
                velocity = section.velocity * (1 - .08 * voice) * accent * shape
                velocity += expression_rng.uniform(-.025, .025)
                duration = 4.0 if bass else 2.0 if voice else 0.0
                group.append(SongNote(voice, pitch, velocity, duration))
            steps.append(tuple(group))
        rendered.append(tuple(steps))
    return SongMaterial(tuple(rendered), tuple(harmony), tuple(motifs.items()))
