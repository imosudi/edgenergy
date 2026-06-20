import time
import json
import random
import logging
import math
from datetime import datetime
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mock_publisher")

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC = "home/energy"

def generate_telemetry(step: int) -> dict:
    """
    Generates realistic home power telemetry, occasionally injecting grid anomalies.
    Appliance cycle:
    - Base load: 50W constant
    - Fridge: 90W (ON for 15 seconds, OFF for 15 seconds)
    - Microwave: 1100W (ON for 10 seconds every 40 seconds)
    - HVAC: 2200W (ON for 20 seconds every 60 seconds)
    
    Grid anomaly cycle (based on step):
    - Steps 50-55 of every 120s cycle: Voltage Swell (~258V)
    - Steps 100-110 of every 120s cycle: Voltage Sag (~192V)
    - Steps 150-160 of every 180s cycle: Overload & Overcurrent (~3850W, ~17.5A)
    - Steps 70-75 of every 150s cycle: Frequency Deviation (48Hz sample rate)
    """
    # Appliance states based on step count
    fridge_on = (step % 30) < 15
    microwave_on = (step % 40) < 10
    hvac_on = (step % 60) < 20

    # Calculate active power
    power = 50.0  # Base load
    if fridge_on:
        power += 90.0 + random.uniform(-5.0, 5.0)
    if microwave_on:
        power += 1100.0 + random.uniform(-20.0, 20.0)
    if hvac_on:
        power += 2200.0 + random.uniform(-50.0, 50.0)

    # Overload / Overcurrent injection
    inject_overload = (step % 180) >= 150 and (step % 180) < 160
    if inject_overload:
        # Simulate EV charger or electric heater turning on
        power += 1500.0 + random.uniform(-30.0, 30.0)

    # Voltage (standard ~230V sinusoidal fluctuations, with sag/swell injection)
    inject_sag = (step % 120) >= 100 and (step % 120) < 110
    inject_swell = (step % 120) >= 50 and (step % 120) < 55
    
    if inject_sag:
        voltage = 192.0 + random.uniform(-1.0, 1.0)
    elif inject_swell:
        voltage = 258.0 + random.uniform(-1.0, 1.0)
    else:
        voltage = 230.0 + 2.0 * math.sin(step * 0.1) + random.uniform(-0.5, 0.5)

    # Current (I = P/V with simple power factor adjustment)
    power_factor = 0.95 if power > 100 else 0.8
    current = power / (voltage * power_factor)

    # Frequency sag/swell injection
    freq = 50
    inject_freq_dev = (step % 150) >= 70 and (step % 150) < 75
    if inject_freq_dev:
        freq = 48

    # Generate current transformer waveform samples (ct_sample)
    samples_count = 10
    ct_samples = []
    for i in range(samples_count):
        angle = (2 * math.pi * i) / samples_count
        sample_val = current * math.sin(angle)
        if microwave_on:
            sample_val += 0.15 * current * math.sin(3 * angle)
        sample_val += random.uniform(-0.02 * current, 0.02 * current)
        ct_samples.append(round(sample_val, 4))

    return {
        "ts": datetime.utcnow().isoformat() + "Z",
        "device_id": "esp32-001",
        "house_id": "home-01",
        "sample_rate": freq,
        "v": round(voltage, 2),
        "i": round(current, 3),
        "p": round(power, 2),
        "ct_sample": ct_samples
    }

def main():
    logger.info("Initializing Mock Telemetry Publisher...")
    client = mqtt.Client(client_id="edgenergy-mock-device")

    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        logger.info(f"Connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
    except Exception as e:
        logger.error(f"Failed to connect to broker: {e}. Ensure docker-compose is running.")
        return

    client.loop_start()

    step = 0
    try:
        while True:
            payload = generate_telemetry(step)
            payload_str = json.dumps(payload)
            
            # Highlight active appliances in logs
            active = ["Base"]
            if (step % 30) < 15: active.append("Fridge")
            if (step % 40) < 10: active.append("Microwave")
            if (step % 60) < 20: active.append("HVAC")
            
            logger.info(f"Publishing Step {step} | Power: {payload['p']}W | Active: {', '.join(active)}")
            client.publish(TOPIC, payload_str)
            
            step += 1
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping mock publisher...")
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Mock publisher stopped.")

if __name__ == "__main__":
    main()
