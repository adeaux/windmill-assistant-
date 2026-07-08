"""Windmill purifier model definitions.

Windmill sells two purifiers, and their names are a minefield: the naming is
**inconsistent across surfaces**.

    Physical unit   Model no.   Retail (box, windmillair.com)   App / dashboard
    -------------   ---------   -----------------------------   ---------------
    larger          WAP1M1      "Air Purifier Max"              "Air Purifier"
    smaller         SAP1V1      "Air Purifier"                  "Air Purifier Mini"

So "Windmill Air Purifier" means the *larger* unit in the app but the *smaller*
unit at retail. The only unambiguous identifier is the **model number**, so that
is what we key models on (and what disambiguates the setup picker). Each model
carries both names to keep the choice foolproof no matter which the user knows.

The model chosen at setup:
  * seeds the pin-mapping / speed defaults (still fully overridable in options), and
  * sets the ``model`` (and ``model_number``) shown for the device in Home
    Assistant.

To support a new/unconfirmed unit, add an entry below. Its layout can start as a
copy of a known one and be refined with ``scripts/discover_pins.py`` — anything
that differs is also remappable per config entry in the options flow.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindmillModel:
    """Static profile of one Windmill purifier model."""

    # Stable id stored in the config entry (never shown to users). We use the
    # model number so the stored value can never be confused between surfaces.
    key: str
    # Model number printed on the unit's rating label / box — the one reliable
    # identifier. Shown in Home Assistant as the device's model id.
    model_number: str
    retail_name: str  # name on the box and windmillair.com retail pages
    app_name: str  # name in the Windmill app and dashboard.windmillair.com
    size: str  # short physical descriptor, e.g. "larger" / "smaller"

    # --- default Blynk datastream ("pin") layout ---
    power_pin: str
    mode_pin: str  # holds fan speed 1..speed_count plus Eco (5) / Sleep (6)
    sleep_submode_pin: str  # Whisper (1) / White noise (2), only in Sleep
    aqi_pin: str  # numeric 0-500 AQI
    aqi_category_pin: str  # text label: Good / Moderate / Bad / Unhealthy
    child_lock_pin: str
    led_fade_pin: str  # display auto-dim
    beep_pin: str
    speed_count: int

    @property
    def name(self) -> str:
        """Canonical model label shown for the device in Home Assistant.

        Uses the retail name (what the box says); the model id carries the
        unambiguous model number alongside it.
        """
        return self.retail_name

    @property
    def picker_label(self) -> str:
        """Fully disambiguated label for the setup dropdown.

        Leads with the retail name + model number, then the size and the app
        name, so the right unit is obvious whichever name the user recognizes.
        """
        return (
            f"{self.retail_name} ({self.model_number}) — {self.size} unit, "
            f"“{self.app_name}” in the Windmill app"
        )


# Pin layout reverse-engineered on the larger unit (WAP1M1). The smaller unit
# (SAP1V1) is assumed to share this layout until it is confirmed on real
# hardware (run ``scripts/discover_pins.py`` against it and adjust MODEL_SAP1V1
# below if anything differs).
_CONFIRMED_PINS = dict(
    power_pin="v0",
    mode_pin="v3",
    sleep_submode_pin="v4",
    aqi_pin="v1",
    aqi_category_pin="v16",
    child_lock_pin="v11",
    led_fade_pin="v5",
    beep_pin="v6",
)

# Model keys are the (lowercased) model numbers — stored in config entries, so
# keep them stable.
MODEL_WAP1M1 = "wap1m1"  # larger unit
MODEL_SAP1V1 = "sap1v1"  # smaller unit

MODELS: dict[str, "WindmillModel"] = {
    MODEL_WAP1M1: WindmillModel(
        key=MODEL_WAP1M1,
        model_number="WAP1M1",
        retail_name="Air Purifier Max",
        app_name="Air Purifier",
        size="larger",
        speed_count=4,
        **_CONFIRMED_PINS,
    ),
    MODEL_SAP1V1: WindmillModel(
        key=MODEL_SAP1V1,
        model_number="SAP1V1",
        retail_name="Air Purifier",
        app_name="Air Purifier Mini",
        size="smaller",
        # Assumed identical to the larger unit until confirmed on the smaller
        # one. Refine with scripts/discover_pins.py.
        speed_count=4,
        **_CONFIRMED_PINS,
    ),
}

# The integration was built and confirmed against the larger unit (WAP1M1), so
# it stays the default selection (and back-fills entries created before models
# existed).
DEFAULT_MODEL = MODEL_WAP1M1


def get_model(key: str | None) -> WindmillModel:
    """Return the model for a stored key, falling back to the default."""
    return MODELS.get(key or DEFAULT_MODEL, MODELS[DEFAULT_MODEL])
