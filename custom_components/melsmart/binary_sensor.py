"""Diagnostic binary sensors for a Lossnay adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MelSmartCoordinator
from .device import adapter_device_info
from .protocol import LossnayStatus


@dataclass(frozen=True, kw_only=True)
class MelSmartBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[LossnayStatus], bool | None]


SENSORS: tuple[MelSmartBinaryDescription, ...] = (
    MelSmartBinaryDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.problem,
    ),
    MelSmartBinaryDescription(
        key="melview_connect",
        translation_key="melview_connect",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.melview_connected,
    ),
    MelSmartBinaryDescription(
        key="echonet",
        translation_key="echonet",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.echonet_flag_on,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MelSmartCoordinator = entry.runtime_data
    async_add_entities(
        MelSmartBinarySensor(coordinator, entry, description)
        for description in SENSORS
    )


class MelSmartBinarySensor(
    CoordinatorEntity[MelSmartCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MelSmartCoordinator,
        entry: ConfigEntry,
        description: MelSmartBinaryDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        uid = coordinator.data.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_{description.key}"
        self._attr_device_info = adapter_device_info(coordinator, entry)

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
