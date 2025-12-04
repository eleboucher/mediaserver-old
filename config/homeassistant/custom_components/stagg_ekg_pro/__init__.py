"""The Stagg EKG Pro integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import StaggEKGProCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.WATER_HEATER,
    Platform.SELECT,
    Platform.TIME,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stagg EKG Pro from a config entry."""
    mac_address = entry.data[CONF_MAC]

    # Create coordinator
    coordinator = StaggEKGProCoordinator(hass, mac_address)

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to connect to kettle: %s", err)
        raise ConfigEntryNotReady from err

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register shutdown handler
    async def async_close_connection(event):
        """Close connection on shutdown."""
        await coordinator.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once("homeassistant_stop", async_close_connection)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Shutdown coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()

        # Remove coordinator from hass.data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
