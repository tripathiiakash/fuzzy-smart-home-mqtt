"""
Broker-free tests: checks the fuzzy rules and the controller's message handling.
Run:  python test_controller.py
"""
import config
import fuzzy_system as fs
from controller import SmartHomeController


def test_empty_room_switches_everything_off_in_cool_dark():
    out = fs.decide(temp=22, hum=50, lux=0, occ=0)
    assert out == {"fan": 0.0, "ac": 0.0, "light": 0.0}, out


def test_hot_crowded_room_gets_strong_cooling():
    out = fs.decide(temp=36, hum=70, lux=500, occ=5)
    assert out["fan"] > 80 and out["ac"] > 80, out


def test_dark_occupied_room_gets_light():
    assert fs.decide(temp=26, hum=50, lux=0, occ=3)["light"] > 80


def test_bright_room_needs_no_light():
    assert fs.decide(temp=26, hum=50, lux=900, occ=3)["light"] == 0.0


def test_output_is_graded_not_binary():
    """Raising temperature must raise the fan monotonically through many
    intermediate speeds (an if-else controller would only give 2-3 levels)."""
    temps = [t / 2 for t in range(36, 77)]                 # 18.0 ... 38.0 in 0.5 steps
    fan = [fs.fan_controller(temp=t, hum=50, occ=3) for t in temps]
    assert all(b >= a - 0.01 for a, b in zip(fan, fan[1:])), fan      # monotonic
    assert len(set(fan)) >= 10, sorted(set(fan))                     # many distinct levels


def test_every_input_combination_fires_a_rule():
    """No gap in the rule base: the engine never returns 'no rule fired'."""
    for t in range(10, 46, 2):
        for h in range(0, 101, 10):
            for o in range(0, 7):
                for ctl, kw in ((fs.fan_controller, dict(temp=t, hum=h, occ=o)),
                                (fs.ac_controller, dict(temp=t, hum=h, occ=o))):
                    assert ctl.infer(**kw)[1], (ctl.name, kw)
    for l in range(0, 1001, 50):
        for o in range(0, 7):
            assert fs.light_controller.infer(lux=l, occ=o)[1], (l, o)


def test_controller_publishes_after_full_cycle_only():
    sent = []
    brain = SmartHomeController(lambda topic, payload: sent.append((topic, payload)))
    assert brain.handle("temperature", 35, "15:00") is None
    assert brain.handle("humidity", 40, "15:00") is None
    assert brain.handle("light", 600, "15:00") is None
    assert sent == []                                   # nothing yet
    out = brain.handle("occupancy", 3, "15:00")         # last sensor completes the cycle
    assert out is not None and len(sent) == 3
    topics = {t for t, _ in sent}
    assert topics == {config.actuator_topic(a) for a in config.ACTUATORS}
    assert all(p["time"] == "15:00" for _, p in sent)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\n{len(tests)} tests passed")
