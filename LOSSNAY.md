# Lossnay support — research and implementation

This fork adds a Home Assistant **fan** entity for ECHONET Lite ventilation
classes, mapped to the Mitsubishi Electric Lossnay controls shown in the
AU/NZ Wi-Fi Control app.

## What the app already proves

The screenshots from a **VL-500** on adapter type **mac578** (MAC-578IF,
firmware v43.00) show the Lossnay as a first-class Wi-Fi device, not a
hidden accessory of the ducted heat pump:

| App control | Meaning |
| --- | --- |
| Power ON / OFF | Unit operation |
| Fan speed 1, 2, 3, 4 | Discrete airflow (VL-500: 30% / 50% / 70% / 100%) |
| BOOST | Timed high-speed override, then returns to the base notch |
| LOSSNAY / BYPASS / AUTO | Heat-exchange core vs bypass duct vs automatic |
| Fresh / stale / exhaust / pre-warmed °C | Four core temperatures |
| Heat recovery % | Derived from those temperatures in the app |
| Clean Air Filters | Maintenance flag |
| Wi-Fi Interlock → Power Interlock | App-level link to a ducted heat pump |

Wi-Fi Interlock is **not** ECHONET. It is coordinated by the Mitsubishi cloud
app (Melview) between two adapters. Each adapter still has its own IP. This
fork talks to the **Lossnay adapter** only.

## Upstream status

