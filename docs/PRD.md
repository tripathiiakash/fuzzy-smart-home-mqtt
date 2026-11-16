# PRD - Fuzzy Logic Smart Home Automation over MQTT

| | |
|---|---|
| **Project type** | Semester mini-project (IoT + Computational Intelligence) |
| **Version** | 1.0 (code complete; live MQTT demo pending verification) |
| **Date** | 2026-11-04 |
| **Effort** | 2-3 days, software only |
| **Language / libs** | Python 3, NumPy, Matplotlib, paho-mqtt (live demo only) |

## 1. Overview

A simulated IoT smart home in which virtual sensors publish environmental readings over
the MQTT protocol, and a fuzzy logic controller subscribes to them and decides fan speed,
air-conditioner power and light brightness, publishing those commands back over MQTT.
A live dashboard visualises sensors and decisions. A separate offline analysis compares the
fuzzy controller with a conventional if-else threshold controller.

**Scope statement (must appear in the report):** sensors and actuators are simulated in
software. The architecture (sensor node -> MQTT broker -> controller -> actuator ->
dashboard) is the standard IoT pattern, and the virtual sensor script can be replaced by
real hardware (e.g. ESP32) publishing to the same topics without changing the controller.

## 2. Problem statement

Conventional home automation uses fixed thresholds ("fan ON if temperature > 28 degC").
This gives abrupt ON/OFF behaviour, ignores combined conditions (heat + humidity +
number of people), wastes energy on empty rooms, and wears appliances through frequent
switching. Human comfort is gradual and imprecise ("warm", "a bit humid"), which fuzzy
logic models naturally.

## 3. Goals and non-goals

**Goals**
- G1. Demonstrate a complete publish/subscribe IoT data pipeline (sensor, broker,
  subscriber, actuator command, dashboard).
- G2. Implement a Mamdani fuzzy inference system from scratch, showing all five steps.
- G3. Produce measurable evidence comparing fuzzy vs threshold control.
- G4. Be runnable and demonstrable in 3 minutes, with a no-internet fallback.
- G5. Be explainable line by line in a viva.

**Non-goals**
- No physical hardware, no real room thermal model, no comfort measurement, no cloud
  deployment, no mobile app, no security/authentication on MQTT, no machine learning.

## 4. Users

- Primary: the student (builds, demonstrates, defends the project).
- Secondary: the course professor (evaluates concept understanding, demo, report).

## 5. System architecture

```
 sensors.py  --publish-->  MQTT broker  --subscribe-->  controller.py (fuzzy logic)
 (4 virtual                (broker.hivemq.com               |
  sensor nodes)             or local Mosquitto)  <--publish-- actuator commands
                                   |
                                   +--subscribe--> dashboard.py (live plots)

 run_offline.py = same fuzzy logic + simulation, no broker (graphs, comparison, report data)
```

Components
| Component | File | Responsibility |
|---|---|---|
| Sensor simulator | `simulation.py` | Generates a realistic 24 h day of readings |
| Sensor nodes | `sensors.py` | Publishes readings to MQTT |
| Fuzzy engine + rules | `fuzzy_system.py` | Inference, 3 controllers, baseline controller |
| Controller | `controller.py` | Subscribe, aggregate readings, decide, publish |
| Dashboard | `dashboard.py` | Live plots; `--selftest` for no-broker rendering |
| Analysis | `run_offline.py` | Day run, metrics, all figures and tables |
| Config | `config.py` | Broker/topic settings |
| Tests | `test_controller.py` | 7 broker-free tests |

## 6. MQTT interface specification

Broker default: `broker.hivemq.com:1883` (override with env vars `MQTT_BROKER`,
`MQTT_PORT`, `MQTT_ROOT`). QoS 0, no retained messages, no authentication.
Topic root default: `iot_ci_fuzzy_home_7q2/livingroom` (**change to a unique value** on a
public broker).

