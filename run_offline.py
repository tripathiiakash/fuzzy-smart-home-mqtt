"""
run_offline.py
--------------
Runs the whole project WITHOUT an MQTT broker: simulates a day, runs the fuzzy
controllers and the if-else baseline, and produces every graph + the results
table for the report. Run this first - it always works.

    python run_offline.py

Outputs go to ./outputs/
    membership_functions.png   input/output membership functions
    control_surface.png        fan speed vs temperature & humidity (3-D)
    day_simulation.png         sensors and actuator decisions over 24 h
    comparison.png             fuzzy vs threshold: energy and switching
    results.csv, comparison.txt
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fuzzy_system as fs
from simulation import STEP_MIN, generate_day

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUT, exist_ok=True)

# Validated categorical palette (slot 1 blue = fuzzy, slot 2 orange = threshold)
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2de", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.titlecolor": INK, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "font.size": 10,
    "legend.frameon": False,
})

# Appliance ratings used for the energy estimate (assumption: power scales with level)
WATTS = {"fan": 75, "ac": 1500, "light": 40}
DT_H = STEP_MIN / 60.0


# ----------------------------------------------------------------------------
def run_day():
    d = generate_day()
    n = len(d["hour"])
    fuzzy = {k: np.zeros(n) for k in WATTS}
    base = {k: np.zeros(n) for k in WATTS}
    for i in range(n):
        args = (d["temp"][i], d["hum"][i], d["lux"][i], d["occ"][i])
        f, b = fs.decide(*args), fs.threshold_decide(*args)
        for k in WATTS:
            fuzzy[k][i], base[k][i] = f[k], b[k]
    return d, fuzzy, base


def metrics(d, out):
    empty = d["occ"] < 1
    res = {}
    for k, w in WATTS.items():
        kwh = (out[k] / 100.0 * w * DT_H).sum() / 1000.0
        kwh_empty = (out[k][empty] / 100.0 * w * DT_H).sum() / 1000.0
        change = np.abs(np.diff(out[k])).mean()
        # ON/OFF toggles: crossings of the 5 % "on" line
        on = out[k] >= 5
        toggles = int(np.sum(on[1:] != on[:-1]))
        res[k] = {"kWh": kwh, "kWh_empty": kwh_empty, "mean_change": change, "toggles": toggles}
    total = sum(v["kWh"] for v in res.values())
    total_empty = sum(v["kWh_empty"] for v in res.values())
    return res, total, total_empty


# ----------------------------------------------------------------------------
def plot_membership():
    variables = [fs.TEMP, fs.HUM, fs.OCC, fs.LUX, fs.FAN]
    titles = ["Temperature (°C)", "Humidity (%)", "Occupancy (people)",
              "Light intensity (lux)", "Output level (%) - fan, AC, light"]
    colors = [BLUE, ORANGE, "#1baf7a", "#6250d6"]       # fixed slot order
    fig, axes = plt.subplots(1, 5, figsize=(18, 3.4))
    for ax, v, t in zip(axes, variables, titles):
        for (term, _), c in zip(v.params.items(), colors):
            ax.plot(v.universe, v.mf(term), lw=2, color=c, label=term)
        ax.set_title(t)
        ax.set_ylim(-0.02, 1.5)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_ylabel("membership")
        ax.legend(loc="upper center", ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "membership_functions.png"), dpi=150)
    plt.close(fig)


def plot_surface():
    temps = np.linspace(15, 42, 28)
    hums = np.linspace(10, 95, 28)
    T, H = np.meshgrid(temps, hums)
    Z = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            Z[i, j] = fs.fan_controller(temp=T[i, j], hum=H[i, j], occ=3)
    fig = plt.figure(figsize=(7.5, 5.5))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(T, H, Z, cmap="Blues", edgecolor="none", alpha=0.95)
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Humidity (%)")
    ax.set_zlabel("Fan speed (%)")
    ax.set_title("Fan control surface (3 people in the room)")
    fig.colorbar(surf, shrink=0.6, pad=0.1, label="fan %")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "control_surface.png"), dpi=150)
    plt.close(fig)


def hour_axis(ax):
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])


def plot_day(d, fuzzy, base):
    h = d["hour"]
    fig, axes = plt.subplots(4, 2, figsize=(14, 10), sharex=True)
    sensors = [("temp", "Temperature (°C)"), ("hum", "Humidity (%)"),
               ("lux", "Light intensity (lux)"), ("occ", "Occupancy (people)")]
    for ax, (k, t) in zip(axes[:, 0], sensors):
        if k == "occ":
            ax.step(h, d[k], where="post", color=INK2, lw=1.6)
        else:
            ax.plot(h, d[k], color=INK2, lw=1.6)
        ax.set_title(t)
    outs = [("fan", "Fan speed (%)"), ("ac", "AC power (%)"), ("light", "Light brightness (%)")]
    for ax, (k, t) in zip(axes[:3, 1], outs):
        ax.plot(h, fuzzy[k], color=BLUE, lw=2, label="Fuzzy controller")
        ax.step(h, base[k], where="post", color=ORANGE, lw=1.6, label="If-else threshold")
        ax.set_ylim(-5, 105)
        ax.set_title(t)
    handles, labels = axes[0, 1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.99, 0.985), ncol=2)
    axes[3, 1].axis("off")
    for ax in axes.flat[:]:
        if ax.axison:
            hour_axis(ax)
    axes[2, 1].tick_params(labelbottom=True)      # bottom visible panel of right column
    fig.suptitle("One simulated day: sensor inputs (left) and controller decisions (right)",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(os.path.join(OUT, "day_simulation.png"), dpi=150)
    plt.close(fig)


def plot_comparison(rf, tf, rb, tb):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    x = np.arange(3)
    w = 0.36
    labels = ["Fan", "AC", "Lights"]
    keys = ["fan", "ac", "light"]

    def bars(ax, key, title, ylabel, fmt):
        vf = [rf[k][key] for k in keys]
        vb = [rb[k][key] for k in keys]
        b1 = ax.bar(x - w / 2 - 0.01, vf, w - 0.02, color=BLUE, label="Fuzzy", zorder=3)
        b2 = ax.bar(x + w / 2 + 0.01, vb, w - 0.02, color=ORANGE, label="If-else threshold", zorder=3)
        for bars_, vals in ((b1, vf), (b2, vb)):
            for r, v in zip(bars_, vals):
                ax.text(r.get_x() + r.get_width() / 2, r.get_height(), fmt.format(v),
                        ha="center", va="bottom", fontsize=8, color=INK2)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.margins(y=0.15)

    bars(axes[0], "kWh", "Energy used over the day", "kWh", "{:.2f}")
    bars(axes[1], "mean_change", "Average output jump per 5 min (lower = smoother)", "% points", "{:.1f}")
    bars(axes[2], "toggles", "ON/OFF switch events (lower = less wear)", "count", "{:.0f}")
    axes[0].legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "comparison.png"), dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------
def main():
    d, fuzzy, base = run_day()
    rf, tf, ef = metrics(d, fuzzy)
    rb, tb, eb = metrics(d, base)

    with open(os.path.join(OUT, "results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "temp", "hum", "lux", "occ",
                    "fuzzy_fan", "fuzzy_ac", "fuzzy_light",
                    "thr_fan", "thr_ac", "thr_light"])
        for i in range(len(d["hour"])):
            hh, mm = int(d["hour"][i]), int(round((d["hour"][i] % 1) * 60))
            w.writerow([f"{hh:02d}:{mm:02d}", f"{d['temp'][i]:.1f}", f"{d['hum'][i]:.0f}",
                        f"{d['lux'][i]:.0f}", int(d["occ"][i]),
                        fuzzy["fan"][i], fuzzy["ac"][i], fuzzy["light"][i],
                        base["fan"][i], base["ac"][i], base["light"][i]])

    lines = []
    lines.append("FUZZY vs IF-ELSE THRESHOLD CONTROLLER - one simulated day (5-min steps)")
    lines.append("Energy assumes appliance power scales with its output level "
                 "(fan 75 W, AC 1500 W, light 40 W at 100 %).")
    lines.append("")
    lines.append(f"{'':8}{'kWh fuzzy':>11}{'kWh thr.':>10}{'jump fuzzy':>12}{'jump thr.':>11}"
                 f"{'toggles F':>11}{'toggles T':>11}")
    for k in WATTS:
        lines.append(f"{k:8}{rf[k]['kWh']:11.2f}{rb[k]['kWh']:10.2f}"
                     f"{rf[k]['mean_change']:12.1f}{rb[k]['mean_change']:11.1f}"
                     f"{rf[k]['toggles']:11d}{rb[k]['toggles']:11d}")
    lines.append("")
    lines.append(f"Total energy   : fuzzy {tf:.2f} kWh   threshold {tb:.2f} kWh   "
                 f"difference {100 * (tb - tf) / tb:+.1f} % saved by fuzzy")
    lines.append(f"Energy while room empty: fuzzy {ef:.2f} kWh   threshold {eb:.2f} kWh")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(OUT, "comparison.txt"), "w") as f:
        f.write(text + "\n")

    plot_membership()
    plot_surface()
    plot_day(d, fuzzy, base)
    plot_comparison(rf, tf, rb, tb)
    print(f"\nSaved graphs and tables to {OUT}")


if __name__ == "__main__":
    main()
