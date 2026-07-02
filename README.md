# Windmill Air Purifier for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration that controls a
[Windmill Air Purifier](https://windmillair.com/products/the-windmill-air-purifier)
through Windmill's cloud (a white-labeled [Blynk](https://blynk.io) server at
`dashboard.windmillair.com`).

It gives you:

- A **fan entity** — power, 5 fan speeds, and optional Auto / Sleep presets
- An **AQI sensor** (plus optional PM2.5)
- Optional **switches** for child lock and display light
- **Diagnostic sensors for every unmapped datastream**, used to discover the pin
  mapping of your unit (see below)

> ⚠️ Unofficial. Not associated with, maintained, supported, or endorsed by Windmill.
> Their cloud may change and break this at any time.

## How it works

Every Windmill device is a Blynk device: its state lives in numbered virtual
datastreams ("pins" — `V0`, `V1`, ...), and Windmill's dashboard exposes Blynk's
token-authenticated device HTTPS API:

```
GET https://dashboard.windmillair.com/external/api/getAll?token=TOKEN
GET https://dashboard.windmillair.com/external/api/get?token=TOKEN&v0
GET https://dashboard.windmillair.com/external/api/update?token=TOKEN&v0=1
GET https://dashboard.windmillair.com/external/api/isHardwareConnected?token=TOKEN
```

The community mapped the pins for the Windmill **AC** (V0 power, V1 current temp,
V2 target temp, V3 mode, V4 fan), but the **purifier's** pin map isn't published
anywhere — so this integration makes the mapping configurable and helps you
discover it in a few minutes.

## Installation

### HACS (recommended)

1. HACS → three-dot menu → **Custom repositories** → add this repository's URL
   with category **Integration**.
2. Install **Windmill Air Purifier**, then restart Home Assistant.

### Manual

Copy `custom_components/windmill_air/` into your Home Assistant `config/custom_components/`
folder and restart.

## Setup

1. Get your device **Auth Token**: log in at
   [dashboard.windmillair.com](https://dashboard.windmillair.com) with your
   Windmill app account, open the **Devices** tab, select your purifier, and copy
   the Auth Token.
2. In Home Assistant: **Settings → Devices & Services → Add Integration →
   Windmill Air Purifier**, paste the token.

## Mapping the pins (one-time, ~5 minutes)

The integration starts with a best-guess mapping (`V0` power, `V1` fan speed,
`V2` AQI). Verify it against your unit:

1. After setup, open the device page. Every datastream the cloud reports that
   isn't already mapped appears as a diagnostic **"Pin Vx"** sensor.
2. Change one setting at a time in the Windmill app (power, fan speed, auto mode,
   sleep, child lock, display light) and watch which pin sensor changes and to
   what value.
3. Open the integration's **Configure** dialog and assign each pin. The dialog
   also shows a live snapshot of all current pin values. Leave a field empty to
   disable that entity.

Alternatively, run the standalone discovery script from any machine (no Home
Assistant needed):

```bash
python3 scripts/discover_pins.py YOUR_AUTH_TOKEN --watch   # watch pins change live
python3 scripts/discover_pins.py YOUR_AUTH_TOKEN --set v1=3  # test a write
```

Once you've confirmed your purifier's mapping, please open an issue or PR with it
so it can become the default!

## No-custom-component alternative

If you'd rather not install a custom integration, the same API works with plain
YAML — for example:

```yaml
rest_command:
  purifier_power_on:
    url: "https://dashboard.windmillair.com/external/api/update?token=YOUR_TOKEN&v0=1"
  purifier_power_off:
    url: "https://dashboard.windmillair.com/external/api/update?token=YOUR_TOKEN&v0=0"

sensor:
  - platform: rest
    name: Purifier AQI
    resource: "https://dashboard.windmillair.com/external/api/get?token=YOUR_TOKEN&v2"
```

The custom integration is nicer (single poll for all values, real fan entity,
config UI), but the YAML route is a fine fallback.

## Credits

- API pattern reverse-engineered by the community for the Windmill AC:
  [bzellman/WindmillAC](https://github.com/bzellman/WindmillAC) and
  [johnanthonyeletto/homebridge-windmill-ac](https://github.com/johnanthonyeletto/homebridge-windmill-ac)
- [Blynk device HTTPS API docs](https://docs.blynk.io/en/blynk.cloud/device-https-api)
