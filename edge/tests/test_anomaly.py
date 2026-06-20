import unittest
from app.anomaly import AnomalyDetector

class TestAnomalyDetector(unittest.TestCase):
    def setUp(self):
        self.detector = AnomalyDetector(
            nominal_voltage=230.0,
            voltage_tolerance=0.10,
            overcurrent_threshold=15.0,
            overload_threshold=3600.0,
            freq_min=49.0,
            freq_max=51.0
        )

    def test_normal_conditions(self):
        telemetry = {"v": 230.0, "i": 2.5, "p": 575.0, "sample_rate": 50}
        detected, anomalies = self.detector.check_telemetry(telemetry)
        self.assertFalse(detected)
        self.assertEqual(anomalies, [])

    def test_voltage_sag(self):
        # 230 * 0.90 = 207.0. Voltage 205.0 is a sag.
        telemetry = {"v": 205.0, "i": 2.5, "p": 512.5, "sample_rate": 50}
        detected, anomalies = self.detector.check_telemetry(telemetry)
        self.assertTrue(detected)
        self.assertIn("VOLTAGE_SAG", anomalies)

    def test_voltage_swell(self):
        # 230 * 1.10 = 253.0. Voltage 255.0 is a swell.
        telemetry = {"v": 255.0, "i": 2.5, "p": 637.5, "sample_rate": 50}
        detected, anomalies = self.detector.check_telemetry(telemetry)
        self.assertTrue(detected)
        self.assertIn("VOLTAGE_SWELL", anomalies)

    def test_overcurrent(self):
        # Current 16.0 A > 15.0 A threshold
        telemetry = {"v": 230.0, "i": 16.0, "p": 3680.0, "sample_rate": 50}
        detected, anomalies = self.detector.check_telemetry(telemetry)
        self.assertTrue(detected)
        self.assertIn("OVERCURRENT", anomalies)

    def test_overload(self):
        # Power 3700.0 W > 3600.0 W threshold
        telemetry = {"v": 230.0, "i": 14.0, "p": 3700.0, "sample_rate": 50}
        detected, anomalies = self.detector.check_telemetry(telemetry)
        self.assertTrue(detected)
        self.assertIn("OVERLOAD", anomalies)

    def test_frequency_deviation(self):
        # Frequency (sample_rate) 48 Hz is out of [49, 51]
        telemetry = {"v": 230.0, "i": 2.5, "p": 575.0, "sample_rate": 48}
        detected, anomalies = self.detector.check_telemetry(telemetry)
        self.assertTrue(detected)
        self.assertIn("FREQ_DEVIATION", anomalies)

    def test_multiple_anomalies(self):
        telemetry = {"v": 200.0, "i": 17.0, "p": 3400.0, "sample_rate": 52}
        detected, anomalies = self.detector.check_telemetry(telemetry)
        self.assertTrue(detected)
        self.assertIn("VOLTAGE_SAG", anomalies)
        self.assertIn("OVERCURRENT", anomalies)
        self.assertIn("FREQ_DEVIATION", anomalies)
        self.assertNotIn("OVERLOAD", anomalies)

if __name__ == "__main__":
    unittest.main()
