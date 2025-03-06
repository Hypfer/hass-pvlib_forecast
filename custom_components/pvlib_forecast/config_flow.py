"""Config flow for PVLib Solar Forecast."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers import selector
from .const import *

class PVLibForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_SYSTEM_NAME],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_SYSTEM_NAME, default="Solar System"): str,
                vol.Required(CONF_LATITUDE, default=self.hass.config.latitude): vol.Coerce(float),
                vol.Required(CONF_LONGITUDE, default=self.hass.config.longitude): vol.Coerce(float),
                vol.Required(CONF_ALTITUDE, default=0): vol.Coerce(float),
                vol.Required(CONF_SYSTEM_KW): vol.Coerce(float),
                vol.Required(CONF_TILT, default=30): vol.Coerce(float),
                vol.Required(CONF_AZIMUTH, default=180): vol.Coerce(float),
                vol.Required(CONF_EFFICIENCY, default=0.96): vol.Coerce(float),
                vol.Optional(CONF_MAX_INVERTER_POWER): vol.Coerce(float),
                vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather"),
                ),
            })
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_SYSTEM_NAME, default=self.config_entry.data.get(CONF_SYSTEM_NAME)): str,
                vol.Required(CONF_LATITUDE, default=self.config_entry.data.get(CONF_LATITUDE)): vol.Coerce(float),
                vol.Required(CONF_LONGITUDE, default=self.config_entry.data.get(CONF_LONGITUDE)): vol.Coerce(float),
                vol.Required(CONF_ALTITUDE, default=self.config_entry.data.get(CONF_ALTITUDE)): vol.Coerce(float),
                vol.Required(CONF_SYSTEM_KW, default=self.config_entry.data.get(CONF_SYSTEM_KW)): vol.Coerce(float),
                vol.Required(CONF_TILT, default=self.config_entry.data.get(CONF_TILT)): vol.Coerce(float),
                vol.Required(CONF_AZIMUTH, default=self.config_entry.data.get(CONF_AZIMUTH)): vol.Coerce(float),
                vol.Required(CONF_EFFICIENCY, default=self.config_entry.data.get(CONF_EFFICIENCY)): vol.Coerce(float),
                vol.Optional(CONF_MAX_INVERTER_POWER, default=self.config_entry.data.get(CONF_MAX_INVERTER_POWER)): vol.Coerce(float),
                vol.Optional(CONF_WEATHER_ENTITY, default=self.config_entry.data.get(CONF_WEATHER_ENTITY)): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather"),
                ),
            })
        )