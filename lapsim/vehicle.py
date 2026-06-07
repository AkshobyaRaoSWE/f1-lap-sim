"""Vehicle model: the grip, power and drag limits that bound the car.

These are the knobs an F1 engineer actually trades off. Defaults are loosely
F1-like (a ~800 kg car, huge downforce giving grip well above 1 g, ~735 kW).
"""

from __future__ import annotations

from dataclasses import dataclass

GRAVITY = 9.81  # m/s^2


@dataclass
class Vehicle:
    """Performance envelope of the car.

    Attributes:
        mass: car + driver mass (kg).
        grip: peak tyre grip as a multiple of g. F1 with downforce reaches 4-5 g
            in fast corners; a road car is around 1 g.
        power: peak engine power (W). Caps acceleration at high speed.
        drag_area: 0.5 * rho * Cd * A lumped (kg/m). Sets top speed and slows
            acceleration as speed rises.
        brake_grip: peak braking as a multiple of g (tyres + aero usually allow a
            bit more than cornering grip).
    """

    mass: float = 798.0
    grip: float = 3.5
    power: float = 735_000.0
    drag_area: float = 1.10
    brake_grip: float = 4.5

    @property
    def lateral_accel_max(self) -> float:
        """Maximum sustainable lateral acceleration (m/s^2)."""
        return self.grip * GRAVITY

    def drag_force(self, speed: float) -> float:
        """Aerodynamic drag force at a given speed (N)."""
        return self.drag_area * speed * speed

    def top_speed(self) -> float:
        """Speed where engine thrust equals drag: power/v = drag_area*v^2."""
        return (self.power / self.drag_area) ** (1.0 / 3.0)
