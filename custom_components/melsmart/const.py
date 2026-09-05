"""Constants for the Mitsubishi /smart Lossnay integration."""

from __future__ import annotations

from .pacer import ERROR_COOLDOWN, MIN_REQUEST_GAP, POST_WRITE_GAP
from .protocol import FAN_SPEEDS

DOMAIN = "melsmart"

CONF_HOST = "host"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "Lossnay"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 300

# Adapter echoes cached CODE on the same POST; wait before the follow-up poll.
WRITE_APPLY_PAUSE = 3.0

# Same factory key used by pymitsubishi / melsmart for unregistered adapters.
DEFAULT_ENCRYPTION_KEY = b"unregistered"

CLASS_VENTILATION = 0x34

__all__ = [
    "CLASS_VENTILATION",
    "CONF_HOST",
    "CONF_NAME",
    "CONF_SCAN_INTERVAL",
    "DEFAULT_ENCRYPTION_KEY",
    "DEFAULT_NAME",
    "DEFAULT_SCAN_INTERVAL",
    "DOMAIN",
    "ERROR_COOLDOWN",
    "MAX_SCAN_INTERVAL",
    "MIN_REQUEST_GAP",
    "MIN_SCAN_INTERVAL",
    "POST_WRITE_GAP",
    "WRITE_APPLY_PAUSE",
    "FAN_SPEEDS",
]
