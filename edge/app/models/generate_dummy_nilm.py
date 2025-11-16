import tensorflow as tf
import numpy as np

# -------- Dummy NILM Tiny Model ----------
# Input shape: (1, 10)
# Output: simple linear regression output
# -----------------------------------------

def create_dummy_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(10,)),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(4, activation="relu"),
        tf.keras.layers.Dense(1)   # predicted watts
    ])
    model.compile(optimizer="adam", loss="mse")
    return model


def convert_to_tflite(model, output_path="nilm.tflite"):
    # Create fake training data so weights aren't zeros
    X = np.random.rand(100, 10).astype(np.float32)
    y = np.random.rand(100, 1).astype(np.float32)

    model.fit(X, y, epochs=3, verbose=0)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    with open(output_path, "wb") as f:
        f.write(tflite_model)

    print(f"[OK] Dummy NILM model created → {output_path}")


if __name__ == "__main__":
    model = create_dummy_model()
    convert_to_tflite(model, "nilm.tflite")
