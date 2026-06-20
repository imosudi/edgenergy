// Web Dashboard MQTT Logic
const brokerHost = window.location.hostname || "localhost";
const brokerPort = 9001;
const clientId = "edgenergy-web-client-" + Math.random().toString(16).substr(2, 8);

const topics = {
  telemetry: "home/energy",
  predictions: "home/predictions",
  events: "home/events",
  alerts: "home/alerts",
  status_cloud: "home/status/cloud"
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

// Appliance Status Badge Elements
const fridgeItem = document.getElementById("appliance-fridge");
const microwaveItem = document.getElementById("appliance-microwave");
const hvacItem = document.getElementById("appliance-hvac");

// Progress bar allocation elements
const fridgePowerVal = document.getElementById("power-fridge-val");
const fridgePowerProgress = document.getElementById("power-fridge-progress");
const microwavePowerVal = document.getElementById("power-microwave-val");
const microwavePowerProgress = document.getElementById("power-microwave-progress");
const hvacPowerVal = document.getElementById("power-hvac-val");
const hvacPowerProgress = document.getElementById("power-hvac-progress");
const eventsFeedLog = document.getElementById("events-feed-log");

// Initialize Paho MQTT Client and Chart variables
let client = null;
let lastLogTime = 0; // Throttling for logs to prevent visual lag

let demandChart = null;
const maxHistoryPoints = 30;
const historyData = Array(maxHistoryPoints).fill(0);
const chartLabels = [...Array(maxHistoryPoints).fill(""), "+10s", "+30s"];

function initChart() {
  const canvas = document.getElementById('demand-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  // Create gradient for history line fill
  const gradHistory = ctx.createLinearGradient(0, 0, 0, 180);
  gradHistory.addColorStop(0, 'rgba(2, 132, 199, 0.15)');
  gradHistory.addColorStop(1, 'rgba(2, 132, 199, 0.0)');

  demandChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: chartLabels,
      datasets: [
        {
          label: 'Historical Load',
          data: [...historyData, null, null],
          borderColor: '#0284c7',
          backgroundColor: gradHistory,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: true,
          tension: 0.3
        },
        {
          label: 'Demand Forecast',
          data: [...Array(maxHistoryPoints - 1).fill(null), 0, 0, 0],
          borderColor: '#f59e0b',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 4,
          pointBackgroundColor: '#f59e0b',
          fill: false,
          tension: 0.0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            font: { family: 'Inter', size: 10 },
            boxWidth: 12
          }
        }
      },
      scales: {
        x: {
          grid: { display: false }
        },
        y: {
          min: 0,
          suggestedMax: 1500,
          grid: { color: '#e2e8f0' },
          ticks: {
            font: { family: 'Inter', size: 9 },
            callback: function(value) { return value + ' W'; }
          }
        }
      }
    }
  });
}

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
  client.subscribe(topics.events);
  client.subscribe(topics.alerts);
  client.subscribe(topics.status_cloud);
  addLogEntry("info", `Subscribed to telemetry, predictions, events, alerts, and cloud status.`);
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
    } else if (topic === topics.events) {
      updateEventsFeedUI(data);
    } else if (topic === topics.alerts) {
      updateAlertsUI(data);
    } else if (topic === topics.status_cloud) {
      updateCloudStatusUI(data);
    }
  } catch (e) {
    console.error("Error parsing message payload:", e, payload);
  }
}

