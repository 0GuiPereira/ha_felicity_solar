"""Felicity Solar integration v2.0 - Using snapshot endpoint for comprehensive data."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfTemperature,
    PERCENTAGE
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, BASE_URL, PLANT_LIST_ENDPOINT, DEVICE_SNAPSHOT_ENDPOINT
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
    """Set up the Felicity Solar sensors v2.0."""
    username = config_entry.data.get("username")
    password_hash = config_entry.data.get("password_hash")
    plant_id = config_entry.data.get("plant_id")
    scan_interval = config_entry.data.get("scan_interval", 30)
    
    # Create shared auth instance
    auth = FelicitySolarAuth(username, password_hash)
    
    # First get device info to get device serial number
    device_info = await hass.async_add_executor_job(_get_device_info, auth, plant_id)
    if not device_info:
        _LOGGER.error("Could not get device information for plant %s", plant_id)
        return
    
    device_sn = device_info.get("deviceSn")
    device_type = device_info.get("deviceType", "OC")
    
    _LOGGER.info(f"Setting up Felicity Solar v2.0 for device {device_sn}")
    
    # Create comprehensive sensors based on snapshot endpoint
    sensors = [
        # Power Generation
        FelicityPvTotalPowerSensor(plant_id, auth, device_sn, device_type),
        FelicityPv1PowerSensor(plant_id, auth, device_sn, device_type),
        FelicityPv2PowerSensor(plant_id, auth, device_sn, device_type),
        FelicityPv3PowerSensor(plant_id, auth, device_sn, device_type),
        FelicityPv4PowerSensor(plant_id, auth, device_sn, device_type),
        
        # PV Voltage & Current
        FelicityPv1VoltageSensor(plant_id, auth, device_sn, device_type),
        FelicityPv2VoltageSensor(plant_id, auth, device_sn, device_type),
        FelicityPv3VoltageSensor(plant_id, auth, device_sn, device_type),
        FelicityPv1CurrentSensor(plant_id, auth, device_sn, device_type),
        FelicityPv2CurrentSensor(plant_id, auth, device_sn, device_type),
        FelicityPv3CurrentSensor(plant_id, auth, device_sn, device_type),
        
        # AC Input (Grid)
        FelicityAcInputVoltageSensor(plant_id, auth, device_sn, device_type),
        FelicityAcInputCurrentSensor(plant_id, auth, device_sn, device_type),
        FelicityAcInputFrequencySensor(plant_id, auth, device_sn, device_type),
        FelicityAcInputPowerSensor(plant_id, auth, device_sn, device_type),
        
        # AC Output (Load)
        FelicityAcOutputVoltageSensor(plant_id, auth, device_sn, device_type),
        FelicityAcOutputCurrentSensor(plant_id, auth, device_sn, device_type),
        FelicityAcOutputFrequencySensor(plant_id, auth, device_sn, device_type),
        FelicityAcOutputPowerSensor(plant_id, auth, device_sn, device_type),
        
        # Energy Totals
        FelicityTotalEnergySensor(plant_id, auth, device_sn, device_type),
        FelicityTodayEnergySensor(plant_id, auth, device_sn, device_type),
        FelicityGridFeedTodaySensor(plant_id, auth, device_sn, device_type),
        FelicityGridFeedTotalSensor(plant_id, auth, device_sn, device_type),
        
        # Temperatures
        FelicityTempMaxSensor(plant_id, auth, device_sn, device_type),
        FelicityDeviceTempMaxSensor(plant_id, auth, device_sn, device_type),
        
        # Load & Grid
        FelicityLoadPercentSensor(plant_id, auth, device_sn, device_type),
        FelicityMeterPowerSensor(plant_id, auth, device_sn, device_type),
        
        # Device Status
        FelicityDeviceStatusSensor(plant_id, auth, device_sn, device_type),
        FelicityWifiSignalSensor(plant_id, auth, device_sn, device_type),
    ]
    
    # Add battery sensors if battery is present
    if device_info.get("batteryCapacity") and float(device_info.get("batteryCapacity", 0)) > 0:
        sensors.extend([
            FelicityBatterySocSensor(plant_id, auth, device_sn, device_type),
            FelicityBatteryVoltageSensor(plant_id, auth, device_sn, device_type),
            FelicityBatteryCurrentSensor(plant_id, auth, device_sn, device_type),
            FelicityBatteryPowerSensor(plant_id, auth, device_sn, device_type),
        ])
    
    async_add_entities(sensors, True)

def _get_device_info(auth: FelicitySolarAuth, plant_id: str):
    """Get device information from plant list."""
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
        if not headers:
            return None
            
        response = requests.post(
            BASE_URL + PLANT_LIST_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200 and data.get("data", {}).get("dataList"):
            for plant in data["data"]["dataList"]:
                if plant["id"] == plant_id:
                    device_list = plant.get("plantDeviceList", [])
                    if device_list:
                        return {"deviceSn": device_list[0]["deviceSn"], "deviceType": "OC"}
        return None
    except Exception as e:
        _LOGGER.error(f"Error getting device info: {e}")
        return None

class FelicitySolarSensorBase(SensorEntity):
    """Base class for Felicity Solar sensors v2.0."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        self._plant_id = plant_id
        self._auth = auth
        self._device_sn = device_sn
        self._device_type = device_type
        self._attr_available = True
        self._snapshot_data = None
    
    def get_snapshot_data(self):
        """Get device snapshot data from API."""
        try:
            payload = {
                "deviceSn": self._device_sn,
                "deviceType": self._device_type,
                "dateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            headers = self._auth.get_auth_headers()
            if not headers:
                _LOGGER.error("No authentication headers available")
                return None
                
            response = requests.post(
                BASE_URL + DEVICE_SNAPSHOT_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            _LOGGER.debug(f"Snapshot data response code: {data.get('code')}")
            
            if data.get("code") == 200 and data.get("data"):
                return data["data"]
            return None
            
        except Exception as e:
            _LOGGER.error(f"Error fetching snapshot data: {e}")
            return None
    
    async def async_update(self):
        """Update sensor data."""
        try:
            # Login if needed
            if not self._auth.get_valid_token():
                _LOGGER.info("Logging in to Felicity Solar API")
                login_success = await self.hass.async_add_executor_job(self._auth.login)
                if not login_success:
                    _LOGGER.error("Failed to login to Felicity Solar API")
                    self._attr_available = False
                    return
            
            # Get snapshot data
            self._snapshot_data = await self.hass.async_add_executor_job(self.get_snapshot_data)
            self._attr_available = self._snapshot_data is not None
            
            if not self._attr_available:
                _LOGGER.warning("No snapshot data available from Felicity Solar API")
                
        except Exception as e:
            _LOGGER.error(f"Error updating sensor data: {e}")
            self._attr_available = False

    def _get_float_value(self, key: str, default: float = 0.0) -> float:
        """Safely get float value from snapshot data, ignoring null values."""
        if not self._snapshot_data:
            return default
        value = self._snapshot_data.get(key)
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _get_string_value(self, key: str, default: str = "Unknown") -> str:
        """Safely get string value from snapshot data."""
        if not self._snapshot_data:
            return default
        value = self._snapshot_data.get(key)
        if value is None or value == "":
            return default
        return str(value)

# Power Generation Sensors
class FelicityPvTotalPowerSensor(FelicitySolarSensorBase):
    """Total PV power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV Total Power"
        self._attr_unique_id = f"felicity_{plant_id}_pv_total_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvTotalPower")

class FelicityPv1PowerSensor(FelicitySolarSensorBase):
    """PV1 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV1 Power"
        self._attr_unique_id = f"felicity_{plant_id}_pv1_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvPower")

class FelicityPv2PowerSensor(FelicitySolarSensorBase):
    """PV2 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV2 Power"
        self._attr_unique_id = f"felicity_{plant_id}_pv2_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv2Power")

class FelicityPv3PowerSensor(FelicitySolarSensorBase):
    """PV3 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV3 Power"
        self._attr_unique_id = f"felicity_{plant_id}_pv3_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv3Power")

