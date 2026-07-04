#!/usr/bin/env python3
"""Discover the Blynk virtual pins of a Windmill device.

Uses only the Python standard library, so you can run it anywhere:

    python3 scripts/discover_pins.py YOUR_AUTH_TOKEN
    python3 scripts/discover_pins.py YOUR_AUTH_TOKEN --watch
    python3 scripts/discover_pins.py YOUR_AUTH_TOKEN --set v1=3

Get the Auth Token from https://dashboard.windmillair.com (Devices tab).

Workflow to map pins:
  1. Run with --watch.
  2. Change one setting at a time in the Windmill app (power, speed, auto,
     sleep, child lock, display light...).
  3. Note which pin changes and to what value; changed pins are marked with *.
  4. Confirm by writing the value back with --set.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://dashboard.windmillair.com/external/api"


def call(endpoint: str, token: str, extra: dict | None = None) -> str:
    params = {"token": token, **(extra or {})}
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace")
        sys.exit(f"HTTP {err.code} from {endpoint}: {body}")
    except urllib.error.URLError as err:
        sys.exit(f"Could not reach the Windmill cloud: {err.reason}")


def get_all(token: str) -> dict:
    data = json.loads(call("getAll", token))
    return {k.lower(): v for k, v in data.items()}


def get_one(token: str, pin: str) -> str | None:
    """Fetch a single datastream; return None if it has no value."""
    url = f"{BASE_URL}/get?{urllib.parse.urlencode({'token': token, pin: ''})}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            value = resp.read().decode().strip('[]" \n')
            return value or None
    except urllib.error.HTTPError:
        return None  # 400 = no data stored for this pin
    except urllib.error.URLError:
        return None


def scan(token: str, max_pin: int) -> dict:
    """Probe v0..vN individually — finds pins that getAll omits."""
    found = {}
    for i in range(max_pin + 1):
        value = get_one(token, f"v{i}")
        if value is not None:
            found[f"v{i}"] = value
    return found


def print_pins(pins: dict, changed: set[str] | None = None) -> None:
    for pin in sorted(pins):
        marker = " *" if changed and pin in changed else ""
        print(f"  {pin.upper():>5} = {pins[pin]!r}{marker}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("token", help="Device Auth Token from dashboard.windmillair.com")
    parser.add_argument("--watch", action="store_true", help="Poll every 3s and highlight changes")
    parser.add_argument("--set", metavar="PIN=VALUE", help="Write a value, e.g. --set v1=3")
    parser.add_argument(
        "--scan",
        nargs="?",
        type=int,
        const=120,
        metavar="MAX",
        help="Probe v0..vMAX individually (default 120). Finds pins getAll hides "
        "— pins marked [hidden] are returned by get but missing from getAll.",
    )
    args = parser.parse_args()

    online = call("isHardwareConnected", args.token).strip().lower() == "true"
    print(f"Device online: {online}")

    if args.set:
        pin, _, value = args.set.partition("=")
        if not value:
            sys.exit("--set expects PIN=VALUE, e.g. --set v1=3")
        call("update", args.token, {pin.lower(): value})
        print(f"Wrote {pin.upper()} = {value}")

    pins = get_all(args.token)
    print(f"\nDatastreams via getAll ({len(pins)}):")
    print_pins(pins)

    if args.scan is not None:
        print(f"\nProbing v0..v{args.scan} individually…")
        probed = scan(args.token, args.scan)
        print(f"Pins with a value via get ({len(probed)}):")
        for pin in sorted(probed, key=lambda p: int(p[1:])):
            hidden = " [hidden: getAll missed this]" if pin not in pins else ""
            print(f"  {pin.upper():>5} = {probed[pin]!r}{hidden}")
        hidden_pins = [p for p in probed if p not in pins]
        if hidden_pins:
            print(
                "\n>> "
                + ", ".join(p.upper() for p in sorted(hidden_pins, key=lambda p: int(p[1:])))
                + " are only reachable via get. If one of these tracks AQI, map it "
                "in the integration — it now fetches mapped pins individually."
            )

    if not args.watch:
        return

    print("\nWatching — change settings in the Windmill app; Ctrl-C to stop.")
    try:
        while True:
            time.sleep(3)
            new = get_all(args.token)
            changed = {p for p in new if new.get(p) != pins.get(p)}
            changed |= set(pins) - set(new)
            if changed:
                print(f"\n{time.strftime('%H:%M:%S')} changed: {', '.join(sorted(p.upper() for p in changed))}")
                print_pins(new, changed)
            pins = new
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
