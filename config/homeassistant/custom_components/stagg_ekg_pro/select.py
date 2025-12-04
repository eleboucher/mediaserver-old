"""Select platform for Stagg EKG Pro."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StaggEKGProCoordinator
from .kettle_ble import ScheduleMode, ClockMode, Language

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up selects from a config entry."""
    coordinator: StaggEKGProCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        StaggScheduleModeSelect(coordinator),
        StaggClockModeSelect(coordinator),
        StaggLanguageSelect(coordinator),
    ])


class StaggScheduleModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for schedule mode."""

    _attr_has_entity_name = True
    _attr_options = ["Off", "Daily", "Once"]
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_schedule_mode"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Schedule mode"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def current_option(self) -> str:
        """Return current schedule mode."""
        mode_str = self.coordinator.data.get('schedule_mode', 'off')
        mode_map = {'off': 'Off', 'daily': 'Daily', 'once': 'Once'}
        return mode_map.get(mode_str, 'Off')

    async def async_select_option(self, option: str) -> None:
        """Change the schedule mode."""
        mode_map = {
            "Off": ScheduleMode.OFF,
            "Daily": ScheduleMode.DAILY,
            "Once": ScheduleMode.ONCE
        }

        # Get current schedule settings
        hour = self.coordinator.data.get('schedule_hour', 7) or 7
        minute = self.coordinator.data.get('schedule_minute', 0) or 0
        temp = self.coordinator.data.get('schedule_temperature', 90) or 90

        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_schedule,
            mode=mode_map[option],
            hour=hour,
            minute=minute,
            temp_celsius=temp
        )


class StaggClockModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for clock mode."""

    _attr_has_entity_name = True
    _attr_options = ["Off", "Digital", "Analog"]
    _attr_icon = "mdi:clock-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_clock_mode"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Clock mode"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def current_option(self) -> str:
        """Return current clock mode."""
        mode_str = self.coordinator.data.get('clock_mode', 'off')
        mode_map = {'off': 'Off', 'digital': 'Digital', 'analog': 'Analog'}
        return mode_map.get(mode_str, 'Off')

    async def async_select_option(self, option: str) -> None:
        """Change the clock mode."""
        mode_map = {
            "Off": ClockMode.OFF,
            "Digital": ClockMode.DIGITAL,
            "Analog": ClockMode.ANALOG
        }

        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_clock_mode,
            mode_map[option]
        )


class StaggLanguageSelect(CoordinatorEntity, SelectEntity):
    """Select entity for language."""

    _attr_has_entity_name = True
    _attr_options = [
        "English",
        "French",
        "Spanish",
        "Simplified Chinese",
        "Traditional Chinese"
    ]
    _attr_icon = "mdi:translate"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_language"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Language"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def current_option(self) -> str:
        """Return current language."""
        lang = self.coordinator.kettle.get_language()
        if lang:
            # Convert enum name to readable format
            name = lang.name.replace('_', ' ').title()
            return name
        return "English"

    async def async_select_option(self, option: str) -> None:
        """Change the language."""
        lang_map = {
            "English": Language.ENGLISH,
            "French": Language.FRENCH,
            "Spanish": Language.SPANISH,
            "Simplified Chinese": Language.SIMPLIFIED_CHINESE,
            "Traditional Chinese": Language.TRADITIONAL_CHINESE
        }

        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_language,
            lang_map[option]
        )