class FelicityPv4PowerSensor(FelicitySolarSensorBase):
    """PV4 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV4 Power"
        self._attr_unique_id = f"felicity_{plant_id}_pv4_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv4Power")

# PV Voltage Sensors
class FelicityPv1VoltageSensor(FelicitySolarSensorBase):
    """PV1 voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV1 Voltage"
        self._attr_unique_id = f"felicity_{plant_id}_pv1_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvVolt")

class FelicityPv2VoltageSensor(FelicitySolarSensorBase):
    """PV2 voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV2 Voltage"
        self._attr_unique_id = f"felicity_{plant_id}_pv2_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv2Volt")

class FelicityPv3VoltageSensor(FelicitySolarSensorBase):
    """PV3 voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV3 Voltage"
        self._attr_unique_id = f"felicity_{plant_id}_pv3_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv3Volt")

# PV Current Sensors
class FelicityPv1CurrentSensor(FelicitySolarSensorBase):
    """PV1 current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV1 Current"
        self._attr_unique_id = f"felicity_{plant_id}_pv1_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvInCurr")

class FelicityPv2CurrentSensor(FelicitySolarSensorBase):
    """PV2 current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV2 Current"
        self._attr_unique_id = f"felicity_{plant_id}_pv2_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv2InCurr")

class FelicityPv3CurrentSensor(FelicitySolarSensorBase):
    """PV3 current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar PV3 Current"
        self._attr_unique_id = f"felicity_{plant_id}_pv3_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv3InCurr")

# AC Input (Grid) Sensors
class FelicityAcInputVoltageSensor(FelicitySolarSensorBase):
    """AC Input voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Input Voltage"
        self._attr_unique_id = f"felicity_{plant_id}_ac_input_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInVolt")

class FelicityAcInputCurrentSensor(FelicitySolarSensorBase):
    """AC Input current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Input Current"
        self._attr_unique_id = f"felicity_{plant_id}_ac_input_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInCurr")

class FelicityAcInputFrequencySensor(FelicitySolarSensorBase):
    """AC Input frequency sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Input Frequency"
        self._attr_unique_id = f"felicity_{plant_id}_ac_input_frequency"
        self._attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
        self._attr_device_class = SensorDeviceClass.FREQUENCY
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInFreq")

