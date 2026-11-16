"""
sensors.py  -  IoT sensor nodes (simulated)  ->  MQTT publisher
----------------------------------------------------------------
Plays back one simulated day and publishes every reading to the broker:

    <ROOT>/sensors/temperature   {"value": 31.2, "time": "10:15"}
    <ROOT>/sensors/humidity
    <ROOT>/sensors/light
    <ROOT>/sensors/occupancy     (published last in every cycle)

Run:   python sensors.py                 # one reading cycle every 0.5 s
       python sensors.py --delay 0.1     # faster demo (a whole day in ~30 s)
       python sensors.py --loop          # repeat the day forever
"""
import argparse
import json
import time

import config
from simulation import generate_day, hhmm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=0.5, help="seconds per 5-minute step")
    ap.add_argument("--loop", action="store_true", help="repeat the day forever")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    client = config.make_client("sensor-node")
    client.connect(config.BROKER, config.PORT, keepalive=60)
    client.loop_start()
    print(f"[sensors] connected to {config.BROKER}:{config.PORT}, topics under '{config.ROOT}/sensors/'")

    try:
        while True:
            day = generate_day(seed=args.seed)
            for i, hour in enumerate(day["hour"]):
                stamp = hhmm(hour)
                readings = {
                    "temperature": round(float(day["temp"][i]), 1),
                    "humidity": round(float(day["hum"][i]), 0),
                    "light": round(float(day["lux"][i]), 0),
                    "occupancy": int(day["occ"][i]),
                }
                for name in config.SENSORS:                    # occupancy goes last
                    payload = json.dumps({"value": readings[name], "time": stamp})
                    client.publish(config.sensor_topic(name), payload, qos=0)
                print(f"[sensors] {stamp}  T={readings['temperature']}  H={readings['humidity']:.0f}  "
                      f"L={readings['light']:.0f}  occ={readings['occupancy']}")
                time.sleep(args.delay)
            if not args.loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
