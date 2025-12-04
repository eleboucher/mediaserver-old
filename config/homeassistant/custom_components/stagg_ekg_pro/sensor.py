"""Sensor platform for Stagg EKG Pro."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, UnitOfTemperature, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StaggEKGProCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: StaggEKGProCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        StaggScheduleStatus(coordinator),
        StaggClockDisplay(coordinator),
        StaggTargetTemperature(coordinator),
    ])


class StaggScheduleStatus(CoordinatorEntity, SensorEntity):
    """Sensor showing the complete schedule status."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_schedule_status"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Schedule status"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> str:
        """Return the schedule status."""
        if self.coordinator.data.get('schedule_enabled'):
            mode = self.coordinator.data.get('schedule_mode', 'unknown').capitalize()
            time_str = self.coordinator.data.get('schedule_time', '--:--')
            return f"{mode} at {time_str}"
        return "Off"

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return additional state attributes."""
        if self.coordinator.data.get('schedule_enabled'):
            return {
                'mode': self.coordinator.data.get('schedule_mode'),
                'time': self.coordinator.data.get('schedule_time'),
                'hour': self.coordinator.data.get('schedule_hour'),
                'minute': self.coordinator.data.get('schedule_minute'),
                'temperature': self.coordinator.data.get('schedule_temperature'),
                'enabled': True
            }
        return {
            'mode': 'off',
            'enabled': False
        }


class StaggClockDisplay(CoordinatorEntity, SensorEntity):
    """Sensor showing the kettle's clock time and mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_clock"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Clock"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> str:
        """Return the clock display."""
        clock_mode = self.coordinator.data.get('clock_mode', 'off')
        if clock_mode != 'off':
            return self.coordinator.data.get('clock_time', '--:--')
        return 'Off'

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return additional state attributes."""
        return {
            'mode': self.coordinator.data.get('clock_mode', 'off'),
            'hours': self.coordinator.data.get('clock_hours'),
            'minutes': self.coordinator.data.get('clock_minutes')
        }


class StaggTargetTemperature(CoordinatorEntity, SensorEntity):
    """Sensor showing the current target temperature."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_target_temp"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Target temperature"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def native_value(self) -> float | None:
        """Return the target temperature."""
        return self.coordinator.data.get('target_temperature')

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return additional state attributes."""
        return {
            'units': self.coordinator.data.get('units', 'celsius'),
            'pre_boil_enabled': self.coordinator.data.get('pre_boil_enabled', False),
            'hold_time_minutes': self.coordinator.data.get('hold_time_minutes', 0),
            'hold_enabled': self.coordinator.data.get('hold_enabled', False)
        }
