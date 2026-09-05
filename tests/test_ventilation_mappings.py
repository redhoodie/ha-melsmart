"""Tests for Lossnay / ECHONET ventilation mappings.

These tests do not require pychonet or Home Assistant.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "echonetlite"))

from pychonet_ext.mappings import (  # noqa: E402
    DEFAULT_LOSSNAY_PRESETS,
    edt_to_preset,
    edt_to_ventilation_mode,
    percentage_to_preset,
    preset_to_edt,
    preset_to_percentage,
    ventilation_mode_to_edt,
)


@pytest.mark.parametrize(
    ("preset", "edt"),
    [
        ("1", 0x31),
        ("2", 0x32),
        ("3", 0x33),
        ("4", 0x34),
        ("boost", 0x35),
        ("auto", 0x41),
        ("BOOST", 0x35),
        ("level-4", 0x34),
        ("high", 0x34),
        ("max", 0x35),
    ],
)
def test_preset_to_edt(preset, edt):
    assert preset_to_edt(preset) == edt


@pytest.mark.parametrize(
    ("edt", "preset"),
    [
        (0x31, "1"),
        (0x32, "2"),
        (0x33, "3"),
        (0x34, "4"),
        (0x35, "boost"),
        (0x41, "auto"),
        (0x36, "6"),
        (0x38, "8"),
    ],
)
def test_edt_to_preset(edt, preset):
    assert edt_to_preset(edt) == preset


@pytest.mark.parametrize(
    ("percentage", "preset"),
    [
        (0, None),
        (1, "1"),
        (25, "1"),
        (26, "2"),
        (50, "2"),
        (51, "3"),
        (75, "3"),
        (76, "4"),
        (100, "4"),
    ],
)
def test_percentage_to_preset(percentage, preset):
    assert percentage_to_preset(percentage) == preset


@pytest.mark.parametrize(
    ("preset", "percentage"),
    [
        ("1", 25),
        ("2", 50),
        ("3", 75),
        ("4", 100),
        ("boost", 100),
        ("auto", None),
    ],
)
def test_preset_to_percentage(preset, percentage):
    assert preset_to_percentage(preset) == percentage


def test_default_presets_match_app():
    assert DEFAULT_LOSSNAY_PRESETS == ["1", "2", "3", "4", "boost"]


def test_roundtrip_app_speeds():
    for preset in DEFAULT_LOSSNAY_PRESETS:
        assert edt_to_preset(preset_to_edt(preset)) == preset


@pytest.mark.parametrize(
    ("mode", "edt"),
    [
        ("lossnay", 0x42),
        ("bypass", 0x41),
        ("heat-exchange", 0x42),
        ("normal", 0x41),
    ],
)
def test_ventilation_mode(mode, edt):
    assert ventilation_mode_to_edt(mode) == edt
    assert edt_to_ventilation_mode(edt) in {"lossnay", "bypass"}


def test_unknown_preset_raises():
    with pytest.raises(ValueError):
        preset_to_edt("turbo")
