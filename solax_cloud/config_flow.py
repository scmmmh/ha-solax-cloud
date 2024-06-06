"""Config flow for SolaX Cloud integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_TOKEN, CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .solax_cloud import (
    ConnectionFailed,
    InvalidAPIToken,
    InvalidDeviceSN,
    SolaXCloudAPI,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): str,
        vol.Required(CONF_DEVICE_ID): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    api = SolaXCloudAPI()
    try:
        metadata = await api.fetch_device_metadata(
            data[CONF_API_TOKEN], data[CONF_DEVICE_ID]
        )
        return {
            "title": metadata["sn"],
            "sn": metadata["sn"],
        }
    except InvalidAPIToken as err:
        raise InvalidApiKey from err
    except InvalidDeviceSN as err:
        raise InvalidDevice from err
    except ConnectionFailed as err:
        raise ConnectionError from err


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolaX Cloud."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(info["sn"], raise_on_progress=True)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidApiKey:
                errors["base"] = "invalid_api_key"
            except InvalidDevice:
                errors["base"] = "invalid_device"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is invalid API key."""


class InvalidDevice(HomeAssistantError):
    """Error to indicate that there is no matching device."""
