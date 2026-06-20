import unittest
from datetime import datetime
from influxdb_client import Point
import sys
import os

# Insert current dir to path to import sync
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync import map_telemetry_to_point, map_predictions_to_point, map_events_to_point, parse_time

class TestCloudSyncMapper(unittest.TestCase):
    def test_parse_time(self):
        ts_str = "2025-11-16T05:00:00.123Z"
        dt = parse_time(ts_str)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 11)
        self.assertEqual(dt.day, 16)

    def test_map_telemetry(self):
        data = {
            "ts": "2025-11-16T05:00:00.123Z",
            "device_id": "esp32-001",
            "house_id": "home-01",
            "sample_rate": 50,
            "v": 230.2,
            "i": 0.48,
            "p": 110.5
        }
        point = map_telemetry_to_point(data)
        self.assertEqual(point._name, "device_telemetry")
        
        # Check tags
        tags = point._tags
        self.assertEqual(tags["device_id"], "esp32-001")
        self.assertEqual(tags["house_id"], "home-01")
        
        # Check fields
        fields = point._fields
        self.assertEqual(fields["v"], 230.2)
        self.assertEqual(fields["i"], 0.48)
        self.assertEqual(fields["p"], 110.5)
        self.assertEqual(fields["sample_rate"], 50)

    def test_map_predictions(self):
        data = {
            "ts": "2025-11-16T05:00:00.123Z",
            "device_id": "esp32-001",
            "house_id": "home-01",
            "appliance_state": {"fridge": True, "microwave": False, "hvac": True},
            "appliance_power": {"fridge": 110.5, "microwave": 0.0, "hvac": 2200.0},
            "anomaly_detected": True,
            "model_mode": "tflite"
        }
        point = map_predictions_to_point(data)
        self.assertEqual(point._name, "appliance_predictions")
        
        tags = point._tags
        self.assertEqual(tags["device_id"], "esp32-001")
        self.assertEqual(tags["house_id"], "home-01")
        self.assertEqual(tags["model_mode"], "tflite")
        
        fields = point._fields
        self.assertEqual(fields["fridge_active"], 1)
        self.assertEqual(fields["fridge_power"], 110.5)
        self.assertEqual(fields["microwave_active"], 0)
        self.assertEqual(fields["microwave_power"], 0.0)
        self.assertEqual(fields["hvac_active"], 1)
        self.assertEqual(fields["hvac_power"], 2200.0)
        self.assertEqual(fields["anomaly_detected"], 1)

    def test_map_events(self):
        data = {
            "ts": "2025-11-16T05:00:00.123Z",
            "device_id": "esp32-001",
            "house_id": "home-01",
            "appliance": "hvac",
            "event": "ON",
            "delta_p": 2200.0,
            "signature_verified": True
        }
        point = map_events_to_point(data)
        self.assertEqual(point._name, "appliance_events")
        
        tags = point._tags
        self.assertEqual(tags["device_id"], "esp32-001")
        self.assertEqual(tags["house_id"], "home-01")
        self.assertEqual(tags["appliance"], "hvac")
        self.assertEqual(tags["event"], "ON")
        
        fields = point._fields
        self.assertEqual(fields["delta_p"], 2200.0)
        self.assertEqual(fields["signature_verified"], 1)

if __name__ == "__main__":
    unittest.main()