| Topic (under root) | Direction | Payload JSON | Unit |
|---|---|---|---|
| `sensors/temperature` | sensor -> broker | `{"value": 31.2, "time": "10:15"}` | degC |
| `sensors/humidity` | sensor -> broker | same | % |
| `sensors/light` | sensor -> broker | same | lux |
| `sensors/occupancy` | sensor -> broker | same (**sent last each cycle**) | people |
| `actuators/fan` | controller -> broker | `{"value": 72.5, "time": "10:15"}` | % 0-100 |
| `actuators/ac` | controller -> broker | same | % 0-100 |
| `actuators/light` | controller -> broker | same | % 0-100 |

Behaviour: the controller stores the latest value of each sensor; when an `occupancy`
message arrives and all four sensors have been seen, it computes and publishes all three
actuator commands. Malformed messages are ignored with a log line.

## 7. Functional requirements

| ID | Requirement |
|---|---|
| FR1 | Simulator generates 288 steps (5 min) of temperature, humidity, light and occupancy, deterministic for a given seed (default 42). |
| FR2 | `sensors.py` publishes each step to the four sensor topics with a configurable delay (`--delay`), optional `--loop`. |
| FR3 | `controller.py` subscribes to `sensors/#`, runs the fan, AC and light fuzzy controllers, publishes three actuator commands per cycle. |
| FR4 | Fuzzy engine implements fuzzification, min-AND rule evaluation, min implication, max aggregation, centroid defuzzification. |
| FR5 | Rules may use lists of terms as OR shorthand; the engine expands them to AND-only rules. |
| FR6 | Outputs below the deadband (8 %) are reported as 0. |
| FR7 | `threshold_decide()` provides an if-else baseline for comparison. |
| FR8 | `run_offline.py` produces membership plots, a 3-D control surface, a 24 h time-series plot, a comparison bar chart, `results.csv` and `comparison.txt` without any broker. |
| FR9 | `dashboard.py` shows live sensor plots (left) and actuator plots (right), and supports `--selftest`. |
| FR10 | `test_controller.py` verifies rule behaviour, rule-base completeness and controller message handling. |

## 8. Fuzzy system design

Method: Mamdani, AND = min, implication = min (clip), aggregation = max, defuzzification =
centroid on a discretised universe, deadband 8 %.

### 8.1 Input membership functions (trapezoid `(a, b, c, d)`; triangle = `(a, b, b, c)`)

| Variable | Universe | Terms |
|---|---|---|
| Temperature (degC) | 10-45, step 0.5 | cool (10,10,20,26); warm (21,27,27,34); hot (30,36,45,45) |
| Humidity (%) | 0-100, step 1 | dry (0,0,25,45); comfortable (30,50,50,70); humid (55,75,100,100) |
| Occupancy (people) | 0-6, step 0.1 | empty (0,0,0,1); few (0,2,2,4); crowded (2,4,6,6) |
| Light (lux) | 0-1000, step 5 | dark (0,0,100,250); dim (150,350,350,550); bright (450,650,1000,1000) |

### 8.2 Output membership functions (fan, AC and light all use the same, 0-100 %)

off (0,0,0,20); low (10,30,30,50); medium (40,60,60,80); high (70,90,100,100).
Note: the centroid of "high" alone is about 90 %, so the maximum reachable output is about
90 %, and pure "off" gives about 6.7 %, which the deadband maps to 0.

### 8.3 Rule bases (`PEOPLE` = few OR crowded)

**Fan (9 written, 15 expanded)**
1. occ empty -> off
2. occ PEOPLE AND temp cool AND hum (dry OR comfortable) -> off
3. occ PEOPLE AND temp cool AND hum humid -> low
4. occ PEOPLE AND temp warm AND hum dry -> low
5. occ few AND temp warm AND hum comfortable -> low
6. occ crowded AND temp warm AND hum comfortable -> medium
7. occ few AND temp warm AND hum humid -> medium
8. occ crowded AND temp warm AND hum humid -> high
9. occ PEOPLE AND temp hot -> high

