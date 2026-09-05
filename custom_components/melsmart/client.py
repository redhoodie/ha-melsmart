"""Async HTTP client for the Mitsubishi /smart endpoint."""

from __future__ import annotations

import asyncio
import logging

from aiohttp import ClientError, ClientSession, ClientTimeout

from .crypto import CryptoError, decrypt_payload, encrypt_payload, pad_key
from .const import (
    ERROR_COOLDOWN,
    MIN_REQUEST_GAP,
    POST_WRITE_GAP,
    WRITE_APPLY_PAUSE,
)
from .pacer import RequestGate
from .protocol import (
    LossnayStatus,
    csv_command,
    csv_status,
    fan_speed_set_packet,
    parse_lsv,
    power_and_speed_set_packet,
    power_set_packet,
    redact_lsv,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_KEY = b"unregistered"


class MelSmartError(Exception):
    """Raised when the adapter cannot be reached or decrypted."""


class MelSmartClient:
    """Talk to a Mitsubishi Wi-Fi adapter over local HTTP /smart."""

    def __init__(
        self,
        host: str,
        session: ClientSession,
        encryption_key: bytes = DEFAULT_KEY,
        *,
        min_gap: float = MIN_REQUEST_GAP,
        write_gap: float = POST_WRITE_GAP,
        error_cooldown: float = ERROR_COOLDOWN,
        apply_pause: float = WRITE_APPLY_PAUSE,
    ) -> None:
        self._host = host
        self._session = session
        self._key = pad_key(encryption_key)
        self._lock = asyncio.Lock()
        self._gate = RequestGate(
            min_gap=min_gap,
            write_gap=write_gap,
            error_cooldown=error_cooldown,
        )
        self._apply_pause = apply_pause
        self.last_lsv_redacted: str | None = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def pacer_remaining(self) -> float:
        return self._gate.remaining()

    async def async_status(self) -> LossnayStatus:
        xml = await self._async_request(csv_status())
        return parse_lsv(xml)

    async def async_set_power(self, on: bool) -> LossnayStatus:
        return await self._async_write_then_status(csv_command(power_set_packet(on)))

    async def async_set_fan_speed(self, speed: int) -> LossnayStatus:
        return await self._async_write_then_status(
            csv_command(fan_speed_set_packet(speed))
        )

    async def async_set_power_and_speed(self, on: bool, speed: int) -> LossnayStatus:
        return await self._async_write_then_status(
            csv_command(power_and_speed_set_packet(on, speed))
        )

    async def _async_write_then_status(self, csv: str) -> LossnayStatus:
        await self._async_request(csv, write=True)
        # Adapter echoes cached CODE on the same POST; wait for apply.
        if self._apply_pause > 0:
            await asyncio.sleep(self._apply_pause)
        return await self.async_status()

    async def _async_request(self, csv: str, *, write: bool = False) -> str:
        encrypted = encrypt_payload(csv, self._key)
        body = f'<?xml version="1.0" encoding="UTF-8"?><ESV>{encrypted}</ESV>'
        url = f"http://{self._host}/smart"
        async with self._lock:
            await self._gate.wait_turn()
            try:
                async with self._session.post(
                    url,
                    data=body,
                    headers={"Content-Type": "text/xml"},
                    timeout=ClientTimeout(total=8),
                ) as resp:
                    text = await resp.text()
                    status = resp.status
            except (ClientError, TimeoutError, asyncio.TimeoutError) as err:
                self._gate.mark_error()
                raise MelSmartError(f"Cannot reach {url}: {err}") from err
            self._gate.mark_ok(write=write)
            if status != 200:
                raise MelSmartError(f"HTTP {status} from {url}")
        start = text.find("<ESV>")
        end = text.find("</ESV>")
        if start < 0 or end < 0:
            raise MelSmartError("Adapter response had no ESV payload")
        try:
            decrypted = decrypt_payload(text[start + 5 : end], self._key)
        except CryptoError as err:
            raise MelSmartError(str(err)) from err
        redacted = redact_lsv(decrypted)
        self.last_lsv_redacted = redacted
        _LOGGER.debug("Decrypted /smart from %s: %s", self._host, redacted)
        return decrypted
