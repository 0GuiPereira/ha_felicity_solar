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

from datetime import timedelta

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
    """Set up the Felicity Solar sensors."""
    username = config_entry.data.get("username")
    password_hash = config_entry.data.get("password_hash")
    scan_interval = config_entry.data.get("scan_interval", 30)
    
    # Set the scan interval for all sensors
    update_interval = timedelta(seconds=scan_interval)
    
    # Create shared auth instance
    auth = FelicitySolarAuth(username, password_hash)
    
    _LOGGER.info("Starting Felicity Solar setup...")
    
    # Get all devices info from API
    try:
        devices_info = await hass.async_add_executor_job(_get_all_devices_info, auth)
        _LOGGER.info(f"Retrieved device info: {devices_info}")
    except Exception as e:
        _LOGGER.error(f"Error getting device info: {e}")
        return
        
    if not devices_info:
        _LOGGER.error("Could not get any device information from API")
        return
    
    _LOGGER.info(f"Setting up Felicity Solar for {len(devices_info)} devices, scan interval: {scan_interval}s")
    
    # Create sensors for each device
    all_sensors = []
    
    for device_info in devices_info:
        plant_id = device_info.get("plantId")
        device_sn = device_info.get("deviceSn")
        device_type = device_info.get("deviceType", "OC")
        device_identifier = device_info.get("deviceIdentifier")

        # Inject device_name from config_entry if present
        device_info["device_name"] = config_entry.data.get("device_name", "")
        _LOGGER.info(f"Creating sensors for device: {device_identifier}")
        
        # Create comprehensive sensors based on snapshot endpoint for this device
        device_sensors = [
            # Power Generation
            FelicityPvTotalPowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv1PowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv2PowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv3PowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv4PowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # PV Voltage & Current
            FelicityPv1VoltageSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv2VoltageSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv3VoltageSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv1CurrentSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv2CurrentSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityPv3CurrentSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # AC Input (Grid)
            FelicityAcInputVoltageSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityAcInputCurrentSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityAcInputFrequencySensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityAcInputPowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # AC Output (Load)
            FelicityAcOutputVoltageSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityAcOutputCurrentSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityAcOutputFrequencySensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityAcOutputPowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # Energy Totals
            FelicityTotalEnergySensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityTodayEnergySensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityGridFeedTodaySensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityGridFeedTotalSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # Temperatures
            FelicityTempMaxSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityDeviceTempMaxSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # Load & Grid
            FelicityLoadPercentSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityMeterPowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # Device Status
            FelicityDeviceStatusSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityWifiSignalSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),

            # Battery Sensors
            FelicityBatterySocSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityBatteryVoltageSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityBatteryCurrentSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
            FelicityBatteryPowerSensor(plant_id, auth, device_sn, device_type, scan_interval, device_info),
        ]
        
        # Add this device's sensors to the main list
        all_sensors.extend(device_sensors)
        _LOGGER.info(f"Added {len(device_sensors)} sensors for device {device_identifier}")
    
    # Add all sensors from all devices
    if all_sensors:
        _LOGGER.info(f"Setting up {len(all_sensors)} total sensors")
        async_add_entities(all_sensors, True)
    else:
        _LOGGER.error("No sensors created - check device discovery")

