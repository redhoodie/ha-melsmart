"""Async HTTP client for the Mitsubishi /smart endpoint."""

from __future__ import annotations

import asyncio
import base64
import logging
import os

from aiohttp import ClientError, ClientSession, ClientTimeout
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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
    power_set_packet,
    redact_lsv,
)

_LOGGER = logging.getLogger(__name__)

KEY_SIZE = 16
DEFAULT_KEY = b"unregistered"


class MelSmartError(Exception):
    """Raised when the adapter cannot be reached or decrypted."""


def _pad_key(key: bytes) -> bytes:
    if len(key) < KEY_SIZE:
        return key + b"\x00" * (KEY_SIZE - len(key))
    return key[:KEY_SIZE]


def _pad_iso7816(data: bytes) -> bytes:
    data = data + b"\x80"
    if len(data) % KEY_SIZE:
        data += b"\x00" * (KEY_SIZE - len(data) % KEY_SIZE)
    return data


def _unpad_iso7816(data: bytes) -> bytes:
    end = len(data)
    while end > 0 and data[end - 1] == 0:
        end -= 1
    if end > 0 and data[end - 1] == 0x80:
        end -= 1
    return data[:end]


def encrypt_payload(plain: str, key: bytes, iv: bytes | None = None) -> str:
    key = _pad_key(key)
    if iv is None:
        iv = os.urandom(KEY_SIZE)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ct = cipher.update(_pad_iso7816(plain.encode("utf-8"))) + cipher.finalize()
    return base64.b64encode(iv + ct).decode("ascii")


def decrypt_payload(payload_b64: str, key: bytes) -> str:
    key = _pad_key(key)
    raw = base64.b64decode(payload_b64)
    if len(raw) < KEY_SIZE:
        raise MelSmartError("ciphertext too short")
    iv, ct = raw[:KEY_SIZE], raw[KEY_SIZE:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = _unpad_iso7816(cipher.update(ct) + cipher.finalize())
    return plain.decode("utf-8", errors="replace")


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
        self._key = _pad_key(encryption_key)
        self._lock = asyncio.Lock()
        self._gate = RequestGate(
            min_gap=min_gap,
            write_gap=write_gap,
            error_cooldown=error_cooldown,
        )
        self._apply_pause = apply_pause

    @property
    def host(self) -> str:
        return self._host

    async def async_status(self) -> LossnayStatus:
        xml = await self._async_request(csv_status())
        return parse_lsv(xml)

    async def async_set_power(self, on: bool) -> LossnayStatus:
        return await self._async_write_then_status(csv_command(power_set_packet(on)))

    async def async_set_fan_speed(self, speed: int) -> LossnayStatus:
        return await self._async_write_then_status(
            csv_command(fan_speed_set_packet(speed))
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
        decrypted = decrypt_payload(text[start + 5 : end], self._key)
        _LOGGER.debug("Decrypted /smart from %s: %s", self._host, redact_lsv(decrypted))
        return decrypted
