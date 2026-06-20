import unittest
from app.forecaster import DemandForecaster

class TestDemandForecaster(unittest.TestCase):
    def setUp(self):
        self.forecaster = DemandForecaster(alpha=0.2, beta=0.1, max_history=10)

    def test_empty_forecast(self):
        self.assertEqual(self.forecaster.forecast(5), 0.0)

    def test_single_reading(self):
        self.forecaster.add_reading(100.0)
        self.assertEqual(self.forecaster.level, 100.0)
        self.assertEqual(self.forecaster.trend, 0.0)
        self.assertEqual(self.forecaster.forecast(5), 100.0)

    def test_two_readings(self):
        self.forecaster.add_reading(100.0)
        self.forecaster.add_reading(110.0)
        self.assertEqual(self.forecaster.level, 110.0)
        self.assertEqual(self.forecaster.trend, 10.0)
        # forecast = 110 + 5 * 10 = 160
        self.assertEqual(self.forecaster.forecast(5), 160.0)

    def test_multiple_readings_trend(self):
        # Linear increasing trend: 10, 20, 30, 40...
        self.forecaster.add_reading(10.0)
        self.forecaster.add_reading(20.0)
        self.forecaster.add_reading(30.0)
        
        # Test level and trend calculations:
        # L0 = 10, T0 = 0
        # L1 = 20, T1 = 10
        # L2 = alpha * 30 + (1-alpha)*(L1 + T1) = 0.2 * 30 + 0.8 * (20 + 10) = 6 + 24 = 30
        # T2 = beta * (L2 - L1) + (1-beta)*T1 = 0.1 * (30 - 20) + 0.9 * 10 = 1 + 9 = 10
        self.assertAlmostEqual(self.forecaster.level, 30.0)
        self.assertAlmostEqual(self.forecaster.trend, 10.0)
        
        # forecast 10 steps ahead: L2 + 10 * T2 = 30 + 100 = 130
        self.assertAlmostEqual(self.forecaster.forecast(10), 130.0)

    def test_get_forecasts(self):
        self.forecaster.add_reading(100.0)
        self.forecaster.add_reading(110.0)
        self.forecaster.add_reading(120.0)
        # L0 = 100, T0 = 0
        # L1 = 110, T1 = 10
        # L2 = 0.2 * 120 + 0.8 * 120 = 120
        # T2 = 0.1 * 10 + 0.9 * 10 = 10
        forecasts = self.forecaster.get_forecasts()
        self.assertEqual(forecasts["next_10s"], 120 + 10 * 10)  # 220
        self.assertEqual(forecasts["next_30s"], 120 + 30 * 10)  # 420

    def test_negative_clipping(self):
        # Decreasing trend: 100, 90, 80...
        self.forecaster.add_reading(100.0)
        self.forecaster.add_reading(80.0)
        # L1 = 80, T1 = -20
        # Forecast 10 steps: 80 - 200 = -120 -> should clip to 0.0
        self.assertEqual(self.forecaster.forecast(10), 0.0)

    def test_history_capping(self):
        # max_history is 10
        for i in range(15):
            self.forecaster.add_reading(float(i))
        self.assertEqual(len(self.forecaster.history), 10)
        self.assertEqual(self.forecaster.history[-1], 14.0)

if __name__ == "__main__":
    unittest.main()
