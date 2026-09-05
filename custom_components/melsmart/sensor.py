"""Sensors for a Lossnay unit via /smart."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import MelSmartCoordinator
from .protocol import LossnayStatus


@dataclass(frozen=True, kw_only=True)
class MelSmartSensorDescription(SensorEntityDescription):
    value_fn: Callable[[LossnayStatus], float | str | None]


SENSORS: tuple[MelSmartSensorDescription, ...] = (
    MelSmartSensorDescription(
        key="fresh_air_in",
        translation_key="fresh_air_in",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.fresh_air_in,
    ),
    MelSmartSensorDescription(
        key="stale_air_out",
        translation_key="stale_air_out",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.stale_air_out,
    ),
    MelSmartSensorDescription(
        key="indoor_temp",
        translation_key="indoor_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.indoor_temp,
    ),
    MelSmartSensorDescription(
        key="outdoor_temp",
        translation_key="outdoor_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.outdoor_temp,
    ),
    MelSmartSensorDescription(
        key="rssi",
        translation_key="rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.rssi,
    ),
    MelSmartSensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.app_ver,
    ),
    MelSmartSensorDescription(
        key="adapter_status",
        translation_key="adapter_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.status,
    ),
    MelSmartSensorDescription(
        key="melview_connect",
        translation_key="melview_connect",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.connect,
    ),
    MelSmartSensorDescription(
        key="echonet",
        translation_key="echonet",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.echonet,
    ),
    MelSmartSensorDescription(
        key="reported_fan_speed",
        translation_key="reported_fan_speed",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.reported_fan_speed,
    ),
    MelSmartSensorDescription(
        key="adapter_clock",
        translation_key="adapter_clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.adapter_clock,
    ),
    MelSmartSensorDescription(
        key="ssl_limit",
        translation_key="ssl_limit",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.ssl_limit,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MelSmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MelSmartSensor(coordinator, entry, description) for description in SENSORS
    )


class MelSmartSensor(CoordinatorEntity[MelSmartCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MelSmartCoordinator,
        entry: ConfigEntry,
        description: MelSmartSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        uid = coordinator.data.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_{description.key}"
        name = entry.data.get(CONF_NAME) or DEFAULT_NAME
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=name,
            manufacturer="Mitsubishi Electric",
            model="Lossnay (Wi-Fi /smart)",
            sw_version=coordinator.data.app_ver,
        )

    @property
    def native_value(self) -> float | str | None:
        return self.entity_description.value_fn(self.coordinator.data)
