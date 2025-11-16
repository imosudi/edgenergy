FROM python:3.10-slim

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Set working directory
WORKDIR /app

# Install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the model first
COPY app/models/nilm.tflite /app/models/nilm.tflite

# Now copy the application code
COPY app/ /app/


# Make wait-for-mqtt executable
RUN chmod +x /app/wait-for-mqtt.sh

# Environment variables
ENV MQTT_BROKER=mqtt \
    MQTT_PORT=1883 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Start script that waits for MQTT before launching main.py
CMD ["/app/wait-for-mqtt.sh"]
