"""Water heater platform for Stagg EKG Pro."""
import logging

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
    STATE_OFF,
    STATE_PERFORMANCE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, CONF_MAC, ATTR_TEMPERATURE
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
    """Set up water heater from a config entry."""
    coordinator: StaggEKGProCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([StaggWaterHeater(coordinator)])


class StaggWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Water heater entity for Stagg EKG Pro.

    This entity represents the main control interface for the kettle,
    allowing temperature setting and on/off control via the schedule hack.
    """

    _attr_has_entity_name = True
    _attr_name = None  # Main entity takes device name
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 40
    _attr_max_temp = 100
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE |
        WaterHeaterEntityFeature.ON_OFF |
        WaterHeaterEntityFeature.OPERATION_MODE
    )
    _attr_operation_list = [STATE_OFF, STATE_PERFORMANCE]

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the water heater."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_water_heater"
        self._attr_device_info = coordinator.device_info
        self._is_on = False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def current_operation(self) -> str:
        """Return current operation mode."""
        return STATE_PERFORMANCE if self._is_on else STATE_OFF

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self.coordinator.data.get('target_temperature', 90)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on using the schedule hack.

        This sets a temporary schedule for 1 minute in the future to trigger heating,
        then restores the original schedule after the kettle starts (65 seconds).

        Note: Requires the kettle's clock to be set correctly!
        """
        _LOGGER.info("Starting kettle via schedule hack")

        # Optimistic update
        self._is_on = True
        self.async_write_ha_state()

        # Run the hack in background
        self.hass.async_create_background_task(
            self._run_smart_turn_on(),
            name="stagg_turn_on"
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the kettle.

        Note: The Stagg EKG Pro cannot be turned off remotely via BLE.
        This only updates the state in Home Assistant.
        """
        self._is_on = False
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp:
            await self.coordinator.async_write_kettle(
                self.coordinator.kettle.set_target_temperature,
                temp
            )

    async def _run_smart_turn_on(self) -> None:
        """Execute the smart turn on sequence."""
        try:
            target_temp = self.coordinator.data.get('target_temperature', 90)
            await self.coordinator.kettle.turn_on_smart(target_temp)
        except Exception as err:
            _LOGGER.error("Smart turn on failed: %s", err)
            self._is_on = False
            self.async_write_ha_state()
