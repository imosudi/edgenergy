import os
import time
import json
import logging
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cloud.sync")

# Configurations
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", 60))

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-token-12345")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "edgenergy")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "telemetry")

TOPICS = {
    "telemetry": "home/energy",
    "predictions": "home/predictions",
    "events": "home/events",
    "status_cloud": "home/status/cloud"
}

# Global Sync Counter
records_synced = 0
counter_lock = threading.Lock()

# Parse ISO8601 string to datetime object or return now
def parse_time(ts_str: str) -> datetime:
    try:
        # Handle formats like 2025-11-16T05:00:00.123Z
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1]
        return datetime.fromisoformat(ts_str)
    except Exception:
        return datetime.utcnow()

# Mapping Functions for Unit Testing
def map_telemetry_to_point(data: dict) -> Point:
    point = Point("device_telemetry") \
        .tag("device_id", data.get("device_id", "unknown")) \
        .tag("house_id", data.get("house_id", "unknown")) \
        .field("v", float(data.get("v", 0.0))) \
        .field("i", float(data.get("i", 0.0))) \
        .field("p", float(data.get("p", 0.0)))
    
    if "sample_rate" in data:
        point.field("sample_rate", int(data["sample_rate"]))
        
    ts = parse_time(data.get("ts", ""))
    point.time(ts, WritePrecision.NS)
    return point

def map_predictions_to_point(data: dict) -> Point:
    point = Point("appliance_predictions") \
        .tag("device_id", data.get("device_id", "unknown")) \
        .tag("house_id", data.get("house_id", "unknown")) \
        .tag("model_mode", data.get("model_mode", "unknown"))
    
    state = data.get("appliance_state", {})
    power = data.get("appliance_power", {})
    
    for app in ["fridge", "microwave", "hvac"]:
        if app in state:
            point.field(f"{app}_active", int(state[app]))
        if app in power:
            point.field(f"{app}_power", float(power[app]))
            
    point.field("anomaly_detected", int(data.get("anomaly_detected", False)))
    
    ts = parse_time(data.get("ts", ""))
    point.time(ts, WritePrecision.NS)
    return point

def map_events_to_point(data: dict) -> Point:
    point = Point("appliance_events") \
        .tag("device_id", data.get("device_id", "unknown")) \
        .tag("house_id", data.get("house_id", "unknown")) \
        .tag("appliance", data.get("appliance", "unknown")) \
        .tag("event", data.get("event", "unknown")) \
        .field("delta_p", float(data.get("delta_p", 0.0))) \
        .field("signature_verified", int(data.get("signature_verified", False)))
        
    ts = parse_time(data.get("ts", ""))
    point.time(ts, WritePrecision.NS)
    return point

class CloudSyncAgent:
    def __init__(self):
        self.influx_client = None
        self.write_api = None
        self.mqtt_client = None
        self.running = True

    def init_database(self):
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        
        # Wait until database is online
        db_connected = False
        while self.running and not db_connected:
            try:
                logger.info(f"Checking InfluxDB health at {INFLUXDB_URL}...")
                health = self.influx_client.health()
                if health.status == "pass":
                    db_connected = True
                    logger.info("Successfully connected to InfluxDB.")
                else:
                    logger.warning(f"InfluxDB health status: {health.status}. Retrying in 3 seconds...")
                    time.sleep(3)
            except Exception as e:
                logger.warning(f"Failed to reach InfluxDB: {e}. Retrying in 3 seconds...")
                time.sleep(3)

        if self.running:
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

    def init_mqtt(self):
        self.mqtt_client = mqtt.Client(client_id="edgenergy-cloud-sync")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
        # Connect loop
        mqtt_connected = False
        while self.running and not mqtt_connected:
            try:
                logger.info(f"Connecting to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}...")
                self.mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
                mqtt_connected = True
                logger.info("Successfully connected to MQTT broker.")
            except Exception as e:
                logger.warning(f"Failed to connect to MQTT broker: {e}. Retrying in 3 seconds...")
                time.sleep(3)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker. Subscribing to topics...")
            client.subscribe(TOPICS["telemetry"])
            client.subscribe(TOPICS["predictions"])
            client.subscribe(TOPICS["events"])
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        global records_synced
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")
        
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON on topic {topic}: {e}")
            return

        point = None
        try:
            if topic == TOPICS["telemetry"]:
                point = map_telemetry_to_point(data)
            elif topic == TOPICS["predictions"]:
                point = map_predictions_to_point(data)
            elif topic == TOPICS["events"]:
                point = map_events_to_point(data)

            if point and self.write_api:
                self.write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
                with counter_lock:
                    records_synced += 1
        except Exception as e:
            logger.error(f"Failed to write point to InfluxDB: {e}")

    def publish_status_reports(self):
        while self.running:
            time.sleep(5)
            if not self.mqtt_client or not self.mqtt_client.is_connected():
                continue
                
            try:
                db_online = False
                if self.influx_client:
                    db_online = self.influx_client.health().status == "pass"
            except Exception:
                db_online = False

            with counter_lock:
                sync_count = records_synced

            status_payload = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "status": "online" if db_online else "degraded",
                "db_connected": db_online,
                "records_synced": sync_count
            }
            try:
                self.mqtt_client.publish(TOPICS["status_cloud"], json.dumps(status_payload))
            except Exception as e:
                logger.error(f"Failed to publish status report: {e}")

    def start(self):
        self.init_database()
        self.init_mqtt()
        
        if not self.running:
            return

        # Start status report thread
        self.report_thread = threading.Thread(target=self.publish_status_reports, daemon=True)
        self.report_thread.start()

        self.mqtt_client.loop_forever()

    def shutdown(self):
        logger.info("Shutdown requested.")
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.influx_client:
            self.influx_client.close()

if __name__ == "__main__":
    agent = CloudSyncAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.shutdown()
