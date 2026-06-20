import logging
import signal
import sys
import time
import numpy as np
from app import config
from app.preprocess import parse_telemetry, extract_features, TransientDetector
from app.signatures import match_signature
from app.infer import NILMInferenceEngine
from app.mqtt_client import EdgeMQTTClient
from app.anomaly import AnomalyDetector
from app.forecaster import DemandForecaster

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
        self.transient_detector = TransientDetector(threshold=50.0)
        self.anomaly_detector = AnomalyDetector()
        self.forecaster = DemandForecaster()
        self.last_anomaly_detected = False
        self.last_active_anomalies = []
        self.last_appliance_states = {} # device_id -> dict of appliance ON/OFF states
        
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

        # 2. Detect power transient (delta)
        dev_id = telemetry["device_id"]
        delta_p = self.transient_detector.detect(dev_id, telemetry["p"])

        # 3. Extract features
        # The TFLite regression model expects [voltage, current, power] features
        features = np.array([telemetry["v"], telemetry["i"], telemetry["p"]], dtype=np.float32)

        # 4. Execute TinyML Inference (Regression load disaggregation)
        result = self.engine.predict(features)

        # 5. Event Detection & Signature Verification
        if dev_id not in self.last_appliance_states:
            self.last_appliance_states[dev_id] = {
                "fridge": False,
                "microwave": False,
                "hvac": False
            }

        current_states = result["appliance_state"]
        last_states = self.last_appliance_states[dev_id]

        for app in ["fridge", "microwave", "hvac"]:
            is_active = current_states.get(app, False)
            was_active = last_states.get(app, False)

            if is_active != was_active:
                event_type = "ON" if is_active else "OFF"
                
                # Verify transient delta against expected device signature
                matched_app = None
                if delta_p != 0.0:
                    matched_app = match_signature(delta_p, telemetry["p"])
                
                logger.info(
                    f"Event Detected: {app} switched {event_type} "
                    f"(delta_p={delta_p:.1f}W, signature_match={matched_app == app})"
                )

                # Publish event to events topic
                event_payload = {
                    "ts": telemetry["ts"],
                    "device_id": telemetry["device_id"],
                    "house_id": telemetry["house_id"],
                    "appliance": app,
                    "event": event_type,
                    "delta_p": round(delta_p, 1),
                    "signature_verified": matched_app == app
                }
                self.client.publish(config.EVENTS_TOPIC, event_payload)

        # Update cache
        self.last_appliance_states[dev_id] = current_states.copy()

        # 6. Run advanced analytics: anomaly detection & forecasting
        anomaly_detected, active_anomalies = self.anomaly_detector.check_telemetry(telemetry)
        
        self.forecaster.add_reading(telemetry["p"])
        forecast_results = self.forecaster.get_forecasts()

        # 7. Construct and publish disaggregated predictions payload
        prediction_payload = {
            "ts": telemetry["ts"],
            "device_id": telemetry["device_id"],
            "house_id": telemetry["house_id"],
            "appliance_state": result["appliance_state"],
            "appliance_power": result["appliance_power"],
            "anomaly_detected": anomaly_detected,
            "anomalies": active_anomalies,
            "forecast": forecast_results,
            "model_mode": result["model_mode"]
        }
        self.client.publish(config.PREDICTIONS_TOPIC, prediction_payload)

        # 8. Publish alerts if triggered or cleared
        if anomaly_detected or (self.last_anomaly_detected and not anomaly_detected):
            logger.warning(
                f"ANOMALY STATUS CHANGE: detected={anomaly_detected}, "
                f"active_anomalies={active_anomalies}, "
                f"v={telemetry['v']}V, i={telemetry['i']}A, p={telemetry['p']}W"
            )
            alert_payload = {
                "ts": telemetry["ts"],
                "device_id": telemetry["device_id"],
                "house_id": telemetry["house_id"],
                "alert": "Grid / load anomaly detected at edge" if anomaly_detected else "Anomaly cleared",
                "anomaly_detected": anomaly_detected,
                "anomalies": active_anomalies,
                "metrics": {
                    "voltage": telemetry["v"],
                    "current": telemetry["i"],
                    "power": telemetry["p"],
                    "sample_rate": telemetry.get("sample_rate", 50)
                }
            }
            self.client.publish(config.ALERTS_TOPIC, alert_payload)
            
        self.last_anomaly_detected = anomaly_detected
        self.last_active_anomalies = active_anomalies.copy()

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
