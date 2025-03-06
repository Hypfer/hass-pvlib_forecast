"""Energy platform integration."""
from datetime import datetime, timedelta
import logging
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_get_solar_forecast(hass: HomeAssistant, config_entry_id: str):
    """Return solar forecast data for the energy dashboard."""
    if (coordinator := hass.data[DOMAIN].get(config_entry_id)) is None:
        return None

    wh_period = coordinator.data["wh_period"]

    forecast_data = {
        "wh_hours": {
            timestamp.isoformat(): wh_value
            for timestamp, wh_value in wh_period.items()
        }
    }

    return forecast_data