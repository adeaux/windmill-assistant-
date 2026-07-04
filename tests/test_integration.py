"""End-to-end tests for the Windmill Air Purifier integration (mocked cloud)."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.windmill_air.const import DOMAIN

BASE = "https://dashboard.windmillair.com/external/api"
TOKEN = "test-token-123"

# v0 power, v1 numeric AQI, v3 mode (speed 2 of 4), v4 sleep sub-mode,
# v5 LED fade, v6 beep, v11 child lock, plus an unmapped pin (v7).
PINS = {
    "v0": 1,
    "v1": 7,
    "v3": 2,
    "v4": 1,
    "v5": 1,
    "v6": 0,
    "v7": 71,
    "v11": 0,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components in tests."""
    return


def mock_cloud(aioclient_mock, pins=PINS, online=True):
    aioclient_mock.get(f"{BASE}/isHardwareConnected", text="true" if online else "false")
    aioclient_mock.get(f"{BASE}/getAll", json=pins)
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
    # (v7 here), while mapped pins (v1, v3, ...) do not.
    assert hass.states.get("sensor.windmill_air_quality_index").state == "7"  # v1
    assert hass.states.get("sensor.windmill_pin_v7").state == "71"
    assert hass.states.get("sensor.windmill_pin_v3") is None
    assert hass.states.get("sensor.windmill_pin_v1") is None


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
