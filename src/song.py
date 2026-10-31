"""Song mode sequencer for structured compositions.

Generates complete songs using common song structures (intro-verse-chorus patterns)
with the configured number of voices, BPM, scale, and other sequencer settings.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass, replace
from enum import Enum
import time
import random
import logging
from state import State
from scale_mapper import ScaleMapper
from musical_time import step_beats
from rhythm import PATTERNS
from fugue_preparation import ScorePreparation
from song_composition import SectionSpec, SongRequest, prepare_song
from note_utils import format_note_with_number, format_rest

log = logging.getLogger(__name__)


class SongEvent(NamedTuple):
    """Emitted attack with stable voice identity and playback duration in seconds."""
    voice: int
    pitch: int
    velocity: int
    duration: float


class SectionType(Enum):
    """Types of song sections."""
    INTRO = "intro"
    VERSE = "verse"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    OUTRO = "outro"
    INSTRUMENTAL = "instrumental"


@dataclass
class SongSection:
    """Represents a section of a song."""
    section_type: SectionType
    bars: int  # Length in bars
    density: float  # Note density for this section (0.0-1.0)
    tempo_factor: float = 1.0  # Tempo multiplier relative to base BPM
    octave_shift: int = 0  # Octave shift for this section
    velocity_factor: float = 1.0  # Velocity multiplier
    step_pattern: Optional[str] = None  # Override step pattern for this section


@dataclass
class SongPattern:
    """Defines a complete song structure."""
    name: str
    sections: List[SongSection]
    estimated_duration_minutes: float


# Common song patterns used in popular music
SONG_PATTERNS = {
    "verse_chorus": SongPattern(
        name="Verse-Chorus",
        sections=[
            SongSection(SectionType.INTRO, bars=8, density=0.6, velocity_factor=0.8),
            SongSection(SectionType.VERSE, bars=16, density=0.7),
            SongSection(SectionType.CHORUS, bars=16, density=0.9, velocity_factor=1.2),
            SongSection(SectionType.VERSE, bars=16, density=0.7),
            SongSection(SectionType.CHORUS, bars=16, density=0.9, velocity_factor=1.2),
            SongSection(SectionType.OUTRO, bars=8, density=0.5, velocity_factor=0.7),
        ],
        estimated_duration_minutes=2.5
    ),
    
    "aaba": SongPattern(
        name="AABA (32-Bar Form)",
        sections=[
            SongSection(SectionType.INTRO, bars=4, density=0.5, velocity_factor=0.8),
            SongSection(SectionType.VERSE, bars=8, density=0.8, step_pattern="syncopated"),  # A
            SongSection(SectionType.VERSE, bars=8, density=0.8, octave_shift=0),  # A
            SongSection(SectionType.BRIDGE, bars=8, density=0.9, octave_shift=1, velocity_factor=1.3),  # B
            SongSection(SectionType.VERSE, bars=8, density=0.8, octave_shift=0),  # A
            SongSection(SectionType.OUTRO, bars=4, density=0.4, velocity_factor=0.6),
        ],
        estimated_duration_minutes=1.8
    ),
    
    "verse_chorus_bridge": SongPattern(
        name="Verse-Chorus-Bridge",
        sections=[
            SongSection(SectionType.INTRO, bars=8, density=0.5, velocity_factor=0.7),
            SongSection(SectionType.VERSE, bars=16, density=0.7),
            SongSection(SectionType.CHORUS, bars=16, density=0.9, velocity_factor=1.2),
            SongSection(SectionType.VERSE, bars=16, density=0.7, octave_shift=0),
            SongSection(SectionType.CHORUS, bars=16, density=0.9, velocity_factor=1.2),
            SongSection(SectionType.BRIDGE, bars=12, density=0.8, octave_shift=1, tempo_factor=0.9),
            SongSection(SectionType.CHORUS, bars=16, density=1.0, velocity_factor=1.3),
            SongSection(SectionType.OUTRO, bars=8, density=0.4, velocity_factor=0.6),
        ],
        estimated_duration_minutes=3.2
    ),
    
    "blues_twelve_bar": SongPattern(
        name="12-Bar Blues",
        sections=[
            SongSection(SectionType.INTRO, bars=4, density=0.6, velocity_factor=0.8),
            SongSection(SectionType.VERSE, bars=12, density=0.8, step_pattern="syncopated"),  # First 12-bar
            SongSection(SectionType.VERSE, bars=12, density=0.8, velocity_factor=1.1),  # Second 12-bar
            SongSection(SectionType.INSTRUMENTAL, bars=12, density=0.9, velocity_factor=1.2),  # Solo
            SongSection(SectionType.VERSE, bars=12, density=0.8, velocity_factor=1.0),  # Final 12-bar
            SongSection(SectionType.OUTRO, bars=4, density=0.5, velocity_factor=0.7),
        ],
        estimated_duration_minutes=2.1
    ),
    
    "pop_standard": SongPattern(
        name="Pop Standard",
        sections=[
            SongSection(SectionType.INTRO, bars=8, density=0.6, velocity_factor=0.8),
            SongSection(SectionType.VERSE, bars=16, density=0.7),
            SongSection(SectionType.CHORUS, bars=16, density=0.9, velocity_factor=1.2),
            SongSection(SectionType.VERSE, bars=16, density=0.7),
            SongSection(SectionType.CHORUS, bars=16, density=0.9, velocity_factor=1.2),
            SongSection(SectionType.BRIDGE, bars=8, density=0.8, octave_shift=1),
            SongSection(SectionType.CHORUS, bars=16, density=1.0, velocity_factor=1.3),
            SongSection(SectionType.CHORUS, bars=16, density=0.9, velocity_factor=1.1),  # Repeat chorus
            SongSection(SectionType.OUTRO, bars=8, density=0.4, velocity_factor=0.6),
        ],
        estimated_duration_minutes=3.5
    ),
    
    "minimalist": SongPattern(
        name="Minimalist",
        sections=[
            SongSection(SectionType.INTRO, bars=16, density=0.3, velocity_factor=0.7, step_pattern="sparse"),
            SongSection(SectionType.VERSE, bars=32, density=0.5, step_pattern="every_other"),
            SongSection(SectionType.BRIDGE, bars=16, density=0.7, octave_shift=1),
            SongSection(SectionType.VERSE, bars=32, density=0.6, velocity_factor=1.1),
            SongSection(SectionType.OUTRO, bars=16, density=0.2, velocity_factor=0.5, step_pattern="sparse"),
        ],
        estimated_duration_minutes=4.0
    )
}


class SongSequencer:
    """Manages song-structured compositions using common song patterns."""
    
    def __init__(self, state: State, scale_mapper: ScaleMapper, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self._next_seed = self.rng.getrandbits(64)
        self._material = None
        self._material_request = None
        self._section_step = 0
        self._next_section_row = 0
        self.preparation = ScorePreparation(self._snapshot, prepare=prepare_song, name="song")
        self.state = state
        self.scale_mapper = scale_mapper
        
        # Song state
        self._current_pattern: Optional[SongPattern] = None
        self._current_section_index = 0
        self._section_start_time = 0.0
        self._section_bar_count = 0
        self._song_start_time = 0.0
        self._between_songs = False
        self._between_songs_start = 0.0
        self._base_bpm = 120.0
        self._base_density = 0.8
        self._base_velocity = 80
        self._base_velocity_range = 40
        self._base_gate_length = 0.8
        self._base_gate_length_range = 0.3
        
        self._musical_position = 0.0
        self._section_origin = 0.0
        self._standalone_position = 0.0
        self._step_beats = step_beats(state.get("note_division", "sixteenth"))

        log.info("song_sequencer_initialized")
    
    def _snapshot(self) -> Optional[SongRequest]:
        """Snapshot upcoming work; selection depends only on composition identity."""
        if self.state.get('direction_pattern', 'song') != 'song':
            return None
        if self._current_pattern is not None and self._material_request is not None:
            updated = replace(self._material_request,
                voices=max(1, min(4, self.state.get('voices', 1))),
                root=self.scale_mapper.root_note,
                intervals=tuple(self.scale_mapper.current_scale_intervals))
            if updated != self._material_request:
                return updated
        name = random.Random(self._next_seed).choice(tuple(SONG_PATTERNS))
        pattern = SONG_PATTERNS[name]
        return SongRequest(self._next_seed, name,
            tuple(SectionSpec(s.section_type.value, s.bars, s.density, s.octave_shift,
                              s.velocity_factor) for s in pattern.sections),
            max(1, min(4, self.state.get('voices', 1))), self.scale_mapper.root_note,
            tuple(self.scale_mapper.current_scale_intervals))

    def start_preparation(self) -> None:
        """Start process preparation from the parent lifecycle, never from a tick."""
        self.preparation.start()

    def stop_preparation(self) -> None:
        """Join the coordinator outside the clock thread."""
        self.preparation.stop()

    def start_new_song(self) -> bool:
        """Adopt a matching prepared song, or stay silent while preparation catches up."""
        ready = self.preparation.ready
        if ready is None or ready is self.preparation.consumed or ready[0] != self._snapshot():
            self.preparation.waiting = True
            return False
        self.preparation.consumed = ready
        self.preparation.waiting = False
        self._material_request, self._material = ready
        self._next_seed = self.rng.getrandbits(64)
        self._between_songs = False
        self._section_origin = self._musical_position
        
        # Select a random pattern
        pattern_name = self._material_request.pattern
        self._current_pattern = SONG_PATTERNS[pattern_name]
        self._current_section_index = 0
        self._section_start_time = time.perf_counter()
        self._section_bar_count = 0
        self._song_start_time = self._section_start_time
        self._between_songs = False
        
        # Store base values from current state
        self._base_bpm = self.state.get('bpm', 120.0)
        self._base_density = self.state.get('density', 0.8)
        self._base_velocity = self.state.get('base_velocity', 80)
        self._base_velocity_range = self.state.get('velocity_range', 40)
        self._base_gate_length = self.state.get('base_gate_length', 0.8)
        self._base_gate_length_range = self.state.get('gate_length_range', 0.3)
        
        # Apply first section settings
        self._apply_section_settings()
        
        log.info(f"song_started pattern={pattern_name} estimated_duration={self._current_pattern.estimated_duration_minutes:.1f}min sections={len(self._current_pattern.sections)}")
        return True
    
    def _apply_section_settings(self):
        """Apply section settings and reset its rhythm and prepared-attack cursors."""
        if not self._current_pattern or self._current_section_index >= len(self._current_pattern.sections):
            return
        
        section = self._current_pattern.sections[self._current_section_index]
        
        # Apply tempo changes
        new_bpm = self._base_bpm * section.tempo_factor
        self.state.set('bpm', new_bpm, source='song_mode')
        
        # Apply density changes
        new_density = min(1.0, max(0.1, section.density))
        self.state.set('density', new_density, source='song_mode')
        
        self._section_step = 0
        self._next_section_row = 0
        self.state.set('song_step_pattern', section.step_pattern or 'all_on', source='song_mode')
        
        # Log section change
        section_info = f"section={section.section_type.value} bars={section.bars} density={section.density:.2f} tempo_factor={section.tempo_factor:.2f}"
        if section.octave_shift != 0:
            section_info += f" octave_shift={section.octave_shift:+d}"
        if section.velocity_factor != 1.0:
            section_info += f" velocity_factor={section.velocity_factor:.2f}"
        
        log.info(f"song_section_started {section_info}")
    
    def update_transport(self, beat: float) -> None:
        """Advance section boundaries from elapsed beats, even between pattern steps."""
        self._musical_position = beat
        ready = self.preparation.ready
        if (ready is not None and ready is not self.preparation.consumed
                and self._material_request is not None
                and ready[0].seed == self._material_request.seed
                and ready[0] == self._snapshot() and abs(beat % 4) < 1e-9):
            self._material_request, self._material = ready
            self.preparation.consumed = ready
        self._check_section_advancement(beat)

    def get_next_step_notes(self, step: int, beat: Optional[float] = None,
                            beats_per_step: Optional[float] = None,
                            bpm: Optional[float] = None) -> List[Tuple[int, int, float]]:
        """Emit playback triples using the same event consumption as identity-aware callers."""
        return [(event.pitch, event.velocity, event.duration)
                for event in self.get_next_step_events(step, beat, beats_per_step, bpm)]

    def get_next_step_events(self, step: int, beat: Optional[float] = None,
                             beats_per_step: Optional[float] = None,
                             bpm: Optional[float] = None) -> List[SongEvent]:
        """Consume a step with voice identities; standalone calls advance elapsed time.

        This is an alternative to get_next_step_notes, not a second read of a step.
        Both APIs advance the same transport and prepared-attack cursors.
        """
        self._step_beats = (beats_per_step if beats_per_step is not None else
                            step_beats(self.state.get('note_division', 'sixteenth')))
        self._playback_bpm = bpm if bpm is not None else self.state.get('bpm', 120.0)
        if beat is None:
            beat = self._standalone_position
            self._standalone_position += self._step_beats
        self._musical_position = beat
        previous_bpm = self.state.get('bpm', 120.0)
        if self._between_songs:
            if time.perf_counter() - self._between_songs_start < 5.0:
                return []
            if not self.start_new_song():
                return []
        if not self._current_pattern:
            if self.start_new_song() is False:
                return []
        self._check_section_advancement(beat)
        if self._between_songs:
            return []
        if self.state.get('bpm', 120.0) != previous_bpm:
            self._playback_bpm = self.state.get('bpm', 120.0)
        return self._generate_section_events(step)

    def _check_section_advancement(self, beat: float) -> None:
        """Complete sections at their elapsed 4/4 boundaries, never at pattern wraps."""
        if not self._current_pattern:
            return
        while self._current_section_index < len(self._current_pattern.sections):
            section = self._current_pattern.sections[self._current_section_index]
            elapsed = beat - self._section_origin
            self._section_bar_count = int(elapsed // 4)
            if elapsed < section.bars * 4:
                return
            self._section_origin += section.bars * 4
            self._current_section_index += 1
            self._section_start_time = time.perf_counter()
            self._section_bar_count = 0
            if self._current_section_index < len(self._current_pattern.sections):
                self._apply_section_settings()
        log.info("song_completed pattern=%s", self._current_pattern.name)
        self._start_between_songs()

    def _start_between_songs(self):
        """Start the pause between songs."""
        self._between_songs = True
        self._between_songs_start = time.perf_counter()
        self._current_pattern = None
        self._current_section_index = 0
        
        # Reset state to base values
        self.state.set('bpm', self._base_bpm, source='song_mode')
        self.state.set('density', self._base_density, source='song_mode')
        
        log.info("song_between_songs_started duration=5.0s")
    
    def _generate_section_events(self, step: int) -> List[SongEvent]:
        """Quantize crossed attacks, retaining each emitted event's voice identity.

        Live division changes retain the parent's step phase, so callbacks need
        not land on prepared attacks. Consume rows through the current beat once,
        including muted steps, keeping the latest attack per voice. Scan at most
        one whole-note interval (16 rows), the longest supported division, to bound
        work even after a playback gap.
        """
        if self._material is None or self._current_pattern is None:
            return []
        section = self._current_pattern.sections[self._current_section_index]
        mask = PATTERNS[section.step_pattern or 'all_on']
        active = mask[self._section_step % len(mask)]
        self._section_step += 1
        elapsed = max(0.0, self._musical_position - self._section_origin)
        table = self._material.sections[self._current_section_index]
        # Floor, rather than round, so an off-grid section origin cannot cause
        # an attack to play before its prepared onset.
        end = min(len(table), int(elapsed * 4 + 1e-9) + 1)
        start = max(self._next_section_row, end - 16)
        self._next_section_row = max(self._next_section_row, end)
        if not active:
            return []
        voices = {}
        for index in range(start, end):
            for note in table[index]:
                voices[note.voice] = note
        bpm = getattr(self, '_playback_bpm', self.state.get('bpm', 120.0))
        remaining = section.bars * 4 - elapsed
        return [SongEvent(n.voice, n.pitch, max(1, min(127, round(self._base_velocity * n.velocity))),
                 min(remaining, n.duration or self._step_beats) * self._base_gate_length * 60.0 / bpm)
                for _, n in sorted(voices.items())]

    def get_current_song_info(self) -> Dict[str, Any]:
        """Get information about the current song state."""
        if self._between_songs:
            elapsed = time.perf_counter() - self._between_songs_start
            return {
                "status": "between_songs",
                "time_until_next_song": max(0, 5.0 - elapsed),
                "pattern": None,
                "section": None
            }
        
        if not self._current_pattern:
            return {
                "status": "no_song",
                "pattern": None,
                "section": None
            }
        
        current_section = None
        if self._current_section_index < len(self._current_pattern.sections):
            section = self._current_pattern.sections[self._current_section_index]
            current_section = {
                "type": section.section_type.value,
                "bars": section.bars,
                "bars_completed": self._section_bar_count,
                "density": section.density,
                "tempo_factor": section.tempo_factor,
                "octave_shift": section.octave_shift,
                "velocity_factor": section.velocity_factor
            }
        
        elapsed = time.perf_counter() - self._song_start_time
        
        return {
            "status": "playing",
            "pattern": self._current_pattern.name,
            "section": current_section,
            "section_index": self._current_section_index,
            "total_sections": len(self._current_pattern.sections),
            "elapsed_time": elapsed,
            "estimated_duration": self._current_pattern.estimated_duration_minutes * 60,
            "voices": self._material_request.voices
        }
    
    def force_next_section(self):
        """Advance manually and measure the next section from the current beat."""
        self._section_origin = self._musical_position
        if self._current_pattern and self._current_section_index < len(self._current_pattern.sections):
            self._current_section_index += 1
            self._section_start_time = time.perf_counter()
            self._section_bar_count = 0
            
            if self._current_section_index < len(self._current_pattern.sections):
                self._apply_section_settings()
                log.info(f"song_section_forced_advance index={self._current_section_index}")
            else:
                self._start_between_songs()
    
    def force_new_song(self):
        """Force start of a new song (for testing/debugging)."""
        self._between_songs = False
        self.start_new_song()


def create_song_sequencer(state: State, scale_mapper: ScaleMapper) -> SongSequencer:
    """Factory function to create a song sequencer instance."""
    return SongSequencer(state, scale_mapper)
