"""Sensors for Eufy Robomow."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    DP_BATTERY,
    DP_AREA,
    DP_NETWORK,
    DP_PROGRESS,
    DP_TOTAL_TIME,
)
from .coordinator import EufyMowerCoordinator

# DP125 unit: ~6.6 seconds per unit (confirmed: 36149 units ≈ 66h total)
DP125_SECONDS_PER_UNIT = 6.6


@dataclass(frozen=True)
class EufySensorDescription(SensorEntityDescription):
    dp: str = ""


SENSORS: tuple[EufySensorDescription, ...] = (
    EufySensorDescription(
        key="battery",
        dp=DP_BATTERY,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
    ),
    EufySensorDescription(
        key="mowed_area",
        dp=DP_AREA,
        name="Mowed Area",
        # Raw counter — exact m² conversion unconfirmed (~9% off vs app).
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="units",
        icon="mdi:grass",
    ),
    EufySensorDescription(
        key="total_time",
        dp=DP_TOTAL_TIME,
        name="Total Mow Time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
    ),
    EufySensorDescription(
        key="progress",
        dp=DP_PROGRESS,
        name="Progress",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:progress-clock",
    ),
    EufySensorDescription(
        key="network",
        dp=DP_NETWORK,
        name="Network",
        icon="mdi:wifi",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EufyMowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EufySensor(coordinator, entry, desc) for desc in SENSORS
    )


class EufySensor(CoordinatorEntity[EufyMowerCoordinator], SensorEntity):
    """A sensor that reads one DPS value."""

    entity_description: EufySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EufyMowerCoordinator,
        entry: ConfigEntry,
        description: EufySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
        )

    @property
    def native_value(self) -> Any:
        raw = self.coordinator.data.get(self.entity_description.dp)
        if raw is None:
            return None
        # Convert DP125 raw units → hours
        if self.entity_description.dp == DP_TOTAL_TIME:
            return round((raw * DP125_SECONDS_PER_UNIT) / 3600, 1)
        return raw
