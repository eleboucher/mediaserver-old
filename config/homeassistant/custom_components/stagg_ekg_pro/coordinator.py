"""Data coordinator for Stagg EKG Pro."""
import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MANUFACTURER, MODEL
from .kettle_ble import StaggEKGPro_Config

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
MAX_RETRIES = 3


class StaggEKGProCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching Stagg EKG Pro data."""

    def __init__(self, hass: HomeAssistant, mac_address: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Stagg EKG Pro",
            update_interval=UPDATE_INTERVAL,
        )
        self.mac_address = mac_address
        self.kettle = StaggEKGPro_Config(mac_address)
        self._lock = asyncio.Lock()
        self._connected = False
        self._retry_count = 0

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for this kettle."""
        return {
            "identifiers": {(DOMAIN, self.mac_address)},
            "name": f"{MODEL}",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "connections": {("mac", self.mac_address)},
        }

    @property
    def available(self) -> bool:
        """Return if the kettle is available."""
        return self._connected

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the kettle."""
        async with self._lock:
            try:
                # Connect if not already connected
                if not self._connected:
                    connected = await self.kettle.connect()
                    if not connected:
                        self._retry_count += 1
                        raise UpdateFailed(
                            f"Failed to connect to kettle (attempt {self._retry_count})"
                        )
                    self._connected = True
                    self._retry_count = 0
                    _LOGGER.info("Successfully connected to kettle at %s", self.mac_address)

                # Refresh state
                await self.kettle.refresh_state()

                # Get all state data
                state = self.kettle.get_state()
                schedule = self.kettle.get_schedule()

                # Reset retry count on success
                self._retry_count = 0

                # Combine into single data dict
                return {
                    **state,
                    **schedule,
                }

            except UpdateFailed:
                # Re-raise UpdateFailed as-is
                self._connected = False
                raise

            except Exception as err:
                # On error, disconnect and reset connection state
                self._connected = False
                self._retry_count += 1

                if self.kettle.client and self.kettle.client.is_connected:
                    try:
                        await self.kettle.disconnect()
                    except Exception:
                        pass

                _LOGGER.error(
                    "Error communicating with kettle: %s (attempt %d)",
                    err, self._retry_count
                )
                raise UpdateFailed(f"Error communicating with kettle: {err}")

    async def async_write_kettle(self, write_func, *args, **kwargs):
        """Execute a write operation to the kettle with proper locking."""
        async with self._lock:
            try:
                # Ensure connected
                if not self._connected:
                    connected = await self.kettle.connect()
                    if not connected:
                        raise UpdateFailed("Failed to connect to kettle")
                    self._connected = True

                # Execute the write function
                result = await write_func(*args, **kwargs)

                # Refresh state after write
                await self.kettle.refresh_state()

                # Update coordinator data
                state = self.kettle.get_state()
                schedule = self.kettle.get_schedule()
                self.async_set_updated_data({**state, **schedule})

                return result

            except Exception as err:
                _LOGGER.error(f"Error writing to kettle: {err}")
                # On error, disconnect and reset
                self._connected = False
                if self.kettle.client and self.kettle.client.is_connected:
                    try:
                        await self.kettle.disconnect()
                    except Exception:
                        pass
                raise

    async def async_shutdown(self) -> None:
        """Disconnect from the kettle on shutdown."""
        async with self._lock:
            if self._connected and self.kettle.client:
                try:
                    await self.kettle.disconnect()
                except Exception as err:
                    _LOGGER.error(f"Error disconnecting: {err}")
                finally:
                    self._connected = False
