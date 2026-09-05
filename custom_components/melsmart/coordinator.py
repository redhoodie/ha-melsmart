"""Data update coordinator for melsmart."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MelSmartClient, MelSmartError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .protocol import LossnayStatus

_LOGGER = logging.getLogger(__name__)


class MelSmartCoordinator(DataUpdateCoordinator[LossnayStatus]):
    """Poll the Lossnay adapter over /smart."""

    def __init__(
        self, hass: HomeAssistant, client: MelSmartClient, entry: ConfigEntry
    ) -> None:
        interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=f"melsmart {client.host}",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> LossnayStatus:
        try:
            return await self.client.async_status()
        except MelSmartError as err:
            raise UpdateFailed(str(err)) from err
