import tensorflow as tf
import numpy as np
import os

def main():
    # Define a simple model that takes [v, i, p] (shape: [1, 3]) 
    # and outputs probability of activation for 3 appliances (shape: [1, 3])
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(3,), name="input_telemetry"),
        tf.keras.layers.Dense(8, activation='relu'),
        tf.keras.layers.Dense(3, activation='sigmoid', name="output_appliances")
    ])

    # Convert to TFLite model
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    # Determine save path (inside container, output to mounted volume)
    output_dir = "/workspace/edge/models"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "nilm.tflite")

    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"Generated dummy TFLite model at: {output_path}")

if __name__ == "__main__":
    main()
