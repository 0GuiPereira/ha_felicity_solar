from homeassistant.core import HomeAssistant

DOMAIN = "felicity_solar"

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry):
    return True