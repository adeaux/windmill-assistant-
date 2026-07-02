"""End-to-end tests for the Windmill Air Purifier integration (mocked cloud)."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.windmill_air.const import DOMAIN

BASE = "https://dashboard.windmillair.com/external/api"
TOKEN = "test-token-123"

PINS = {"v0": 1, "v1": 3, "v2": 42, "v5": 0, "v7": "some text"}


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


async def test_entities_created(hass: HomeAssistant, aioclient_mock) -> None:
    await _setup_entry(hass, aioclient_mock)

    fan = hass.states.get("fan.windmill")
    assert fan is not None
    assert fan.state == "on"  # v0 == 1
    assert fan.attributes["percentage"] == 60  # v1 == 3 of 5 speeds

    aqi = hass.states.get("sensor.windmill_air_quality_index")
    assert aqi is not None
    assert aqi.state == "42"  # v2

    # Unmapped pins (v5, v7) become diagnostic sensors
    assert hass.states.get("sensor.windmill_pin_v5").state == "0"
    assert hass.states.get("sensor.windmill_pin_v7").state == "some text"
    # Mapped pins do not
    assert hass.states.get("sensor.windmill_pin_v0") is None


async def test_fan_commands(hass: HomeAssistant, aioclient_mock) -> None:
    await _setup_entry(hass, aioclient_mock)

    # The post-write refresh polls getAll again; serve the post-write state.
    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v0": 0})
    await hass.services.async_call(
        "fan", "turn_off", {"entity_id": "fan.windmill"}, blocking=True
    )
    update_calls = [c for c in aioclient_mock.mock_calls if "update" in str(c[1])]
    assert any("v0=0" in str(c[1].query_string) for c in update_calls)
    assert hass.states.get("fan.windmill").state == "off"

    aioclient_mock.clear_requests()
    mock_cloud(aioclient_mock, pins={**PINS, "v1": 5})
    await hass.services.async_call(
        "fan",
        "set_percentage",
        {"entity_id": "fan.windmill", "percentage": 100},
        blocking=True,
    )
    update_calls = [c for c in aioclient_mock.mock_calls if "update" in str(c[1])]
    assert any("v1=5" in str(c[1].query_string) for c in update_calls)
    assert hass.states.get("fan.windmill").attributes["percentage"] == 100


async def test_switches_and_presets_from_options(
    hass: HomeAssistant, aioclient_mock
) -> None:
    await _setup_entry(
        hass,
        aioclient_mock,
        options={"child_lock_pin": "v5", "auto_pin": "v6", "display_light_pin": ""},
    )
    assert hass.states.get("switch.windmill_child_lock").state == "off"  # v5 == 0
    assert hass.states.get("switch.windmill_display_light") is None
    fan = hass.states.get("fan.windmill")
    assert fan.attributes["preset_modes"] == ["Auto"]


async def test_device_offline_marks_unavailable(
    hass: HomeAssistant, aioclient_mock
) -> None:
    mock_cloud(aioclient_mock, online=False)
    entry = MockConfigEntry(domain=DOMAIN, data={"token": TOKEN}, title="Windmill")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("fan.windmill").state == "unavailable"
