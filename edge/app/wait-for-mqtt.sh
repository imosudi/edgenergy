#!/bin/sh
# wait-for-mqtt.sh

set -e

host="${MQTT_BROKER_HOST:-localhost}"
port="${MQTT_BROKER_PORT:-1883}"

echo "Waiting for MQTT broker at $host:$port..."

# Use netcat (nc) to check if the broker port is open
until nc -z -w 2 "$host" "$port"; do
  echo "MQTT broker is unavailable - retrying in 2 seconds..."
  sleep 2
done

echo "MQTT is up! Starting application..."
exec "$@"
