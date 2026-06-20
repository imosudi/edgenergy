import unittest
import numpy as np
from app.preprocess import parse_telemetry, extract_features
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
        # Remove ct_sample
        payload_no_ct = (
            '{"ts": "2025-11-16T05:00:00.123Z", "device_id": "esp32-001", '
            '"house_id": "home-01", "sample_rate": 50, "v": 230.2, "i": 0.48, '
            '"p": 110.5}'
        )
        data = parse_telemetry(payload_no_ct)
        features = extract_features(data)
        self.assertTrue(isinstance(features, np.ndarray))
        np.testing.assert_array_almost_equal(features, np.array([230.2, 0.48, 110.5], dtype=np.float32))

    def test_inference_engine_fallback(self):
        # Instantiate with a non-existent model to force mock fallback mode
        engine = NILMInferenceEngine(model_path="non_existent_model.tflite")
        features = np.array([230.0, 0.5, 115.0], dtype=np.float32)
        
        result = engine.predict(features)
        self.assertIn("appliance_state", result)
        self.assertIn("anomaly_detected", result)
        self.assertIn("model_mode", result)
        self.assertEqual(result["model_mode"], "mock_heuristic")
        
        # Test low power (base load, fridge active, other appliances off)
        self.assertTrue(result["appliance_state"]["fridge"])
        self.assertFalse(result["appliance_state"]["microwave"])
        self.assertFalse(result["appliance_state"]["hvac"])
        self.assertFalse(result["anomaly_detected"])

        # Test high power (HVAC and Microwave active, triggers anomaly)
        high_power_features = np.array([230.0, 16.0, 3600.0], dtype=np.float32)
        high_power_result = engine.predict(high_power_features)
        self.assertTrue(high_power_result["appliance_state"]["hvac"])
        self.assertTrue(high_power_result["anomaly_detected"])

    def test_inference_engine_real_load(self):
        import os
        model_path = os.getenv("MODEL_PATH", "/app/models/nilm.tflite")
        # Fallback for local testing if running on host
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
            self.assertIn("anomaly_detected", result)
            self.assertIn("model_mode", result)
            
            # If tflite-runtime/tensorflow is available (like inside container), it should load successfully
            from app.infer import TFLITE_AVAILABLE
            if TFLITE_AVAILABLE:
                self.assertTrue(engine.is_loaded)
                self.assertEqual(result["model_mode"], "tflite")

if __name__ == "__main__":
    unittest.main()
