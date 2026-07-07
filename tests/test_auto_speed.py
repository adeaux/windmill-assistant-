"""Unit tests for the pure AQI -> speed mapping used by the "auto" preset."""

import pytest

from custom_components.windmill_air.fan import auto_target_speed

# Default 4-speed device thresholds and dead-band.
THRESHOLDS = [50, 100, 150]
SPEED_COUNT = 4
HYST = 10


@pytest.mark.parametrize(
    ("aqi", "expected"),
    [
        (0, 1),
        (49, 1),
        (50, 2),  # at the boundary -> steps up
        (99, 2),
        (100, 3),
        (149, 3),
        (150, 4),
        (500, 4),  # clamped to speed_count
    ],
)
def test_bands_map_to_speeds(aqi, expected):
    # current=None: first engage, hysteresis does not apply.
    assert auto_target_speed(aqi, THRESHOLDS, SPEED_COUNT, None, HYST) == expected


def test_steps_up_at_threshold_no_dead_band():
    # Rising: step up as soon as the AQI reaches the threshold (100), not 100+hyst.
    assert auto_target_speed(99, THRESHOLDS, SPEED_COUNT, 2, HYST) == 2   # below -> holds
    assert auto_target_speed(100, THRESHOLDS, SPEED_COUNT, 2, HYST) == 3  # at threshold -> steps


def test_hysteresis_holds_stepping_down():
    # Boundary between speed 2 and 3 is 100; need < 90 to step down from 3.
    assert auto_target_speed(95, THRESHOLDS, SPEED_COUNT, 3, HYST) == 3  # holds
    assert auto_target_speed(89, THRESHOLDS, SPEED_COUNT, 3, HYST) == 2  # steps


def test_hysteresis_is_downward_only():
    # At exactly 100 the up-point and the resting band agree (speed 3), but once
    # there it won't drop back to 2 until the AQI falls below 90 -> no flapping.
    assert auto_target_speed(100, THRESHOLDS, SPEED_COUNT, 2, HYST) == 3  # up at 100
    assert auto_target_speed(95, THRESHOLDS, SPEED_COUNT, 3, HYST) == 3   # sticky down
    assert auto_target_speed(90, THRESHOLDS, SPEED_COUNT, 3, HYST) == 3   # still holds
    assert auto_target_speed(89, THRESHOLDS, SPEED_COUNT, 3, HYST) == 2   # releases


def test_large_jump_moves_multiple_speeds():
    # A big AQI spike jumps straight to the top speed once past the dead-band.
    assert auto_target_speed(300, THRESHOLDS, SPEED_COUNT, 1, HYST) == 4


def test_no_thresholds_is_safe():
    assert auto_target_speed(200, [], SPEED_COUNT, 3, HYST) == 1


def test_speed_count_above_thresholds_does_not_index_error():
    # 6 speeds but only 3 thresholds: high seeds must not raise.
    assert auto_target_speed(0, THRESHOLDS, 6, 6, HYST) == 1
