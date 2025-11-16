import time
import threading
from mqtt_client import build_client
from infer import InferenceEngine
from config import EDGE_ID, HOUSE_ID
import json

queue = []
client = build_client(queue)
engine = InferenceEngine()

def mqtt_loop():
    client.loop_forever()

def processing_loop():
    while True:
        if queue:
            item = queue.pop(0)
            ct_samples = item.get('ct_sample', [])
            preds, latency = engine.infer_nilm(ct_samples)
            if preds:
                msg = {
                    "ts": item.get('ts'),
                    "edge_id": EDGE_ID,
                    "house_id": HOUSE_ID,
                    "model": "nilm-v1.tflite",
                    "inference_type": "nilm",
                    "predictions": preds,
                    "latency_ms": latency
                }
                client.publish(
                    f"home/{HOUSE_ID}/edge/{EDGE_ID}/inference",
                    json.dumps(msg)
                )
                print("Published inference", msg)
        else:
            time.sleep(0.1)

if __name__ == "__main__":
    threading.Thread(target=mqtt_loop, daemon=True).start()
    processing_loop()
