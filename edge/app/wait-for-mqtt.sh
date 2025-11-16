#!/bin/sh
python3 - << 'EOF'
import time
import socket

host = "mqtt"
port = 1883

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            print("MQTT is up!")
            break
    except OSError:
        print("Waiting for MQTT...")
        time.sleep(1)
EOF

exec python3 main.py
