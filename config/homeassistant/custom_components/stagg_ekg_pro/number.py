"""Number platform for Stagg EKG Pro."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, UnitOfTemperature, UnitOfLength, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StaggEKGProCoordinator
from .kettle_ble import ScheduleMode

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from a config entry."""
    coordinator: StaggEKGProCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        StaggScheduleTemperature(coordinator),
        StaggHoldTime(coordinator),
        StaggChimeVolume(coordinator),
        StaggAltitude(coordinator),
    ])


class StaggScheduleTemperature(CoordinatorEntity, NumberEntity):
    """Number entity for schedule target temperature."""

    _attr_has_entity_name = True
    _attr_native_min_value = 40
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_schedule_temp"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Schedule temperature"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> float:
        """Return the schedule temperature."""
        return self.coordinator.data.get('schedule_temperature', 90)

    async def async_set_native_value(self, value: float) -> None:
        """Update the schedule temperature on the kettle."""
        # Preserve existing mode and time
        mode_str = self.coordinator.data.get('schedule_mode', 'daily')
        if mode_str == 'off':
            mode_str = 'daily'

        mode_enum = ScheduleMode.DAILY if mode_str == 'daily' else ScheduleMode.ONCE
        hour = self.coordinator.data.get('schedule_hour', 7) or 7
        minute = self.coordinator.data.get('schedule_minute', 0) or 0

        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_schedule,
            mode=mode_enum,
            hour=hour,
            minute=minute,
            temp_celsius=value
        )


class StaggHoldTime(CoordinatorEntity, NumberEntity):
    """Number entity for hold time in minutes."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 60
    _attr_native_step = 15
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:timer"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_hold_time"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Hold time"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> float:
        """Return the hold time."""
        return self.coordinator.data.get('hold_time_minutes', 0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the hold time on the kettle."""
        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_hold_time,
            int(value)
        )


class StaggChimeVolume(CoordinatorEntity, NumberEntity):
    """Number entity for chime volume (0-10)."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_icon = "mdi:bell"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_chime_volume"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Chime volume"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> float:
        """Return the chime volume."""
        return self.coordinator.data.get('chime_volume', 5)

    async def async_set_native_value(self, value: float) -> None:
        """Update the chime volume on the kettle."""
        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_chime_volume,
            int(value)
        )


class StaggAltitude(CoordinatorEntity, NumberEntity):
    """Number entity for altitude compensation."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 3000
    _attr_native_step = 30
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_icon = "mdi:mountain"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_altitude"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Altitude"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> float:
        """Return the altitude."""
        return self.coordinator.data.get('altitude_meters', 0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the altitude on the kettle."""
        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_altitude,
            int(value)
        )
