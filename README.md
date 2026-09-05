# Mitsubishi Wi-Fi (`/smart`)

[![HACS][hacs-badge]][hacs]
[![GitHub release][release-badge]][releases]
[![License][license-badge]](LICENSE)

Home Assistant custom integration for Mitsubishi Wi-Fi adapters that speak
the local HTTP **`/smart`** API. Built for a **Lossnay VL-500** on a
**MAC-578IF-E**. Requires Home Assistant **2024.4** or newer.

This is **not** ECHONET Lite and **not** Melview cloud. The adapter may
advertise ECHONET as on, but this unit never answers UDP 3610.

## Install with HACS

This is a **custom repository** (not in the default HACS store).

[![Open this repository in HACS][hacs-repo-badge]][hacs-repo]

1. [Install HACS](https://www.hacs.xyz/docs/use/download/download/) if you do not have it.
2. Open the button above, or in Home Assistant go to
   **HACS → ⋮ → Custom repositories**, add
   `https://github.com/redhoodie/ha-melsmart` as type **Integration**.
3. Download **Mitsubishi Wi-Fi (/smart)**.
4. Restart Home Assistant.
5. Add the integration:

[![Add the integration][config-flow-badge]][config-flow]

Or **Settings → Devices & services → Add integration → Mitsubishi Wi-Fi (/smart)**
and enter the Lossnay adapter LAN IP.

Do not add the ducted heat-pump adapter. That is a different device.

## What it exposes

| Entity | Notes |
| --- | --- |
| Fan | On/off and 4-notch speed slider. Attributes show setpoint vs reported speed. |
| Fresh air in | Temperature |
| Stale air out | Temperature |
| Problem | On when adapter `STATUS` is not `NORMAL` |
| Melview connected | Binary diagnostic from the `CONNECT` flag |
| ECHONET Lite flag | Binary diagnostic; this adapter still never answers UDP 3610 |

Other diagnostic sensors: adapter status, reported fan speed, adapter
clock, SSL certificate limit, firmware, RSSI.

After setup, **Configure** can change the IP, name, and poll interval
(15–300s, default 30). Download diagnostics from the device page for a
redacted `/smart` dump.

## Compatible hardware

Tested: **VL-500** + **MAC-578IF-E**, firmware **43.00**, class `0x0134`.

Likely the same `/smart` transport on other MAC-5xx Lossnay adapters.
HVAC adapters (`0x0130`) are out of scope.

### What this firmware actually does

| App control | Local `/smart` |
| --- | --- |
| Power on / off | Yes |
| Fan speed 1, 3, 4 | Yes |
| Fan speed 2 | Adapter stores 1 |
| Boost | Same local frame as speed 4 |
| Lossnay / Bypass / Auto | Melview only |
| Pre-warmed / exhaust | Not in local frames |

## Manual install

Copy `custom_components/melsmart` into `/config/custom_components/melsmart`
and restart Home Assistant.

## Notes

The adapter wedges if `/smart` is hammered. This integration serializes
requests, waits between polls and writes, and never sends
`<CONNECT>ON</CONNECT>` on a status poll.

Protocol notes: [PROTOCOL.md](PROTOCOL.md).  
Redacted live capture: [examples/lossnay-mac578-fw43](examples/lossnay-mac578-fw43).

## Related

- [pymitsubishi](https://github.com/pymitsubishi/pymitsubishi) — same transport, HVAC only
- [bodhi/ha-melview](https://github.com/bodhi/ha-melview) — Melview cloud
- [scottyphillips/echonetlite_homeassistant](https://github.com/scottyphillips/echonetlite_homeassistant) — ECHONET Lite

[hacs]: https://www.hacs.xyz/
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-repo]: https://my.home-assistant.io/redirect/hacs_repository/?owner=redhoodie&repository=ha-melsmart&category=integration
[hacs-repo-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[config-flow]: https://my.home-assistant.io/redirect/config_flow_start/?domain=melsmart
[config-flow-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
[releases]: https://github.com/redhoodie/ha-melsmart/releases
[release-badge]: https://img.shields.io/github/v/release/redhoodie/ha-melsmart
[license-badge]: https://img.shields.io/github/license/redhoodie/ha-melsmart
