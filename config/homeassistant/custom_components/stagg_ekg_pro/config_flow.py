"""Config flow for Stagg EKG Pro integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .kettle_ble import StaggEKGPro_Config

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): str,
    }
)


class StaggEKGProConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Stagg EKG Pro."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            mac_address = user_input[CONF_MAC].upper()

            # Validate MAC address format
            if not self._is_valid_mac(mac_address):
                errors["base"] = "invalid_mac"
            else:
                # Check if already configured
                await self.async_set_unique_id(mac_address)
                self._abort_if_unique_id_configured()

                # Try to connect to verify it works
                kettle = StaggEKGPro_Config(mac_address)
                try:
                    connected = await kettle.connect()
                    if connected:
                        await kettle.disconnect()

                        # Create entry
                        return self.async_create_entry(
                            title=f"Stagg EKG Pro ({mac_address[-8:]})",
                            data={CONF_MAC: mac_address},
                        )
                    else:
                        errors["base"] = "cannot_connect"
                except Exception as err:
                    _LOGGER.error(f"Error connecting to kettle: {err}")
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    def _is_valid_mac(self, mac: str) -> bool:
        """Validate MAC address format."""
        if len(mac) != 17:
            return False

        parts = mac.split(":")
        if len(parts) != 6:
            return False

        for part in parts:
            if len(part) != 2:
                return False
            try:
                int(part, 16)
            except ValueError:
                return False

        return True
