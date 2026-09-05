"""Runtime pychonet extensions for ventilation / Lossnay support."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

_PATCHED = False

# Extra EPC names missing from pychonet 2.8.1's EPC_CODE table for 0x0134.
_EPC_CODE_0134 = {
    0xB0: "Ventilation mode automatic setting",
    0xB1: "Ventilation method setting",
    0xB2: "Ventilation mode setting",
    0xB3: "Cooling / heating high-low setting",
    0xB9: "Measured value of electric current consumption",
    0xBE: "Measured value of outdoor air temperature",
    0xCA: "Measured value of outdoor relative humidity",
    0xD0: "Measured value of return air temperature",
    0xD1: "Measured value of return air relative humidity",
    0xD2: "Measured value of supply air temperature",
    0xD3: "Measured value of supply air relative humidity",
    0xD4: "Measured value of exhaust air temperature",
    0xD5: "Measured value of exhaust air relative humidity",
}


def apply_pychonet_patches() -> None:
    """Register 0x0133/0x0134 classes on pychonet.Factory and fill EPC names."""
    global _PATCHED
    if _PATCHED:
        return

    import pychonet
    from pychonet.lib.epc import EPC_CODE

    from .ventilation import AirConditionerVentilationFan, VentilationFan

    original_factory = pychonet.Factory

    def factory(host, server, eojgc, eojcc, eojci=0x01):
        if eojgc == 0x01 and eojcc == 0x33:
            return VentilationFan(host, server, eojci)
        if eojgc == 0x01 and eojcc == 0x34:
            return AirConditionerVentilationFan(host, server, eojci)
        return original_factory(host, server, eojgc, eojcc, eojci)

    pychonet.Factory = factory

    epc_0133 = EPC_CODE.setdefault(0x01, {}).setdefault(0x33, {})
    epc_0133.setdefault(0x80, "Operation status")
    epc_0133.setdefault(0xA0, "Set value of ventilation air flow rate")
    epc_0133.setdefault(0xBF, "Ventilation Auto setting")

    epc_0134 = EPC_CODE.setdefault(0x01, {}).setdefault(0x34, {})
    epc_0134.setdefault(0x80, "Operation status")
    epc_0134.setdefault(0xA0, "Set value of ventilation air flow rate")
    epc_0134.setdefault(0xBF, "Ventilation auto setting")
    epc_0134.setdefault(0xE0, "Heat exchanger operation setting")
    for code, name in _EPC_CODE_0134.items():
        epc_0134.setdefault(code, name)

    _PATCHED = True
    _LOGGER.debug("Registered ECHONET ventilation fan classes 0x0133 and 0x0134")