def _get_all_devices_info(auth: FelicitySolarAuth):
    """Get all plants and devices information from API."""
    try:
        # Login first to get fresh token
        if not auth.login():
            _LOGGER.error("Failed to login during device info retrieval")
            return []
            
        payload = {
            "pageNum": 1,
            "pageSize": 100,  # Get more devices
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
            return []
            
        _LOGGER.debug(f"Getting plant list with headers: {headers}")
        
        response = requests.post(
            BASE_URL + PLANT_LIST_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        _LOGGER.debug(f"Plant list response: {data}")
        
        devices_info = []
        if data.get("code") == 200 and data.get("data", {}).get("dataList"):
            # Get all plants and their devices
            for plant in data["data"]["dataList"]:
                plant_id = plant["id"]
                plant_name = plant.get("plantName", "Unknown")
                device_list = plant.get("plantDeviceList", [])
                
                for device in device_list:
                    device_sn = device.get("deviceSn")
                    battery_capacity = device.get("batteryCapacity", 0)
                    device_type = device.get("deviceType", "OC")

                    # Always use SN as model and identifier
                    device_model = device_sn

                    if device_sn:
                        device_identifier = device_sn
                        devices_info.append({
                            "plantId": plant_id,
                            "plantName": plant_name,
                            "deviceSn": device_sn,
                            "deviceModel": device_model,
                            "deviceType": device_type,
                            "batteryCapacity": battery_capacity,
                            "deviceIdentifier": device_identifier
                        })
                        _LOGGER.info(f"Found device: {device_identifier} in plant '{plant_name}' (ID: {plant_id})")
        
        return devices_info
    except Exception as e:
        _LOGGER.error(f"Error getting devices info: {e}")
        return []

class FelicitySolarSensorBase(SensorEntity):
    """Base class for Felicity Solar sensors."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        self._plant_id = plant_id
        self._auth = auth
        self._device_sn = device_sn
        self._device_type = device_type
        self._attr_available = True
        self._snapshot_data = None
        self._scan_interval = scan_interval
        self._device_info = device_info or {}
        
        # Set up device info for Home Assistant device registry
        device_identifier = self._get_device_identifier()
        device_model = self._device_info.get("deviceModel", "Unknown")
        plant_name = self._device_info.get("plantName", "Unknown Plant")
        
    @property  
    def device_info(self):
        """Return device information to link entities with devices."""
        device_identifier = self._get_device_identifier()
        device_model = self._get_string_value("deviceModel", self._device_info.get("deviceModel", "Unknown"))
        configuration_url = f"https://shine.felicityess.com/login"
        
        return {
            "identifiers": {(DOMAIN, device_identifier)},
            "name": device_model,
            "manufacturer": "Felicity Solar", 
            "model": device_identifier,
            "configuration_url": configuration_url
        }

    @property
    def name(self):
        """Return the display name for the sensor."""
        # Get custom device name from config flow, or fallback to deviceModel from API
        device_name = self._device_info.get("device_name")
        if not device_name or device_name.strip() == "":
            # Fallback to deviceModel from snapshot data or device_info
            device_name = self._get_string_value("deviceModel", self._device_info.get("deviceModel", "Unknown"))
        
        # Use the sensor type from the static _attr_name (set in child class)
        if hasattr(self, "_attr_name") and self._attr_name:
            # Remove the device_identifier part from _attr_name to get just the sensor type
            device_identifier = self._get_device_identifier()
            sensor_type = self._attr_name.replace(device_identifier, "").strip()
            # Remove leading/trailing dashes, underscores, or spaces
            sensor_type = sensor_type.lstrip("-_ ").rstrip("-_ ")
            return f"{device_name} {sensor_type}".strip()
        return device_name

    @property
    def should_poll(self) -> bool:
        """Return True if entity should be polled."""
        return True
        
    @property
    def scan_interval(self) -> timedelta:
        """Return the scan interval for this sensor."""
        return timedelta(seconds=self._scan_interval)
    
    def _get_device_identifier(self):
        """Get device identifier, fetching from snapshot API if not available."""
        # First try to get from device_info
        if self._device_info.get("deviceIdentifier"):
            return self._device_info.get("deviceIdentifier")
        
        # If not available, try to get device model from snapshot API
        try:
            device_model = self._get_device_model_from_snapshot()
            if device_model and device_model != "Unknown":
                device_identifier = f"{device_model}-{self._device_sn}"
                # Update device_info with the found information
                self._device_info["deviceModel"] = device_model
                self._device_info["deviceIdentifier"] = device_identifier
                return device_identifier
        except Exception as e:
            _LOGGER.debug(f"Could not get device model from snapshot: {e}")
        
        # Fallback to Unknown
        return f"Unknown-{self._device_sn}"
    
    def _get_device_model_from_snapshot(self):
        """Get device model from snapshot API."""
        try:
            # Login if needed
            if not self._auth.get_valid_token():
                if not self._auth.login():
                    return "Unknown"
            
            payload = {
                "deviceSn": self._device_sn,
                "deviceType": self._device_type,
                "dateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            headers = self._auth.get_auth_headers()
            if not headers:
                return "Unknown"
                
            response = requests.post(
                BASE_URL + DEVICE_SNAPSHOT_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200 and data.get("data"):
                device_model = data["data"].get("deviceModel")
                if device_model:
                    _LOGGER.info(f"Retrieved device model from snapshot API: {device_model} for device {self._device_sn}")
                    return device_model
            
            return "Unknown"
            
        except Exception as e:
            _LOGGER.debug(f"Error getting device model from snapshot: {e}")
            return "Unknown"
    
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
                
            _LOGGER.debug(f"Getting snapshot data with payload: {payload}")
            _LOGGER.debug(f"Using headers: {headers}")
                
            response = requests.post(
                BASE_URL + DEVICE_SNAPSHOT_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            _LOGGER.debug(f"Snapshot data response: {data}")
            
            if data.get("code") == 200 and data.get("data"):
                return data["data"]
            else:
                _LOGGER.error(f"Snapshot API error: {data.get('message', 'Unknown error')}")
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
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        # Sanitize device identifier for unique_id (replace special characters)
        sanitized_id = device_identifier.replace("-", "_").replace(" ", "_").lower()
        self._attr_name = f"{device_identifier} PV Total Power"
        self._attr_unique_id = f"felicity_{sanitized_id}_pv_total_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvTotalPower")

class FelicityPv1PowerSensor(FelicitySolarSensorBase):
    """PV1 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV1 Power"
        sanitized_id = device_identifier.replace("-", "_").replace(" ", "_").lower()
        self._attr_unique_id = f"felicity_{sanitized_id}_pv1_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvPower")

class FelicityPv2PowerSensor(FelicitySolarSensorBase):
    """PV2 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV2 Power"
        self._attr_unique_id = f"felicity_{device_identifier}_pv2_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv2Power")

class FelicityPv3PowerSensor(FelicitySolarSensorBase):
    """PV3 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV3 Power"
        self._attr_unique_id = f"felicity_{device_identifier}_pv3_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv3Power")

