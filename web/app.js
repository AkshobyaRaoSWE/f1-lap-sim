"use strict";

// F1 lap-time visualizer. Pulls a speed profile from the Python backend
// (/api/simulate), draws the track coloured by speed, and animates a car that
// physically slows in the corners because it moves at the simulated speed.

const canvas = document.getElementById("track");
const ctx = canvas.getContext("2d");

let sim = null;        // current simulation data
let layout = null;     // canvas transform for the current track
let carS = 0;          // car position as arc length along the lap (m)
let lapClock = 0;      // elapsed lap time (s)
let lastFrame = null;

// Map a normalised speed (0 slow .. 1 fast) to a blue->green->yellow->red colour.
function speedColor(t) {
  const stops = [
    [43, 108, 255], [25, 210, 122], [242, 210, 10], [225, 6, 0],
  ];
  const x = Math.max(0, Math.min(1, t)) * (stops.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const a = stops[i];
  const b = stops[Math.min(i + 1, stops.length - 1)];
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// Work out how to fit the track into the canvas (scale + offset, y flipped).
function computeLayout(points) {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 50;
  const scale = Math.min(
    (canvas.width - 2 * pad) / (maxX - minX),
    (canvas.height - 2 * pad) / (maxY - minY)
  );
  return {
    scale,
    ox: pad - minX * scale + (canvas.width - 2 * pad - (maxX - minX) * scale) / 2,
    oy: canvas.height - (pad - minY * scale) -
        (canvas.height - 2 * pad - (maxY - minY) * scale) / 2,
  };
}

function toScreen(p) {
  return [p[0] * layout.scale + layout.ox, layout.oy - p[1] * layout.scale];
}

// Cumulative arc length so we can place the car by distance travelled.
function arcLengths(points) {
  const s = [0];
  for (let i = 1; i < points.length; i++) {
    const dx = points[i][0] - points[i - 1][0];
    const dy = points[i][1] - points[i - 1][1];
    s.push(s[i - 1] + Math.hypot(dx, dy));
  }
  // close the loop
  const dx = points[0][0] - points[points.length - 1][0];
  const dy = points[0][1] - points[points.length - 1][1];
  s.totalLength = s[s.length - 1] + Math.hypot(dx, dy);
  return s;
}

// Find position + speed at a given arc length (linear interpolation).
function sampleAt(s) {
  const arr = sim.arc;
  const L = arr.totalLength;
  s = ((s % L) + L) % L;
  let i = 0;
  while (i < arr.length - 1 && arr[i + 1] <= s) i++;
  const j = (i + 1) % sim.points.length;
  const segLen = (i + 1 < arr.length ? arr[i + 1] : L) - arr[i];
  const f = segLen > 0 ? (s - arr[i]) / segLen : 0;
  const p = [
    sim.points[i][0] + (sim.points[j][0] - sim.points[i][0]) * f,
    sim.points[i][1] + (sim.points[j][1] - sim.points[i][1]) * f,
  ];
  const v = sim.speed_kph[i] + (sim.speed_kph[j] - sim.speed_kph[i]) * f;
  return { p, v };
}

function drawTrack() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const { speed_kph, points } = sim;
  const lo = Math.min(...speed_kph), hi = Math.max(...speed_kph);

  ctx.lineWidth = 9;
  ctx.lineCap = "round";
  for (let i = 0; i < points.length; i++) {
    const j = (i + 1) % points.length;
    const a = toScreen(points[i]), b = toScreen(points[j]);
    const t = (speed_kph[i] - lo) / Math.max(hi - lo, 1e-6);
    ctx.strokeStyle = speedColor(t);
    ctx.beginPath();
    ctx.moveTo(a[0], a[1]);
    ctx.lineTo(b[0], b[1]);
    ctx.stroke();
  }
}

function drawCar() {
  const { p, v } = sampleAt(carS);
  const s = toScreen(p);
  ctx.beginPath();
  ctx.arc(s[0], s[1], 7, 0, 2 * Math.PI);
  ctx.fillStyle = "#ffffff";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#e10600";
  ctx.stroke();
  document.getElementById("speed").textContent = v.toFixed(0);
  document.getElementById("laptime").textContent = lapClock.toFixed(2);
}

function frame(ts) {
  if (!sim) return;
  if (lastFrame === null) lastFrame = ts;
  const dt = Math.min((ts - lastFrame) / 1000, 0.05);
  lastFrame = ts;

  const { v } = sampleAt(carS);
  const speedMs = v / 3.6;
  const TIME_SCALE = 1.0; // real-time playback
  carS += speedMs * dt * TIME_SCALE;
  lapClock += dt * TIME_SCALE;

  if (carS >= sim.arc.totalLength) {
    carS -= sim.arc.totalLength;
    lapClock = 0;
  }

  drawTrack();
  drawCar();
  requestAnimationFrame(frame);
}

function applySim(data) {
  sim = data;
  sim.arc = arcLengths(data.points);
  layout = computeLayout(data.points);
  carS = 0;
  lapClock = 0;
  lastFrame = null;
  document.getElementById("topspeed").textContent = data.top_speed_kph.toFixed(0);
  document.getElementById("hint").textContent =
    `lap ${data.lap_time.toFixed(2)} s on the ${data.track}`;
  requestAnimationFrame(frame);
}

async function runLap() {
  const params = new URLSearchParams({
    track: document.getElementById("trackSel").value,
    grip: document.getElementById("grip").value,
    power: document.getElementById("power").value * 1000,
    mass: document.getElementById("mass").value,
    drag: document.getElementById("drag").value,
  });
  document.getElementById("hint").textContent = "simulating...";
  try {
    const res = await fetch("/api/simulate?" + params);
    if (!res.ok) throw new Error((await res.json()).error || "request failed");
    applySim(await res.json());
  } catch (err) {
    // Static-hosting fallback: load the pre-generated default lap.
    try {
      const res = await fetch("data.json");
      applySim(await res.json());
      document.getElementById("hint").textContent =
        "showing default lap (run server.py for live parameters)";
    } catch {
      document.getElementById("hint").textContent = "error: " + err.message;
    }
  }
}

// Wire up the live slider read-outs.
["grip", "power", "mass", "drag"].forEach((id) => {
  const el = document.getElementById(id);
  const out = document.getElementById(id + "Out");
  el.addEventListener("input", () => { out.textContent = el.value; });
});
document.getElementById("run").addEventListener("click", runLap);

runLap();
