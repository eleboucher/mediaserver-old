"""Switch platform for Stagg EKG Pro."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory
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
    """Set up switches from a config entry."""
    coordinator: StaggEKGProCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        StaggEKGProPowerSwitch(coordinator),
        StaggEKGProPreBoilSwitch(coordinator),
    ])


class StaggEKGProPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Power switch using the schedule hack.

    This switch turns on the kettle by temporarily setting a schedule for 1 minute
    in the future, then restoring the original schedule after the kettle starts.

    Note: This requires the kettle's clock to be set correctly!
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:kettle"

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the power switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_power"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Power"
        self._is_on = False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        """Return if the kettle is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the kettle on using the schedule hack.

        This sets a temporary schedule for 1 minute in the future to trigger heating,
        then restores the original schedule after the kettle starts (65 seconds).
        """
        _LOGGER.info("Turning on kettle via schedule hack")

        # Optimistic update
        self._is_on = True
        self.async_write_ha_state()

        # Run the smart turn on in background
        self.hass.async_create_background_task(
            self._async_run_smart_turn_on(),
            name="stagg_pro_turn_on"
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the kettle.

        Note: The Stagg EKG Pro cannot be turned off remotely via BLE.
        This only updates the switch state in Home Assistant.
        """
        self._is_on = False
        self.async_write_ha_state()

    async def _async_run_smart_turn_on(self) -> None:
        """Execute the schedule hack sequence to turn on the kettle."""
        try:
            await self.coordinator.kettle.turn_on_smart()
        except Exception as err:
            _LOGGER.error("Failed to turn on kettle: %s", err)
            self._is_on = False
            self.async_write_ha_state()


class StaggEKGProPreBoilSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for pre-boil feature.

    Pre-boil brings water to a full boil before cooling to the target temperature.
    This helps remove chlorine and other impurities from the water.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-boiler"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StaggEKGProCoordinator):
        """Initialize the pre-boil switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address.replace(':', '')}_pre_boil"
        self._attr_device_info = coordinator.device_info
        self._attr_name = "Pre-boil"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        """Return if pre-boil is enabled."""
        return self.coordinator.data.get('pre_boil_enabled', False)

    async def async_turn_on(self, **kwargs) -> None:
        """Enable pre-boil."""
        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_pre_boil,
            True
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Disable pre-boil."""
        await self.coordinator.async_write_kettle(
            self.coordinator.kettle.set_pre_boil,
            False
        )
