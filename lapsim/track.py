"""Track geometry: a closed centerline with curvature and arc length.

A lap-time simulation needs three things from the track at every point: where it
is, how far along the lap it is (arc length `s`), and how sharply it bends
(curvature `kappa`). Cornering speed is set entirely by curvature, so it has to
be smooth -- raw waypoints would give spiky, unusable curvature. We run the
control points through a closed Catmull-Rom spline first, which passes through
every control point while staying smooth in between.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Control points (rough corner markers) for a few built-in circuits. The spline
# smooths them into a drivable centerline.
CIRCUITS: dict[str, list[tuple[float, float]]] = {
    # A simple rounded oval -- the sanity-check track.
    "oval": [
        (-120, -50), (120, -50), (160, 0), (120, 50), (-120, 50), (-160, 0),
    ],
    # A stylized road course with a mix of fast and slow corners.
    "circuit": [
        (0, 0), (140, 0), (200, 40), (200, 120), (140, 150), (60, 130),
        (40, 80), (-40, 90), (-120, 70), (-180, 110), (-200, 40),
        (-150, -40), (-60, -30), (-20, -70), (40, -60),
    ],
}


@dataclass
class Track:
    """A closed track centerline sampled at roughly even arc length."""

    name: str
    points: np.ndarray      # (N, 2) centerline points
    s: np.ndarray           # (N,) cumulative arc length at each point
    curvature: np.ndarray   # (N,) curvature magnitude (1/m) at each point

    @property
    def length(self) -> float:
        """Total lap length in meters."""
        return float(self.s[-1] + np.hypot(*(self.points[0] - self.points[-1])))


def _catmull_rom_closed(ctrl: np.ndarray, samples_per_seg: int = 40) -> np.ndarray:
    """Sample a closed Catmull-Rom spline through the control points."""
    n = len(ctrl)
    out = []
    for i in range(n):
        p0 = ctrl[(i - 1) % n]
        p1 = ctrl[i]
        p2 = ctrl[(i + 1) % n]
        p3 = ctrl[(i + 2) % n]
        for j in range(samples_per_seg):
            t = j / samples_per_seg
            t2, t3 = t * t, t * t * t
            # Standard Catmull-Rom basis (tension 0.5).
            out.append(0.5 * (
                (2 * p1)
                + (-p0 + p2) * t
                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
            ))
    return np.asarray(out)


def _menger_curvature(points: np.ndarray) -> np.ndarray:
    """Curvature at each point from the circle through its two neighbors."""
    n = len(points)
    kappa = np.zeros(n)
    for i in range(n):
        a = points[(i - 1) % n]
        b = points[i]
        c = points[(i + 1) % n]
        ab = np.hypot(*(b - a))
        bc = np.hypot(*(c - b))
        ca = np.hypot(*(a - c))
        # Twice the signed triangle area via the cross product.
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        denom = ab * bc * ca
        kappa[i] = (2.0 * area) / denom if denom > 1e-9 else 0.0
    return kappa


def load_track(name: str = "circuit", samples_per_seg: int = 40) -> Track:
    """Build a Track by name from the built-in circuits."""
    if name not in CIRCUITS:
        raise ValueError(f"unknown track '{name}'; choose from {list(CIRCUITS)}")

    ctrl = np.asarray(CIRCUITS[name], dtype=float)
    pts = _catmull_rom_closed(ctrl, samples_per_seg)

    # Cumulative arc length along the (closed) centerline.
    seg = np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(seg)])

    kappa = _menger_curvature(pts)
    return Track(name=name, points=pts, s=s, curvature=kappa)
