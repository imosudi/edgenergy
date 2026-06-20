import logging
import signal
import sys
import time
from app import config
from app.preprocess import parse_telemetry, extract_features
from app.infer import NILMInferenceEngine
from app.mqtt_client import EdgeMQTTClient

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("edgenergy.main")

class EdgeApp:
    def __init__(self):
        self.running = True
        
        logger.info("Initializing EdgeNergy Inference Engine...")
        self.engine = NILMInferenceEngine(config.MODEL_PATH)
        
        logger.info(f"Connecting to MQTT Broker at {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}...")
        self.client = EdgeMQTTClient(
            broker_host=config.MQTT_BROKER_HOST,
            broker_port=config.MQTT_BROKER_PORT,
            keepalive=config.MQTT_KEEPALIVE
        )
        self.client.set_message_callback(self.on_telemetry_received)

    def on_telemetry_received(self, payload_str: str):
        # 1. Parse telemetry JSON
        telemetry = parse_telemetry(payload_str)
        if not telemetry:
            return  # Skip invalid payloads

        logger.info(
            f"Telemetry received from node={telemetry['device_id']}, "
            f"v={telemetry['v']}V, i={telemetry['i']}A, p={telemetry['p']}W"
        )

        # 2. Extract features
        features = extract_features(telemetry)

        # 3. Execute TinyML Inference
        result = self.engine.predict(features)

        # 4. Construct prediction payload
        prediction_payload = {
            "ts": telemetry["ts"],
            "device_id": telemetry["device_id"],
            "house_id": telemetry["house_id"],
            "appliance_state": result["appliance_state"],
            "anomaly_detected": result["anomaly_detected"],
            "model_mode": result["model_mode"]
        }

        # 5. Publish disaggregated state predictions
        self.client.publish(config.PREDICTIONS_TOPIC, prediction_payload)

        # 6. Publish anomalies/alerts if triggered
        if result["anomaly_detected"]:
            alert_payload = {
                "ts": telemetry["ts"],
                "device_id": telemetry["device_id"],
                "house_id": telemetry["house_id"],
                "alert": "Overcurrent or anomalous energy consumption detected",
                "metrics": {
                    "voltage": telemetry["v"],
                    "current": telemetry["i"],
                    "power": telemetry["p"]
                }
            }
            self.client.publish(config.ALERTS_TOPIC, alert_payload)

    def run(self):
        # Register shutdown handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        try:
            self.client.connect()
            self.client.subscribe(config.TELEMETRY_TOPIC)
            self.client.start_loop()
            
            logger.info("EdgeNergy MVP App is running. Press Ctrl+C to terminate.")
            while self.running:
                time.sleep(1)
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}")
        finally:
            self.cleanup()

    def shutdown(self, signum, frame):
        logger.info("Received termination signal. Requesting shutdown...")
        self.running = False

    def cleanup(self):
        logger.info("Cleaning up resources...")
        self.client.stop_loop()
        logger.info("EdgeNergy MVP App stopped.")

if __name__ == "__main__":
    app = EdgeApp()
    app.run()
