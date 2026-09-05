"""Mitsubishi Wi-Fi (/smart) Lossnay integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MelSmartClient
from .const import CONF_HOST, DOMAIN
from .coordinator import MelSmartCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.FAN, Platform.SENSOR]

_REMOVED_SENSOR_KEYS = (
    "indoor_temp",
    "outdoor_temp",
    "melview_connect",
    "echonet",
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = MelSmartClient(entry.data[CONF_HOST], session)
    coordinator = MelSmartCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    _async_remove_legacy_sensors(hass, entry, coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _async_remove_legacy_sensors(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: MelSmartCoordinator
) -> None:
    registry = er.async_get(hass)
    uids = {entry.entry_id}
    if coordinator.data.unique_id:
        uids.add(coordinator.data.unique_id)
    for uid in uids:
        for key in _REMOVED_SENSOR_KEYS:
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{uid}_{key}")
            if entity_id:
                registry.async_remove(entity_id)
