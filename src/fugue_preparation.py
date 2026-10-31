"""Bounded, process-isolated score preparation with a non-timing coordinator."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import logging
import multiprocessing
import threading
import time
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparationRequest:
    """Immutable composition and scale snapshot; epoch rejects superseded work."""
    epoch: int
    voices: int
    root: int
    mode: str
    density: float
    intervals: tuple[int, ...]
    seed: int = 0


@dataclass(frozen=True)
class PreparedScore:
    """Immutable onset groups and end position, computed entirely in the worker."""
    events: tuple[tuple[float, tuple[tuple[int, int, float], ...]], ...]
    end_beat: float


def prepare_score(request: PreparationRequest) -> PreparedScore:
    """Render a composition in a spawned process without shared runtime state."""
    from fugue import FugueEngine, FugueParams
    from scale_mapper import ScaleMapper
    mapper = ScaleMapper({'major': list(request.intervals)})
    mapper.root_note = request.root
    engine = FugueEngine(mapper, seed=request.seed)
    params = FugueParams(n_voices=request.voices, key_root=request.root,
                         mode=request.mode, entry_gap_beats=2.0,
                         stretto_overlap=request.density * 0.5,
                         use_tonal_answer=True, episode_density=request.density)
    score = engine.render_fugue(engine.generate_subject(params, bars=1), params)
    return compile_score(score)


def compile_score(score) -> PreparedScore:
    """Group simultaneous onsets and retain the full duration including final rests."""
    groups = {}
    end = 0.0
    for voice in score:
        beat = 0.0
        for note in voice:
            if note['dur'] <= 0:
                raise ValueError('Score durations must be positive')
            if note['pitch'] is not None:
                groups.setdefault(beat, []).append((note['pitch'], note['vel'], note['dur']))
            beat += note['dur']
        end = max(end, beat)
    return PreparedScore(tuple((beat, tuple(notes)) for beat, notes in sorted(groups.items())), end)


class ScorePreparation:
    """Own one in-flight job and one ready result; the clock only reads references.

    Publication uses atomic object-reference assignment on CPython. The coordinator
    is the sole publisher; consumers acknowledge by identity instead of clearing a
    slot that could already contain a newer result.
    """

    def __init__(self, snapshot: Callable[[], Optional[Any]],
                 executor_factory=None, prepare=prepare_score, name="fugue"):
        self.snapshot = snapshot
        self.prepare = prepare
        self.name = name
        self.ready = None
        self.consumed = None
        self.waiting = False
        self._stop = threading.Event()
        self._thread = None
        self._executor_factory = executor_factory or (
            lambda: ProcessPoolExecutor(max_workers=1,
                                        mp_context=multiprocessing.get_context('spawn')))

    def start(self) -> None:
        """Start the coordinator outside timing/input handlers; repeated starts are harmless."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f'{self.name}-preparation', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Join the coordinator and worker outside the timing path."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        self.ready = None
        self.consumed = None

    def _run(self) -> None:
        """Submit, deserialize, log, and retry only on the coordinator thread."""
        executor = None
        future = None
        submitted = None
        retry_at = 0.0
        was_waiting = False
        try:
            while not self._stop.is_set():
                request = self.snapshot()
                if self.waiting and not was_waiting:
                    log.info('%s_preparation_waiting boundary_deferred=true', self.name)
                was_waiting = self.waiting
                if self.ready is not None and (self.ready[0] != request or self.ready is self.consumed):
                    self.ready = None
                if future is not None and future.done():
                    try:
                        result = future.result()
                        if submitted == request:
                            self.ready = (submitted, result)
                            log.info('composition_prepared request=%s', submitted)
                    except Exception:
                        log.exception('%s_preparation_failed retry_seconds=5', self.name)
                        retry_at = time.monotonic() + 5.0
                        if executor is not None:
                            executor.shutdown(wait=True, cancel_futures=True)
                            executor = None
                    future = None
                if request is not None and self.ready is None and future is None and time.monotonic() >= retry_at:
                    try:
                        if executor is None:
                            executor = self._executor_factory()
                        submitted = request
                        future = executor.submit(self.prepare, request)
                    except Exception:
                        log.exception('%s_preparation_submit_failed retry_seconds=5', self.name)
                        retry_at = time.monotonic() + 5.0
                        if executor is not None:
                            executor.shutdown(wait=True, cancel_futures=True)
                            executor = None
                self._stop.wait(0.01)
        finally:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=True)
