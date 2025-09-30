from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ENERGY_WATT

from .const import DOMAIN, BASE_URL, LOGIN_ENDPOINT, DEVICE_ENDPOINT
import requests
from datetime import datetime

class FelicityPvPowerSensor(SensorEntity):
    def __init__(self, email, password, plant_id):
        self._email = email
        self._password = password
        self._plant_id = plant_id
        self._attr_name = "Felicity PV Power"
        self._attr_unique_id = f"felicity_{plant_id}_pv_power"
        self._attr_native_unit_of_measurement = ENERGY_WATT
        self._state = None

    def login(self):
        payload = {"userName": self._email, "password": self._password, "version": "1.0"}
        r = requests.post(BASE_URL + LOGIN_ENDPOINT, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["data"]["token"]

    def update(self):
        token = self.login()
        payload = {
            "deviceSn": None,
            "icons": ["BLOCK_PV"],
            "plantId": self._plant_id,
            "pageSize": 10,
            "pageNum": 1,
            "dateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        headers = {"Authorization": token, "Content-Type": "application/json"}
        r = requests.post(BASE_URL + DEVICE_ENDPOINT, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        try:
            self._state = data["data"]["BLOCK_PV"]
        except Exception:
            self._state = None

    @property
    def native_value(self):
        return self._state