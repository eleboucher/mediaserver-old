"""Time platform for Stagg EKG Pro."""
import logging
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory
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
    """Set up time entities from a config entry."""
    coordinator: StaggEKGProCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        StaggScheduleTime(coordinator),
        StaggClockTime(coordinator),
    ])


class StaggScheduleTime(CoordinatorEntity, TimeEntity):
    """Time entity for schedule time."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-time-four-outline"

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_schedule_time"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Schedule time"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> time:
        """Return the schedule time."""
        hour = self.coordinator.data.get('schedule_hour', 7)
        minute = self.coordinator.data.get('schedule_minute', 0)
        if hour is not None and minute is not None:
            return time(hour, minute)
        return time(7, 0)

    async def async_set_value(self, value: time) -> None:
        """Update the schedule time on the kettle."""
        # Preserve existing mode and temperature
        mode_str = self.coordinator.data.get('schedule_mode', 'daily')
        if mode_str == 'off':
            mode_str = 'daily'

        mode_enum = ScheduleMode.DAILY if mode_str == 'daily' else ScheduleMode.ONCE
        current_temp = self.coordinator.data.get('schedule_temperature', 90) or 90

        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_schedule,
            mode=mode_enum,
            hour=value.hour,
            minute=value.minute,
            temp_celsius=current_temp
        )


class StaggClockTime(CoordinatorEntity, TimeEntity):
    """Time entity for kettle clock time."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-edit-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_clock_time"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Clock time"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> time:
        """Return the clock time."""
        hour = self.coordinator.data.get('clock_hours', 0)
        minute = self.coordinator.data.get('clock_minutes', 0)
        if hour is not None and minute is not None:
            return time(hour, minute)
        return time(0, 0)

    async def async_set_value(self, value: time) -> None:
        """Update the clock time on the kettle."""
        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_clock_time,
            hours=value.hour,
            minutes=value.minute
        )