class FelicityPv4PowerSensor(FelicitySolarSensorBase):
    """PV4 power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV4 Power"
        self._attr_unique_id = f"felicity_{device_identifier}_pv4_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv4Power")

# PV Voltage Sensors
class FelicityPv1VoltageSensor(FelicitySolarSensorBase):
    """PV1 voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV1 Voltage"
        self._attr_unique_id = f"felicity_{device_identifier}_pv1_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvVolt")

class FelicityPv2VoltageSensor(FelicitySolarSensorBase):
    """PV2 voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV2 Voltage"
        self._attr_unique_id = f"felicity_{device_identifier}_pv2_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv2Volt")

class FelicityPv3VoltageSensor(FelicitySolarSensorBase):
    """PV3 voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV3 Voltage"
        self._attr_unique_id = f"felicity_{device_identifier}_pv3_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv3Volt")

# PV Current Sensors
class FelicityPv1CurrentSensor(FelicitySolarSensorBase):
    """PV1 current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV1 Current"
        self._attr_unique_id = f"felicity_{device_identifier}_pv1_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pvInCurr")

class FelicityPv2CurrentSensor(FelicitySolarSensorBase):
    """PV2 current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV2 Current"
        self._attr_unique_id = f"felicity_{device_identifier}_pv2_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv2InCurr")

class FelicityPv3CurrentSensor(FelicitySolarSensorBase):
    """PV3 current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} PV3 Current"
        self._attr_unique_id = f"felicity_{device_identifier}_pv3_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("pv3InCurr")

# AC Input (Grid) Sensors
class FelicityAcInputVoltageSensor(FelicitySolarSensorBase):
    """AC Input voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Input Voltage"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_input_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInVolt")

class FelicityAcInputCurrentSensor(FelicitySolarSensorBase):
    """AC Input current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Input Current"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_input_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInCurr")

class FelicityAcInputFrequencySensor(FelicitySolarSensorBase):
    """AC Input frequency sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Input Frequency"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_input_frequency"
        self._attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
        self._attr_device_class = SensorDeviceClass.FREQUENCY
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInFreq")

class FelicityAcInputPowerSensor(FelicitySolarSensorBase):
    """AC Input power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Input Power"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_input_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acRInPower")

# AC Output (Load) Sensors
class FelicityAcOutputVoltageSensor(FelicitySolarSensorBase):
    """AC Output voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Output Voltage"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_output_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acROutVolt")

class FelicityAcOutputCurrentSensor(FelicitySolarSensorBase):
    """AC Output current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Output Current"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_output_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acROutCurr")

class FelicityAcOutputFrequencySensor(FelicitySolarSensorBase):
    """AC Output frequency sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Output Frequency"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_output_frequency"
        self._attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
        self._attr_device_class = SensorDeviceClass.FREQUENCY
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acROutFreq")

