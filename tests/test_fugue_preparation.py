"""Worker lifecycle tests use controlled futures; no real-time sleeps for generation."""
from concurrent.futures import Future
import threading
import time
from fugue_preparation import PreparationRequest, ScorePreparation, PreparedScore


def wait_for(predicate):
    """Bound asynchronous assertions so a coordinator failure cannot hang the suite."""
    deadline = time.monotonic() + 2
    while not predicate():
        assert time.monotonic() < deadline
        time.sleep(.005)


class Executor:
    """Expose submitted futures and execution thread for deterministic worker control."""
    def __init__(self):
        self.jobs = []
        self.closed = False

    def submit(self, fn, request):
        """Return a controllable result without running generation."""
        future = Future()
        self.jobs.append((request, future, threading.current_thread().name))
        return future

    def shutdown(self, **kwargs):
        """Record resource release."""
        self.closed = True


def request(epoch=0):
    """Create the minimum immutable composition snapshot."""
    return PreparationRequest(epoch, 3, 60, 'minor', .5, (0, 2, 3, 5, 7, 8, 10))


def test_bounded_handoff_stale_result_and_shutdown():
    desired = [request()]
    executor = Executor()
    service = ScorePreparation(lambda: desired[0], lambda: executor)
    service.start()
    try:
        wait_for(lambda: len(executor.jobs) == 1)
        desired[0] = request(1)
        executor.jobs[0][1].set_result(PreparedScore((), 4))
        wait_for(lambda: len(executor.jobs) == 2)
        assert service.ready is None
        assert all(job[2] == 'fugue-preparation' for job in executor.jobs)
        executor.jobs[1][1].set_result(PreparedScore((), 8))
        wait_for(lambda: service.ready is not None)
        assert service.ready[0] == desired[0]
        time.sleep(.03)
        assert len(executor.jobs) == 2  # One ready score bounds lookahead.
        service.consumed = service.ready
        wait_for(lambda: len(executor.jobs) == 3)
        desired[0] = None  # Mode change while work is in flight.
        executor.jobs[2][1].set_result(PreparedScore((), 12))
        wait_for(lambda: service.ready is None)
    finally:
        service.stop()
    assert executor.closed
    assert service._thread is None
    assert service.ready is None


def test_failure_backoff_and_recovery(monkeypatch, caplog):
    executor = Executor()
    now = [100.0]
    # Replace only the preparation module's time reference, not the test clock.
    from types import SimpleNamespace
    monkeypatch.setattr('fugue_preparation.time', SimpleNamespace(monotonic=lambda: now[0]))
    service = ScorePreparation(lambda: request(), lambda: executor)
    service.start()
    try:
        wait_for(lambda: len(executor.jobs) == 1)
        executor.jobs[0][1].set_exception(RuntimeError('fixture failure'))
        wait_for(lambda: executor.closed)
        time.sleep(.03)
        assert len(executor.jobs) == 1
        now[0] = 105.0
        wait_for(lambda: len(executor.jobs) == 2)
        executor.jobs[1][1].set_result(PreparedScore((), 4))
        wait_for(lambda: service.ready is not None)
        assert 'fugue_preparation_failed' in caplog.text
    finally:
        service.stop()
