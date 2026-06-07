"""Flask backend: serves the web UI and a /api/simulate endpoint.

The browser sends the car parameters from the sliders; this runs the lap-time
simulation and returns the track geometry plus the speed profile as JSON. Run:

    python server.py    ->    open http://localhost:5000
"""

from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory

from lapsim import Vehicle, load_track, simulate_lap

app = Flask(__name__, static_folder="web", static_url_path="")


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/api/simulate")
def api_simulate():
    """Run a lap and return geometry + speed profile for the given car/track."""
    try:
        track = load_track(request.args.get("track", "circuit"))
        vehicle = Vehicle(
            mass=float(request.args.get("mass", 798)),
            grip=float(request.args.get("grip", 3.5)),
            power=float(request.args.get("power", 735_000)),
            drag_area=float(request.args.get("drag", 1.10)),
        )
        result = simulate_lap(track, vehicle)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    return jsonify({
        "track": track.name,
        "points": track.points.tolist(),
        "speed_kph": result.speed_kph.tolist(),
        "lap_time": result.lap_time,
        "top_speed_kph": result.top_speed * 3.6,
        "min_speed_kph": result.min_speed * 3.6,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
