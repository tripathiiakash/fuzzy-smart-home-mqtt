"""
simulation.py
-------------
Virtual sensors: generates one realistic day of readings for a living room
(a hot, humid Patna-style day) at 5-minute intervals.

    temperature : 24-36 °C, coolest ~3 am, hottest ~3 pm
    humidity    : opposite of temperature (humid at night, drier in afternoon)
    light       : ambient daylight in the room (lux) with passing clouds
    occupancy   : number of people in the room, follows a family daily routine
"""
import numpy as np

STEP_MIN = 5


def occupancy_schedule(hour):
    """Typical family routine for the living room (people count)."""
    if hour < 6.5:   return 0          # night, living room empty
    if hour < 8.5:   return 2          # morning tea / breakfast
    if hour < 12.5:  return 0          # everyone out (college / work)
    if hour < 14.0:  return 1          # one person home for lunch
    if hour < 17.0:  return 0
    if hour < 18.5:  return 2          # evening return
    if hour < 19.5:  return 4          # family time
    if hour < 21.5:  return 5          # guests / dinner
    if hour < 22.5:  return 3
    return 1                            # winding down


def generate_day(seed=42, step_min=STEP_MIN):
    rng = np.random.default_rng(seed)
    hours = np.arange(0, 24, step_min / 60.0)
    n = len(hours)

    # slow random drift (AR(1)) so the data is not a perfect sine wave
    def drift(scale):
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.95 * x[i - 1] + rng.normal(0, scale)
        return x

    temp = 30 + 6 * np.sin(2 * np.pi * (hours - 9) / 24) + drift(0.15)
    hum = 60 - 22 * np.sin(2 * np.pi * (hours - 9) / 24) + drift(0.6)

    daylight = np.clip(np.sin(np.pi * (hours - 6) / 12), 0, None) ** 1.2
    clouds = np.clip(1 - 0.8 * np.abs(drift(0.12)), 0.45, 1.0)
    lux = 850 * daylight * clouds

    occ = np.array([occupancy_schedule(h) for h in hours], dtype=float)
    jitter = rng.choice([-1, 0, 0, 0, 0, 1], size=n)          # people drift in/out
    occ = np.clip(occ + np.where(occ > 0, jitter, 0), 0, 6)

    return {
        "hour": hours,
        "temp": np.clip(temp, 10, 45),
        "hum": np.clip(hum, 5, 98),
        "lux": np.clip(lux, 0, 1000),
        "occ": occ,
    }


def hhmm(hour):
    h = int(hour)
    m = int(round((hour - h) * 60)) % 60
    return f"{h:02d}:{m:02d}"


if __name__ == "__main__":
    d = generate_day()
    for i in range(0, len(d["hour"]), 24):          # print every 2 hours
        print(hhmm(d["hour"][i]), f"T={d['temp'][i]:.1f}  H={d['hum'][i]:.0f}  "
              f"L={d['lux'][i]:.0f}  occ={int(d['occ'][i])}")
