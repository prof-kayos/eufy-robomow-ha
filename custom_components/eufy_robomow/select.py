"""Select entities for Eufy Robomow — cloud-managed settings.

All entities require Eufy account credentials; they are skipped when no
cloud client is configured.

  • Travel Speed    — slow / normal / fast      (DP155 field 2)
  • Blade Speed     — slow / normal / fast      (DP155 field 6)
  • Path Distance   — 8 cm / 10 cm / 12 cm     (DP155 field 5)

Pad Direction is a continuous 0–359° value; see number.py.
"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .cloud import SPEED_OPTIONS
from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CLOUD_TRAVEL_SPEED,
    CLOUD_BLADE_SPEED,
    CLOUD_PATH_MM,
    PATH_DISTANCE_OPTIONS,
    PATH_DISTANCE_MM,
)
from .coordinator import EufyMowerCoordinator

# Reverse lookup: mm value → display label
_MM_TO_PATH_LABEL: dict[int, str] = {v: k for k, v in PATH_DISTANCE_MM.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EufyMowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.cloud_client is None:
        return  # No cloud credentials → no cloud select entities

    device_id = entry.data[CONF_DEVICE_ID]
    async_add_entities(
        [
            EufySpeedSelect(
                coordinator, entry, device_id,
                speed_key="travel_speed",
                data_key=CLOUD_TRAVEL_SPEED,
                name="Travel Speed",
                icon="mdi:speedometer",
                unique_suffix="travel_speed",
            ),
            EufySpeedSelect(
                coordinator, entry, device_id,
                speed_key="blade_speed",
                data_key=CLOUD_BLADE_SPEED,
                name="Blade Speed",
                icon="mdi:fan",
                unique_suffix="blade_speed",
            ),
            EufyPathDistanceSelect(coordinator, entry, device_id),
        ]
    )


# ── Speed select ───────────────────────────────────────────────────────────────

class EufySpeedSelect(CoordinatorEntity[EufyMowerCoordinator], SelectEntity):
    """Speed select entity (travel speed or blade speed) for the Eufy E15."""

    _attr_has_entity_name = True
    _attr_options = SPEED_OPTIONS

    def __init__(
        self,
        coordinator: EufyMowerCoordinator,
        entry: ConfigEntry,
        device_id: str,
        *,
        speed_key: str,     # kwarg for set_settings() — "travel_speed" or "blade_speed"
        data_key: str,      # key in coordinator.data
        name: str,
        icon: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._speed_key = speed_key
        self._data_key  = data_key
        self._attr_name        = name
        self._attr_icon        = icon
        self._attr_unique_id   = f"{device_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._data_key)

    @property
    def available(self) -> bool:
        return (
            super().available
            and bool(self.coordinator.data)
            and self._data_key in self.coordinator.data
        )

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_cloud_setting(**{self._speed_key: option})


# ── Path distance select ───────────────────────────────────────────────────────

class EufyPathDistanceSelect(CoordinatorEntity[EufyMowerCoordinator], SelectEntity):
    """Path distance (lane spacing) for the Eufy E15.

    The app offers exactly three fixed values: 8 cm, 10 cm, 12 cm.
    DP155 field 5 stores the value in mm (80 / 100 / 120).
    """

    _attr_has_entity_name = True
    _attr_name = "Path Distance"
    _attr_icon = "mdi:arrow-expand-horizontal"
    _attr_options = PATH_DISTANCE_OPTIONS   # ["8 cm", "10 cm", "12 cm"]

    def __init__(
        self,
        coordinator: EufyMowerCoordinator,
        entry: ConfigEntry,
        device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id   = f"{device_id}_path_distance"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        mm = self.coordinator.data.get(CLOUD_PATH_MM)
        if mm is None:
            return None
        return _MM_TO_PATH_LABEL.get(int(mm))

    @property
    def available(self) -> bool:
        return (
            super().available
            and bool(self.coordinator.data)
            and CLOUD_PATH_MM in self.coordinator.data
        )

    async def async_select_option(self, option: str) -> None:
        """Write the selected path distance (label → mm for cloud)."""
        mm = PATH_DISTANCE_MM[option]
        await self.coordinator.async_set_cloud_setting(path_mm=mm)
