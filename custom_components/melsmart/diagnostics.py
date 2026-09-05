"""Redacted diagnostics dump for a melsmart config entry."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import MelSmartCoordinator
from .protocol import diagnostics_payload


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: MelSmartCoordinator = entry.runtime_data
    return diagnostics_payload(
        host=coordinator.client.host,
        status=coordinator.data,
        last_lsv=coordinator.client.last_lsv_redacted,
        pacer_remaining=coordinator.client.pacer_remaining,
    )