**AC (12 written, 15 expanded)**
1. occ empty AND temp (cool OR warm) -> off
2. occ empty AND temp hot -> low (pre-cooling)
3. occ PEOPLE AND temp cool -> off
4. occ few AND warm AND dry -> off
5. occ few AND warm AND comfortable -> low
6. occ few AND warm AND humid -> medium
7. occ crowded AND warm AND dry -> low
8. occ crowded AND warm AND comfortable -> medium
9. occ crowded AND warm AND humid -> high
10. occ few AND hot AND dry -> medium
11. occ few AND hot AND (comfortable OR humid) -> high
12. occ crowded AND hot -> high

**Light (5 written, 7 expanded)**
1. occ empty -> off
2. occ PEOPLE AND lux dark -> high
3. occ few AND lux dim -> low
4. occ crowded AND lux dim -> medium
5. occ PEOPLE AND lux bright -> off

Design property: every input combination fires at least one rule (tested).

### 8.4 Baseline (if-else threshold) controller

someone = occupancy >= 1.
- Fan: 100 % if someone and temp > 28; 50 % if someone and temp > 24; else 0.
- AC: 100 % if someone and temp > 26; else 0.
- Light: 100 % if someone and lux < 300; else 0.

## 9. Simulation specification (`simulation.py`)

- 24 h, 5-minute steps (288 samples), numpy RNG seed 42.
- Temperature: 30 + 6 sin(2 pi (h-9)/24) + AR(1) drift (phi 0.95, sigma 0.15). Range about 24-36 degC, peak ~15:00. Represents a hot, humid Indian summer day.
- Humidity: 60 - 22 sin(2 pi (h-9)/24) + AR(1) drift (sigma 0.6), clipped 5-98 %.
- Light: 850 * daylight(h in 6-18) * cloud factor (0.45-1.0), 0 at night; ambient light without the room's own lamps.
- Occupancy (family routine): 0 until 06:30; 2 until 08:30; 0 until 12:30; 1 until 14:00; 0 until 17:00; 2 until 18:30; 4 until 19:30; 5 until 21:30; 3 until 22:30; 1 afterwards; plus random +-1 jitter while occupied; clipped 0-6.

## 10. Evaluation method and results

Metrics (computed per appliance, per day):
- Energy (kWh) = sum(level/100 * rated watts * 5/60 h) / 1000. Rated: fan 75 W, AC 1500 W, light 40 W. **Assumes power proportional to level.**
- Energy while room empty (occupancy < 1).
- Mean absolute output change per step (smoothness).
- ON/OFF toggles: crossings of the 5 % output line.

Results (seed 42):

| | Fuzzy | If-else |
|---|---|---|
| Total energy | 13.69 kWh | 15.73 kWh (about 13 % lower) |
| Fan / AC / Light energy (kWh) | 0.52 / 12.85 / 0.31 | 0.62 / 14.75 / 0.36 |
| Fan / AC / Light toggles | 17 / 5 / 17 | 17 / 18 / 5 |
| Mean jump per step, AC | 4.0 | 6.3 |
| Energy while empty | 2.66 kWh | 0.00 kWh |

Interpretation: fuzzy control is smoother and cuts AC switching by about 70 %, and the
total saving comes mainly from proportional AC output. Fuzzy lights toggle more because
simulated occupancy jitters. Fuzzy pre-cooling wastes energy in an empty room by design.
Comfort is not measured.

## 11. Testing

`python test_controller.py` (7 tests, no framework):
1. Empty room in cool dark conditions -> all outputs 0.
2. Hot crowded room -> fan and AC above 80.
3. Dark occupied room -> light above 80.
4. Bright occupied room -> light 0.
5. Fan monotonic with temperature and at least 10 distinct levels from 18-38 degC.
6. Every input combination (fan, AC, light) fires at least one rule.
7. Controller publishes exactly three actuator messages only after a full sensor cycle.

