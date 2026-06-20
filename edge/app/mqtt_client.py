import logging
import json
from typing import Callable, Optional
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

# Check if CallbackAPIVersion is available (paho-mqtt v2.x)
try:
    from paho.mqtt.enums import CallbackAPIVersion
    PAHO_V2 = True
except ImportError:
    PAHO_V2 = False

class EdgeMQTTClient:
    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        keepalive: int = 60,
        client_id: str = "edgenergy-edge-app"
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.keepalive = keepalive
        self.client_id = client_id
        
        # Initialize client according to Paho version
        if PAHO_V2:
            self.client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION1,
                client_id=self.client_id
            )
        else:
            self.client = mqtt.Client(client_id=self.client_id)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self.message_callback: Optional[Callable[[str], None]] = None

    def set_message_callback(self, callback: Callable[[str], None]):
        self.message_callback = callback

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"MQTT Connected successfully to {self.broker_host}:{self.broker_port}")
        else:
            logger.error(f"MQTT Connection failed with return code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"MQTT Disconnected from broker (rc={rc}). Reconnecting...")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            logger.debug(f"Received message on topic '{msg.topic}': {payload}")
            if self.message_callback:
                self.message_callback(payload)
        except Exception as e:
            logger.error(f"Error handling incoming message on topic '{msg.topic}': {e}")

    def connect(self):
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, self.keepalive)
        except Exception as e:
            logger.error(f"Could not connect to MQTT broker: {e}")
            raise

    def subscribe(self, topic: str):
        logger.info(f"Subscribing to topic '{topic}'")
        self.client.subscribe(topic)

    def publish(self, topic: str, payload: dict):
        try:
            payload_str = json.dumps(payload)
            logger.debug(f"Publishing message to topic '{topic}': {payload_str}")
            self.client.publish(topic, payload_str)
        except Exception as e:
            logger.error(f"Failed to publish message to topic '{topic}': {e}")

    def start_loop(self):
        logger.info("Starting MQTT client network loop...")
        self.client.loop_start()

    def stop_loop(self):
        logger.info("Stopping MQTT client network loop...")
        self.client.loop_stop()
        self.client.disconnect()
