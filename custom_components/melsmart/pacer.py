"""Serialize /smart POSTs and enforce gaps so we do not lock the adapter."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

_LOGGER = logging.getLogger(__name__)

# Conservative defaults. Burst POSTs lock the adapter HTTP stack.
MIN_REQUEST_GAP = 3.0
POST_WRITE_GAP = 6.0
ERROR_COOLDOWN = 20.0


class RequestGate:
    """One request at a time, with a minimum gap and a timeout cooldown.

    After a successful poll wait ``min_gap`` seconds before the next POST.
    After a write wait ``write_gap``. After a transport timeout or ClientError
    wait ``error_cooldown``. The failed call is not retried — the next caller
    waits out the cooldown, then tries once.
    """

    def __init__(
        self,
        *,
        min_gap: float = MIN_REQUEST_GAP,
        write_gap: float = POST_WRITE_GAP,
        error_cooldown: float = ERROR_COOLDOWN,
        monotonic: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self.min_gap = min_gap
        self.write_gap = write_gap
        self.error_cooldown = error_cooldown
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._next_allowed = 0.0

    def remaining(self) -> float:
        return max(0.0, self._next_allowed - self._monotonic())

    async def wait_turn(self) -> float:
        wait = self.remaining()
        if wait > 0:
            _LOGGER.debug("Rate-limiting /smart for %.1fs", wait)
            await self._sleep(wait)
        return wait

    def mark_ok(self, *, write: bool = False) -> None:
        gap = self.write_gap if write else self.min_gap
        self._next_allowed = self._monotonic() + gap

    def mark_error(self) -> None:
        self._next_allowed = self._monotonic() + self.error_cooldown
