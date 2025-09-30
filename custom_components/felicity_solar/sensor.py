from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    PERCENTAGE
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, BASE_URL, PLANT_LIST_ENDPOINT, DEVICE_REALTIME_ENDPOINT, ORGAN_CODE
from .auth import FelicitySolarAuth
import requests
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Felicity Solar sensors."""
    username = config_entry.data.get("username")
    password_hash = config_entry.data.get("password_hash")
    plant_id = config_entry.data.get("plant_id")
    
    # Create shared auth instance
    auth = FelicitySolarAuth(username, password_hash)
    
    sensors = [
        FelicityCurrentPowerSensor(plant_id, auth),
        FelicityTodayEnergySensor(plant_id, auth),
        FelicityTotalEnergySensor(plant_id, auth),
        FelicityPvVoltageSensor(plant_id, auth, "FV1", 0),
        FelicityPvVoltageSensor(plant_id, auth, "FV2", 1),
        FelicityPvCurrentSensor(plant_id, auth, "FV1", 0),
        FelicityPvCurrentSensor(plant_id, auth, "FV2", 1),
        FelicityPvPowerSensor(plant_id, auth, "FV1", 0),
        FelicityPvPowerSensor(plant_id, auth, "FV2", 1),
        FelicityTotalPvPowerSensor(plant_id, auth),
    ]
    
    async_add_entities(sensors, True)

class FelicitySolarSensorBase(SensorEntity):
    """Base class for Felicity Solar sensors."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth):
        self._plant_id = plant_id
        self._auth = auth
        self._attr_available = True
        self._plant_data = None
        self._device_data = None
    
    def get_plant_data(self):
        """Get plant data from API."""
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
            
            headers = self._auth.get_auth_headers()
            response = requests.post(
                BASE_URL + PLANT_LIST_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data["code"] == 200 and data["data"]["dataList"]:
                for plant in data["data"]["dataList"]:
                    if plant["id"] == self._plant_id:
                        return plant
            return None
            
        except Exception as e:
            _LOGGER.error(f"Error fetching plant data: {e}")
            return None
    
    def get_device_data(self):
        """Get device realtime data from API."""
        try:
            payload = {
                "deviceSn": None,
                "icons": ["BLOCK_PV"],
                "plantId": self._plant_id,
                "pageSize": 10,
                "pageNum": 1,
                "dateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            headers = self._auth.get_auth_headers()
            response = requests.post(
                BASE_URL + DEVICE_REALTIME_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data["code"] == 200 and data["data"]["dataList"]:
                return data["data"]["dataList"][0]
            return None
            
        except Exception as e:
            _LOGGER.error(f"Error fetching device data: {e}")
            return None
    
    async def async_update(self):
        """Update sensor data."""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Run the blocking API calls in executor
        self._plant_data = await loop.run_in_executor(None, self.get_plant_data)
        self._device_data = await loop.run_in_executor(None, self.get_device_data)
        self._attr_available = self._plant_data is not None

class FelicityCurrentPowerSensor(FelicitySolarSensorBase):
    """Current power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth):
        super().__init__(plant_id, auth)
        self._attr_name = "Felicity Solar Current Power"
        self._attr_unique_id = f"felicity_{plant_id}_current_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        if self._plant_data:
            return float(self._plant_data.get("currentPower", 0))
        return None

class FelicityTodayEnergySensor(FelicitySolarSensorBase):
    """Today energy sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth):
        super().__init__(plant_id, auth)
        self._attr_name = "Felicity Solar Today Energy"
        self._attr_unique_id = f"felicity_{plant_id}_today_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total_increasing"
    
    @property
    def native_value(self):
        if self._plant_data:
            return float(self._plant_data.get("todayEnergy", 0))
        return None

class FelicityTotalEnergySensor(FelicitySolarSensorBase):
    """Total energy sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth):
        super().__init__(plant_id, auth)
        self._attr_name = "Felicity Solar Total Energy"
        self._attr_unique_id = f"felicity_{plant_id}_total_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total"
    
    @property
    def native_value(self):
        if self._plant_data:
            return float(self._plant_data.get("totalEnergy", 0))
        return None

class FelicityPvVoltageSensor(FelicitySolarSensorBase):
    """PV string voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, string_name: str, string_index: int):
        super().__init__(plant_id, auth)
        self._string_name = string_name
        self._string_index = string_index
        self._attr_name = f"Felicity Solar {string_name} Voltage"
        self._attr_unique_id = f"felicity_{plant_id}_{string_name.lower()}_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        if self._device_data and "templateBlockVO" in self._device_data:
            tables = self._device_data["templateBlockVO"].get("tables", [])
            if tables and len(tables) > 0:
                table = tables[0]
                points = table.get("points", [])
                if len(points) > self._string_index and len(points[self._string_index]) > 0:
                    return float(points[self._string_index][0])
        return None

class FelicityPvCurrentSensor(FelicitySolarSensorBase):
    """PV string current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, string_name: str, string_index: int):
        super().__init__(plant_id, auth)
        self._string_name = string_name
        self._string_index = string_index
        self._attr_name = f"Felicity Solar {string_name} Current"
        self._attr_unique_id = f"felicity_{plant_id}_{string_name.lower()}_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        if self._device_data and "templateBlockVO" in self._device_data:
            tables = self._device_data["templateBlockVO"].get("tables", [])
            if tables and len(tables) > 0:
                table = tables[0]
                points = table.get("points", [])
                if len(points) > self._string_index and len(points[self._string_index]) > 1:
                    return float(points[self._string_index][1])
        return None

class FelicityPvPowerSensor(FelicitySolarSensorBase):
    """PV string power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, string_name: str, string_index: int):
        super().__init__(plant_id, auth)
        self._string_name = string_name
        self._string_index = string_index
        self._attr_name = f"Felicity Solar {string_name} Power"
        self._attr_unique_id = f"felicity_{plant_id}_{string_name.lower()}_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        if self._device_data and "templateBlockVO" in self._device_data:
            tables = self._device_data["templateBlockVO"].get("tables", [])
            if tables and len(tables) > 0:
                table = tables[0]
                points = table.get("points", [])
                if len(points) > self._string_index and len(points[self._string_index]) > 2:
                    return float(points[self._string_index][2])
        return None

class FelicityTotalPvPowerSensor(FelicitySolarSensorBase):
    """Total PV power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth):
        super().__init__(plant_id, auth)
        self._attr_name = "Felicity Solar Total PV Power"
        self._attr_unique_id = f"felicity_{plant_id}_total_pv_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        if self._device_data and "templateBlockVO" in self._device_data:
            tables = self._device_data["templateBlockVO"].get("tables", [])
            if len(tables) > 1:
                table = tables[1]
                points = table.get("points", [])
                if points and len(points) > 0 and len(points[0]) > 0:
                    return float(points[0][0])
        return None