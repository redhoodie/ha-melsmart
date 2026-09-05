# Mitsubishi Wi-Fi (`/smart`) for Home Assistant

Local Home Assistant integration for Mitsubishi Wi-Fi adapters that speak
the encrypted HTTP **`/smart`** API. Built for a **Lossnay VL-500** on a
**MAC-578IF-E** (firmware 43.00, class `0x0134`).

This is **not** ECHONET Lite. This adapter advertises ECHONET as `ON` but
never answers UDP 3610. Control is `POST http://<adapter>/smart`.

## What works on this firmware

| Control | Local `/smart` |
| --- | --- |
| Power on / off | Yes |
| Fan speed 1, 3, 4 | Yes |
| Fan speed 2 | Adapter remaps to 1 |
| Boost | Same local frame as speed 4 |
| Lossnay / Bypass / Auto | Melview cloud only |
| Fresh air in, stale air out | Yes |
| Pre-warmed, exhaust | Not in local frames |

Diagnostic sensors (same poll): adapter status, Melview connect flag,
ECHONET flag, reported fan speed, adapter clock, SSL certificate limit,
firmware, RSSI.

A redacted live status capture is in
[`examples/lossnay-mac578-fw43`](examples/lossnay-mac578-fw43).
Protocol notes are in [PROTOCOL.md](PROTOCOL.md).

## Install

Copy `custom_components/melsmart` into `/config/custom_components/melsmart`
and restart Home Assistant.

Then **Settings → Devices & services → Add integration → Mitsubishi Wi-Fi (/smart)**
and enter the Lossnay adapter LAN IP.

Do not add the ducted heat-pump adapter here. That is a different device.

## Rate limits

The adapter wedges if `/smart` is hammered (TCP:80 still opens, HTTP times out).
The client serializes POSTs, waits 3s between polls, 6s after a write, and
20s after a timeout. The coordinator polls every 30s. Status polls use
`<CSV></CSV>` and do **not** send `<CONNECT>ON</CONNECT>`.

## Related

- [pymitsubishi](https://github.com/pymitsubishi/pymitsubishi) — same transport, HVAC class `0x0130` only
- [bodhi/ha-melview](https://github.com/bodhi/ha-melview) — Melview cloud, including experimental Lossnay
- [scottyphillips/echonetlite_homeassistant](https://github.com/scottyphillips/echonetlite_homeassistant) — ECHONET Lite (unused by this adapter)
