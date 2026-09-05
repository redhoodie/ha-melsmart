# Captured `/smart` status — VL-500 + MAC-578IF-E

Live decrypted `<LSV>` from this Lossnay adapter (firmware **43.00**,
class `0x0134`). Serial number removed. Do not commit unredacted
`<SERIAL>` values.

The poll is `POST http://<adapter>/smart` with encrypted `<CSV></CSV>`.
Do not send `<CONNECT>ON</CONNECT>` on every poll; that writes the
Melview cloud flag.

## XML fields

| Field | Sample | Pull into HA? | Notes |
| --- | --- | --- | --- |
| `MAC` | `8c:53:e6:19:d1:76` | Device unique id | Adapter Wi-Fi MAC. |
| `SERIAL` | redacted | No | Adapter serial. PII. |
| `CONNECT` | `ON` | Diagnostic | Melview cloud registration flag. |
| `STATUS` | `NORMAL` | Diagnostic | Becomes useful if it ever leaves `NORMAL` (e.g. `COMM`). |
| `DATDATE` | `2026/09/05 23:06:46` | Diagnostic | Adapter clock (treated as UTC). Moves on a live poll. |
| `APP_VER` | `43.00` | Diagnostic | Firmware. |
| `SSL_LIMIT` | `20371231` | Diagnostic | Adapter TLS cert end date. |
| `RSSI` | `-57` | Diagnostic | Wi-Fi signal, dBm. |
| `ECHONET` | `ON` | Diagnostic | Firmware says ECHONET is on; this unit never answers UDP 3610. |
| `LED1`–`LED4` | `0:1,0:1` / `1:5,0:45` | No | Adapter LED blink pattern. Undecoded. |
| `PROFILECODE` | `0xC9`, `0xCD` | No | Capability frames. Stable on this firmware. |

## CODE groups (22-byte CN105 frames)

| Group | Sample role on this firmware |
| --- | --- |
| `02` | Power (`[8]`), fan setpoint (`[11]`). Byte `[9]` does **not** change with Lossnay / Bypass / Auto. |
| `03` | Fresh air in (`[10]`), stale air out (`[11]`). Bytes `[12]` / `[13]` stay `0x00` (no pre-warmed / exhaust). |
| `04` | Present, undecoded. Unchanged across app mode and speed tests. |
| `06` | Present, undecoded. Same. |
| `09` | Actual fan speed in `[14]` / `[15]` (can lag the group `02` setpoint). |
| `15` | Present, undecoded. Same. |

## What the app shows that `/smart` does not

App changes to **Lossnay / Bypass / Auto**, **Boost**, **fan speed 2**,
**pre-warmed**, and **exhaust** leave these frames unchanged (or remap
speed 2 → 1). Those stay Melview-cloud only on firmware 43.00.

Proven local writes: power on/off, fan speeds **1 / 3 / 4**.
