"""Tests for Mitsubishi /smart Lossnay frames. No Home Assistant required."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "melsmart"))

from datetime import date, datetime, timezone

from protocol import (  # noqa: E402
    checksum,
    csv_command,
    csv_status,
    fan_speed_set_packet,
    make_packet,
    mitsubishi_temp_c,
    parse_lsv,
    power_set_packet,
    redact_lsv,
)

EXAMPLE_LSV = (
    ROOT / "examples" / "lossnay-mac578-fw43" / "lsv-status.xml"
)

CAPTURED_LSV = (
    "<LSV><MAC>8c:53:e6:19:d1:76</MAC><SERIAL>REDACTED</SERIAL>"
    "<CONNECT>ON</CONNECT><STATUS>NORMAL</STATUS>"
    "<CODE>"
    "<VALUE>fc620134100200000100000100000000000000000055</VALUE>"
    "<VALUE>fc62013410030000ff009ca800000000000000ffff15</VALUE>"
    "</CODE>"
    "<APP_VER>43.00</APP_VER><RSSI>-56</RSSI><ECHONET>ON</ECHONET></LSV>"
)


def test_checksum_matches_captured_group02():
    packet = bytes.fromhex("fc620134100200000100000100000000000000000055")
    assert checksum(packet[:-1]) == packet[-1]


def test_parse_captured_lossnay_status():
    state = parse_lsv(CAPTURED_LSV)
    assert state.mac == "8c:53:e6:19:d1:76"
    assert state.unique_id == "8c53e619d176"
    assert state.power_on is True
    assert state.outdoor_temp == 14.0
    assert state.indoor_temp == 20.0
    assert state.fresh_air_in == 14.0
    assert state.stale_air_out == 20.0
    assert state.app_ver == "43.00"
    assert state.rssi == -56
    assert state.device_class == 0x34
    assert state.fan_speed == 1


def test_parse_power_off():
    payload = bytes.fromhex("02000000000001000000000000000000")
    off = make_packet(0x62, 0x34, payload)
    xml = CAPTURED_LSV.replace(
        "fc620134100200000100000100000000000000000055",
        off.hex(),
    )
    assert parse_lsv(xml).power_on is False


def test_parse_group03_temps():
    payload = bytes.fromhex("030000ff009ca8a2a00000000000ffff")
    pkt = make_packet(0x62, 0x34, payload)
    xml = CAPTURED_LSV.replace(
        "fc62013410030000ff009ca800000000000000ffff15",
        pkt.hex(),
    )
    state = parse_lsv(xml)
    assert state.fresh_air_in == 14.0
    assert state.stale_air_out == 20.0


def test_temps_ignore_unavailable():
    assert mitsubishi_temp_c(0xFF) is None
    assert mitsubishi_temp_c(0x00) is None
    assert mitsubishi_temp_c(0x9C) == 14.0
    assert mitsubishi_temp_c(0xA8) == 20.0


def test_power_set_packet_on_and_off():
    on = power_set_packet(True)
    off = power_set_packet(False)
    assert on[1] == 0x41
    assert on[3] == 0x34
    assert on[8] == 0x01
    assert off[8] == 0x00
    assert checksum(on[:-1]) == on[-1]
    assert checksum(off[:-1]) == off[-1]


def test_csv_helpers():
    assert "CONNECT" not in csv_status()
    cmd = csv_command(power_set_packet(True))
    assert "<VALUE>" in cmd
    assert "fc41" in cmd


def test_parse_fan_speed_three():
    xml = CAPTURED_LSV.replace(
        "fc620134100200000100000100000000000000000055",
        "fc620134100200000100000300000000000000000053",
    )
    assert parse_lsv(xml).fan_speed == 3


def test_fan_speed_set_packet():
    pkt = fan_speed_set_packet(4)
    assert pkt[1] == 0x41
    assert pkt[3] == 0x34
    assert pkt[6] == 0x08
    assert pkt[11] == 0x04
    assert checksum(pkt[:-1]) == pkt[-1]
    assert fan_speed_set_packet(1).hex() == "fc410134100108000000000100000000000000000070"


def test_redact_lsv_strips_serial():
    raw = "<LSV><SERIAL>ABC123SECRET</SERIAL><STATUS>NORMAL</STATUS></LSV>"
    assert "SECRET" not in redact_lsv(raw)
    assert "<SERIAL>REDACTED</SERIAL>" in redact_lsv(raw)


def test_parse_example_capture():
    xml = EXAMPLE_LSV.read_text()
    assert "REDACTED" in xml
    state = parse_lsv(xml)
    assert state.mac == "8c:53:e6:19:d1:76"
    assert state.serial == "REDACTED"
    assert state.connect == "ON"
    assert state.status == "NORMAL"
    assert state.echonet == "ON"
    assert state.app_ver == "43.00"
    assert state.rssi == -57
    assert state.power_on is True
    assert state.fan_speed == 1
    assert state.reported_fan_speed == 1
    assert state.fresh_air_in == 15.0
    assert state.stale_air_out == 21.0
    assert state.ssl_limit == date(2037, 12, 31)
    assert state.adapter_clock == datetime(2026, 9, 5, 23, 6, 46, tzinfo=timezone.utc)
    assert set(state.codes) == {0x02, 0x03, 0x04, 0x06, 0x09, 0x15}


