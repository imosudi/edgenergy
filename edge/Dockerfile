FROM python:3.10-slim

# Install system dependencies (like netcat for checking MQTT port status)
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY app/requirements.txt /app/app/requirements.txt
RUN pip install --no-cache-dir -r /app/app/requirements.txt

# Copy the application source code and models
COPY app/ /app/app/
COPY models/ /app/models/

# Make the wait-for-mqtt script executable
RUN chmod +x /app/app/wait-for-mqtt.sh

# Run the application using python -m app.main
ENTRYPOINT ["/app/app/wait-for-mqtt.sh"]
CMD ["python", "-m", "app.main"]
