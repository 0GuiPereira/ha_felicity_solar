"""Config flow for Felicity Solar integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

class FelicitySolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Felicity Solar."""

    VERSION = 1

    def _get_plant_id(self, auth):
        """Get plant ID from API."""
        import requests
        from .const import BASE_URL, PLANT_LIST_ENDPOINT
        
        try:
            payload = {
                "pageNum": 1,
                "pageSize": 10,
                "plantName": "",
                "deviceSn": "",
                "status": "",
                "isCollected": "",
                "plantType": "",
                "onGridType": "",
                "tagName": "",
                "realName": "",
                "orgCode": "",
                "authorized": "",
                "cityId": "",
                "countryId": "",
                "provinceId": ""
            }
            
            headers = auth.get_auth_headers()
            response = requests.post(
                BASE_URL + PLANT_LIST_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200 and data.get("data", {}).get("dataList"):
                plants = data["data"]["dataList"]
                if plants:
                    return plants[0]["id"]  # Return first plant ID
            return None
            
        except Exception:
            return None

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required("username"): str,
                    vol.Required("password_hash"): str,
                    vol.Optional("scan_interval", default=30): int,
                }),
            )

        # Validate credentials by attempting login and get plant ID
        plant_id = None
        try:
            from .auth import FelicitySolarAuth
            auth = FelicitySolarAuth(user_input["username"], user_input["password_hash"])
            if await self.hass.async_add_executor_job(auth.login):
                # Get plant ID from API
                plant_id = await self.hass.async_add_executor_job(self._get_plant_id, auth)
                if not plant_id:
                    errors["base"] = "no_plants_found"
            else:
                errors["base"] = "invalid_auth"
        except Exception:
            errors["base"] = "cannot_connect"
        
        if not errors:
            # Don't store plant_id - it will be auto-detected each time in sensor.py
            return self.async_create_entry(
                title=f"Felicity Solar ({user_input['username']})",
                data=user_input,
            )
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username", default=user_input.get("username", "")): str,
                vol.Required("password_hash"): str,
                vol.Optional("scan_interval", default=user_input.get("scan_interval", 30)): int,
            }),
            errors=errors,
        )