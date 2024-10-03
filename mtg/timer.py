from datetime import timedelta
import time

import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

class WaitPeriodTimer:
    """Contains methods for coordinating actions that need to have a certain
    amount of time between them at minimum. This class allows a waiting period
    to be defined, and once started, next() can be called to wait until at least
    that much time has passed since previous call to next() or start(). This can
    be used for any operation that requires actions not occur too quickly, such
    as applying anti-flood measures to requests.
    
    Create a WaitPeriodTimer by providing a timedelta, then use start() to begin
    it. Perform an operation, than call next() to wait until the start of the
    next period.
    """
    
    def __init__(self, period: timedelta):
        """Create a new PeriodTimer. It will not start counting until start() or
        next() is called."""
        self.period: timedelta = period
        self._running: bool = False
        self._last_called: float = 0

    @property
    def running(self) -> bool:
        """Return whether the timer is currently running. This will be true from
        the first call to either next() or start() up until stop() is called."""
        return self._running

    def start(self):
        """Begin the timer. If it has already been started, this method has no
        effect."""
        if self.running:
            return
        self._last_called = time.monotonic()
        self._running = True

    def next(self):
        """Wait until the start of the next period. If the timer has not yet
        been started with a call to start(), it is started automatically and
        next() immediately returns."""
        if not self.running:
            self.start()
            return
        
        now = time.monotonic()
        wait_time = self._target() - now
        
        if wait_time > 0:
            time.sleep(wait_time)
        
        self.reset()

    def reset(self):
        """
        Reset the wait time to start from this point forward.
        """
        self._last_called = time.monotonic()

    def stop(self):
        """Stop the running timer."""
        self._running = False

    def _target(self) -> float:
        return self._last_called + self.period.total_seconds()
