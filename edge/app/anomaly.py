import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, 
                 nominal_voltage: float = 230.0,
                 voltage_tolerance: float = 0.10,  # 10%
                 overcurrent_threshold: float = 15.0,  # 15 Amps
                 overload_threshold: float = 3600.0,  # 3.6 kW
                 freq_min: float = 49.0,
                 freq_max: float = 51.0):
        self.nominal_voltage = nominal_voltage
        self.voltage_sag_limit = nominal_voltage * (1.0 - voltage_tolerance)
        self.voltage_swell_limit = nominal_voltage * (1.0 + voltage_tolerance)
        self.overcurrent_threshold = overcurrent_threshold
        self.overload_threshold = overload_threshold
        self.freq_min = freq_min
        self.freq_max = freq_max

    def check_telemetry(self, telemetry: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Analyzes telemetry and returns (anomaly_detected, list_of_anomalies).
        """
        anomalies = []
        
        voltage = telemetry.get("v")
        current = telemetry.get("i")
        power = telemetry.get("p")
        freq = telemetry.get("sample_rate")  # sample_rate corresponds to system frequency

        if voltage is not None:
            if voltage < self.voltage_sag_limit:
                anomalies.append("VOLTAGE_SAG")
            elif voltage > self.voltage_swell_limit:
                anomalies.append("VOLTAGE_SWELL")

        if current is not None and current > self.overcurrent_threshold:
            anomalies.append("OVERCURRENT")

        if power is not None and power > self.overload_threshold:
            anomalies.append("OVERLOAD")

        if freq is not None:
            if freq < self.freq_min or freq > self.freq_max:
                anomalies.append("FREQ_DEVIATION")

        detected = len(anomalies) > 0
        return detected, anomalies
