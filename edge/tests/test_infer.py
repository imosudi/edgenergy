import unittest
import numpy as np
from app.preprocess import parse_telemetry, extract_features, TransientDetector
from app.signatures import match_signature
from app.infer import NILMInferenceEngine

class TestEdgeProcessing(unittest.TestCase):
    def setUp(self):
        self.valid_payload = (
            '{"ts": "2025-11-16T05:00:00.123Z", "device_id": "esp32-001", '
            '"house_id": "home-01", "sample_rate": 50, "v": 230.2, "i": 0.48, '
            '"p": 110.5, "ct_sample": [0.12, 0.13, 0.11]}'
        )
        self.invalid_json = '{"ts": "2025-11-16T05:00:00.123Z", "device_id":'
        self.missing_fields = '{"ts": "2025-11-16T05:00:00.123Z", "device_id": "esp32-001"}'

    def test_parse_telemetry_valid(self):
        data = parse_telemetry(self.valid_payload)
        self.assertIsNotNone(data)
        self.assertEqual(data["device_id"], "esp32-001")
        self.assertEqual(data["p"], 110.5)

    def test_parse_telemetry_invalid_json(self):
        data = parse_telemetry(self.invalid_json)
        self.assertIsNone(data)

    def test_parse_telemetry_missing_fields(self):
        data = parse_telemetry(self.missing_fields)
        self.assertIsNone(data)

    def test_extract_features_waveform(self):
        data = parse_telemetry(self.valid_payload)
        features = extract_features(data)
        self.assertTrue(isinstance(features, np.ndarray))
        np.testing.assert_array_almost_equal(features, np.array([0.12, 0.13, 0.11], dtype=np.float32))

    def test_extract_features_scalar_fallback(self):
        payload_no_ct = (
            '{"ts": "2025-11-16T05:00:00.123Z", "device_id": "esp32-001", '
            '"house_id": "home-01", "sample_rate": 50, "v": 230.2, "i": 0.48, '
            '"p": 110.5}'
        )
        data = parse_telemetry(payload_no_ct)
        features = extract_features(data)
        self.assertTrue(isinstance(features, np.ndarray))
        np.testing.assert_array_almost_equal(features, np.array([230.2, 0.48, 110.5], dtype=np.float32))

    def test_transient_detector(self):
        detector = TransientDetector(threshold=50.0)
        dev = "esp32-001"
        
        # First sample sets baseline
        self.assertEqual(detector.detect(dev, 100.0), 0.0)
        # Small change < threshold
        self.assertEqual(detector.detect(dev, 120.0), 0.0)
        # Big change > threshold (transient ON)
        self.assertEqual(detector.detect(dev, 1220.0), 1100.0)
        # Big change > threshold (transient OFF)
        self.assertEqual(detector.detect(dev, 120.0), -1100.0)

    def test_signature_matcher(self):
        # Refrigerator ON transient (~90W)
        self.assertEqual(match_signature(90.0, 140.0), "fridge")
        # Microwave ON transient (~1200W)
        self.assertEqual(match_signature(1200.0, 1250.0), "microwave")
        # HVAC ON transient (~2200W)
        self.assertEqual(match_signature(2200.0, 2250.0), "hvac")
        # Unmatched small change
        self.assertIsNone(match_signature(10.0, 60.0))

    def test_inference_engine_fallback(self):
        engine = NILMInferenceEngine(model_path="non_existent_model.tflite")
        features = np.array([230.0, 0.5, 115.0], dtype=np.float32)
        
        result = engine.predict(features)
        self.assertIn("appliance_state", result)
        self.assertIn("appliance_power", result)
        self.assertIn("anomaly_detected", result)
        self.assertEqual(result["model_mode"], "mock_heuristic")
        
        # Test fridge active load
        self.assertTrue(result["appliance_state"]["fridge"])
        self.assertFalse(result["appliance_state"]["microwave"])
        self.assertEqual(result["appliance_power"]["fridge"], 110.0)
        self.assertEqual(result["appliance_power"]["microwave"], 0.0)

        # Test high power HVAC load
        high_power_features = np.array([230.0, 10.0, 2300.0], dtype=np.float32)
        high_power_result = engine.predict(high_power_features)
        self.assertTrue(high_power_result["appliance_state"]["hvac"])
        self.assertEqual(high_power_result["appliance_power"]["hvac"], 2200.0)

    def test_inference_engine_real_load(self):
        import os
        model_path = os.getenv("MODEL_PATH", "/app/models/nilm.tflite")
        if not os.path.exists(model_path):
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "models",
                "nilm.tflite"
            )

        if os.path.exists(model_path):
            engine = NILMInferenceEngine(model_path=model_path)
            features = np.array([230.0, 0.5, 115.0], dtype=np.float32)
            result = engine.predict(features)
            
            self.assertIn("appliance_state", result)
            self.assertIn("appliance_power", result)
            self.assertIn("anomaly_detected", result)
            
            from app.infer import TFLITE_AVAILABLE
            if TFLITE_AVAILABLE:
                self.assertTrue(engine.is_loaded)
                self.assertEqual(result["model_mode"], "tflite")

if __name__ == "__main__":
    unittest.main()
