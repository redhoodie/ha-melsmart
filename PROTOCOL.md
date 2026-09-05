# Mitsubishi `/smart` on Lossnay (MAC-578IF-E)

## Transport

`POST http://<ip>/smart`

- AES-128-CBC, key `unregistered` padded to 16 nulls
- ISO 7816-4 padding
- Request XML: `<ESV>base64(IV + ciphertext)</ESV>` wrapping `<CSV>…</CSV>`
- Reply decrypts to `<LSV>…</LSV>` with 22-byte CN105-style `CODE` hex frames

Checksum: `(0xFC - sum(body)) & 0xFF`. Class byte is `0x34`.

Status poll: `<CSV></CSV>` only. Do not send `<CONNECT>ON</CONNECT>` on
every poll (that writes the Melview cloud flag).

Same-POST replies echo cached `CODE`. A change appears on a later poll
(~3s). Aggressive writes will wedge the adapter.

## Proven local writes (SET `0x41`, group `0x01`)

| Action | Flag | Payload |
| --- | --- | --- |
| Power | `0x01` | byte 3 = `0` / `1` |
| Fan speed | `0x08` | byte 6 = `1` / `3` / `4` |

Speed **2** is accepted by the app UI and rejected by this firmware
(stored as 1). Speeds 5 and 6 are rejected.

## Status `CODE` groups on firmware 43.00

| Group | Used fields |
| --- | --- |
| `02` | `[8]` power, `[11]` fan setpoint. `[9]` does not change with mode. |
| `03` | `[10]` fresh air in, `[11]` stale air out. Mitsubishi encoding `5*(byte-0x80)/10` if `byte >= 0x80`; `0x00` / `0xFF` = unavailable. |
| `09` | `[14]` / `[15]` actual fan speed (can lag). |
| `04`, `06`, `15` | Present, undecoded, unchanged across app tests. |

Temperatures use the same packed byte as pymitsubishi HVAC.

## App-only on this firmware

Melview can show Lossnay / Bypass / Auto, Boost, fan speed 2, pre-warmed,
and exhaust. Local `/smart` does not expose those. App Bypass / Auto /
Boost / speed 2 leave the local frames identical to Lossnay + speed 1 or 4.

ECHONET Lite is advertised (`<ECHONET>ON</ECHONET>`) but UDP 3610 never
gets a reply from this adapter, unicast or multicast.

See [`examples/lossnay-mac578-fw43`](examples/lossnay-mac578-fw43) for a
redacted live `<LSV>`.
