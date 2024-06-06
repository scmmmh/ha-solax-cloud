"""The SolaX Cloud integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .solax_cloud import SolaXCloudAPI

PLATFORMS: list[Platform] = [Platform.SENSOR]

type SolaXCloudConfigEntry = ConfigEntry[SolaXCloudAPI]  # noqa: F821


async def async_setup_entry(hass: HomeAssistant, entry: SolaXCloudConfigEntry) -> bool:
    """Set up SolaX Cloud from a config entry."""

    api = SolaXCloudAPI()
    entry.runtime_data = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SolaXCloudConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
