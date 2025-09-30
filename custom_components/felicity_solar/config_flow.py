"""Config flow for Felicity Solar integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

class FelicitySolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Felicity Solar."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Optional("plant_id", default="11114725281235393"): str,
                    vol.Optional("scan_interval", default=30): int,
                }),
            )

        # Validate credentials by attempting login
        try:
            from .auth import FelicitySolarAuth
            auth = FelicitySolarAuth(user_input["username"], user_input["password"])
            if not await self.hass.async_add_executor_job(auth.login):
                errors["base"] = "invalid_auth"
        except Exception:
            errors["base"] = "cannot_connect"
        
        if not errors:
            return self.async_create_entry(
                title=f"Felicity Solar ({user_input['username']})",
                data=user_input,
            )
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username", default=user_input.get("username", "")): str,
                vol.Required("password"): str,
                vol.Optional("plant_id", default=user_input.get("plant_id", "11114725281235393")): str,
                vol.Optional("scan_interval", default=user_input.get("scan_interval", 30)): int,
            }),
            errors=errors,
        )