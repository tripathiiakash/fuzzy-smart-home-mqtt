"""
dashboard.py  -  live Matplotlib dashboard (MQTT subscriber)
------------------------------------------------------------
Subscribes to everything under <ROOT>/ and plots sensor readings (left) and
the fuzzy controller's actuator commands (right), updating live.

Run:   python dashboard.py              # live, needs a broker + sensors.py + controller.py
       python dashboard.py --selftest   # no broker: draws fake data to dashboard_selftest.png
"""
import argparse
import json
import os
from collections import defaultdict, deque

import matplotlib
import numpy as np

import config

SENSOR_PANELS = [("temperature", "Temperature (°C)"), ("humidity", "Humidity (%)"),
                 ("light", "Light intensity (lux)"), ("occupancy", "Occupancy (people)")]
ACTUATOR_PANELS = [("fan", "Fan speed (%)"), ("ac", "AC power (%)"), ("light", "Light brightness (%)")]
BLUE, INK2, GRID, SURFACE = "#2a78d6", "#52514e", "#e3e2de", "#fcfcfb"
MAXLEN = 300


class DashboardState:
    """Stores the last MAXLEN values of every topic (filled by the MQTT thread)."""

    def __init__(self):
        self.data = defaultdict(lambda: deque(maxlen=MAXLEN))
        self.stamp = ""

    def update(self, topic, payload):
        kind, name = topic.split("/")[-2:]                 # ".../sensors/temperature"
        self.data[(kind, name)].append(float(payload["value"]))
        self.stamp = payload.get("time", self.stamp)


def build_figure(plt):
    fig, axes = plt.subplots(4, 2, figsize=(13, 8.5))
    fig.patch.set_facecolor(SURFACE)
    lines = {}
    for row, (name, title) in enumerate(SENSOR_PANELS):
        ax = axes[row, 0]
        (lines[("sensors", name)],) = ax.plot([], [], color=INK2, lw=1.6)
        ax.set_title(title, loc="left", fontweight="bold", fontsize=10)
    for row, (name, title) in enumerate(ACTUATOR_PANELS):
        ax = axes[row, 1]
        (lines[("actuators", name)],) = ax.plot([], [], color=BLUE, lw=2)
        ax.set_title(title, loc="left", fontweight="bold", fontsize=10)
        ax.set_ylim(-5, 105)
    axes[3, 1].axis("off")
    for ax in axes.flat:
        if ax.axison:
            ax.set_facecolor(SURFACE)
            ax.grid(True, color=GRID)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
    title = fig.suptitle("Fuzzy smart home - live", x=0.01, ha="left", fontweight="bold")
    return fig, axes, lines, title


def redraw(state, axes, lines, title):
    for key, line in lines.items():
        ys = list(state.data.get(key, []))
        line.set_data(range(len(ys)), ys)
    for ax in axes.flat:
        if ax.axison:
            ax.relim()
            ax.autoscale_view(scalex=True, scaley=ax.get_ylim() != (-5, 105))
            ax.set_xlim(0, MAXLEN)
    title.set_text(f"Fuzzy smart home - live   (simulated time {state.stamp})")


def selftest():
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import fuzzy_system as fs
    from simulation import generate_day, hhmm

    state, day = DashboardState(), generate_day()
    for i, h in enumerate(day["hour"][:MAXLEN]):
        vals = {"temperature": day["temp"][i], "humidity": day["hum"][i],
                "light": day["lux"][i], "occupancy": day["occ"][i]}
        for n, v in vals.items():
            state.update(config.sensor_topic(n), {"value": v, "time": hhmm(h)})
        out = fs.decide(vals["temperature"], vals["humidity"], vals["light"], vals["occupancy"])
        for n, v in out.items():
            state.update(config.actuator_topic(n), {"value": v, "time": hhmm(h)})
    fig, axes, lines, title = build_figure(plt)
    redraw(state, axes, lines, title)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "dashboard_selftest.png")
    fig.savefig(path, dpi=110)
    print("saved", path)


def live():
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    state = DashboardState()
    client = config.make_client("dashboard")

    def on_connect(client, userdata, flags, rc, props=None):
        client.subscribe(f"{config.ROOT}/#")

    def on_message(client, userdata, msg):
        try:
            state.update(msg.topic, json.loads(msg.payload.decode()))
        except (ValueError, KeyError):
            pass

    client.on_connect, client.on_message = on_connect, on_message
    client.connect(config.BROKER, config.PORT, keepalive=60)
    client.loop_start()

    fig, axes, lines, title = build_figure(plt)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _anim = FuncAnimation(fig, lambda _: redraw(state, axes, lines, title),
                          interval=500, cache_frame_data=False)
    try:
        plt.show()
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    selftest() if ap.parse_args().selftest else live()
