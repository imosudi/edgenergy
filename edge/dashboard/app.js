// Web Dashboard MQTT Logic
const brokerHost = window.location.hostname || "localhost";
const brokerPort = 9001;
const clientId = "edgenergy-web-client-" + Math.random().toString(16).substr(2, 8);

const topics = {
  telemetry: "home/energy",
  predictions: "home/predictions"
};

// UI Elements
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const powerVal = document.getElementById("power-val");
const powerBar = document.getElementById("power-progress-bar");
const voltageVal = document.getElementById("voltage-val");
const currentVal = document.getElementById("current-val");
const rateVal = document.getElementById("rate-val");
const alertsLog = document.getElementById("alerts-log");

// Appliance Elements
const fridgeItem = document.getElementById("appliance-fridge");
const microwaveItem = document.getElementById("appliance-microwave");
const hvacItem = document.getElementById("appliance-hvac");

// Initialize Paho MQTT Client
let client = null;
let lastLogTime = 0; // Throttling for logs to prevent visual lag

function initMQTT() {
  console.log(`Connecting to MQTT Broker on ws://${brokerHost}:${brokerPort}/mqtt`);
  client = new Paho.MQTT.Client(brokerHost, brokerPort, clientId);
  
  client.onConnectionLost = onConnectionLost;
  client.onMessageArrived = onMessageArrived;

  const connectOptions = {
    onSuccess: onConnect,
    onFailure: onFailure,
    useSSL: false,
    reconnect: true,
    keepAliveInterval: 30
  };

  client.connect(connectOptions);
}

function onConnect() {
  console.log("MQTT Connection established via WebSockets.");
  statusDot.className = "status-dot connected";
  statusText.textContent = "Broker Connected";
  
  // Clear placeholder log
  alertsLog.innerHTML = "";
  addLogEntry("info", "System initialized. Connected to MQTT broker WebSockets interface.");

  // Subscribe to topics
  client.subscribe(topics.telemetry);
  client.subscribe(topics.predictions);
  addLogEntry("info", `Subscribed to telemetry [${topics.telemetry}] and predictions [${topics.predictions}]`);
}

function onFailure(err) {
  console.error("MQTT Connection failed:", err);
  statusDot.className = "status-dot disconnected";
  statusText.textContent = "Connection Failed. Retrying...";
  setTimeout(initMQTT, 5000);
}

function onConnectionLost(responseObject) {
  console.warn("MQTT Connection lost:", responseObject.errorMessage);
  statusDot.className = "status-dot disconnected";
  statusText.textContent = "Connection Lost. Reconnecting...";
  addLogEntry("anomaly", "MQTT Broker Connection lost: " + responseObject.errorMessage);
  if (responseObject.errorCode !== 0) {
    setTimeout(initMQTT, 3000);
  }
}

function onMessageArrived(message) {
  const topic = message.destinationName;
  const payload = message.payloadString;

  try {
    const data = JSON.parse(payload);
    
    if (topic === topics.telemetry) {
      updateTelemetryUI(data);
    } else if (topic === topics.predictions) {
      updatePredictionsUI(data);
    }
  } catch (e) {
    console.error("Error parsing message payload:", e, payload);
  }
}

// UI updates
function updateTelemetryUI(data) {
  // Update numerical indicators
  powerVal.textContent = parseFloat(data.p).toFixed(2);
  voltageVal.textContent = parseFloat(data.v).toFixed(1);
  currentVal.textContent = parseFloat(data.i).toFixed(3);
  rateVal.textContent = data.sample_rate || "--";

  // Update progress bar (max scale capped at 4000W for visualization)
  const maxPower = 4000;
  const percent = Math.min((data.p / maxPower) * 100, 100);
  powerBar.style.width = percent + "%";

  // Throttled log entry to avoid UI locking (max once every 5 seconds)
  const now = Date.now();
  if (now - lastLogTime > 5000) {
    addLogEntry("info", `Raw telemetry parsed: aggregate demand = ${data.p}W | current draw = ${data.i}A`);
    lastLogTime = now;
  }
}

function updatePredictionsUI(data) {
  const state = data.appliance_state;
  
  if (!state) return;

  // 1. Update Fridge status
  const fridgeActive = !!state.fridge;
  updateApplianceUI(fridgeItem, "active-fridge", fridgeActive);

  // 2. Update Microwave status
  const microwaveActive = !!state.microwave;
  updateApplianceUI(microwaveItem, "active-microwave", microwaveActive);

  // 3. Update HVAC status
  const hvacActive = !!state.hvac;
  updateApplianceUI(hvacItem, "active-hvac", hvacActive);

  // 4. Handle Anomaly logs
  if (data.anomaly_detected) {
    addLogEntry(
      "anomaly",
      `CRITICAL ALERT: Overcurrent / anomaly flag detected on Node ${data.device_id}. Check load draws!`
    );
  }

  // 5. General prediction output disaggregation log
  const activeAppliances = [];
  if (fridgeActive) activeAppliances.push("Fridge");
  if (microwaveActive) activeAppliances.push("Microwave");
  if (hvacActive) activeAppliances.push("HVAC");

  const disaggregationStr = activeAppliances.length > 0 
    ? `Active: ${activeAppliances.join(", ")}` 
    : "No major appliances detected";
    
  addLogEntry("prediction", `TinyML disaggregation output: ${disaggregationStr} [Model: ${data.model_mode}]`);
}

function updateApplianceUI(element, activeClass, isActive) {
  const badgeIndicator = element.querySelector(".status-indicator");
  const badgeLabel = element.querySelector(".status-lbl");

  if (isActive) {
    element.classList.add(activeClass);
    badgeLabel.textContent = "ON";
  } else {
    element.classList.remove(activeClass);
    badgeLabel.textContent = "OFF";
  }
}

function addLogEntry(type, message) {
  const entry = document.createElement("div");
  entry.className = `log-entry ${type}`;

  const timeStr = new Date().toLocaleTimeString();

  entry.innerHTML = `
    <div class="log-header">
      <span class="log-type">${type}</span>
      <span class="log-time">${timeStr}</span>
    </div>
    <div class="log-body">${message}</div>
  `;

  alertsLog.insertBefore(entry, alertsLog.firstChild);

  // Cap log history length
  if (alertsLog.children.length > 50) {
    alertsLog.removeChild(alertsLog.lastChild);
  }
}

// Start MQTT client on load
window.addEventListener("load", initMQTT);
