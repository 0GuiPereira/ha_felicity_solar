"""Felicity Solar - sensors (coordinator + snapshot)."""
from __future__ import annotations

import logging
from datetime import timedelta, datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfTemperature,
    PERCENTAGE,
)

from .auth import FelicitySolarAuth
from .const import (
    DOMAIN,
    BASE_URL,
    DEVICE_SNAPSHOT_ENDPOINT,
    PLANT_LIST_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors via config entry."""
    username: str = entry.data["username"]
    password_hash: str = entry.data["password_hash"]
    scan_interval: int = entry.data.get("scan_interval", 30)

    auth = FelicitySolarAuth(username, password_hash)
    ok = await hass.async_add_executor_job(auth.login)
    if not ok:
        _LOGGER.error("Falha no login. Verifica credenciais.")
        return

    # descobre dispositivos a partir do endpoint de lista de plantas
    devices_info = await hass.async_add_executor_job(_discover_devices, auth)
    if not devices_info:
        _LOGGER.error("Não foram encontrados dispositivos.")
        return

    # cria 1 coordinator por device
    entities: List[SensorEntity] = []

    for dev in devices_info:
        device_sn = dev["deviceSn"]
        device_type = dev.get("deviceType", "OC")
        plant_id = dev["plantId"]
        device_identifier = _sanitize_id(f"{dev.get('deviceModel','device')}-{device_sn}")

        coordinator = FelicityCoordinator(
            hass=hass,
            auth=auth,
            device_sn=device_sn,
            device_type=device_type,
            name=f"felicity_{device_identifier}",
            update_interval=timedelta(seconds=scan_interval),
        )
        # primeira atualização
        await coordinator.async_config_entry_first_refresh()

        # criar sensores
        entities.extend(_build_sensors_for_device(dev, coordinator))

    async_add_entities(entities, update_before_add=False)


# --------------------- Coordinator --------------------- #
class FelicityCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Busca o snapshot de 1 device e guarda em memory."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth: FelicitySolarAuth,
        device_sn: str,
        device_type: str,
        name: str,
        update_interval: timedelta,
    ) -> None:
        super().__init__(hass, _LOGGER, name=name, update_interval=update_interval)
        self._auth = auth
        self._device_sn = device_sn
        self._device_type = device_type

    def _payload(self) -> Dict[str, Any]:
        # usar UTC para consistência com API
        return {
            "deviceSn": self._device_sn,
            "deviceType": self._device_type,
            "dateStr": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def _async_update_data(self) -> Dict[str, Any]:
        # garantir token
        if not self._auth.get_valid_token():
            ok = await self.hass.async_add_executor_job(self._auth.login)
            if not ok:
                raise UpdateFailed("Auth failed")

        def _fetch() -> Dict[str, Any]:
            headers = self._auth.get_auth_headers()
            if not headers:
                raise UpdateFailed("No auth headers")

            r = requests.post(
                BASE_URL + DEVICE_SNAPSHOT_ENDPOINT,
                json=self._payload(),
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            j = r.json()
            if j.get("code") != 200 or not j.get("data"):
                raise UpdateFailed(j.get("message", "API error"))
            return j["data"]

        return await self.hass.async_add_executor_job(_fetch)


# --------------------- Descoberta --------------------- #
def _discover_devices(auth: FelicitySolarAuth) -> List[Dict[str, Any]]:
    """Obtém plantas e dispositivos (mínimo necessário para device info)."""
    try:
        headers = auth.get_auth_headers()
        r = requests.post(
            BASE_URL + PLANT_LIST_ENDPOINT,
            json={"pageSize": 10, "currentPage": 1},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        res = []
        for plant in (data.get("data") or {}).get("dataList") or []:
            plant_id = plant["id"]
            plant_name = plant.get("plantName", "Plant")
            for dev in plant.get("plantDeviceList") or []:
                device_sn = dev.get("deviceSn")
                if not device_sn:
                    continue
                res.append(
                    {
                        "plantId": plant_id,
                        "plantName": plant_name,
                        "deviceSn": device_sn,
                        # tentar enriquecer com dados do snapshot na primeira ronda (feito pelos sensores)
                        "deviceModel": plant.get("deviceModel") or "Felicity",
                        "deviceType": dev.get("deviceType", "OC"),
                    }
                )
        return res
    except Exception as exc:
        _LOGGER.exception("Erro a obter devices: %s", exc)
        return []


# --------------------- Base Entity --------------------- #
class FelicityBaseSensor(CoordinatorEntity[FelicityCoordinator], SensorEntity):
    """Base para sensores Felicity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        dev: Dict[str, Any],
        coordinator: FelicityCoordinator,
        name_suffix: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._dev = dev
        self._device_sn = dev["deviceSn"]
        self._device_model = dev.get("deviceModel", "Felicity")
        self._plant_name = dev.get("plantName", "Plant")
        dev_id = _sanitize_id(f"{self._device_model}-{self._device_sn}")

        self._attr_name = f"{self._device_model} {self._device_sn} {name_suffix}".strip()
        self._attr_unique_id = f"felicity_{dev_id}_{unique_suffix}"

        # DeviceInfo para agrupar as entidades
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_sn)},
            manufacturer="Felicity Solar",
            model=self._device_model,
            name=f"{self._device_model} {self._device_sn}",
            configuration_url="https://shine.felicitysolar.com/",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    # helpers
    def _get(self, key: str) -> Optional[str]:
        data = self.coordinator.data or {}
        return data.get(key)

    def _get_float(self, key: str) -> Optional[float]:
        v = self._get(key)
        if v in (None, "", "-", "--"):
            return None
        try:
            return float(v)
        except Exception:
            return None


