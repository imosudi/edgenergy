import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

def parse_telemetry(payload_str: str) -> dict:
    """
    Parses and validates the raw JSON telemetry payload.
    Returns the parsed dictionary if valid, or None if invalid.
    """
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON telemetry: {e}")
        return None

    # Required fields
    required_fields = ["ts", "device_id", "house_id", "v", "i", "p"]
    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field '{field}' in telemetry data.")
            return None

    return data

def extract_features(data: dict) -> np.ndarray:
    """
    Extracts features for the TFLite NILM/anomaly model.
    If 'ct_sample' is present, converts it to a float32 numpy array.
    Otherwise, constructs a feature vector from scalar metrics: [voltage, current, power].
    """
    if "ct_sample" in data and isinstance(data["ct_sample"], list) and len(data["ct_sample"]) > 0:
        # Convert waveform to numpy array and ensure it is float32
        return np.array(data["ct_sample"], dtype=np.float32)
    else:
        # Fallback to scalar features
        return np.array([data["v"], data["i"], data["p"]], dtype=np.float32)

class TransientDetector:
    def __init__(self, threshold: float = 50.0):
        self.threshold = threshold
        self.last_power = {} # device_id -> last_power

    def detect(self, device_id: str, current_power: float) -> float:
        """
        Detects significant power transitions (transients).
        Returns the delta power if a transient is detected (i.e. |delta| > threshold).
        Otherwise returns 0.0.
        """
        if device_id not in self.last_power:
            self.last_power[device_id] = current_power
            return 0.0 # First sample, no transient can be calculated yet
        
        last = self.last_power[device_id]
        delta = current_power - last
        self.last_power[device_id] = current_power
        
        if abs(delta) >= self.threshold:
            return delta
        return 0.0
