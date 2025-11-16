import time
import random
import json
import paho.mqtt.client as mqtt
import os

# MQTT settings
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC = "home/energy"

# Simulate N smart plugs
NUM_DEVICES = 5

def generate_mock_reading(device_id):
    """Generate a dummy power reading (Watts) for a device"""
    return {
        "device_id": f"plug_{device_id}",
        "voltage": round(random.uniform(210, 240), 1),
        "current": round(random.uniform(0.0, 5.0), 2),
        "power": round(random.uniform(0.0, 1200.0), 1),
        "timestamp": int(time.time())
    }

def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    print(f"Publishing mock power readings to {MQTT_BROKER}:{MQTT_PORT}/{TOPIC} ...")
    try:
        while True:
            for device_id in range(1, NUM_DEVICES + 1):
                reading = generate_mock_reading(device_id)
                payload = json.dumps(reading)
                client.publish(TOPIC, payload)
                print(f"Published: {payload}")
            time.sleep(2)  # wait 2 seconds before next batch
    except KeyboardInterrupt:
        print("Stopping publisher...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
