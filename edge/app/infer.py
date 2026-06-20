import logging
import numpy as np
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try importing tflite-runtime or tensorflow.lite
TFLITE_AVAILABLE = False
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import tensorflow.lite as tflite
        TFLITE_AVAILABLE = True
    except ImportError:
        logger.warning("Neither tflite_runtime nor tensorflow.lite is available. Running in MOCK inference mode.")

class NILMInferenceEngine:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.is_loaded = False
        
        if TFLITE_AVAILABLE:
            self.load_model()
        else:
            logger.info("Mock engine initialized without loading a model.")

    def load_model(self):
        try:
            self.interpreter = tflite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.is_loaded = True
            logger.info(f"Successfully loaded TFLite model from {self.model_path}")
            logger.info(f"Input details: {self.input_details}")
            logger.info(f"Output details: {self.output_details}")
        except Exception as e:
            logger.error(f"Failed to load TFLite model from {self.model_path}: {e}. Falling back to MOCK mode.")
            self.is_loaded = False

    def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """
        Executes model inference on preprocessed features.
        Returns a dictionary containing:
          - "appliance_state": Prediction scores or classifications
          - "anomaly_detected": Boolean flag
        """
        if not self.is_loaded:
            return self._mock_predict(features)

        try:
            input_detail = self.input_details[0]
            input_shape = input_detail["shape"]
            input_dtype = input_detail["dtype"]

            # Reshape features to match model's expected input shape
            # TFLite models usually expect a batch dimension, e.g. [1, features_len]
            prepared_features = features.astype(input_dtype)
            
            # If model expects batch dimension and features does not have it, prepend
            if len(input_shape) > len(prepared_features.shape):
                # E.g. shape is [1, 3] and prepared_features is [3] -> [1, 3]
                # If shape is [1, N] and prepared_features is [M], we need to pad/slice
                expected_len = input_shape[-1]
                actual_len = prepared_features.shape[0]
                if actual_len < expected_len:
                    prepared_features = np.pad(prepared_features, (0, expected_len - actual_len), 'constant')
                elif actual_len > expected_len:
                    prepared_features = prepared_features[:expected_len]
                
                prepared_features = np.expand_dims(prepared_features, axis=0)

            self.interpreter.set_tensor(input_detail["index"], prepared_features)
            self.interpreter.invoke()

            # Retrieve output tensor
            output_detail = self.output_details[0]
            output_data = self.interpreter.get_tensor(output_detail["index"])
            
            predictions = output_data.tolist()[0]
            
            # Handle regression predictions: outputs are continuous power draws in Watts
            if isinstance(predictions, list) and len(predictions) >= 3:
                p_fridge = max(0.0, float(predictions[0]))
                p_microwave = max(0.0, float(predictions[1]))
                p_hvac = max(0.0, float(predictions[2]))
                
                appliance_power = {
                    "fridge": round(p_fridge, 1),
                    "microwave": round(p_microwave, 1),
                    "hvac": round(p_hvac, 1)
                }
                # Determine state flag: active if power draw is above threshold
                appliance_state = {
                    "fridge": p_fridge > 15.0,
                    "microwave": p_microwave > 50.0,
                    "hvac": p_hvac > 50.0
                }
            else:
                p_val = max(0.0, float(predictions)) if isinstance(predictions, (int, float)) else 0.0
                appliance_power = {"appliance": round(p_val, 1)}
                appliance_state = {"appliance_active": p_val > 50.0}

            # Anomaly logic (e.g. if overall active power is higher than a threshold)
            # Or by checking features/voltage
            voltage = float(features[0]) if len(features) >= 1 else 230.0
            power = float(features[2]) if len(features) >= 3 else 0.0
            anomaly_detected = power > 3500.0 or voltage < 180.0 or voltage > 260.0
            
            return {
                "appliance_state": appliance_state,
                "appliance_power": appliance_power,
                "anomaly_detected": anomaly_detected,
                "model_mode": "tflite"
            }

        except Exception as e:
            logger.error(f"Inference error: {e}. Falling back to mock prediction.")
            return self._mock_predict(features)

    def _mock_predict(self, features: np.ndarray) -> Dict[str, Any]:
        """
        Mock inference logic when TFLite model is not loaded or errors.
        """
        power = float(features[2]) if len(features) >= 3 else 100.0
        
        # Heuristic disaggregation based on raw aggregate power ranges
        fridge_active = (80.0 <= power <= 220.0) or (880.0 <= power <= 1400.0) or (2080.0 <= power <= 2600.0) or (power > 3000.0)
        microwave_active = (1000.0 <= power <= 1500.0) or (3000.0 <= power <= 3600.0)
        hvac_active = power >= 2000.0
        
        p_fridge = 110.0 if fridge_active else 0.0
        p_microwave = 1200.0 if microwave_active else 0.0
        p_hvac = 2200.0 if hvac_active else 0.0
        
        anomaly_detected = power > 3500.0
        
        return {
            "appliance_state": {
                "fridge": fridge_active,
                "microwave": microwave_active,
                "hvac": hvac_active
            },
            "appliance_power": {
                "fridge": p_fridge,
                "microwave": p_microwave,
                "hvac": p_hvac
            },
            "anomaly_detected": anomaly_detected,
            "model_mode": "mock_heuristic"
        }