class FelicityAcOutputPowerSensor(FelicitySolarSensorBase):
    """AC Output power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} AC Output Power"
        self._attr_unique_id = f"felicity_{device_identifier}_ac_output_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("acTotalOutActPower")

# Energy Sensors
class FelicityTotalEnergySensor(FelicitySolarSensorBase):
    """Total energy sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Total Energy"
        self._attr_unique_id = f"felicity_{device_identifier}_total_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total"
    
    @property
    def native_value(self):
        return self._get_float_value("totalEnergy")

class FelicityTodayEnergySensor(FelicitySolarSensorBase):
    """Today energy sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Today Energy"
        self._attr_unique_id = f"felicity_{device_identifier}_today_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total_increasing"
    
    @property
    def native_value(self):
        return self._get_float_value("ePvToday")

class FelicityGridFeedTodaySensor(FelicitySolarSensorBase):
    """Grid feed today sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Grid Feed Today"
        self._attr_unique_id = f"felicity_{device_identifier}_grid_feed_today"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total_increasing"
    
    @property
    def native_value(self):
        return self._get_float_value("eGridFeedToday")

class FelicityGridFeedTotalSensor(FelicitySolarSensorBase):
    """Grid feed total sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Grid Feed Total"
        self._attr_unique_id = f"felicity_{device_identifier}_grid_feed_total"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = "total"
    
    @property
    def native_value(self):
        return self._get_float_value("eGridFeedTotal")

# Temperature Sensors
class FelicityTempMaxSensor(FelicitySolarSensorBase):
    """Maximum temperature sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Temperature Max"
        self._attr_unique_id = f"felicity_{device_identifier}_temp_max"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("tempMax")

class FelicityDeviceTempMaxSensor(FelicitySolarSensorBase):
    """Device maximum temperature sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Device Temperature Max"
        self._attr_unique_id = f"felicity_{device_identifier}_device_temp_max"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("devTempMax")

# Load & Grid Sensors
class FelicityLoadPercentSensor(FelicitySolarSensorBase):
    """Load percentage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Load Percentage"
        self._attr_unique_id = f"felicity_{device_identifier}_load_percent"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("loadPercent")

class FelicityMeterPowerSensor(FelicitySolarSensorBase):
    """Meter power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Meter Power"
        self._attr_unique_id = f"felicity_{device_identifier}_meter_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("meterPower")

# Device Status Sensors
class FelicityDeviceStatusSensor(FelicitySolarSensorBase):
    """Device status sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Device Status"
        self._attr_unique_id = f"felicity_{device_identifier}_device_status"
    
    @property
    def native_value(self):
        return self._get_string_value("status")

class FelicityWifiSignalSensor(FelicitySolarSensorBase):
    """WiFi signal sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} WiFi Signal"
        self._attr_unique_id = f"felicity_{device_identifier}_wifi_signal"
        self._attr_native_unit_of_measurement = "dBm"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("wifiSignal")

# Battery Sensors (only created if battery is present)
class FelicityBatterySocSensor(FelicitySolarSensorBase):
    """Battery State of Charge sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Battery SOC"
        self._attr_unique_id = f"felicity_{device_identifier}_battery_soc"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("battSoc")

class FelicityBatteryVoltageSensor(FelicitySolarSensorBase):
    """Battery voltage sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Battery Voltage"
        self._attr_unique_id = f"felicity_{device_identifier}_battery_voltage"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("battVolt")

class FelicityBatteryCurrentSensor(FelicitySolarSensorBase):
    """Battery current sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Battery Current"
        self._attr_unique_id = f"felicity_{device_identifier}_battery_current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("battCurr")

class FelicityBatteryPowerSensor(FelicitySolarSensorBase):
    """Battery power sensor."""
    
    def __init__(self, plant_id: str, auth: FelicitySolarAuth, device_sn: str, device_type: str, scan_interval: int = 30, device_info: dict = None):
        super().__init__(plant_id, auth, device_sn, device_type, scan_interval, device_info)
        device_identifier = self._get_device_identifier()
        self._attr_name = f"{device_identifier} Battery Power"
        self._attr_unique_id = f"felicity_{device_identifier}_battery_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = "measurement"
    
    @property
    def native_value(self):
        return self._get_float_value("bmsPower")