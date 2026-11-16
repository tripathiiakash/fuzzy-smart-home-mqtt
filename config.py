"""Shared MQTT settings. Override with environment variables if you like.

    MQTT_BROKER   default broker.hivemq.com  (free public broker, no install)
                  or "localhost" if you installed Mosquitto
    MQTT_ROOT     topic prefix. CHANGE IT to something unique to you when using a
                  public broker, otherwise other students' messages will mix in.
"""
import os

BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT = int(os.getenv("MQTT_PORT", "1883"))
ROOT = os.getenv("MQTT_ROOT", "iot_ci_fuzzy_akash_17nov/livingroom")

SENSORS = ["temperature", "humidity", "light", "occupancy"]   # occupancy is sent LAST
ACTUATORS = ["fan", "ac", "light"]


def sensor_topic(name):
    return f"{ROOT}/sensors/{name}"


def actuator_topic(name):
    return f"{ROOT}/actuators/{name}"


def make_client(client_id):
    """Create a paho-mqtt client that works with both paho 1.x and 2.x."""
    import paho.mqtt.client as mqtt
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except AttributeError:                      # paho-mqtt 1.x
        return mqtt.Client(client_id=client_id)
