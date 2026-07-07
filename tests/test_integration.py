"""End-to-end tests for the Windmill Air Purifier integration (mocked cloud)."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.windmill_air.const import DOMAIN

BASE = "https://dashboard.windmillair.com/external/api"
TOKEN = "test-token-123"

# v0 power, v1 numeric AQI, v3 mode (speed 2 of 4), v4 sleep sub-mode,
# v5 LED fade, v6 beep, v11 child lock, v16 AQI category (getAll returns the
# numeric code; the label comes from an individual get), plus unmapped v7.
PINS = {
    "v0": 1,
    "v1": 7,
    "v3": 2,
    "v4": 1,
    "v5": 1,
    "v6": 0,
    "v7": 71,
    "v11": 0,
    "v16": 1,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components in tests."""
    return


def mock_cloud(aioclient_mock, pins=PINS, online=True, label="Good"):
    aioclient_mock.get(f"{BASE}/isHardwareConnected", text="true" if online else "false")
    aioclient_mock.get(f"{BASE}/getAll", json=pins)
    # Individual get returns enum labels (e.g. the AQI category) and is the
    # fallback for pins missing from getAll.
    aioclient_mock.get(f"{BASE}/get", text=label)
    aioclient_mock.get(f"{BASE}/update", text="")


async def test_config_flow_creates_entry(hass: HomeAssistant, aioclient_mock) -> None:
    mock_cloud(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"token": TOKEN}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"token": TOKEN}


