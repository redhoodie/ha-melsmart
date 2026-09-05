"""pychonet device classes for ECHONET Lite ventilation fans.

These classes are registered into pychonet.Factory at integration import time
so Home Assistant can talk to 0x0133 / 0x0134 objects without waiting for a
pychonet release.
"""

from __future__ import annotations

from pychonet.EchonetInstance import EchonetInstance
from pychonet.lib.const import ENL_OFF, ENL_ON, ENL_STATUS
from pychonet.lib.epc_functions import (
    DICT_41_YES_NO,
    _int,
    _signed_int,
)

from .mappings import (
    AUTO_SETTING_EDT,
    DEFAULT_LOSSNAY_PRESETS,
    HEAT_EXCHANGER_EDT,
    SPEED_COUNT,
    VENTILATION_METHOD_EDT,
    VENTILATION_MODE_EDT,
    edt_to_preset,
    percentage_to_preset,
    preset_to_edt,
    ventilation_mode_to_edt,
)

ENL_FANSPEED = 0xA0
ENL_VENTILATION_AUTO = 0xBF
ENL_VENTILATION_MODE_AUTO = 0xB0
ENL_VENTILATION_METHOD = 0xB1
ENL_VENTILATION_MODE = 0xB2
ENL_HEAT_EXCHANGER = 0xE0
ENL_OUTDOOR_TEMP = 0xBE
ENL_RETURN_AIR_TEMP = 0xD0
ENL_SUPPLY_AIR_TEMP = 0xD2
ENL_EXHAUST_AIR_TEMP = 0xD4


def _0133A0(edt):
    """Decode airflow rate (0xA0) into Lossnay preset names."""
    return edt_to_preset(_int(edt))


def _first_signed_temp(edt):
    """Decode a 1-byte Celsius value, or the first sample of an array (0xD0)."""
    if edt is None or len(edt) == 0:
        return None
    value = _signed_int(edt[0:1])
    # 0x7E is the ECHONET "unmeasurable" sentinel for this data type.
    if value == 0x7E:
        return None
    return value


class VentilationFan(EchonetInstance):
    """ECHONET class 0x0133 — ventilation fan (power + airflow)."""

    EPC_FUNCTIONS = {
        0xA0: _0133A0,
        0xBF: [_int, AUTO_SETTING_EDT],
    }
    SPEED_COUNT = SPEED_COUNT
    PRESET_MODES = list(DEFAULT_LOSSNAY_PRESETS)

    def __init__(self, host, api_connector=None, instance=0x1):
        self._eojgc = 0x01
        self._eojcc = 0x33
        EchonetInstance.__init__(
            self, host, self._eojgc, self._eojcc, instance, api_connector
        )

    async def on(self):
        return await self.setMessage(ENL_STATUS, ENL_ON)

    async def off(self):
        return await self.setMessage(ENL_STATUS, ENL_OFF)

    async def setFanSpeed(self, fan_speed):
        return await self.setMessage(ENL_FANSPEED, preset_to_edt(fan_speed))

    async def getFanSpeed(self):
        return await self.getMessage(ENL_FANSPEED)

    async def setFanSpeedPercent(self, percentage: int):
        preset = percentage_to_preset(percentage)
        if preset is None:
            return await self.off()
        return await self.setFanSpeed(preset)


class AirConditionerVentilationFan(VentilationFan):
    """ECHONET class 0x0134 — air-conditioner ventilation fan (Lossnay / ERV).

    Adds heat-exchange mode, four core temperatures, filter/pollution flags,
    and auto ventilation — the object class that matches a VL-500 Lossnay.
    """

    EPC_FUNCTIONS = {
        **VentilationFan.EPC_FUNCTIONS,
        0xB0: [_int, AUTO_SETTING_EDT],
        0xB1: [_int, VENTILATION_METHOD_EDT],
        0xB2: [_int, VENTILATION_MODE_EDT],
        0xB4: _int,
        0xBA: _int,
        0xBE: _signed_int,
        0xC0: _int,
        0xC1: [_int, DICT_41_YES_NO],
        0xC2: [_int, DICT_41_YES_NO],
        0xCA: _int,
        0xD0: _first_signed_temp,
        0xD1: _int,
        0xD2: _signed_int,
        0xD3: _int,
        0xD4: _signed_int,
        0xD5: _int,
        0xE0: [_int, HEAT_EXCHANGER_EDT],
    }

    def __init__(self, host, api_connector=None, instance=0x1):
        self._eojgc = 0x01
        self._eojcc = 0x34
        EchonetInstance.__init__(
            self, host, self._eojgc, self._eojcc, instance, api_connector
        )

    async def setVentilationMode(self, mode: str):
        """Set LOSSNAY / BYPASS style mode via EPC 0xB2."""
        return await self.setMessage(ENL_VENTILATION_MODE, ventilation_mode_to_edt(mode))

    async def setHeatExchanger(self, enabled: bool):
        edt = 0x41 if enabled else 0x42
        return await self.setMessage(ENL_HEAT_EXCHANGER, edt)
