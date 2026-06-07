"""Quasi-steady-state (QSS) lap-time simulation.

This is the classic first-order lap sim used in motorsport. The car is a point
mass limited by a *friction circle*: the tyres have a fixed total grip budget
shared between cornering and accelerating/braking. The lap speed profile comes
from three limits combined:

  1. Corner speed   -- how fast you can hold each corner: mu*g = v^2 * kappa.
  2. Acceleration   -- you can't speed up faster than grip + engine allow.
  3. Braking        -- you must already be slow enough to brake for the next corner.

A forward pass applies the acceleration limit, a backward pass applies the
braking limit, and we iterate the two around the closed loop until the speed
profile stops changing. Integrating dt = ds / v around the lap gives the time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .track import Track
from .vehicle import GRAVITY, Vehicle


@dataclass
class LapResult:
    speed: np.ndarray       # (N,) speed at each centerline point (m/s)
    s: np.ndarray           # (N,) arc length at each point (m)
    lap_time: float         # seconds
    top_speed: float        # m/s
    min_speed: float        # m/s (slowest corner)

    @property
    def speed_kph(self) -> np.ndarray:
        return self.speed * 3.6


def _segment_lengths(track: Track) -> np.ndarray:
    """Distance from each point to the next, wrapping around the closed loop."""
    pts = track.points
    nxt = np.roll(pts, -1, axis=0)
    return np.hypot(nxt[:, 0] - pts[:, 0], nxt[:, 1] - pts[:, 1])


def simulate_lap(track: Track, vehicle: Vehicle, iterations: int = 6) -> LapResult:
    """Compute the speed profile and lap time for a car on a track."""
    n = len(track.points)
    kappa = np.abs(track.curvature)
    ds = _segment_lengths(track)
    lat_max = vehicle.lateral_accel_max
    v_top = vehicle.top_speed()

    # Limit 1: the most speed each corner can physically hold.
    v_corner = np.where(kappa > 1e-6, np.sqrt(lat_max / np.maximum(kappa, 1e-9)), v_top)
    v_corner = np.minimum(v_corner, v_top)

    v = v_corner.copy()

    def accel_limit(speed: float, k: float) -> float:
        """Longitudinal accel available when already pulling lateral g (m/s^2)."""
        a_lat = speed * speed * k
        grip_long = np.sqrt(max(lat_max ** 2 - a_lat ** 2, 0.0))
        thrust = vehicle.power / max(speed, 1.0) - vehicle.drag_force(speed)
        engine_long = thrust / vehicle.mass
        return max(min(grip_long, engine_long), 0.0)

    def brake_limit(speed: float, k: float) -> float:
        """Longitudinal deceleration available at a given lateral load (m/s^2)."""
        a_lat = speed * speed * k
        grip_long = np.sqrt(max((vehicle.brake_grip * GRAVITY) ** 2 - a_lat ** 2, 0.0))
        return grip_long + vehicle.drag_force(speed) / vehicle.mass

    # Iterate forward (accel) and backward (braking) passes until convergence.
    for _ in range(iterations):
        for i in range(n):
            j = (i + 1) % n
            reachable = np.sqrt(v[i] ** 2 + 2.0 * accel_limit(v[i], kappa[i]) * ds[i])
            v[j] = min(v[j], reachable, v_corner[j])
        for i in range(n - 1, -1, -1):
            j = (i + 1) % n
            stoppable = np.sqrt(v[j] ** 2 + 2.0 * brake_limit(v[i], kappa[i]) * ds[i])
            v[i] = min(v[i], stoppable, v_corner[i])

    # Lap time: integrate dt = ds / average segment speed.
    v_avg = 0.5 * (v + np.roll(v, -1))
    lap_time = float(np.sum(ds / np.maximum(v_avg, 0.1)))

    return LapResult(
        speed=v,
        s=track.s,
        lap_time=lap_time,
        top_speed=float(v.max()),
        min_speed=float(v.min()),
    )
