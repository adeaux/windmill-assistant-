#!/usr/bin/env python3
"""Generate a side-by-side "dev" copy of the integration for on-device testing.

Home Assistant only allows one config entry per (domain, unique-id), and the
unique id is derived from the device Auth Token — so you cannot add this
integration twice against the same token in a single HA. This script produces a
second copy under a different domain (``windmill_air_dev``) so you can install
the in-development branch *alongside* your stable integration, pointed at the
same physical purifier, and compare behavior live.

Uses only the Python standard library:

    python3 scripts/make_dev_copy.py

Then restart Home Assistant and add "Windmill Air Purifier (dev)" with the SAME
Auth Token. It gets its own entities/device, independent of the stable install.

Note: avoid actively driving controls from both integrations at once (both
would write the mode pin); concurrent reads/observation are fine. The generated
folder is gitignored — regenerate it whenever the source changes. It is a
throwaway; delete it (and restart HA) when you are done testing.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SRC_DOMAIN = "windmill_air"
DEV_DOMAIN = "windmill_air_dev"
SRC_NAME = "Windmill Air Purifier"
DEV_NAME = "Windmill Air Purifier (dev)"

COMPONENTS = Path(__file__).resolve().parent.parent / "custom_components"
SRC = COMPONENTS / SRC_DOMAIN
DEST = COMPONENTS / DEV_DOMAIN


def main() -> int:
    if not SRC.is_dir():
        print(f"Source integration not found: {SRC}", file=sys.stderr)
        return 1

    if DEST.exists():
        shutil.rmtree(DEST)
    # Copy everything (.py, strings.json, translations/) except caches.
    shutil.copytree(SRC, DEST, ignore=shutil.ignore_patterns("__pycache__"))

    # Only two files hard-code the domain/name; everything else uses the DOMAIN
    # and NAME constants or relative imports, so they carry over unchanged.
    const = DEST / "const.py"
    const.write_text(
        const.read_text()
        .replace(f'DOMAIN = "{SRC_DOMAIN}"', f'DOMAIN = "{DEV_DOMAIN}"')
        .replace(f'NAME = "{SRC_NAME}"', f'NAME = "{DEV_NAME}"')
    )

    manifest_path = DEST / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["domain"] = DEV_DOMAIN
    manifest["name"] = DEV_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"Wrote {DEST.relative_to(COMPONENTS.parent)}")
    print(
        "Restart Home Assistant, then add "
        f'"{DEV_NAME}" with the same Auth Token.'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
