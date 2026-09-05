"""Fan entity for a Lossnay unit via /smart."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .client import MelSmartError
from .const import CONF_NAME, DEFAULT_NAME, DOMAIN, FAN_SPEEDS
from .coordinator import MelSmartCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MelSmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MelSmartFan(coordinator, entry)])


class MelSmartFan(CoordinatorEntity[MelSmartCoordinator], FanEntity):
    """On/off and 4-notch speed. Ventilation mode is not on local /smart."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_speed_count = len(FAN_SPEEDS)
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
    )

    def __init__(self, coordinator: MelSmartCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        uid = coordinator.data.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_fan"
        name = entry.data.get(CONF_NAME) or DEFAULT_NAME
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=name,
            manufacturer="Mitsubishi Electric",
            model="Lossnay (Wi-Fi /smart)",
            sw_version=coordinator.data.app_ver,
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.power_on

    @property
    def percentage(self) -> int | None:
        if self.is_on is False:
            return 0
        speed = self.coordinator.data.fan_speed
        if speed not in FAN_SPEEDS:
            return None
        return ordered_list_item_to_percentage(list(FAN_SPEEDS), speed)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        speed = percentage_to_ordered_list_item(list(FAN_SPEEDS), percentage)
        await self._async_set_speed(speed, turn_on=True)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        await self._async_set_power(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_power(False)

    async def _async_set_speed(self, speed: int, *, turn_on: bool) -> None:
        if turn_on and self.is_on is False:
            await self._async_set_power(True)
        try:
            status = await self.coordinator.client.async_set_fan_speed(speed)
        except MelSmartError:
            await self.coordinator.async_request_refresh()
            raise
        self.coordinator.async_set_updated_data(status)

    async def _async_set_power(self, on: bool) -> None:
        try:
            status = await self.coordinator.client.async_set_power(on)
        except MelSmartError:
            await self.coordinator.async_request_refresh()
            raise
        self.coordinator.async_set_updated_data(status)
