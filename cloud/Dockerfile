FROM python:3.10-slim

WORKDIR /app

# Install utility dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set running command
ENTRYPOINT ["python", "-u", "services/sync.py"]
