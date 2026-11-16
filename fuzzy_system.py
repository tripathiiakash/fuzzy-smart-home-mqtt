"""
fuzzy_system.py
---------------
A small Mamdani fuzzy inference engine written from scratch with NumPy, plus
the three controllers of the smart home (fan, AC, lighting).

Pipeline for every controller (this is what you explain in the viva):
    1. FUZZIFICATION    crisp sensor value  -> membership degree of each term
    2. RULE EVALUATION  AND = min of the antecedent memberships
    3. IMPLICATION      clip the output term at the rule's firing strength (min)
    4. AGGREGATION      combine all clipped output shapes with max
    5. DEFUZZIFICATION  centroid (centre of gravity) -> crisp output 0-100 %

Controllers
    fan   : temperature + humidity + occupancy
    ac    : temperature + humidity + occupancy
    light : light intensity + occupancy
Splitting into three small controllers keeps each rule base small
(about 10-15 rules) instead of one huge 3^4 = 81 rule base.
"""
from itertools import product

import numpy as np


# ----------------------------------------------------------------------------
# Membership function
# ----------------------------------------------------------------------------
def trapmf(x, a, b, c, d):
    """Trapezoidal membership function.

    0 below a, rises to 1 at b, stays 1 until c, falls to 0 at d.
    Triangle  : trapmf(x, a, b, b, c)
    Left shoulder  (a == b): membership is 1 everywhere left of c.
    Right shoulder (c == d): membership is 1 everywhere right of b.
    """
    x = np.asarray(x, dtype=float)
    left = np.ones_like(x) if b == a else (x - a) / (b - a)
    right = np.ones_like(x) if d == c else (d - x) / (d - c)
    return np.clip(np.minimum(left, right), 0.0, 1.0)


# ----------------------------------------------------------------------------
# Linguistic variable and Mamdani controller
# ----------------------------------------------------------------------------
class FuzzyVar:
    """A linguistic variable: a universe of discourse and named fuzzy terms."""

    def __init__(self, name, lo, hi, step, terms, unit=""):
        self.name = name
        self.unit = unit
        self.universe = np.arange(lo, hi + step, step, dtype=float)
        self.params = terms                      # term name -> (a, b, c, d)

    def mf(self, term, x=None):
        a, b, c, d = self.params[term]
        return trapmf(self.universe if x is None else x, a, b, c, d)

    def fuzzify(self, x):
        """Membership degree of the crisp value x in every term."""
        x = float(np.clip(x, self.universe[0], self.universe[-1]))
        return {t: float(self.mf(t, x)) for t in self.params}


class MamdaniController:
    """Mamdani FIS with AND-only rules (OR is expressed with a list of terms)."""

    DEADBAND = 8.0   # outputs below 8 % are treated as "off" (the centroid of the
                     # "off" shape alone is ~6.7 %, so it can never reach exactly 0)

    def __init__(self, name, inputs, output, rules):
        self.name = name
        self.inputs = {v.name: v for v in inputs}
        self.output = output
        self.rules = self._expand(rules)

    @staticmethod
    def _expand(rules):
        """rule = ({var: term or [terms]}, output_term). A list means OR and is
        expanded into one plain AND-rule per combination."""
        expanded = []
        for conditions, out_term in rules:
            names = list(conditions)
            options = [c if isinstance(c, (list, tuple)) else [c]
                       for c in conditions.values()]
            for combo in product(*options):
                expanded.append((dict(zip(names, combo)), out_term))
        return expanded

    def infer(self, **crisp):
        """Return (output %, list of (firing strength, rule)) for the inputs."""
        degrees = {n: v.fuzzify(crisp[n]) for n, v in self.inputs.items()}
        aggregated = np.zeros_like(self.output.universe)
        fired = []
        for cond, out_term in self.rules:
            strength = min(degrees[var][term] for var, term in cond.items())  # AND
            if strength <= 0.0:
                continue
            fired.append((strength, cond, out_term))
            clipped = np.minimum(strength, self.output.mf(out_term))          # implication
            aggregated = np.maximum(aggregated, clipped)                      # aggregation
        area = aggregated.sum()
        if area == 0.0:
            return 0.0, fired
        value = float((self.output.universe * aggregated).sum() / area)       # centroid
        return (0.0 if value < self.DEADBAND else round(value, 1)), fired

    def __call__(self, **crisp):
        return self.infer(**crisp)[0]


# ----------------------------------------------------------------------------
# Linguistic variables (membership functions)
# ----------------------------------------------------------------------------
# Inputs
TEMP = FuzzyVar("temp", 10, 45, 0.5, {
    "cool": (10, 10, 20, 26),
    "warm": (21, 27, 27, 34),
    "hot":  (30, 36, 45, 45),
}, unit="°C")

HUM = FuzzyVar("hum", 0, 100, 1, {
    "dry":         (0, 0, 25, 45),
    "comfortable": (30, 50, 50, 70),
    "humid":       (55, 75, 100, 100),
}, unit="%")

OCC = FuzzyVar("occ", 0, 6, 0.1, {
    "empty":   (0, 0, 0, 1),
    "few":     (0, 2, 2, 4),
    "crowded": (2, 4, 6, 6),
}, unit="people")