async def test_config_flow_bad_token(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(
        f"{BASE}/isHardwareConnected", status=400, text="Invalid token."
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"token": "bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def _setup_entry(hass, aioclient_mock, options=None) -> MockConfigEntry:
    mock_cloud(aioclient_mock)
    entry = MockConfigEntry(
        domain=DOMAIN, data={"token": TOKEN}, options=options or {}, title="Windmill"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _last_updates(aioclient_mock):
    return [
        str(c[1].query_string)
        for c in aioclient_mock.mock_calls
        if "update" in str(c[1])
    ]


async def test_entities_created(hass: HomeAssistant, aioclient_mock) -> None:
    await _setup_entry(hass, aioclient_mock)

    fan = hass.states.get("fan.windmill")
    assert fan is not None
    assert fan.state == "on"  # v0 == 1
    assert fan.attributes["percentage"] == 50  # v3 == 2 of 4 speeds
    assert fan.attributes["preset_modes"] == [
        "auto",  # first, so Apple Home folds it into the Auto/Manual toggle
        "Eco",
        "Sleep: Whisper",
        "Sleep: White noise",
    ]
    assert fan.attributes["preset_mode"] is None  # numbered speed, not a preset

    # Switches from the default pin mapping
    assert hass.states.get("switch.windmill_child_lock").state == "off"  # v11 == 0
    assert hass.states.get("switch.windmill_display_auto_dim").state == "on"  # v5 == 1
    assert hass.states.get("switch.windmill_beep").state == "off"  # v6 == 0

    # AQI defaults to v1; other unmapped pins become diagnostic sensors
    # (v7 here), while mapped pins (v1, v3, v16, ...) do not.
    assert hass.states.get("sensor.windmill_air_quality_index").state == "7"  # v1
    # AQI category (v16) shows the label from the individual get, not the code
    assert hass.states.get("sensor.windmill_air_quality").state == "Good"
    assert hass.states.get("sensor.windmill_pin_v7").state == "71"
    assert hass.states.get("sensor.windmill_pin_v3") is None
    assert hass.states.get("sensor.windmill_pin_v1") is None
    assert hass.states.get("sensor.windmill_pin_v16") is None


async def test_speed_slider_writes_mode_pin(
    hass: HomeAssistant, aioclient_mock
) -> None:
    await _setup_entry(hass, aioclient_mock)
    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v3": 4})
    await hass.services.async_call(
        "fan",
        "set_percentage",
        {"entity_id": "fan.windmill", "percentage": 100},
        blocking=True,
    )
    assert any("v3=4" in q for q in _last_updates(aioclient_mock))
    assert hass.states.get("fan.windmill").attributes["percentage"] == 100


async def test_eco_and_sleep_presets(hass: HomeAssistant, aioclient_mock) -> None:
    await _setup_entry(hass, aioclient_mock)

    # Eco -> mode pin 5
    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v3": 5})
    await hass.services.async_call(
        "fan",
        "set_preset_mode",
        {"entity_id": "fan.windmill", "preset_mode": "Eco"},
        blocking=True,
    )
    assert any("v3=5" in q for q in _last_updates(aioclient_mock))
    assert hass.states.get("fan.windmill").attributes["preset_mode"] == "Eco"

    # Sleep: White noise -> mode pin 6 and sub-mode pin 2
    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v3": 6, "v4": 2})
    await hass.services.async_call(
        "fan",
        "set_preset_mode",
        {"entity_id": "fan.windmill", "preset_mode": "Sleep: White noise"},
        blocking=True,
    )
    updates = _last_updates(aioclient_mock)
    assert any("v3=6" in q for q in updates)
    assert any("v4=2" in q for q in updates)
    fan = hass.states.get("fan.windmill")
    assert fan.attributes["preset_mode"] == "Sleep: White noise"
    assert fan.attributes["percentage"] is None  # a preset, not a speed


async def _refresh_with(hass, aioclient_mock, coordinator, **pins) -> None:
    """Re-poll the (mocked) cloud with an updated pin snapshot.

    Uses async_refresh (not async_request_refresh, which is debounced) so the
    poll — and the auto driver's _handle_coordinator_update — run immediately.
    """
    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, **pins})
    await coordinator.async_refresh()
    await hass.async_block_till_done()


async def _engage_auto_at(hass, aioclient_mock, entry, aqi, seed_speed):
    """Load an AQI reading, then engage the auto preset; return the coordinator."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await _refresh_with(hass, aioclient_mock, coordinator, v1=aqi, v3=seed_speed)
    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v1": aqi})
    await hass.services.async_call(
        "fan",
        "set_preset_mode",
        {"entity_id": "fan.windmill", "preset_mode": "auto"},
        blocking=True,
    )
    return coordinator


async def test_auto_preset_sets_speed_from_aqi(
    hass: HomeAssistant, aioclient_mock
) -> None:
    entry = await _setup_entry(hass, aioclient_mock)
    # AQI 120 falls in the speed-3 band (thresholds 50/100/150); seed a manual
    # speed 1 so the auto write is clearly the AQI-driven choice, not a no-op.
    await _engage_auto_at(hass, aioclient_mock, entry, aqi=120, seed_speed=1)

    assert any("v3=3" in q for q in _last_updates(aioclient_mock))
    fan = hass.states.get("fan.windmill")
    assert fan.attributes["preset_mode"] == "auto"
    assert fan.state == "on"


async def test_auto_follows_aqi_across_a_poll(
    hass: HomeAssistant, aioclient_mock
) -> None:
    entry = await _setup_entry(hass, aioclient_mock)
    coordinator = await _engage_auto_at(
        hass, aioclient_mock, entry, aqi=120, seed_speed=1
    )

    # AQI spikes to 200 (speed-4 band). The device still reports the old speed
    # 3, so the auto driver must write the new speed on this update.
    await _refresh_with(hass, aioclient_mock, coordinator, v1=200, v3=3)
    assert any("v3=4" in q for q in _last_updates(aioclient_mock))
    assert hass.states.get("fan.windmill").attributes["preset_mode"] == "auto"


async def test_auto_hysteresis_holds_near_boundary(
    hass: HomeAssistant, aioclient_mock
) -> None:
    entry = await _setup_entry(hass, aioclient_mock)
    coordinator = await _engage_auto_at(
        hass, aioclient_mock, entry, aqi=120, seed_speed=1
    )  # -> speed 3

    # AQI drifts to 95: naive band is speed 2, but stepping down from 3 needs
    # AQI < 90 (boundary 100 minus hysteresis 10), so the speed must hold.
    await _refresh_with(hass, aioclient_mock, coordinator, v1=95, v3=3)
    assert not any("v3=" in q for q in _last_updates(aioclient_mock))
    assert hass.states.get("fan.windmill").attributes["preset_mode"] == "auto"


async def test_manual_speed_exits_auto(
    hass: HomeAssistant, aioclient_mock
) -> None:
    entry = await _setup_entry(hass, aioclient_mock)
    await _engage_auto_at(hass, aioclient_mock, entry, aqi=120, seed_speed=1)

    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v1": 120, "v3": 4})
    await hass.services.async_call(
        "fan",
        "set_percentage",
        {"entity_id": "fan.windmill", "percentage": 100},
        blocking=True,
    )
    fan = hass.states.get("fan.windmill")
    assert fan.attributes["preset_mode"] is None  # auto disengaged
    assert fan.attributes["percentage"] == 100


async def test_eco_exits_auto(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await _setup_entry(hass, aioclient_mock)
    await _engage_auto_at(hass, aioclient_mock, entry, aqi=120, seed_speed=1)

    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v1": 120, "v3": 5})
    await hass.services.async_call(
        "fan",
        "set_preset_mode",
        {"entity_id": "fan.windmill", "preset_mode": "Eco"},
        blocking=True,
    )
    assert hass.states.get("fan.windmill").attributes["preset_mode"] == "Eco"


async def test_switch_toggle_writes_pin(hass: HomeAssistant, aioclient_mock) -> None:
    await _setup_entry(hass, aioclient_mock)
    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v11": 1})
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.windmill_child_lock"}, blocking=True
    )
    assert any("v11=1" in q for q in _last_updates(aioclient_mock))
    assert hass.states.get("switch.windmill_child_lock").state == "on"


async def test_aqi_pin_hidden_from_getall_is_fetched_individually(
    hass: HomeAssistant, aioclient_mock
) -> None:
    # v9 is NOT in the getAll blob, but the device returns it via get?v9 —
    # the coordinator must fall back to an individual fetch for mapped pins.
    aioclient_mock.get(f"{BASE}/isHardwareConnected", text="true")
    aioclient_mock.get(f"{BASE}/getAll", json=PINS)  # no v9
    aioclient_mock.get(f"{BASE}/get", text="[12]")  # individual v9 fetch
    aioclient_mock.get(f"{BASE}/update", text="")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"token": TOKEN},
        options={"aqi_pin": "v9"},
        title="Windmill",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    aqi = hass.states.get("sensor.windmill_air_quality_index")
    assert aqi is not None
    assert aqi.state == "12"
    assert hass.states.get("sensor.windmill_pin_v9") is None


async def test_device_offline_marks_unavailable(
    hass: HomeAssistant, aioclient_mock
) -> None:
    mock_cloud(aioclient_mock, online=False)
    entry = MockConfigEntry(domain=DOMAIN, data={"token": TOKEN}, title="Windmill")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("fan.windmill").state == "unavailable"
