import logging
from typing import Dict

logger = logging.getLogger(__name__)

class DemandForecaster:
    def __init__(self, alpha: float = 0.2, beta: float = 0.1, max_history: int = 60):
        self.alpha = alpha
        self.beta = beta
        self.max_history = max_history
        self.history = []
        
        self.level = 0.0
        self.trend = 0.0

    def add_reading(self, reading: float):
        """
        Adds a new active power reading and updates the Holt linear trend model state.
        """
        self.history.append(reading)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Update level and trend using Holt's Linear Trend equations
        if len(self.history) == 1:
            self.level = reading
            self.trend = 0.0
        elif len(self.history) == 2:
            self.level = reading
            self.trend = reading - self.history[0]
        else:
            prev_level = self.level
            prev_trend = self.trend
            
            self.level = self.alpha * reading + (1.0 - self.alpha) * (prev_level + prev_trend)
            self.trend = self.beta * (self.level - prev_level) + (1.0 - self.beta) * prev_trend

    def forecast(self, steps: int) -> float:
        """
        Forecasts the power demand for k steps ahead.
        """
        if not self.history:
            return 0.0
        
        predicted = self.level + float(steps) * self.trend
        return max(0.0, round(predicted, 1))

    def get_forecasts(self) -> Dict[str, float]:
        """
        Returns forecasts for 10 seconds and 30 seconds ahead.
        """
        return {
            "next_10s": self.forecast(10),
            "next_30s": self.forecast(30)
        }
