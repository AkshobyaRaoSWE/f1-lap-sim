"""Tests for the lap-time simulation.

Run with:  python -m pytest   (or: python tests/test_lap.py)
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lapsim import Vehicle, load_track, simulate_lap  # noqa: E402


def test_tracks_are_closed_and_smooth():
    """Both built-in tracks load with matching point/curvature arrays."""
    for name in ("oval", "circuit"):
        t = load_track(name)
        assert len(t.points) == len(t.curvature) == len(t.s)
        assert t.length > 0


def test_more_grip_is_faster():
    """Higher tyre grip can only lower the lap time."""
    t = load_track("circuit")
    slow = simulate_lap(t, Vehicle(grip=2.0)).lap_time
    fast = simulate_lap(t, Vehicle(grip=4.5)).lap_time
    assert fast < slow


def test_more_power_is_faster():
    """More engine power can only lower the lap time."""
    t = load_track("circuit")
    base = simulate_lap(t, Vehicle(power=500_000)).lap_time
    more = simulate_lap(t, Vehicle(power=900_000)).lap_time
    assert more < base


def test_car_slows_in_corners():
    """The slowest point of the lap must be well below the top speed."""
    t = load_track("circuit")
    r = simulate_lap(t, Vehicle())
    assert r.min_speed < 0.7 * r.top_speed


def test_speed_never_exceeds_corner_limit():
    """No point may exceed the grip-limited cornering speed there."""
    t = load_track("circuit")
    v = Vehicle()
    r = simulate_lap(t, v)
    kappa = np.abs(t.curvature)
    lat_max = v.lateral_accel_max
    cornering = np.where(kappa > 1e-6, np.sqrt(lat_max / np.maximum(kappa, 1e-9)),
                         v.top_speed())
    # allow a tiny numerical margin
    assert np.all(r.speed <= np.minimum(cornering, v.top_speed()) + 1e-6)


def test_unknown_track_raises():
    try:
        load_track("monaco")
    except ValueError:
        return
    raise AssertionError("expected ValueError for an unknown track")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
