import json
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, HOUSE_ID

def on_connect(client, userdata, flags, rc):
    print("MQTT connected", rc)
    client.subscribe(f"home/{HOUSE_ID}/device/+/telemetry")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
    except Exception as e:
        print("Invalid JSON", e)
        return
    userdata['queue'].append(payload)

def build_client(queue):
    client = mqtt.Client(userdata={'queue': queue})
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    return client
