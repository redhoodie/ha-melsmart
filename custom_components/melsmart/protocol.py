"""Local Mitsubishi /smart frames for Lossnay (class 0x0134).

The adapter speaks the same encrypted HTTP /smart transport as
pymitsubishi (AES-128-CBC, key ``unregistered``, ISO 7816-4 padding)
and the same 22-byte CN105-style CODE hex frames. HVAC parsers assume
class 0x0130; Lossnay uses 0x0134.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
import re
import xml.etree.ElementTree as ET

CLASS_VENTILATION = 0x34
PACKET_LEN = 22
PAYLOAD_LEN = 16
# VL-500 notches. Local CN105 uses 1–4 (not HVAC's 1/2/3/5/6).
# This adapter accepts 1, 3 and 4; 2 is remapped to 1.
FAN_SPEEDS = (1, 2, 3, 4)
FAN_SPEED_FLAG = 0x08
POWER_FLAG = 0x01
# Ventilation mode (Lossnay / Bypass / Auto) is Melview-cloud only.
# App changes leave local CODE unchanged, including group 02 packet[9].


def checksum(body: bytes) -> int:
    """CN105 checksum: 0xFC minus the sum of all bytes before the last."""
    return (0xFC - (sum(body) & 0xFF)) & 0xFF


def make_packet(ptype: int, cls: int, payload16: bytes) -> bytes:
    if len(payload16) != PAYLOAD_LEN:
        raise ValueError("payload must be 16 bytes")
    body = bytes([0xFC, ptype, 0x01, cls, 0x10]) + payload16
    return body + bytes([checksum(body)])


def power_set_packet(on: bool, cls: int = CLASS_VENTILATION) -> bytes:
    """SET (0x41) group 0x01 with the power flag. Proven on VL-500 / MAC-578."""
    payload = bytearray(PAYLOAD_LEN)
    payload[0] = 0x01
    payload[1] = POWER_FLAG
    payload[3] = 0x01 if on else 0x00
    return make_packet(0x41, cls, bytes(payload))


def fan_speed_set_packet(speed: int, cls: int = CLASS_VENTILATION) -> bytes:
    """SET (0x41) group 0x01 with the HVAC wind-speed flag (0x08)."""
    if speed not in FAN_SPEEDS:
        raise ValueError(f"unsupported fan speed {speed}")
    payload = bytearray(PAYLOAD_LEN)
    payload[0] = 0x01
    payload[1] = FAN_SPEED_FLAG
    payload[6] = speed
    return make_packet(0x41, cls, bytes(payload))


def power_and_speed_set_packet(
    on: bool, speed: int, cls: int = CLASS_VENTILATION
) -> bytes:
    """One SET with both power and fan-speed flags, to avoid two POSTs."""
    if speed not in FAN_SPEEDS:
        raise ValueError(f"unsupported fan speed {speed}")
    payload = bytearray(PAYLOAD_LEN)
    payload[0] = 0x01
    payload[1] = POWER_FLAG | FAN_SPEED_FLAG
    payload[3] = 0x01 if on else 0x00
    payload[6] = speed
    return make_packet(0x41, cls, bytes(payload))


def is_supported_adapter(state: LossnayStatus) -> bool:
    """Local /smart Lossnay uses class 0x34. HVAC 0x30 must not be added."""
    return state.device_class == CLASS_VENTILATION


def probe_error(status: LossnayStatus | None, *, failed: bool) -> str | None:
    """Config-flow error key after a /smart probe, or None if the unit is OK."""
    if failed or status is None:
        return "cannot_connect"
    if not status.unique_id:
        return "no_device_id"
    if not is_supported_adapter(status):
        return "not_lossnay"
    return None


def mitsubishi_temp_c(value: int) -> float | None:
    """Decode a Mitsubishi packed temperature byte."""
    if value in (0x00, 0xFF):
        return None
    if value >= 0x80:
        return round(5 * (value - 0x80) / 10.0, 1)
    return None


@dataclass
class LossnayStatus:
    mac: str | None = None
    serial: str | None = None
    connect: str | None = None
    status: str | None = None
    app_ver: str | None = None
    rssi: int | None = None
    echonet: str | None = None
    datdate: str | None = None
    adapter_clock: datetime | None = None
    ssl_limit: date | None = None
    reported_fan_speed: int | None = None
    power_on: bool | None = None
    outdoor_temp: float | None = None
    indoor_temp: float | None = None
    fresh_air_in: float | None = None
    stale_air_out: float | None = None
    fan_speed: int | None = None
    device_class: int | None = None
    codes: dict[int, bytes] = field(default_factory=dict)

    @property
    def unique_id(self) -> str | None:
        if self.mac:
            return self.mac.replace(":", "").lower()
        return None

    @property
    def problem(self) -> bool | None:
        if self.status is None:
            return None
        return self.status.upper() != "NORMAL"

    @property
    def melview_connected(self) -> bool | None:
        if self.connect is None:
            return None
        return self.connect.upper() == "ON"

    @property
    def echonet_flag_on(self) -> bool | None:
        if self.echonet is None:
            return None
        return self.echonet.upper() == "ON"


def parse_lsv(xml_text: str) -> LossnayStatus:
    """Parse a decrypted LSV status document."""
    root = ET.fromstring(xml_text)
    state = LossnayStatus(
        mac=_text(root, "MAC"),
        serial=_text(root, "SERIAL"),
        connect=_text(root, "CONNECT"),
        status=_text(root, "STATUS"),
        app_ver=_text(root, "APP_VER"),
        echonet=_text(root, "ECHONET"),
        datdate=_text(root, "DATDATE"),
    )
    rssi = _text(root, "RSSI")
    if rssi is not None:
        try:
            state.rssi = int(rssi)
        except ValueError:
            pass
    state.adapter_clock = _parse_datdate(state.datdate)
    state.ssl_limit = _parse_ssl_limit(_text(root, "SSL_LIMIT"))

    for el in root.findall(".//CODE/VALUE"):
        if not el.text:
            continue
        try:
            packet = bytes.fromhex(el.text.strip())
        except ValueError:
            continue
        if len(packet) != PACKET_LEN:
            continue
        if checksum(packet[:-1]) != packet[-1]:
            continue
        group = packet[5]
        state.codes[group] = packet
        state.device_class = packet[3]
        if group == 0x02:
            state.power_on = packet[8] == 0x01
            # Same index as pymitsubishi wind_speed on HVAC group 02.
            state.fan_speed = packet[11]
        elif group == 0x09:
            # Trailing pair tracks the speed the unit is actually running,
            # sometimes a poll behind the group 02 setpoint.
            actual = packet[14]
            if actual in FAN_SPEEDS:
                state.reported_fan_speed = actual
        elif group == 0x03:
            # Local /smart fills only these two temps on this adapter.
            state.fresh_air_in = mitsubishi_temp_c(packet[10])
            state.stale_air_out = mitsubishi_temp_c(packet[11])
            state.outdoor_temp = state.fresh_air_in
            state.indoor_temp = state.stale_air_out
    return state


def redact_lsv(xml_text: str) -> str:
    """Strip adapter serial numbers from a decrypted LSV document."""
    return re.sub(
        r"(<SERIAL>)(.*?)(</SERIAL>)",
        r"\1REDACTED\3",
        xml_text,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _parse_datdate(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y/%m/%d %H:%M:%S")
        return parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_ssl_limit(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _text(root: ET.Element, tag: str) -> str | None:
    value = root.findtext(tag)
    if value is None:
        return None
    value = value.strip()
    return value or None


def csv_status() -> str:
    """Poll status without touching the Melview CONNECT flag."""
    return "<CSV></CSV>"


def csv_command(packet: bytes) -> str:
    return (
        "<CSV>\n"
        " <CODE>\n"
        f"  <VALUE>{packet.hex()}</VALUE>\n"
        " </CODE>\n"
        "</CSV>"
    )


def diagnostics_payload(
    *,
    host: str,
    status: LossnayStatus,
    last_lsv: str | None,
    pacer_remaining: float,
) -> dict[str, Any]:
    """Build a serial-free diagnostics document."""
    return {
        "host": host,
        "mac": status.mac,
        "device_class": status.device_class,
        "adapter_status": status.status,
        "connect": status.connect,
        "echonet": status.echonet,
        "app_ver": status.app_ver,
        "power_on": status.power_on,
        "fan_speed": status.fan_speed,
        "reported_fan_speed": status.reported_fan_speed,
        "fresh_air_in": status.fresh_air_in,
        "stale_air_out": status.stale_air_out,
        "codes": {
            f"{group:02x}": packet.hex()
            for group, packet in sorted(status.codes.items())
        },
        "last_lsv": last_lsv,
        "pacer_remaining_s": round(pacer_remaining, 3),
    }
