"""
controller.py  -  fuzzy smart-home controller (MQTT subscriber + publisher)
---------------------------------------------------------------------------
Subscribes to   <ROOT>/sensors/#
Runs the fuzzy controllers every time a full set of readings has arrived
Publishes to    <ROOT>/actuators/fan | ac | light   {"value": 72.5, "time": "14:05"}

The decision logic lives in SmartHomeController, which knows nothing about
MQTT - so it can be unit-tested without a broker (see test_controller.py).

Run:   python controller.py
"""
import json

import config
import fuzzy_system as fs


class SmartHomeController:
    """Collects sensor readings and turns them into actuator commands."""

    def __init__(self, publish):
        self.publish = publish          # function(topic, payload_dict)
        self.latest = {}
        self.last_commands = {}

    def handle(self, sensor, value, stamp=""):
        """Feed one sensor reading. When the cycle completes (occupancy is the
        last sensor sent) all three fuzzy controllers run and commands go out."""
        self.latest[sensor] = float(value)
        if sensor != "occupancy" or not all(s in self.latest for s in config.SENSORS):
            return None
        out = fs.decide(temp=self.latest["temperature"], hum=self.latest["humidity"],
                        lux=self.latest["light"], occ=self.latest["occupancy"])
        for name in config.ACTUATORS:
            self.publish(config.actuator_topic(name), {"value": out[name], "time": stamp})
        self.last_commands = out
        return out


def main():
    client = config.make_client("fuzzy-controller")

    def publish(topic, payload):
        client.publish(topic, json.dumps(payload), qos=0)

    brain = SmartHomeController(publish)

    def on_connect(client, userdata, flags, rc, props=None):
        client.subscribe(f"{config.ROOT}/sensors/#")
        print(f"[controller] connected, listening on '{config.ROOT}/sensors/#'")

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            sensor = msg.topic.rsplit("/", 1)[-1]
            out = brain.handle(sensor, data["value"], data.get("time", ""))
        except (ValueError, KeyError) as err:
            print(f"[controller] ignored bad message on {msg.topic}: {err}")
            return
        if out:
            t = brain.latest
            print(f"[controller] {data.get('time', '')}  T={t['temperature']:.1f} H={t['humidity']:.0f} "
                  f"L={t['light']:.0f} occ={t['occupancy']:.0f}  ->  "
                  f"fan {out['fan']:5.1f}%  ac {out['ac']:5.1f}%  light {out['light']:5.1f}%")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.BROKER, config.PORT, keepalive=60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()


if __name__ == "__main__":
    main()
