"""Sensor entities for Best Run Time."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import BestRunTimeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: BestRunTimeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            BestRunTimeSensor(coordinator, entry),
            BestRunScoreSensor(coordinator, entry),
        ]
    )


class _BaseRunSensor(CoordinatorEntity[BestRunTimeCoordinator], SensorEntity):
    """Shared device-info wiring."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BestRunTimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Best Run Time ({coordinator.weather_entity})",
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Best Run Time",
        )


class BestRunTimeSensor(_BaseRunSensor):
    """Timestamp of the best running hour in the look-ahead window."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:run-fast"
    _attr_name = "Best run time"

    def __init__(self, coordinator: BestRunTimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_best_run_time"

    @property
    def native_value(self) -> datetime | None:
        if not self.coordinator.data:
            return None
        return dt_util.parse_datetime(self.coordinator.data["best"]["datetime"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        best = self.coordinator.data["best"]
        return {
            "score": best["score"],
            "temperature": best.get("temperature"),
            "precipitation_probability": best.get("precipitation_probability"),
            "wind_speed": best.get("wind_speed"),
            "humidity": best.get("humidity"),
            "condition": best.get("condition"),
            "reasons": best.get("reasons"),
            "top_3": self.coordinator.data["top_3"],
        }


class BestRunScoreSensor(_BaseRunSensor):
    """Numeric runnability score (0..100) for the best hour."""

    _attr_icon = "mdi:gauge"
    _attr_name = "Best run score"
    _attr_native_unit_of_measurement = "pts"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: BestRunTimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_best_run_score"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data["best"]["score"]
