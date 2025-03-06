"""Sensor platform for PVLib Solar Forecast."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

import numpy as np
import pandas as pd

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PVLibForecastCoordinator


@dataclass
class PVLibSensorEntityDescription(SensorEntityDescription):
    """Describe PVLib sensor entity."""


SENSOR_TYPES: List[PVLibSensorEntityDescription] = [
    PVLibSensorEntityDescription(
        key="energy_today",
        name="Energy Production Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    ),
    PVLibSensorEntityDescription(
        key="energy_tomorrow",
        name="Energy Production Tomorrow",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    ),
    PVLibSensorEntityDescription(
        key="power_now",
        name="Current Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PVLib Solar Forecast sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PVLibForecastSensor(
            coordinator=coordinator,
            description=description,
        )
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities)


class PVLibForecastSensor(SensorEntity):
    """Representation of a PVLib Solar Forecast sensor."""

    def __init__(
        self,
        coordinator: PVLibForecastCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entity_description = description

        self._attr_name = f"{description.name}"
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.system_name}_{description.key}"
            .lower()
            .replace(" ", "_")
        )
        self.entity_id = f"sensor.{DOMAIN}_{coordinator.system_name}_{description.key}".lower().replace(" ", "_")

    @property
    def state(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        forecast = self.coordinator.data["forecast"]
        timestamps = self.coordinator.data["timestamps"]

        if len(forecast) != len(timestamps):
            return None

        if self.entity_description.key == "power_now":
            return self._get_current_power(forecast, timestamps)
        elif self.entity_description.key == "energy_today":
            return self._get_energy_for_day(forecast, timestamps, 0)
        elif self.entity_description.key == "energy_tomorrow":
            return self._get_energy_for_day(forecast, timestamps, 1)

        return None

    def _get_current_power(self, forecast: np.ndarray, timestamps: pd.DatetimeIndex) -> Optional[float]:
        """Get the current power output."""
        now = pd.Timestamp.now(tz='UTC')
        closest_idx = np.argmin(np.abs(timestamps - now))
        if closest_idx < len(forecast):
            return round(forecast[closest_idx])
        return None

    def _get_energy_for_day(
        self,
        forecast: np.ndarray,
        timestamps: pd.DatetimeIndex,
        days_offset: int
    ) -> Optional[float]:
        """Get the energy production for a specific day."""
        target_day = (pd.Timestamp.now(tz='UTC') + pd.Timedelta(days=days_offset)).floor('D')
        mask = timestamps.floor('D') == target_day
        return round(forecast[mask].sum())

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )