"""SolaX Cloud Sensors."""

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import SolaXCloudConfigEntry
from .const import BIDIRECTIONAL_ABOVE_ZERO, BIDIRECTIONAL_BELOW_ZERO, DOMAIN
from .solax_cloud import ConnectionFailed, InvalidAPIToken, InvalidDeviceSN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolaXCloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the entities for a SolaX cloud device."""
    coordinator = SolaXAPICoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.data["device_id"])}, name=entry.data["device_id"]
    )
    async_add_entities(
        (
            PowerSensor(coordinator, entry, "acpower", "AC power", device_info),
            BiDirectionalPowerSensor(
                coordinator,
                entry,
                "feedinpower",
                "Grid power import",
                device_info,
                BIDIRECTIONAL_BELOW_ZERO,
                icon="mdi:transmission-tower-import",
            ),
            BiDirectionalPowerSensor(
                coordinator,
                entry,
                "feedinpower",
                "Grid power export",
                device_info,
                BIDIRECTIONAL_ABOVE_ZERO,
                icon="mdi:transmission-tower-export",
            ),
            BiDirectionalPowerSensor(
                coordinator,
                entry,
                "batPower",
                "Battery power charging",
                device_info,
                BIDIRECTIONAL_ABOVE_ZERO,
                icon="mdi:battery-arrow-up-outline",
            ),
            BiDirectionalPowerSensor(
                coordinator,
                entry,
                "batPower",
                "Battery power discharging",
                device_info,
                BIDIRECTIONAL_BELOW_ZERO,
                icon="mdi:battery-arrow-down-outline",
            ),
            PowerSensor(
                coordinator,
                entry,
                "powerdc1",
                "Solar power (DC1)",
                device_info,
                icon="mdi:solar-panel",
            ),
            PowerSensor(
                coordinator,
                entry,
                "powerdc2",
                "Solar power (DC2)",
                device_info,
                icon="mdi:solar-panel",
            ),
            PowerSensor(
                coordinator,
                entry,
                "powerdc3",
                "Solar power (DC3)",
                device_info,
                icon="mdi:solar-panel",
            ),
            PowerSensor(
                coordinator,
                entry,
                "powerdc4",
                "Solar power (DC4)",
                device_info,
                icon="mdi:solar-panel",
            ),
            EnergySensor(
                coordinator,
                entry,
                "yieldtoday",
                "Solar energy (today)",
                device_info,
                icon="mdi:solar-power",
            ),
            BatteryChargeSensor(
                coordinator, entry, "soc", "Battery charge percentage", device_info
            ),
        )
    )


class SolaXAPICoordinator(DataUpdateCoordinator):
    """Coordinator for accessing the SolaX API."""

    def __init__(self, hass: HomeAssistant, entry: SolaXCloudConfigEntry):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="SolaX API Coordinator",
            update_interval=timedelta(seconds=10),
        )
        self._api = entry.runtime_data
        self._entry = entry

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            return await self._api.fetch_api_data(
                self._entry.data["api_token"], self._entry.data["device_id"]
            )
        except InvalidAPIToken as err:
            raise ConfigEntryAuthFailed from err
        except InvalidDeviceSN as err:
            raise ConfigEntryAuthFailed from err
        except ConnectionFailed as err:
            err_msg = f"Error communicating with the SolaX API: {err}"
            raise UpdateFailed(err_msg) from err


class SolaXSensor(CoordinatorEntity, SensorEntity):
    """A sensor that handles input from the SolaXAPICoordinator."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: SolaXAPICoordinator,
        entry: SolaXCloudConfigEntry,
        data_key: str,
        entity_name: str,
        device_info: DeviceInfo,
        icon: str | None = None,
    ) -> None:
        """Create a new SolaXSensor."""
        super().__init__(coordinator)
        self._attr_name = entity_name
        self._attr_unique_id = f"{entry.data['device_id']}.{data_key}"
        self._attr_device_info = device_info
        self._current_value = None
        self._data_key = data_key
        if icon:
            self._attr_icon = icon

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (
            self.coordinator.data[self._data_key]
            and self._current_value != self.coordinator.data[self._data_key]
        ):
            self._current_value = self.coordinator.data[self._data_key]
            self.async_write_ha_state()

    @property
    def native_value(self: "PowerSensor") -> float | None:
        """Return the current native value."""
        return self._current_value


class PowerSensor(SolaXSensor):
    """A sensor representing current power."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "W"


class BiDirectionalPowerSensor(PowerSensor):
    """A sensor that handles a bidirectional power setup."""

    def __init__(
        self,
        coordinator: SolaXAPICoordinator,
        entry: SolaXCloudConfigEntry,
        data_key: str,
        entity_name: str,
        device_info: DeviceInfo,
        limit_values: BIDIRECTIONAL_ABOVE_ZERO | BIDIRECTIONAL_BELOW_ZERO,
        icon: str | None = None,
    ) -> None:
        """Create a new BiDirectionalPowerSensor."""
        super().__init__(
            coordinator, entry, data_key, entity_name, device_info, icon=icon
        )
        self._attr_unique_id = f"{entry.data['device_id']}.{data_key}.{limit_values}"
        self._limit_values = limit_values

    @property
    def native_value(self: "PowerSensor") -> float | None:
        """Return the current native value or zero if it is outside the limit_values setting."""
        if self._current_value is None:
            return None
        if self._limit_values == BIDIRECTIONAL_ABOVE_ZERO:
            return abs(max(0, self._current_value))
        if self._limit_values == BIDIRECTIONAL_BELOW_ZERO:
            return abs(min(0, self._current_value))
        return None


class EnergySensor(SolaXSensor):
    """A sensor that handles energy (power over time)."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = "kWh"
    _attr_state_class = "total_increasing"


class BatteryChargeSensor(SolaXSensor):
    """A sensor that handles battery charging percentage."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = "battery"
    _attr_icon = "mdi:battery-unknown"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()
        new_icon = "mdi:battery"
        if self._current_value == 0:
            new_icon = "mdi:battery-outline"
        elif self._current_value < 10:
            new_icon = "mdi:battery-10"
        elif self._current_value < 20:
            new_icon = "mdi:battery-20"
        elif self._current_value < 30:
            new_icon = "mdi:battery-30"
        elif self._current_value < 40:
            new_icon = "mdi:battery-40"
        elif self._current_value < 50:
            new_icon = "mdi:battery-50"
        elif self._current_value < 60:
            new_icon = "mdi:battery-60"
        elif self._current_value < 70:
            new_icon = "mdi:battery-70"
        elif self._current_value < 80:
            new_icon = "mdi:battery-80"
        elif self._current_value < 90:
            new_icon = "mdi:battery-90"
        if self._attr_icon != new_icon:
            self._attr_icon = new_icon
            self.async_write_ha_state()
