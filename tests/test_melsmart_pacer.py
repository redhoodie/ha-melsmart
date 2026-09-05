"""Rate-limit gate tests. No Home Assistant or network required."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "melsmart"))

from pacer import ERROR_COOLDOWN, MIN_REQUEST_GAP, POST_WRITE_GAP, RequestGate  # noqa: E402


class FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_first_request_does_not_wait():
    clock = FakeClock()
    gate = RequestGate(monotonic=clock.monotonic, sleep=clock.sleep)
    waited = asyncio.run(gate.wait_turn())
    assert waited == 0.0
    assert clock.sleeps == []


def test_poll_enforces_min_gap():
    clock = FakeClock()
    gate = RequestGate(monotonic=clock.monotonic, sleep=clock.sleep)
    gate.mark_ok(write=False)
    waited = asyncio.run(gate.wait_turn())
    assert waited == MIN_REQUEST_GAP
    assert clock.sleeps == [MIN_REQUEST_GAP]


def test_write_enforces_longer_gap():
    clock = FakeClock()
    gate = RequestGate(monotonic=clock.monotonic, sleep=clock.sleep)
    gate.mark_ok(write=True)
    waited = asyncio.run(gate.wait_turn())
    assert waited == POST_WRITE_GAP
    assert POST_WRITE_GAP > MIN_REQUEST_GAP
    assert clock.sleeps == [POST_WRITE_GAP]


def test_timeout_cools_down_without_retry():
    clock = FakeClock()
    gate = RequestGate(monotonic=clock.monotonic, sleep=clock.sleep)
    gate.mark_error()
    assert gate.remaining() == ERROR_COOLDOWN
    waited = asyncio.run(gate.wait_turn())
    assert waited == ERROR_COOLDOWN
    assert clock.sleeps == [ERROR_COOLDOWN]
    # After the cooldown, the next caller is not delayed again until mark_*.
    assert asyncio.run(gate.wait_turn()) == 0.0


def test_defaults_are_conservative():
    assert MIN_REQUEST_GAP >= 2.0
    assert POST_WRITE_GAP >= MIN_REQUEST_GAP + 2.0
    assert ERROR_COOLDOWN >= 15.0