class FelicityAcInputPowerSensor(FelicitySolarSensorBase):
    """AC Input power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Input Power"
        self._attr_unique_id = f"felicity_{plant_id}_ac_input_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInPower")

# AC Output (Load) Sensors
class FelicityAcOutputVoltageSensor(FelicitySolarSensorBase):
    """AC Output voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Output Voltage"
        self._attr_unique_id = f"felicity_{plant_id}_ac_output_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acROutVolt")

class FelicityAcOutputCurrentSensor(FelicitySolarSensorBase):
    """AC Output current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Output Current"
        self._attr_unique_id = f"felicity_{plant_id}_ac_output_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acROutCurr")

class FelicityAcOutputFrequencySensor(FelicitySolarSensorBase):
    """AC Output frequency sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Output Frequency"
        self._attr_unique_id = f"felicity_{plant_id}_ac_output_frequency"
        self._attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
        self._attr_device_class = SensorDeviceClass.FREQUENCY
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acROutFreq")

class FelicityAcOutputPowerSensor(FelicitySolarSensorBase):
    """AC Output power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar AC Output Power"
        self._attr_unique_id = f"felicity_{plant_id}_ac_output_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acTotalOutActPower")

# Energy Sensors
class FelicityTotalEnergySensor(FelicitySolarSensorBase):
    """Total energy sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Total Energy"
        self._attr_unique_id = f"felicity_{plant_id}_total_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total"
    
    @property
    def native_value(self):
        return self._get_float_value("totalEnergy")

class FelicityTodayEnergySensor(FelicitySolarSensorBase):
    """Today energy sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Today Energy"
        self._attr_unique_id = f"felicity_{plant_id}_today_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total_increasing"
    
    @property
    def native_value(self):
        return self._get_float_value("ePvToday")

class FelicityGridFeedTodaySensor(FelicitySolarSensorBase):
    """Grid feed today sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Grid Feed Today"
        self._attr_unique_id = f"felicity_{plant_id}_grid_feed_today"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total_increasing"
    
    @property
    def native_value(self):
        return self._get_float_value("eGridFeedToday")

class FelicityGridFeedTotalSensor(FelicitySolarSensorBase):
    """Grid feed total sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Grid Feed Total"
        self._attr_unique_id = f"felicity_{plant_id}_grid_feed_total"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total"
    
    @property
    def native_value(self):
        return self._get_float_value("eGridFeedTotal")

# Temperature Sensors
class FelicityTempMaxSensor(FelicitySolarSensorBase):
    """Maximum temperature sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Temperature Max"
        self._attr_unique_id = f"felicity_{plant_id}_temp_max"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("tempMax")

class FelicityDeviceTempMaxSensor(FelicitySolarSensorBase):
    """Device maximum temperature sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Device Temperature Max"
        self._attr_unique_id = f"felicity_{plant_id}_device_temp_max"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("devTempMax")

# Load & Grid Sensors
class FelicityLoadPercentSensor(FelicitySolarSensorBase):
    """Load percentage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Load Percentage"
        self._attr_unique_id = f"felicity_{plant_id}_load_percent"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("loadPercent")

class FelicityMeterPowerSensor(FelicitySolarSensorBase):
    """Meter power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Meter Power"
        self._attr_unique_id = f"felicity_{plant_id}_meter_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("meterPower")

# Device Status Sensors
class FelicityDeviceStatusSensor(FelicitySolarSensorBase):
    """Device status sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Device Status"
        self._attr_unique_id = f"felicity_{plant_id}_device_status"
    
    @property
    def native_value(self):
        return self._get_string_value("status")

class FelicityWifiSignalSensor(FelicitySolarSensorBase):
    """WiFi signal sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar WiFi Signal"
        self._attr_unique_id = f"felicity_{plant_id}_wifi_signal"
        self._attr_native_unit_of_measurement = "dBm"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("wifiSignal")

# Battery Sensors (only created if battery is present)
class FelicityBatterySocSensor(FelicitySolarSensorBase):
    """Battery State of Charge sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Battery SOC"
        self._attr_unique_id = f"felicity_{plant_id}_battery_soc"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("battSoc")

class FelicityBatteryVoltageSensor(FelicitySolarSensorBase):
    """Battery voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Battery Voltage"
        self._attr_unique_id = f"felicity_{plant_id}_battery_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("battVolt")

class FelicityBatteryCurrentSensor(FelicitySolarSensorBase):
    """Battery current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Battery Current"
        self._attr_unique_id = f"felicity_{plant_id}_battery_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("battCurr")

class FelicityBatteryPowerSensor(FelicitySolarSensorBase):
    """Battery power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str):
        super().__init__(plant_id, auth, device_sn, device_type)
        self._attr_name = "Felicity Solar Battery Power"
        self._attr_unique_id = f"felicity_{plant_id}_battery_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("bmsPower")