def _sanitize_id(text: str) -> str:
    return (
        (text or "")
        .replace(" ", "_")
        .replace("-", "_")
        .replace(":", "_")
        .lower()
    )


# --------------------- Sensor Factory --------------------- #
def _build_sensors_for_device(dev: Dict[str, Any], coord: FelicityCoordinator) -> List[SensorEntity]:
    s: List[SensorEntity] = []

    # PV Power
    s.append(PvTotalPower(dev, coord))
    s.append(Pv1Power(dev, coord))
    s.append(Pv2Power(dev, coord))
    s.append(Pv3Power(dev, coord))
    s.append(Pv4Power(dev, coord))

    # PV V/I
    s.append(Pv1Voltage(dev, coord))
    s.append(Pv2Voltage(dev, coord))
    s.append(Pv3Voltage(dev, coord))
    s.append(Pv1Current(dev, coord))
    s.append(Pv2Current(dev, coord))
    s.append(Pv3Current(dev, coord))

    # AC In
    s.append(AcInVoltage(dev, coord))
    s.append(AcInCurrent(dev, coord))
    s.append(AcInFrequency(dev, coord))
    s.append(AcInPower(dev, coord))

    # AC Out
    s.append(AcOutVoltage(dev, coord))
    s.append(AcOutCurrent(dev, coord))
    s.append(AcOutFrequency(dev, coord))
    s.append(AcOutPower(dev, coord))

    # Energy
    s.append(TotalEnergy(dev, coord))
    s.append(TodayPvEnergy(dev, coord))
    s.append(TodayGridFeed(dev, coord))
    s.append(TotalGridFeed(dev, coord))

    # Temps
    s.append(MaxTemp(dev, coord))
    s.append(DeviceMaxTemp(dev, coord))

    # Misc
    s.append(LoadPercent(dev, coord))
    s.append(MeterPower(dev, coord))
    s.append(WifiSignal(dev, coord))
    s.append(StatusText(dev, coord))

    # Debug timing
    s.append(LastUpdate(dev, coord))

    return s