Manual tests still required: live 3-terminal MQTT run, live dashboard, public broker
connectivity.

## 12. Non-functional requirements

- Runs on any machine with Python 3.9+; fuzzy part needs only NumPy and Matplotlib.
- `run_offline.py` completes in a few seconds with no internet.
- Code is readable and commented so every step can be explained in a viva.
- Documentation never contradicts the code (update docs when rules change).

## 13. Risks and limitations

| Risk / limitation | Mitigation |
|---|---|
| Live MQTT path untested in build environment | User runs the live demo once; fallback is `run_offline.py` plus a screen recording |
| Public broker is shared and unreliable | Unique `MQTT_ROOT`; or local Mosquitto with `MQTT_BROKER=localhost` |
| Port 1883 blocked on college Wi-Fi | Use a phone hotspot or a local broker |
| Simulated hardware may be questioned | State it upfront; point to the ESP32 swap path |
| Energy saving depends on a proportional-power assumption | State the assumption wherever the number is shown |
| Centroid gives steep ramps at narrow-output boundaries | Documented; could be reduced with wider output sets or another defuzzifier |
| Light flicker from jittering occupancy | Future work: hysteresis or smoothing |
| No comfort/thermal model | Listed as a limitation and future work |

## 14. Report outline (6-8 pages)

1. Title, abstract (include the simulated-hardware statement)
2. Introduction and problem statement
3. Literature/background: fuzzy logic basics, MQTT basics
4. System architecture (diagram from section 5)
5. Fuzzy design: variables, membership plots, rule tables, control surface
6. Implementation: simulation, MQTT topics, controller flow
7. Results: day_simulation, comparison, table from section 10, honest discussion
8. Limitations and future work
9. Conclusion
10. References, appendix (code listing or GitHub link)

## 15. Roadmap / optional extensions

Choose by the professor's favourite CI topic:
- GA or PSO tuning of membership-function parameters against the energy + switching cost.
- Light-controller hysteresis to remove flicker.
- Neural-network or regression model predicting next-hour temperature to enable pre-cooling.
- Real sensors: ESP32 + DHT11 + LDR + PIR publishing to the same topics.
- Dashboard upgrade to Streamlit; cloud broker with authentication/TLS.

## 16. Viva Q&A

- **Why fuzzy?** Comfort is gradual; overlapping sets like "warm" and "hot" give smooth
  graded outputs rather than ON/OFF jumps.
- **Explain the five steps.** Fuzzification, rule evaluation (min), implication (clip),
  aggregation (max), defuzzification (centroid).
- **Why three controllers?** Avoids an 81-rule base; each has 5-12 written rules.
- **What is MQTT, QoS?** Lightweight pub/sub protocol with a broker routing by topic; QoS 0
  at most once, 1 at least once, 2 exactly once. This project uses QoS 0.
- **Is this real IoT?** Sensors are simulated, but the protocol and architecture are real.
- **Why is the energy saving not a pure fuzzy win?** It relies on proportional AC output.
- **Weakness?** Flickering lights, no comfort model, centroid steepness, untested hardware.
- **What would you improve?** GA-tuned membership functions, hysteresis, real sensors.

## 17. Glossary

- **Fuzzy set / membership function:** degree (0-1) to which a value belongs to a term.
- **Mamdani:** fuzzy inference style whose rule outputs are fuzzy sets.
- **Centroid:** centre of gravity of the aggregated output shape.
- **MQTT:** lightweight publish/subscribe messaging protocol common in IoT.
- **Broker:** server that receives published messages and forwards them to subscribers.
- **Topic:** hierarchical message address such as `.../sensors/temperature`.
- **QoS:** MQTT delivery guarantee level (0, 1, 2).
- **Deadband:** range of small outputs forced to zero.