// UI updates
function updateTelemetryUI(data) {
  // Update numerical indicators
  const p = parseFloat(data.p);
  powerVal.textContent = p.toFixed(2);
  voltageVal.textContent = parseFloat(data.v).toFixed(1);
  currentVal.textContent = parseFloat(data.i).toFixed(3);
  rateVal.textContent = data.sample_rate || "--";

  // Update history buffer
  historyData.push(p);
  if (historyData.length > maxHistoryPoints) {
    historyData.shift();
  }

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
  const power = data.appliance_power;
  
  if (!state) return;

  // 1. Update Fridge status and power breakdown
  const fridgeActive = !!state.fridge;
  updateApplianceUI(fridgeItem, "active-fridge", fridgeActive);
  
  if (power) {
    const pFridge = parseFloat(power.fridge || 0.0);
    fridgePowerVal.textContent = pFridge.toFixed(1);
    const fridgePercent = Math.min((pFridge / 200.0) * 100, 100);
    fridgePowerProgress.style.width = fridgePercent + "%";
  }

  // 2. Update Microwave status and power breakdown
  const microwaveActive = !!state.microwave;
  updateApplianceUI(microwaveItem, "active-microwave", microwaveActive);
  
  if (power) {
    const pMicro = parseFloat(power.microwave || 0.0);
    microwavePowerVal.textContent = pMicro.toFixed(1);
    const microPercent = Math.min((pMicro / 1500.0) * 100, 100);
    microwavePowerProgress.style.width = microPercent + "%";
  }

  // 3. Update HVAC status and power breakdown
  const hvacActive = !!state.hvac;
  updateApplianceUI(hvacItem, "active-hvac", hvacActive);
  
  if (power) {
    const pHvac = parseFloat(power.hvac || 0.0);
    hvacPowerVal.textContent = pHvac.toFixed(1);
    const hvacPercent = Math.min((pHvac / 3500.0) * 100, 100);
    hvacPowerProgress.style.width = hvacPercent + "%";
  }

  // 4. Update demand forecast chart
  if (demandChart && data.forecast) {
    const currentVal = historyData[historyData.length - 1];
    demandChart.data.datasets[0].data = [...historyData, null, null];
    demandChart.data.datasets[1].data = [
      ...Array(maxHistoryPoints - 1).fill(null),
      currentVal,
      data.forecast.next_10s,
      data.forecast.next_30s
    ];
    demandChart.update('none');
  }

  // 5. Toggle Anomaly Banner and overlays
  const anomalyBanner = document.getElementById("anomaly-alert-banner");
  const anomalyText = document.getElementById("anomaly-alert-text");
  const mainPowerCard = document.querySelector(".main-power-card");

  if (data.anomaly_detected && data.anomalies && data.anomalies.length > 0) {
    anomalyBanner.classList.remove("d-none");
    anomalyBanner.classList.add("d-flex");
    anomalyText.textContent = "Active anomalies: " + data.anomalies.join(", ");
    mainPowerCard.classList.add("anomaly-active-overlay");
  } else {
    anomalyBanner.classList.add("d-none");
    anomalyBanner.classList.remove("d-flex");
    mainPowerCard.classList.remove("anomaly-active-overlay");
  }

  // 6. General prediction output disaggregation log
  const activeAppliances = [];
  if (fridgeActive) activeAppliances.push("Fridge");
  if (microwaveActive) activeAppliances.push("Microwave");
  if (hvacActive) activeAppliances.push("HVAC");

  const disaggregationStr = activeAppliances.length > 0 
    ? `Active: ${activeAppliances.join(", ")}` 
    : "No major appliances detected";
    
  addLogEntry("prediction", `TinyML disaggregation output: ${disaggregationStr} [Model: ${data.model_mode}]`);
}

function updateAlertsUI(data) {
  const type = data.anomaly_detected ? "anomaly" : "info";
  const anomaliesText = data.anomalies && data.anomalies.length > 0
    ? ` [Active: ${data.anomalies.join(", ")}]`
    : "";
  addLogEntry(type, `Alert update: ${data.alert}${anomaliesText}`);
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

function updateEventsFeedUI(data) {
  // Clear placeholder if it's there
  const placeholder = eventsFeedLog.querySelector(".events-placeholder");
  if (placeholder) {
    eventsFeedLog.innerHTML = "";
  }

  const item = document.createElement("div");
  item.className = "event-log-item";
  
  const appNames = {
    fridge: "Refrigerator",
    microwave: "Microwave Oven",
    hvac: "HVAC System"
  };
  
  const appName = appNames[data.appliance] || data.appliance;
  const badgeClass = data.event === "ON" ? "on" : "off";
  const sigBadge = data.signature_verified 
    ? '<span class="sig-badge">✓ Signature Verified</span>' 
    : '<span class="sig-badge text-warning" style="background: rgba(217, 119, 6, 0.1); color: var(--color-warning); border: 1px solid rgba(217, 119, 6, 0.15);">? Signature Unmatched</span>';
  
  const timeStr = new Date().toLocaleTimeString();
  
  item.innerHTML = `
    <div>
      <span class="fw-semibold text-dark">${appName}</span>
      <span class="event-badge ${badgeClass} ms-2">${data.event}</span>
      <div class="text-muted mt-1" style="font-size: 11px;">
        ${timeStr} | &Delta;P: ${data.delta_p > 0 ? '+' : ''}${data.delta_p} W
      </div>
    </div>
    <div class="text-end">
      ${sigBadge}
    </div>
  `;
  
  eventsFeedLog.insertBefore(item, eventsFeedLog.firstChild);
  
  // Cap history length
  if (eventsFeedLog.children.length > 30) {
    eventsFeedLog.removeChild(eventsFeedLog.lastChild);
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

function updateCloudStatusUI(data) {
  const badge = document.getElementById("db-status-badge");
  const badgeLabel = document.getElementById("db-status-text");
  const counterLabel = document.getElementById("sync-records-label");

  if (data.db_connected && data.status === "online") {
    badge.className = "appliance-status-badge d-flex align-items-center gap-2 px-3 py-1 rounded-pill border db-status-online";
    badgeLabel.textContent = "ONLINE";
  } else if (data.status === "degraded") {
    badge.className = "appliance-status-badge d-flex align-items-center gap-2 px-3 py-1 rounded-pill border db-status-degraded";
    badgeLabel.textContent = "DEGRADED";
  } else {
    badge.className = "appliance-status-badge d-flex align-items-center gap-2 px-3 py-1 rounded-pill border db-status-offline";
    badgeLabel.textContent = "OFFLINE";
  }

  if (data.records_synced !== undefined) {
    counterLabel.textContent = `${data.records_synced} records synced`;
  }
}

window.addEventListener("load", () => {
  initChart();
  initMQTT();
});