# --------------------- Concrete Sensors --------------------- #
class PvTotalPower(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV Total Power", "pv_total_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        # as chaves na API aparecem como 'pvTotalPower'
        return self._get_float("pvTotalPower")


class Pv1Power(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV1 Power", "pv1_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property:
    def native_value(self):
        return self._get_float("pvPower")


class Pv2Power(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV2 Power", "pv2_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pv2Power")


class Pv3Power(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV3 Power", "pv3_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pv3Power")


class Pv4Power(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV4 Power", "pv4_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pv4Power")


class Pv1Voltage(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV1 Voltage", "pv1_voltage")
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pvVolt")


class Pv2Voltage(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV2 Voltage", "pv2_voltage")
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pv2Volt")


class Pv3Voltage(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV3 Voltage", "pv3_voltage")
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pv3Volt")


class Pv1Current(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV1 Current", "pv1_current")
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pvInCurr")


class Pv2Current(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV2 Current", "pv2_current")
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pv2InCurr")


class Pv3Current(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV3 Current", "pv3_current")
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("pv3InCurr")


class AcInVoltage(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Input Voltage", "ac_in_voltage")
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("acRInVolt")


class AcInCurrent(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Input Current", "ac_in_current")
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("acRInCurr")


class AcInFrequency(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Input Frequency", "ac_in_frequency")
        self._attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
        self._attr_device_class = SensorDeviceClass.FREQUENCY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("acRInFreq")


class AcInPower(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Input Power", "ac_in_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        # atenção: na tua API veio negativo quando a rede estava a entregar à casa
        return self._get_float("acRInPower")


class AcOutVoltage(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Output Voltage", "ac_out_voltage")
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("acROutVolt")


class AcOutCurrent(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Output Current", "ac_out_current")
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("acROutCurr")


class AcOutFrequency(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Output Frequency", "ac_out_frequency")
        self._attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
        self._attr_device_class = SensorDeviceClass.FREQUENCY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("acROutFreq")


class AcOutPower(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "AC Output Power", "ac_out_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        # 'acTotalOutActPower' no teu snapshot
        return self._get_float("acTotalOutActPower")


class TotalEnergy(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Total Energy", "total_energy")
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        return self._get_float("totalEnergy")


class TodayPvEnergy(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "PV Today", "pv_today")
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self._get_float("ePvToday")


class TodayGridFeed(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Grid Feed Today", "grid_feed_today")
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self._get_float("eGridFeedToday")


class TotalGridFeed(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Grid Feed Total", "grid_feed_total")
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        return self._get_float("eGridFeedTotal")


class MaxTemp(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Max Temp", "max_temp")
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("tempMax")


class DeviceMaxTemp(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Device Max Temp", "device_max_temp")
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("devTempMax")


class LoadPercent(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Load Percent", "load_percent")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("loadPercent")


class MeterPower(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Meter Power", "meter_power")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("meterPower")


class WifiSignal(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "WiFi Signal", "wifi_signal")
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        # unidade na API é dBm, HA usa dBm em sensors genéricos
        self._attr_native_unit_of_measurement = "dBm"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._get_float("wifiSignal")


class StatusText(FelicityBaseSensor):
    def __init__(self, dev, c):
        super().__init__(dev, c, "Status", "status_text")

    @property
    def native_value(self):
        return self.coordinator.data.get("status")


class LastUpdate(FelicityBaseSensor):
    """Carimbo temporal convertido a local time (útil para debug)."""

    def __init__(self, dev, c):
        super().__init__(dev, c, "Last Update", "last_update")
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        # API fornece em epoch ms como 'dataTime' e string 'dataTimeStr' no fuso da planta
        ts = self.coordinator.data.get("dataTime")
        if isinstance(ts, (int, float)):
            try:
                # converter para UTC (epoch ms) e devolver ISO8601
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                return dt
            except Exception:
                return None
        # fallback para string (sem tz info)
        s = self.coordinator.data.get("dataTimeStr")
        if isinstance(s, str):
            try:
                # tratar como naive e devolver assim mesmo
                return s
            except Exception:
                return None
        return None
