"""Shared Home Assistant device info for a Lossnay adapter."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import MelSmartCoordinator


def adapter_device_info(
    coordinator: MelSmartCoordinator, entry: ConfigEntry
) -> DeviceInfo:
    uid = coordinator.data.unique_id or entry.entry_id
    name = entry.data.get(CONF_NAME) or DEFAULT_NAME
    mac = coordinator.data.mac
    connections: set[tuple[str, str]] = set()
    if mac:
        connections.add((CONNECTION_NETWORK_MAC, mac.lower()))
    return DeviceInfo(
        identifiers={(DOMAIN, uid)},
        connections=connections,
        name=name,
        manufacturer="Mitsubishi Electric",
        model="Lossnay (Wi-Fi /smart)",
        sw_version=coordinator.data.app_ver,
    )
