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
            
            # Post-process output
            # For a basic NILM classifier, the output might be appliance activation probabilities
            # E.g. [p_fridge, p_microwave, p_hvac] or a single scalar probability
            predictions = output_data.tolist()[0]
            
            # Handle classification/prediction logic
            # Let's say if prediction probability > 0.5, appliance is ON
            if isinstance(predictions, list):
                appliance_state = {
                    "fridge": predictions[0] > 0.5 if len(predictions) > 0 else False,
                    "microwave": predictions[1] > 0.5 if len(predictions) > 1 else False,
                    "hvac": predictions[2] > 0.5 if len(predictions) > 2 else False,
                    "scores": predictions
                }
            else:
                appliance_state = {
                    "appliance_active": predictions > 0.5,
                    "score": predictions
                }

            # Anomaly logic (e.g. if overall active power is higher than a threshold, or by model output)
            anomaly_detected = False
            
            return {
                "appliance_state": appliance_state,
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
        # If we have 3 features [v, i, p]
        power = float(features[2]) if len(features) >= 3 else 100.0
        
        # Simple heuristic-based disaggregation for demo
        fridge_active = 80.0 < power < 150.0
        microwave_active = 800.0 < power < 1500.0
        hvac_active = power > 2000.0
        
        anomaly_detected = power > 3500.0  # Anomaly if drawing > 3.5kW
        
        return {
            "appliance_state": {
                "fridge": fridge_active,
                "microwave": microwave_active,
                "hvac": hvac_active,
                "raw_power": power
            },
            "anomaly_detected": anomaly_detected,
            "model_mode": "mock_heuristic"
        }
