"""Lossnay / ECHONET ventilation fan speed and mode mappings.

These helpers are pure functions so they can be unit-tested without pychonet
or Home Assistant. EDT values follow ECHONET Lite Appendix classes:

* 0x0133 Ventilation fan
* 0x0134 Air conditioner ventilation fan

Air-flow EPC 0xA0 uses 8 discrete levels (0x31-0x38) plus auto (0x41).
Mitsubishi Lossnay VL-250/350/500 Wi-Fi Control exposes four named speeds
plus a timed Boost override. Boost is mapped to level 5 (0x35). If a given
adapter rejects that write, the HA options UI can drop Boost from the list.
"""

from __future__ import annotations

# Named presets matching the Mitsubishi AU/NZ Wi-Fi Control app.
# EDT 0x31-0x34 = speeds 1-4 (30% / 50% / 70% / 100% on VL-500).
# EDT 0x35 = Boost (timed high-speed override on the wall controller).
# EDT 0x41 = Auto airflow (ECHONET spec; not a separate button on VL-500).
LOSSNAY_FAN_SPEED = {
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "boost": 0x35,
    "auto": 0x41,
}

LOSSNAY_FAN_SPEED_EDT = {edt: name for name, edt in LOSSNAY_FAN_SPEED.items()}

DEFAULT_LOSSNAY_PRESETS = ["1", "2", "3", "4", "boost"]

# Four-speed percentage scale used by Home Assistant SET_SPEED.
# Boost is a preset, not a fifth percentage step.
SPEED_COUNT = 4

# 0xB2 ventilation mode (0x0134)
VENTILATION_MODE = {
    "other": 0x40,
    "bypass": 0x41,  # normal / non-heat-exchange (app: BYPASS)
    "lossnay": 0x42,  # heat exchange (app: LOSSNAY)
    "cooling": 0x43,
    "heating": 0x44,
    "dehumidifying": 0x45,
    "humidifying": 0x46,
}

VENTILATION_MODE_EDT = {edt: name for name, edt in VENTILATION_MODE.items()}

# 0xB1 ventilation method (0x0134)
VENTILATION_METHOD = {
    "blowing": 0x41,
    "air-conditioning": 0x42,
}

VENTILATION_METHOD_EDT = {edt: name for name, edt in VENTILATION_METHOD.items()}

# 0xE0 heat exchanger operation (0x0134) — ON is Lossnay core, OFF is bypass duct.
HEAT_EXCHANGER = {
    "on": 0x41,
    "off": 0x42,
}

HEAT_EXCHANGER_EDT = {edt: name for name, edt in HEAT_EXCHANGER.items()}

# 0xB0 / 0xBF auto flags
AUTO_SETTING = {
    "auto": 0x41,
    "manual": 0x42,
}

AUTO_SETTING_EDT = {edt: name for name, edt in AUTO_SETTING.items()}

EOJ_VENTILATION_FAN = (0x01, 0x33)
EOJ_AIRCON_VENTILATION_FAN = (0x01, 0x34)
VENTILATION_EOJCC = {0x33, 0x34}


def edt_to_preset(edt: int) -> str:
    """Decode a 0xA0 airflow EDT byte to a Lossnay preset name."""
    if edt in LOSSNAY_FAN_SPEED_EDT:
        return LOSSNAY_FAN_SPEED_EDT[edt]
    if 0x31 <= edt <= 0x38:
        return str(edt - 0x30)
    return f"unknown-{edt:#x}"


def preset_to_edt(preset: str) -> int:
    """Encode a Lossnay preset name to a 0xA0 EDT byte."""
    key = str(preset).strip().lower()
    aliases = {
        "level-1": "1",
        "level-2": "2",
        "level-3": "3",
        "level-4": "4",
        "level-5": "boost",
        "minimum": "1",
        "low": "2",
        "medium-low": "3",
        "medium": "3",
        "medium-high": "4",
        "high": "4",
        "very-high": "boost",
        "max": "boost",
        "boost": "boost",
        "auto": "auto",
    }
    key = aliases.get(key, key)
    if key not in LOSSNAY_FAN_SPEED:
        raise ValueError(f"Unsupported Lossnay fan preset: {preset}")
    return LOSSNAY_FAN_SPEED[key]


def percentage_to_preset(percentage: int) -> str | None:
    """Map a Home Assistant fan percentage onto speeds 1-4.

    0 means off (caller should turn the unit off). Boost is not reachable
    via percentage — use the boost preset instead.
    """
    if percentage is None:
        return None
    if percentage <= 0:
        return None
    if percentage <= 25:
        return "1"
    if percentage <= 50:
        return "2"
    if percentage <= 75:
        return "3"
    return "4"


def preset_to_percentage(preset: str | None) -> int | None:
    """Map a named preset onto the 4-speed percentage scale."""
    if not preset:
        return None
    key = str(preset).strip().lower()
    table = {
        "1": 25,
        "2": 50,
        "3": 75,
        "4": 100,
        "boost": 100,
        "auto": None,
    }
    aliases = {
        "level-1": "1",
        "level-2": "2",
        "level-3": "3",
        "level-4": "4",
        "level-5": "boost",
    }
    key = aliases.get(key, key)
    return table.get(key)


def edt_to_ventilation_mode(edt: int) -> str:
    return VENTILATION_MODE_EDT.get(edt, f"unknown-{edt:#x}")


def ventilation_mode_to_edt(mode: str) -> int:
    key = str(mode).strip().lower()
    aliases = {
        "normal": "bypass",
        "heat-exchange": "lossnay",
        "heatexchange": "lossnay",
        "heat_exchange": "lossnay",
    }
    key = aliases.get(key, key)
    if key not in VENTILATION_MODE:
        raise ValueError(f"Unsupported ventilation mode: {mode}")
    return VENTILATION_MODE[key]
