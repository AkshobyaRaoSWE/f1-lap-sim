"""Generate the static fallback data and the README demo image.

  * web/data.json  -- a default lap so the web UI animates even on static
    hosting (GitHub Pages) where the Python backend isn't running.
  * assets/demo.png -- the track coloured by speed, for the README.

Run after changing the model:  python generate_data.py
"""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

from lapsim import Vehicle, load_track, simulate_lap

TRACK = "circuit"


def write_json() -> None:
    track = load_track(TRACK)
    result = simulate_lap(track, Vehicle())
    data = {
        "track": track.name,
        "points": track.points.tolist(),
        "speed_kph": result.speed_kph.tolist(),
        "lap_time": result.lap_time,
        "top_speed_kph": result.top_speed * 3.6,
        "min_speed_kph": result.min_speed * 3.6,
    }
    with open("web/data.json", "w") as f:
        json.dump(data, f)
    print(f"wrote web/data.json (lap {result.lap_time:.2f} s)")


def write_demo() -> None:
    track = load_track(TRACK)
    result = simulate_lap(track, Vehicle())
    pts = track.points
    speed = result.speed_kph

    # Build coloured segments of the track.
    segs = np.concatenate([pts[:, None, :], np.roll(pts, -1, axis=0)[:, None, :]], axis=1)
    lc = LineCollection(segs, cmap="turbo", linewidth=5)
    lc.set_array(speed)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.add_collection(lc)
    ax.autoscale()
    ax.set_aspect("equal")
    ax.set_title(f"Speed around the lap  |  {result.lap_time:.2f} s  |  "
                 f"top {result.top_speed*3.6:.0f} kph")
    ax.axis("off")
    cbar = fig.colorbar(lc, ax=ax, shrink=0.8)
    cbar.set_label("speed (kph)")
    fig.tight_layout()
    fig.savefig("assets/demo.png", dpi=130)
    print("wrote assets/demo.png")


if __name__ == "__main__":
    write_json()
    write_demo()