[scottyphillips/echonetlite_homeassistant](https://github.com/scottyphillips/echonetlite_homeassistant)
(v4.0.8, pychonet 2.8.1):

- Confirmed for MAC-568 / 577 / 578 / 587 / 588 / 900 HVAC adapters as
  **HomeAirConditioner (`0x0130`)**.
- Fan platform only created entities for **Air Cleaner `0x0135`** and
  **Ceiling Fan `0x013A`**.
- pychonet *names* `0x0133` / `0x0134` in `eojx.py` and `epc.py`, but has
  **no device class** and does not register them in `Factory`.
- No open PR adds Lossnay. The closest issue is
  [#245 Ichijo “Loss Guard”](https://github.com/scottyphillips/echonetlite_homeassistant/issues/245):
  a Panasonic `0x0134` ventilation fan is *discovered*, but HA only shows a
  generic ON/OFF switch because there is no fan mapping.
- [#226](https://github.com/scottyphillips/echonetlite_homeassistant/issues/226)
  comment: *“Too bad the Energy Recovery Ventilator is not supported.”*
  That was about ERV control **through the heat-pump adapter**. A dedicated
  Lossnay MAC-578 is a different device.

Older write-ups (jethrocarr, ~2018) said Lossnay was not in the Wi-Fi app
and not on ECHONET. That is outdated: Mitsubishi’s current AU/NZ Wi-Fi
Control manual documents both **Lossnay Wi-Fi Control** and **ECHONET Lite
on MAC-568/578/588IF-E**.

## ECHONET object classes

| EOJ | Name | Fits Lossnay? |
| --- | --- | --- |
| `0x0133` | Ventilation fan | Power (`0x80`) + airflow (`0xA0`) + auto (`0xBF`) |
| `0x0134` | Air conditioner ventilation fan | Same, plus heat-exchange mode, four air-path temperatures, CO2, filter/pollution flags |

`0x0134` is the class that matches a VL-500. `0x0133` is the fallback if
the adapter only implements the simpler fan.

### Airflow (EPC `0xA0`) — the speed map

ECHONET specifies 8 levels plus auto:

| EDT | Spec | This fork (app names) |
| --- | --- | --- |
| `0x31` | level 1 | **1** |
| `0x32` | level 2 | **2** |
| `0x33` | level 3 | **3** |
| `0x34` | level 4 | **4** |
| `0x35` | level 5 | **boost** |
| `0x41` | auto | auto |

Home Assistant also gets a 4-step percentage slider (25 / 50 / 75 / 100)
for speeds 1–4. Boost is a **preset**, not a fifth slider step, because the
wall controller treats it as a timed override.

If Boost writes are rejected by firmware, remove `boost` under
**Configure → fan settings**.

### Mode (EPC `0xB2` / `0xE0`) — Lossnay vs Bypass

| App | ECHONET |
| --- | --- |
| LOSSNAY | `0xB2` = heat exchange (`0x42`), `0xE0` heat exchanger ON (`0x41`) |
| BYPASS | `0xB2` = normal (`0x41`), `0xE0` heat exchanger OFF (`0x42`) |
| AUTO | `0xB0` / `0xBF` auto flag (`0x41`) |

These appear as extra **select/switch** entities when the adapter lists
them in SETMAP.

### Temperatures (0x0134, Get)

| App label | EPC | ECHONET name |
| --- | --- | --- |
| Fresh air in | `0xBE` | Outdoor air temperature |
| Stale air out | `0xD0` | Return air temperature |
| Pre-warmed | `0xD2` | Supply (charging) air temperature |
| Exhaust | `0xD4` | Exhaust (discharging) air temperature |

The app’s “92% heat recovery” figure is computed from those four sensors,
not a separate ECHONET property:
`(supply − outdoor) / (return − outdoor)`.

## What this fork changes

1. `custom_components/echonetlite/pychonet_ext/` — `VentilationFan` and
   `AirConditionerVentilationFan` classes, patched into `pychonet.Factory`
   at import time (no wait for a pychonet release).
2. `fan.py` — create a fan entity for EOJCC `0x33` and `0x34`.
3. `const.py` — sensor metadata for the air-path temperatures and modes.
4. Options flow — Lossnay speed list `1 / 2 / 3 / 4 / boost / auto`.

Power is EPC `0x80` (`0x30` ON, `0x31` OFF), the same as every other
ECHONET appliance. The fan entity exposes `turn_on` / `turn_off`.

## Setup on a real VL-500 + MAC-578IF

1. Confirm the Lossnay has its **own** Wi-Fi interface (MAC-578IF / type
   `mac578` in the app). Both the heat pump and the Lossnay need adapters
   for Wi-Fi Interlock; this integration uses the Lossnay one.
2. Edit unit settings on the **Lossnay** → enable **ECHONET Lite**.
3. Reserve a DHCP address for that MAC (`8c:53:e6:…` in the sample app).
4. Home Assistant → Add Integration → **ECHONET Lite** → Lossnay IP.
5. Expect `eojgc=1`, `eojcc=52` (`0x34`) or `eojcc=51` (`0x33`) in debug
   logs. A fan entity named after the config title should appear.

Debug logging: Integration → ECHONET Lite → Enable debug logging, reload,
then look for `Air conditioner ventilation fan` / `Ventilation fan`.

## If ECHONET is enabled but nothing useful appears

Mitsubishi’s MAC-578 firmware is written primarily for air conditioners.
It is possible a Lossnay-typed adapter:

- does not start the ECHONET UDP service at all, or
- announces only `0x0130` HomeAirConditioner with HVAC properties, or
- announces `0x0134` with power but without `0xA0` in SETMAP.

None of those can be faked from Home Assistant. Capture the discovery
`getmap` / `setmap` from the log and we can add a manufacturer quirk.

**Cloud fallback (not this repo):** the AU/NZ app speaks Melview, not
MELCloud. Experimental Lossnay support exists in
[rowds15/rowdys15-ha-melview](https://github.com/rowds15/rowdys15-ha-melview).
Europe MELCloud ERV devices use [ojkaas/MELCloud](https://github.com/ojkaas/MELCloud).
Those are cloud APIs. This fork stays local ECHONET.

## Related work

- [sayurin/hems_echonet_lite](https://github.com/sayurin/hems_echonet_lite)
  already maps `0x0133` / `0x0134` to a generic 8-level fan. This fork
  keeps the scottyphillips architecture and uses Lossnay-named presets.
- ECHONET Appendix / MRA device files `0x0133.json` and `0x0134.json`
  (vendored in pychonet) are the source of the EPC encodings above.
