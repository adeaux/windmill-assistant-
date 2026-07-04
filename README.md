# Windmill Air Purifier for Home Assistant

[![Validate](https://github.com/adeaux/windmill-assistant-/actions/workflows/validate.yml/badge.svg)](https://github.com/adeaux/windmill-assistant-/actions/workflows/validate.yml)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)

A custom [Home Assistant](https://www.home-assistant.io/) integration that controls the
[Windmill Air Purifier](https://windmillair.com/products/the-windmill-air-purifier)
through Windmill's cloud — a white-labeled [Blynk](https://blynk.io) server at
`dashboard.windmillair.com`.

There's a community integration for the Windmill **AC**, but nothing for the
**purifier** — this fills that gap.

> ⚠️ **Unofficial.** Not associated with, maintained, supported, or endorsed by
> Windmill. Their cloud can change and break this at any time.

## Features

- **Fan** — power, 4 fan speeds, and presets: **Eco**, **Sleep: Whisper**,
  **Sleep: White noise**
- **Air quality** — numeric AQI (0–500) sensor and a Good/Moderate/… category sensor
- **Switches** — child lock, display auto-dim, beep (audible feedback)
- **Diagnostic sensors** for every unmapped datastream, to help map other units
- UI config flow (just paste your device Auth Token) with reauth support
- All pins remappable via the options flow, for units that differ

## Supported devices

Developed and confirmed against the Windmill Air Purifier. Other Windmill
purifier models likely work but may use a different pin layout — everything is
remappable, and unmapped pins show as diagnostic sensors to help you adjust.

## Installation

### HACS (custom repository)

1. HACS → three-dot menu → **Custom repositories** → add
   `https://github.com/adeaux/windmill-assistant-` with category **Integration**.
2. Install **Windmill Air Purifier**, then **restart Home Assistant**.

### Manual

Copy `custom_components/windmill_air/` into your HA `config/custom_components/`
folder and restart.

## Setup

1. Get your device **Auth Token**: log in at
   [dashboard.windmillair.com](https://dashboard.windmillair.com) with your
   Windmill app account → **Devices** tab → select your purifier → copy the Auth Token.
2. **Settings → Devices & Services → Add Integration → Windmill Air Purifier**,
   paste the token.

Defaults already match a standard Windmill Air Purifier, so no manual mapping is
usually needed.

## Entities

| Entity | Source | Notes |
|--------|--------|-------|
| `fan.windmill…` | V0 power, V3 mode | 4-speed slider + Eco / Sleep presets |
| `sensor.…air_quality_index` | V1 | numeric AQI 0–500 |
| `sensor.…air_quality` | V16 | category: Good / Moderate / … |
| `switch.…child_lock` | V11 | |
| `switch.…display_auto_dim` | V5 | LED auto-fade after interaction |
| `switch.…beep` | V6 | audible feedback |
| `sensor.…pin_v#` | unmapped pins | diagnostic, for discovery |

## How it works

Windmill devices are Blynk devices: state lives in numbered virtual datastreams
("pins"), read/written over Blynk's token-authenticated device HTTPS API. The
integration polls `getAll` and writes with `update`.

Two Blynk quirks are handled automatically:

- **`getAll` can omit datastreams** that have no web-dashboard widget. Any pin you
  map that's missing from the bulk response is fetched individually via `get?vN`.
- **`get?vN` returns human labels** for enum pins (e.g. the AQI category), so the
  category pin is always fetched individually to show "Good"/"Moderate" rather
  than a raw code.

## Configuration & remapping

Open the integration's **Configure** dialog to remap any pin (blank disables that
entity) or change the polling interval. The dialog shows a live snapshot of all
current pin values. Confirmed default mapping:

| Pin | Function |
|-----|----------|
| V0 | Power |
| V1 | AQI (numeric) |
| V3 | Mode: 1–4 speeds, 5 = Eco, 6 = Sleep |
| V4 | Sleep sub-mode: 1 = Whisper, 2 = White noise |
| V5 | Display auto-dim |
| V6 | Beep |
| V11 | Child lock |
| V16 | AQI category |

### Discovering pins on a different unit

`scripts/discover_pins.py` (standard library only):

```bash
python3 scripts/discover_pins.py YOUR_TOKEN --watch    # highlight pins that change live
python3 scripts/discover_pins.py YOUR_TOKEN --scan     # probe v0..v120, flag getAll-hidden pins
python3 scripts/discover_pins.py YOUR_TOKEN --set v3=5  # test a write (Eco)
```

Change one setting at a time in the Windmill app and note which pin flips.

## Development

```bash
pip install pytest-homeassistant-custom-component
pytest
```

The suite runs the integration end-to-end against a mocked cloud (config flow,
entities, fan/preset/switch writes, the getAll-omission fallback, the category
label override, offline handling).

## Credits

- API pattern reverse-engineered by the community for the Windmill AC:
  [bzellman/WindmillAC](https://github.com/bzellman/WindmillAC) and
  [johnanthonyeletto/homebridge-windmill-ac](https://github.com/johnanthonyeletto/homebridge-windmill-ac)
- [Blynk device HTTPS API docs](https://docs.blynk.io/en/blynk.cloud/device-https-api)

## License

[MIT](LICENSE)