LUX = FuzzyVar("lux", 0, 1000, 5, {
    "dark":   (0, 0, 100, 250),
    "dim":    (150, 350, 350, 550),
    "bright": (450, 650, 1000, 1000),
}, unit="lux")


# Outputs (all expressed as 0-100 %)
def _level(name):
    return FuzzyVar(name, 0, 100, 1, {
        "off":    (0, 0, 0, 20),
        "low":    (10, 30, 30, 50),
        "medium": (40, 60, 60, 80),
        "high":   (70, 90, 100, 100),
    }, unit="%")


FAN, AC, LIGHT = _level("fan"), _level("ac"), _level("light")

PEOPLE = ["few", "crowded"]   # shorthand for "someone is in the room"

# ----------------------------------------------------------------------------
# Rule bases
# ----------------------------------------------------------------------------
FAN_RULES = [
    ({"occ": "empty"},                                        "off"),
    ({"occ": PEOPLE, "temp": "cool", "hum": ["dry", "comfortable"]}, "off"),
    ({"occ": PEOPLE, "temp": "cool", "hum": "humid"},         "low"),
    ({"occ": PEOPLE, "temp": "warm", "hum": "dry"},           "low"),
    ({"occ": "few",     "temp": "warm", "hum": "comfortable"}, "low"),
    ({"occ": "crowded", "temp": "warm", "hum": "comfortable"}, "medium"),
    ({"occ": "few",     "temp": "warm", "hum": "humid"},      "medium"),
    ({"occ": "crowded", "temp": "warm", "hum": "humid"},      "high"),
    ({"occ": PEOPLE, "temp": "hot"},                          "high"),
]

AC_RULES = [
    ({"occ": "empty", "temp": ["cool", "warm"]},              "off"),
    ({"occ": "empty", "temp": "hot"},                         "low"),     # pre-cooling
    ({"occ": PEOPLE, "temp": "cool"},                         "off"),
    ({"occ": "few",     "temp": "warm", "hum": "dry"},        "off"),
    ({"occ": "few",     "temp": "warm", "hum": "comfortable"}, "low"),
    ({"occ": "few",     "temp": "warm", "hum": "humid"},      "medium"),
    ({"occ": "crowded", "temp": "warm", "hum": "dry"},        "low"),
    ({"occ": "crowded", "temp": "warm", "hum": "comfortable"}, "medium"),
    ({"occ": "crowded", "temp": "warm", "hum": "humid"},      "high"),
    ({"occ": "few",     "temp": "hot", "hum": "dry"},         "medium"),
    ({"occ": "few",     "temp": "hot", "hum": ["comfortable", "humid"]}, "high"),
    ({"occ": "crowded", "temp": "hot"},                       "high"),
]

LIGHT_RULES = [
    ({"occ": "empty"},                                        "off"),
    ({"occ": PEOPLE, "lux": "dark"},                          "high"),
    ({"occ": "few",     "lux": "dim"},                        "low"),
    ({"occ": "crowded", "lux": "dim"},                        "medium"),
    ({"occ": PEOPLE, "lux": "bright"},                        "off"),
]

fan_controller = MamdaniController("fan", [TEMP, HUM, OCC], FAN, FAN_RULES)
ac_controller = MamdaniController("ac", [TEMP, HUM, OCC], AC, AC_RULES)
light_controller = MamdaniController("light", [LUX, OCC], LIGHT, LIGHT_RULES)


def decide(temp, hum, lux, occ):
    """Run all three fuzzy controllers. Returns outputs in percent (0-100)."""
    return {
        "fan": fan_controller(temp=temp, hum=hum, occ=occ),
        "ac": ac_controller(temp=temp, hum=hum, occ=occ),
        "light": light_controller(lux=lux, occ=occ),
    }


# ----------------------------------------------------------------------------
# Baseline: the usual if-else threshold controller we compare against
# ----------------------------------------------------------------------------
def threshold_decide(temp, hum, lux, occ):
    """Classic ON/OFF logic with fixed thresholds (no fuzziness)."""
    someone = occ >= 1
    if someone and temp > 28:
        fan = 100.0
    elif someone and temp > 24:
        fan = 50.0
    else:
        fan = 0.0
    ac = 100.0 if (someone and temp > 26) else 0.0
    light = 100.0 if (someone and lux < 300) else 0.0
    return {"fan": fan, "ac": ac, "light": light}


if __name__ == "__main__":
    # quick sanity check
    cases = [
        (36, 40, 800, 0), (36, 40, 800, 4), (31, 80, 100, 4),
        (27, 55, 300, 2), (20, 50, 50, 1), (26, 30, 700, 3),
    ]
    print(f"{'temp':>5} {'hum':>4} {'lux':>5} {'occ':>4} | {'fuzzy fan/ac/light':>20} | threshold fan/ac/light")
    for t, h, l, o in cases:
        f, b = decide(t, h, l, o), threshold_decide(t, h, l, o)
        print(f"{t:5} {h:4} {l:5} {o:4} | {f['fan']:6} {f['ac']:6} {f['light']:6} | "
              f"{b['fan']:5.0f} {b['ac']:5.0f} {b['light']:5.0f}")
