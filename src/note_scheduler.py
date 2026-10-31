"""Serialize retriggers and monotonic note deadlines away from musical callbacks."""
import logging
import queue
import threading
import time

log = logging.getLogger(__name__)


class NoteScheduler:
    """One output owner; at most 2048 active keys and a bounded command queue.

    New attacks explicitly release the previous owner. Replacing its deadline
    prevents an old release from cutting off the replacement. Queue overflow
    requests a worker-side panic so overload cannot strand a sounding pitch.
    """

    def __init__(self, midi_output, clock=time.monotonic):
        self.midi_output = midi_output
        self.clock = clock
        self._commands = queue.Queue(maxsize=2048)
        self._active = {}
        self._running = False
        self._thread = None
        self._panic = threading.Event()
        self.dropped = 0
        self.max_queue_latency = 0.0

    def start(self) -> None:
        """Start the single MIDI writer outside input and clock handlers."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_thread, name='note-output', daemon=True)
        self._thread.start()

    def schedule_note(self, note: int, velocity: int, channel: int, duration: float) -> None:
        """Enqueue an attack without device I/O or waiting for queue capacity."""
        self._enqueue((note, velocity, channel, duration, self.clock()))

    def schedule_note_off(self, note: int, channel: int, delay: float) -> None:
        """Compatibility entry point for callers that already emitted an attack."""
        self._enqueue((note, None, channel, delay, self.clock()))

    def _enqueue(self, command):
        """Bound backlog and recover stuck notes on overload in the output worker."""
        try:
            self._commands.put_nowait(command)
        except queue.Full:
            self.dropped += 1
            self._panic.set()

    def _flush(self) -> None:
        """Release every owned pitch, including each expanded broadcast channel."""
        for channel, note in tuple(self._active):
            self.midi_output.send_note_off(note, 0, channel)
        self._active.clear()

    def _process(self, command=None):
        """Process one command and expired owners; only the writer calls this."""
        if command is not None:
            note, velocity, channel, duration, queued = command
            self.max_queue_latency = max(self.max_queue_latency, self.clock() - queued)
            for ch in (range(1, 17) if channel == 0 else (channel,)):
                key = (ch, note)
                if velocity is not None:
                    if key in self._active:
                        self.midi_output.send_note_off(note, 0, ch)
                    self.midi_output.send_note_on(note, velocity, ch)
                self._active[key] = self.clock() + max(0.0, duration)
        now = self.clock()
        for key, deadline in tuple(self._active.items()):
            if deadline <= now:
                channel, note = key
                self.midi_output.send_note_off(note, 0, channel)
                del self._active[key]

    def _scheduler_thread(self) -> None:
        """Keep all MIDI operations and error reporting outside playback callbacks."""
        try:
            while self._running:
                try:
                    if self._panic.is_set():
                        self._flush()
                        while not self._commands.empty():
                            try:
                                self._commands.get_nowait()
                            except queue.Empty:
                                break
                        self._panic.clear()
                        log.error('note_queue_overflow dropped=%s', self.dropped)
                    try:
                        command = self._commands.get(timeout=.0005)
                    except queue.Empty:
                        command = None
                    self._process(command)
                except Exception:
                    log.exception('note_output_failed')
                    self._panic.set()
        finally:
            self._flush()
            while not self._commands.empty():
                try:
                    self._commands.get_nowait()
                except queue.Empty:
                    break

    def stop(self) -> None:
        """Join the writer and release notes before the MIDI port is closed."""
        self._running = False
        if self._thread is not None:
            self._thread.join()
            self._thread = None
