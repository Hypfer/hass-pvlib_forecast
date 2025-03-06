"""Sensor platform for PVLib Solar Forecast."""
from datetime import datetime, timedelta
from typing import Optional
import numpy as np
import pandas as pd

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
)

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PVLibForecastSensor(
            coordinator,
            "energy_today",
            "Energy Production Today",
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.WATT_HOUR,
        ),
        PVLibForecastSensor(
            coordinator,
            "energy_tomorrow",
            "Energy Production Tomorrow",
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.WATT_HOUR,
        ),
        PVLibForecastSensor(
            coordinator,
            "power_now",
            "Current Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
        ),
    ]

    async_add_entities(entities)


class PVLibForecastSensor(SensorEntity):
    def __init__(self, coordinator, key, name, device_class, unit):
        self.coordinator = coordinator
        self._key = key
        self._attr_name = f"{coordinator.system_name}_{name}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{DOMAIN}_{coordinator.system_name}_{key}".lower().replace(" ", "_")

    @property
    def state(self):
        if not self.coordinator.data:
            return None

        forecast = self.coordinator.data["forecast"]
        timestamps = self.coordinator.data["timestamps"]

        if self._key == "power_now":
            now = pd.Timestamp.now(tz='UTC')  # Make timezone-aware
            closest_idx = np.argmin(np.abs(timestamps - now))
            if closest_idx < len(forecast):
                return round(forecast[closest_idx])
            else:
                return None

        elif self._key == "energy_today":
            today = pd.Timestamp.now(tz='UTC').floor('D')  # Make timezone-aware
            mask = timestamps.floor('D') == today
            if len(forecast) == len(mask):
                return round(forecast[mask].sum() * 1)  # 1 hour intervals
            else:
                return None  # Or handle mismatch appropriately

        elif self._key == "energy_tomorrow":
            tomorrow = (pd.Timestamp.now(tz='UTC') + pd.Timedelta(days=1)).floor('D')  # Make timezone-aware
            mask = timestamps.floor('D') == tomorrow
            if len(forecast) == len(mask):
                return round(forecast[mask].sum() * 1)  # 1 hour intervals
            else:
                return None  # Or handle mismatch appropriately

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )