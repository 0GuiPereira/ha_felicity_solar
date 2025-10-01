"""Sensor platform for Felicity Solar."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES
from .coordinator import FelicitySolarCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class FelicitySolarSensorEntityDescription(SensorEntityDescription):
    """Describes Felicity Solar sensor entity."""

    value_fn: Callable[[dict[str, Any]], StateType] = lambda x: None
    available_fn: Callable[[dict[str, Any]], bool] = lambda x: True


def _get_float_value(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    """Safely get float value from data."""
    value = data.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _get_string_value(data: dict[str, Any], key: str, default: str = "Unknown") -> str:
    """Safely get string value from data."""
    value = data.get(key)
    if value is None or value == "":
        return default
    return str(value)


def _build_sensor_description(key: str, config: dict[str, Any]) -> FelicitySolarSensorEntityDescription:
    """Build sensor entity description from config."""
    description_kwargs = {
        "key": key,
        "translation_key": key,
        "name": config.get("name"),
        "icon": config.get("icon"),
        "native_unit_of_measurement": config.get("unit"),
        "entity_registry_enabled_default": config.get("enabled_by_default", True),
    }
    
    # Add device class if specified
    if device_class := config.get("device_class"):
        description_kwargs["device_class"] = getattr(SensorDeviceClass, device_class.upper(), None)
    
    # Add state class if specified
    if state_class := config.get("state_class"):
        if state_class == "measurement":
            description_kwargs["state_class"] = SensorStateClass.MEASUREMENT
        elif state_class == "total":
            description_kwargs["state_class"] = SensorStateClass.TOTAL
        elif state_class == "total_increasing":
            description_kwargs["state_class"] = SensorStateClass.TOTAL_INCREASING
    
    # Define value function based on type
    if key == "status":
        description_kwargs["value_fn"] = lambda data: _get_string_value(data, key)
    else:
        description_kwargs["value_fn"] = lambda data: _get_float_value(data, key)
    
    return FelicitySolarSensorEntityDescription(**description_kwargs)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Felicity Solar sensor entities."""
    coordinator: FelicitySolarCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Wait for first data fetch to know what devices we have
    if not coordinator.data:
        _LOGGER.warning("No data available from coordinator")
        return
    
    # Create sensors for each device
    for device_identifier, device_data in coordinator.data.items():
        device_info = device_data["device_info"]
        snapshot = device_data["snapshot"]
        
        # Determine which sensors to create based on available data
        for sensor_key, sensor_config in SENSOR_TYPES.items():
            # Skip battery sensors if no battery
            if sensor_key.startswith("batt") or sensor_key == "bmsPower":
                battery_capacity = float(device_info.get("batteryCapacity", 0))
                if battery_capacity <= 0:
                    continue
            
            # Skip PV3/PV4 sensors if values are always 0 or None
            if sensor_key in ["pv3Power", "pv3Volt", "pv3InCurr", "pv4Power"]:
                if snapshot.get(sensor_key) in [None, "", 0, "0"]:
                    continue
            
            description = _build_sensor_description(sensor_key, sensor_config)
            
            entities.append(
                FelicitySolarSensor(
                    coordinator=coordinator,
                    description=description,
                    device_identifier=device_identifier,
                    device_info=device_info,
                )
            )
    
    if entities:
        _LOGGER.info("Setting up %d sensors", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.warning("No sensors created")


class FelicitySolarSensor(CoordinatorEntity[FelicitySolarCoordinator], SensorEntity):
    """Representation of a Felicity Solar sensor."""

    entity_description: FelicitySolarSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FelicitySolarCoordinator,
        description: FelicitySolarSensorEntityDescription,
        device_identifier: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self.entity_description = description
        self._device_identifier = device_identifier
        self._device_info = device_info
        
        # Create unique ID
        sanitized_id = device_identifier.replace("-", "_").replace(" ", "_").lower()
        self._attr_unique_id = f"{sanitized_id}_{description.key}"
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_identifier)},
            "name": device_identifier,
            "manufacturer": "Felicity Solar",
            "model": device_info.get("deviceModel", "Unknown"),
            "sw_version": "API v2.0",
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        device_data = self.coordinator.data.get(self._device_identifier)
        if not device_data:
            return None
        
        snapshot = device_data.get("snapshot", {})
        return self.entity_description.value_fn(snapshot)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        
        if not self.coordinator.data:
            return False
        
        device_data = self.coordinator.data.get(self._device_identifier)
        if not device_data:
            return False
        
        snapshot = device_data.get("snapshot", {})
        return self.entity_description.available_fn(snapshot)