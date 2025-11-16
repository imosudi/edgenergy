import time
import numpy as np
from tflite_runtime.interpreter import Interpreter
from preprocess import extract_features_from_ct
from config import MODEL_PATH, EDGE_ID, HOUSE_ID, INFERENCE_THRESHOLD

class InferenceEngine:
    def __init__(self, model_path=MODEL_PATH):
        self.interp = Interpreter(model_path=model_path)
        self.interp.allocate_tensors()
        inp = self.interp.get_input_details()
        out = self.interp.get_output_details()
        self.input_index = inp[0]['index']
        self.output_index = out[0]['index']

    def infer_nilm(self, ct_samples):
        start = time.time()
        features = extract_features_from_ct(ct_samples).reshape((1, -1))
        self.interp.set_tensor(self.input_index, features)
        self.interp.invoke()
        out = self.interp.get_tensor(self.output_index)[0]
        latency_ms = (time.time() - start) * 1000.0

        labels = ["washing_machine", "fridge", "microwave", "unknown"]
        preds = {labels[i]: float(out[i]) for i in range(len(out))}
        preds = {k: v for k, v in preds.items() if v >= INFERENCE_THRESHOLD}
        return preds, latency_ms
