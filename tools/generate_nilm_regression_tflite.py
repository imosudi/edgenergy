import tensorflow as tf
import numpy as np
import os

def generate_synthetic_data(num_samples=10000):
    np.random.seed(42)
    # Generate random active powers in various states:
    # 0: base load only (50W)
    # 1: base + fridge (140W)
    # 2: base + microwave (1150W)
    # 3: base + hvac (2250W)
    # 4: base + fridge + microwave (1240W)
    # 5: base + fridge + hvac (2340W)
    # 6: base + microwave + hvac (3350W)
    # 7: base + fridge + microwave + hvac (3440W)
    
    X = []
    y = []
    
    for _ in range(num_samples):
        state = np.random.randint(0, 8)
        v = np.random.uniform(225.0, 235.0)
        
        p_base = 50.0 + np.random.uniform(-2.0, 2.0)
        p_fridge = 90.0 + np.random.uniform(-5.0, 5.0) if state in [1, 4, 5, 7] else 0.0
        p_microwave = 1100.0 + np.random.uniform(-15.0, 15.0) if state in [2, 4, 6, 7] else 0.0
        p_hvac = 2200.0 + np.random.uniform(-40.0, 40.0) if state in [3, 5, 6, 7] else 0.0
        
        p = p_base + p_fridge + p_microwave + p_hvac
        pf = 0.95 if p > 100 else 0.8
        i = p / (v * pf)
        
        X.append([v, i, p])
        y.append([p_fridge, p_microwave, p_hvac])
        
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

def main():
    print("Generating synthetic disaggregation training dataset...")
    X, y = generate_synthetic_data()
    
    print("Building regression model...")
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(3,), name="input_telemetry"),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(16, activation='relu'),
        tf.keras.layers.Dense(3, activation='linear', name="output_appliances_power")
    ])
    
    model.compile(optimizer='adam', loss='mse')
    
    print("Training model...")
    model.fit(X, y, epochs=15, batch_size=32, verbose=1)
    
    # Convert to TFLite model
    print("Converting to TFLite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    # Determine save path (inside container, output to mounted volume)
    output_dir = "/workspace/edge/models"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "nilm.tflite")

    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"Generated trained regression TFLite model at: {output_path}")

if __name__ == "__main__":
    main()
