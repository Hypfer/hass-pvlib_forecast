"""PVLib Solar Forecast coordinator."""
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List

import pandas as pd
import pvlib
from pvlib import irradiance

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.weather import WeatherEntityFeature
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.config_entries import ConfigEntry

from .pvlib_misc import adjust_clearsky

from .weather_cache import WeatherDataCache
from .const import (
    DOMAIN,
    CONF_ALTITUDE,
    CONF_INSTALLED_KW,
    CONF_TILT,
    CONF_AZIMUTH,
    CONF_EFFICIENCY,
    CONF_INVERTER_KW,
    CONF_WEATHER_ENTITY,
    CONF_SYSTEM_NAME,
)

LOGGER = logging.getLogger(__name__)


def _create_synthetic_hourly_entries(daily_forecast_list: List[Dict]) -> List[Dict]:
    """Create synthetic hourly entries from daily forecast data."""
    hourly_forecast_list = []
    for daily in daily_forecast_list:
        date = pd.Timestamp(daily['datetime'])
        daily_hours = pd.date_range(date, date + timedelta(days=1), freq='h')[:-1]

        for hour in daily_hours:
            hourly_entry = daily.copy()  # Clone the daily data to each hourly slot.
            hourly_entry['datetime'] = hour
            hourly_forecast_list.append(hourly_entry)

    return hourly_forecast_list


class PVLibForecastCoordinator(DataUpdateCoordinator):
    """Coordinator for PVLib solar forecasts."""

    def __init__(self, hass, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),
        )
        self.hass = hass
        # Configuration parameters that don't change
        self.latitude = entry.data[CONF_LATITUDE]
        self.longitude = entry.data[CONF_LONGITUDE]
        self.altitude = entry.data[CONF_ALTITUDE]
        self.system_name = entry.data[CONF_SYSTEM_NAME]

        # Adjustable parameters from options
        self.installed_kw = entry.options.get(CONF_INSTALLED_KW, entry.data[CONF_INSTALLED_KW])
        self.tilt = entry.options.get(CONF_TILT, entry.data[CONF_TILT])
        self.azimuth = entry.options.get(CONF_AZIMUTH, entry.data[CONF_AZIMUTH])
        self.efficiency = entry.options.get(CONF_EFFICIENCY, entry.data[CONF_EFFICIENCY])
        self.inverter_kw = entry.options.get(CONF_INVERTER_KW, entry.data.get(CONF_INVERTER_KW))
        self.weather_entity = entry.options.get(CONF_WEATHER_ENTITY, entry.data.get(CONF_WEATHER_ENTITY))

        self.weather_cache = WeatherDataCache()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Calculate forecast data and manage weather data cache."""

        times = pd.date_range(
            start=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            end=datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=7),
            freq='h',
            tz='UTC'
        )
        LOGGER.debug("Generated time series:\n%s", times)

        location = pvlib.location.Location(
            latitude=self.latitude,
            longitude=self.longitude,
            tz='UTC',
            altitude=self.altitude
        )
        solpos = location.get_solarposition(times)
        clearsky = location.get_clearsky(times)
        LOGGER.debug("Solar position:\n%s", solpos)
        LOGGER.debug("Clear sky data:\n%s", clearsky)

        try:
            if self.weather_entity:
                LOGGER.debug("Checking weather for %s", self.weather_entity)
                state = self.hass.states.get(self.weather_entity)
                if state is None:
                    raise ValueError(f"Weather entity state not available: {self.weather_entity}")

                supported_features = state.attributes.get('supported_features', 0)
                LOGGER.debug("Supported features of the weather entity: %s", supported_features)

                if supported_features & WeatherEntityFeature.FORECAST_HOURLY:
                    forecast_type = 'hourly'
                elif supported_features & WeatherEntityFeature.FORECAST_DAILY:
                    forecast_type = 'daily'
                else:
                    raise ValueError("No supported forecast feature available.")

                forecast_data = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"entity_id": self.weather_entity, "type": forecast_type},
                    blocking=True,
                    return_response=True
                )

                if forecast_data and self.weather_entity in forecast_data:
                    forecast_list = forecast_data[self.weather_entity]['forecast']
                    for entry in forecast_list:
                        entry['datetime'] = pd.Timestamp(entry['datetime']).floor('h')

                    if forecast_type == 'daily':
                        forecast_list = _create_synthetic_hourly_entries(forecast_list)

                    self.weather_cache.upsert(pd.DataFrame(forecast_list))

                cached_weather_data = self.weather_cache.get_data()
                LOGGER.debug("Cached weather data:\n%s", cached_weather_data)

                cloud_cover = pd.Series(index=times, data=[0.0] * len(times))
                unmatched_entries = 0

                for entry in cached_weather_data.itertuples():
                    forecast_timestamp = pd.Timestamp(entry.datetime).tz_convert('UTC')

                    if forecast_timestamp in cloud_cover.index:
                        cloud_cover[forecast_timestamp] = entry.cloud_coverage or 0
                    else:
                        unmatched_entries += 1

                LOGGER.debug("Total timestamps in cloud_cover: %d", len(cloud_cover))
                LOGGER.debug("Total timestamps in cached_weather_data: %d", len(cached_weather_data))
                LOGGER.debug("Matched Entries: %d. Unmatched timestamps: %d",
                           len(cached_weather_data) - unmatched_entries, unmatched_entries)

                LOGGER.debug("Computed cloud cover series:\n%s", cloud_cover)

                clearsky = adjust_clearsky(
                    location,
                    clearsky,
                    cloud_cover,
                    method='clearsky_scaling'
                )
                LOGGER.debug("Adjusted clear sky data:\n%s", clearsky)
            else:
                LOGGER.debug("No weather entity configured")

        except Exception as e:
            LOGGER.warning("Failed to get weather forecast: %s", e, exc_info=True)

        poa_irradiance = irradiance.get_total_irradiance(
            self.tilt,
            self.azimuth,
            solpos.apparent_zenith,
            solpos.azimuth,
            clearsky.dni,
            clearsky.ghi,
            clearsky.dhi
        )
        LOGGER.debug("POA Irradiance:\n%s", poa_irradiance)

        dc_power = poa_irradiance['poa_global'] * self.installed_kw * self.efficiency

        if self.inverter_kw is not None:
            max_inverter_watts = self.inverter_kw * 1000
            dc_power = dc_power.clip(lower=0, upper=max_inverter_watts)

        wh_period = dc_power.to_dict()
        LOGGER.debug("Calculated DC power:\n%s", dc_power)

        return {
            "wh_period": wh_period,
            "timestamps": times,
            "forecast": dc_power.to_numpy(),
        }