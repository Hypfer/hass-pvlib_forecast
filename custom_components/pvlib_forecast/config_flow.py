"""Config flow for PVLib Solar Forecast."""
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers import selector

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


def create_schema(defaults: Dict[str, Any]) -> vol.Schema:
    """Create a schema with the provided defaults."""
    return vol.Schema({
        vol.Required(CONF_SYSTEM_NAME, default=defaults.get(CONF_SYSTEM_NAME, "Solar System")): str,
        vol.Required(CONF_LATITUDE, default=defaults.get(CONF_LATITUDE)): vol.Coerce(float),
        vol.Required(CONF_LONGITUDE, default=defaults.get(CONF_LONGITUDE)): vol.Coerce(float),
        vol.Required(CONF_ALTITUDE, default=defaults.get(CONF_ALTITUDE, 0)): vol.Coerce(float),
        vol.Required(CONF_INSTALLED_KW, default=defaults.get(CONF_INSTALLED_KW)): vol.Coerce(float),
        vol.Required(CONF_TILT, default=defaults.get(CONF_TILT, 30)): vol.Coerce(float),
        vol.Required(CONF_AZIMUTH, default=defaults.get(CONF_AZIMUTH, 180)): vol.Coerce(float),
        vol.Required(CONF_EFFICIENCY, default=defaults.get(CONF_EFFICIENCY, 0.96)): vol.Coerce(float),
        vol.Optional(CONF_INVERTER_KW, default=defaults.get(CONF_INVERTER_KW)): vol.Coerce(float),
        vol.Optional(CONF_WEATHER_ENTITY, default=defaults.get(CONF_WEATHER_ENTITY)): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="weather"),
        ),
    })


def create_options_schema(defaults: Dict[str, Any]) -> vol.Schema:
    """Create a schema for options with the provided defaults."""
    return vol.Schema({
        vol.Required(CONF_INSTALLED_KW, default=defaults.get(CONF_INSTALLED_KW)): vol.Coerce(float),
        vol.Required(CONF_TILT, default=defaults.get(CONF_TILT, 30)): vol.Coerce(float),
        vol.Required(CONF_AZIMUTH, default=defaults.get(CONF_AZIMUTH, 180)): vol.Coerce(float),
        vol.Required(CONF_EFFICIENCY, default=defaults.get(CONF_EFFICIENCY, 0.96)): vol.Coerce(float),
        vol.Optional(CONF_INVERTER_KW, default=defaults.get(CONF_INVERTER_KW)): vol.Coerce(float),
        vol.Optional(CONF_WEATHER_ENTITY, default=defaults.get(CONF_WEATHER_ENTITY)): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="weather"),
        ),
    })

class PVLibForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PVLib Solar Forecast."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_SYSTEM_NAME],
                data=user_input
            )

        defaults = {
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=create_schema(defaults)
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for PVLib Solar Forecast."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Use existing options if they exist, otherwise use config data
        current_data = {
            **self.config_entry.data,
            **self.config_entry.options
        }

        return self.async_show_form(
            step_id="init",
            data_schema=create_options_schema(current_data)
        )