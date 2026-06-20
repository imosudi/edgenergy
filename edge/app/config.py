import os

# MQTT Broker Configuration
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", 60))

# MQTT Topics
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "home/energy")
PREDICTIONS_TOPIC = os.getenv("PREDICTIONS_TOPIC", "home/predictions")
EVENTS_TOPIC = os.getenv("EVENTS_TOPIC", "home/events")
ALERTS_TOPIC = os.getenv("ALERTS_TOPIC", "home/alerts")

# TFLite Model Configuration
# Fallback to local relative path if not running inside the Docker container
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models",
    "nilm.tflite"
)
MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
