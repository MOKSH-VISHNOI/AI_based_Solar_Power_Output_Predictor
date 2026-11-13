/**
 * SolarPredict — Unified Multi-Page Controller
 * Manages SPA Tab Switching, Scenario Studio, History Analytics,
 * Regional Locations Explorer, Academic Model Metrics, and Main Dashboard.
 */

// Use same-origin relative URLs when served by any web server (Flask local or Render cloud).
// Only point to local Flask dev server when opened directly as a file:// URL.
const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : '';

// Chart instances
let hourlyChartInstance = null;
let dailyChartInstance = null;
let scenarioChartInstance = null;
let modelCompChartInstance = null;

// Application State
let latestPredictionData = null;
let allHistoryRecords = [];

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    setupNavigation();
    setupEventListeners();
    setupLocationCards();
    
    // Auto-generate initial prediction on page load
    fetchPrediction();
});

/**
 * Tab Navigation Controller between Pages
 */
function setupNavigation() {
    const navItems = document.querySelectorAll(".nav-item[data-tab]");
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const tabName = item.getAttribute("data-tab");
            switchPage(tabName);
        });
    });
}

function switchPage(pageId) {
    // 1. Update Sidebar Active Class
    document.querySelectorAll(".nav-item").forEach(item => {
        if (item.getAttribute("data-tab") === pageId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    // 2. Update Page View Active Class
    document.querySelectorAll(".page-view").forEach(page => {
        if (page.id === `page-${pageId}`) {
            page.classList.add("active");
        } else {
            page.classList.remove("active");
        }
    });

    // 3. Trigger View-Specific Refresh
    if (pageId === "predictions") {
        if (latestPredictionData) {
            renderPredictionsStudio(latestPredictionData);
        }
    } else if (pageId === "history") {
        fetchHistory();
    } else if (pageId === "models") {
        fetchModelInfo();
    } else if (pageId === "dashboard") {
        // Resize charts to prevent canvas clipping
        setTimeout(() => {
            hourlyChartInstance?.resize();
            dailyChartInstance?.resize();
        }, 50);
    }
}

/**
 * Initializes Chart.js instances
 */
function initCharts() {
    // 1. Hourly Power Curve Chart
    const ctxHourly = document.getElementById("hourlyPowerChart")?.getContext("2d");
    if (ctxHourly) {
        const powerGradient = ctxHourly.createLinearGradient(0, 0, 0, 220);
        powerGradient.addColorStop(0, "rgba(245, 158, 11, 0.38)");
        powerGradient.addColorStop(0.7, "rgba(245, 158, 11, 0.08)");
        powerGradient.addColorStop(1, "rgba(245, 158, 11, 0.0)");

        hourlyChartInstance = new Chart(ctxHourly, {
            type: "line",
            data: {
                labels: [],
                datasets: [{
                    label: "Predicted Power (kW)",
                    data: [],
                    borderColor: "#F59E0B",
                    borderWidth: 2.5,
                    backgroundColor: powerGradient,
                    fill: true,
                    tension: 0.38,
                    pointRadius: 3.5,
                    pointBackgroundColor: "#FBBF24",
                    pointBorderColor: "#131B2E",
                    pointBorderWidth: 1.5,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: "#F59E0B"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#1E293B",
                        titleColor: "#94A3B8",
                        bodyColor: "#F8FAFC",
                        borderColor: "rgba(245, 158, 11, 0.4)",
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: (c) => `Power Output: ${c.parsed.y.toFixed(2)} kW`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.04)" },
                        ticks: { color: "#64748B", font: { size: 11, family: "Plus Jakarta Sans" }, maxTicksLimit: 9 }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "Power Output (kW)", color: "#64748B" },
                        grid: { color: "rgba(255, 255, 255, 0.06)" },
                        ticks: { color: "#64748B", font: { size: 11, family: "Plus Jakarta Sans" } }
                    }
                }
            }
        });
    }

    // 2. Daily Energy Estimate Bar Chart
    const ctxDaily = document.getElementById("dailyEnergyChart")?.getContext("2d");
    if (ctxDaily) {
        dailyChartInstance = new Chart(ctxDaily, {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Energy (kWh)",
                    data: [],
                    backgroundColor: [],
                    borderRadius: 6,
                    borderSkipped: false,
                    barThickness: 28
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#1E293B",
                        titleColor: "#94A3B8",
                        bodyColor: "#F8FAFC",
                        borderColor: "rgba(255, 255, 255, 0.1)",
                        borderWidth: 1,
                        callbacks: {
                            label: (c) => `Estimated: ${c.parsed.y.toFixed(1)} kWh`
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#94A3B8" } },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "Energy (kWh)", color: "#64748B" },
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#64748B" }
                    }
                }
            }
        });
    }

    // 3. Predictions Studio: Multi-Scenario Capacity Chart
    const ctxScenario = document.getElementById("scenarioChart")?.getContext("2d");
    if (ctxScenario) {
        scenarioChartInstance = new Chart(ctxScenario, {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    { label: "3 kW System", data: [], borderColor: "#38BDF8", borderWidth: 2, tension: 0.35, pointRadius: 0 },
                    { label: "5 kW System (Standard)", data: [], borderColor: "#F59E0B", borderWidth: 2.5, tension: 0.35, pointRadius: 0 },
                    { label: "10 kW System", data: [], borderColor: "#10B981", borderWidth: 2, tension: 0.35, pointRadius: 0 },
                    { label: "15 kW Commercial", data: [], borderColor: "#A855F7", borderWidth: 2, tension: 0.35, pointRadius: 0 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: "#94A3B8", font: { family: "Plus Jakarta Sans", size: 11 } }
                    },
                    tooltip: {
                        backgroundColor: "#1E293B",
                        titleColor: "#94A3B8",
                        bodyColor: "#F8FAFC",
                        borderColor: "rgba(255, 255, 255, 0.1)",
                        borderWidth: 1
                    }
                },
                scales: {
                    x: { grid: { color: "rgba(255, 255, 255, 0.04)" }, ticks: { color: "#64748B", maxTicksLimit: 9 } },
                    y: { beginAtZero: true, title: { display: true, text: "Power (kW)", color: "#64748B" }, grid: { color: "rgba(255, 255, 255, 0.06)" }, ticks: { color: "#64748B" } }
                }
            }
        });
    }

    // 4. Model Metrics Benchmark Bar Chart
    const ctxModelComp = document.getElementById("modelCompChart")?.getContext("2d");
    if (ctxModelComp) {
        modelCompChartInstance = new Chart(ctxModelComp, {
            type: "bar",
            data: {
                labels: ["Linear Regression", "Decision Tree Regressor", "Random Forest (Champion)"],
                datasets: [
                    { label: "MAE (kW) — Lower is Better", data: [0.0182, 0.0059, 0.0041], backgroundColor: "#38BDF8", borderRadius: 4 },
                    { label: "RMSE (kW) — Lower is Better", data: [0.0322, 0.0118, 0.0088], backgroundColor: "#F59E0B", borderRadius: 4 },
                    { label: "R² Score — Closer to 1.0 is Better", data: [0.9991, 0.9999, 0.9999], backgroundColor: "#10B981", borderRadius: 4 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: "#94A3B8", font: { size: 11, family: "Plus Jakarta Sans" } } },
                    tooltip: { backgroundColor: "#1E293B" }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#94A3B8" } },
                    y: { beginAtZero: true, grid: { color: "rgba(255, 255, 255, 0.06)" }, ticks: { color: "#64748B" } }
                }
            }
        });
    }
}

/**
 * Event Listeners for UI interaction, forms, and CSV download
 */
function setupEventListeners() {
    // Form Submission
    const form = document.getElementById("prediction-form");
    form?.addEventListener("submit", (e) => {
        e.preventDefault();
        fetchPrediction();
    });

    // Export CSV in Predictions Studio
    document.getElementById("btn-export-csv")?.addEventListener("click", () => {
        exportPredictionCSV();
    });

    // History Table Search
    document.getElementById("history-search-input")?.addEventListener("input", (e) => {
        filterHistoryTable(e.target.value);
    });

    // History Location Filter
    document.getElementById("history-loc-filter")?.addEventListener("change", (e) => {
        filterHistoryTable(document.getElementById("history-search-input")?.value || "", e.target.value);
    });
}

/**
 * Setup Location Cards with "Select & Predict"
 */
function setupLocationCards() {
    const selectButtons = document.querySelectorAll(".btn-select-location");
    selectButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const locName = btn.getAttribute("data-location");
            if (locName) {
                const selectElem = document.getElementById("location-select");
                if (selectElem) {
                    selectElem.value = locName;
                }
                // Switch back to Dashboard view and trigger prediction
                switchPage("dashboard");
                fetchPrediction();
            }
        });
    });
}

/**
 * Fetches solar PV prediction from Flask backend API.
 */
async function fetchPrediction() {
    const btn = document.getElementById("generate-btn");
    const btnText = btn?.querySelector(".btn-text");
    const originalText = btnText ? btnText.innerText : "Generate Prediction";

    const locationVal = document.getElementById("location-select")?.value || "Indore, Madhya Pradesh";
    const capacityVal = document.getElementById("capacity-input")?.value || 5.0;
    const dateVal = document.getElementById("date-select")?.value || "tomorrow";

    try {
        if (btn) {
            btn.disabled = true;
            if (btnText) btnText.innerText = "Forecasting...";
        }

        const response = await fetch(`${API_BASE}/api/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                location: locationVal,
                capacity_kw: parseFloat(capacityVal),
                date: dateVal
            })
        });

        const res = await response.json();
        if (!response.ok || res.status !== "success") {
            throw new Error(res.message || "Failed to generate prediction");
        }

        latestPredictionData = res.data;
        renderDashboard(res.data);
        renderPredictionsStudio(res.data);

    } catch (err) {
        console.error("Prediction failed:", err);
        alert("Prediction Error: " + err.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            if (btnText) btnText.innerText = originalText;
        }
    }
}

/**
 * Updates Dashboard cards, charts, and tables
 */
function renderDashboard(data) {
    // Header
    const locTag = document.getElementById("header-location-tag");
    if (locTag) locTag.innerText = data.short_name || data.location_name;
    const updTag = document.getElementById("last-updated-text");
    if (updTag) updTag.innerText = `Today, ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

    // KPIs
    const energyElem = document.getElementById("kpi-total-energy");
    if (energyElem) energyElem.innerText = `${data.total_energy_kwh} kWh`;
    
    const badge = document.getElementById("kpi-energy-badge");
    if (badge) {
        badge.innerText = `${data.vs_previous_day_pct.startsWith('+') ? '↑' : '↓'} ${data.vs_previous_day_pct}`;
        badge.style.color = data.vs_previous_day_pct.startsWith('-') ? "#F87171" : "#10B981";
        badge.style.backgroundColor = data.vs_previous_day_pct.startsWith('-') ? "rgba(248, 113, 113, 0.15)" : "rgba(16, 185, 129, 0.15)";
    }

    const peakElem = document.getElementById("kpi-peak-power");
    if (peakElem) peakElem.innerText = `${data.peak_power_kw} kW`;
    const peakTimeElem = document.getElementById("kpi-peak-time");
    if (peakTimeElem) peakTimeElem.innerText = data.peak_time;

    const sunElem = document.getElementById("kpi-sun-hours");
    if (sunElem) sunElem.innerText = `${data.effective_sunshine_hours} hrs`;

    const condElem = document.getElementById("kpi-forecast-cond");
    if (condElem) condElem.innerText = data.forecast_condition;
    const cloudElem = document.getElementById("kpi-cloud-cover");
    if (cloudElem) cloudElem.innerText = `${data.avg_cloud_cover}%`;

    // Hourly Power Chart
    if (hourlyChartInstance) {
        const formattedTimes = data.hourly_times.map((t, idx) => {
            const dt = new Date(2000, 0, 1, idx);
            return dt.toLocaleTimeString([], { hour: "numeric", hour12: true });
        });
        hourlyChartInstance.data.labels = formattedTimes;
        hourlyChartInstance.data.datasets[0].data = data.hourly_power;
        hourlyChartInstance.update();
    }

    // Weather Table
    const titleElem = document.getElementById("weather-card-title");
    if (titleElem) titleElem.innerText = `Weather Forecast (${data.prediction_date_formatted || 'Target Date'})`;
    
    const tbody = document.getElementById("weather-tbody");
    if (tbody && data.weather_table) {
        tbody.innerHTML = "";
        data.weather_table.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${row.time}</strong></td>
                <td>${row.temperature}</td>
                <td>${row.cloud_cover}</td>
                <td>${row.wind_speed}</td>
                <td><div class="weather-cond-cell"><span>${row.icon}</span> <span>${row.condition}</span></div></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Daily Energy Chart
    if (dailyChartInstance && data.daily_estimates) {
        dailyChartInstance.data.labels = data.daily_estimates.map(d => d.label);
        dailyChartInstance.data.datasets[0].data = data.daily_estimates.map(d => d.energy_kwh);
        dailyChartInstance.data.datasets[0].backgroundColor = data.daily_estimates.map(d => d.is_selected ? "#FBBF24" : "#334155");
        dailyChartInstance.update();
    }

    // Insights
    const insightsList = document.getElementById("insights-list");
    if (insightsList && data.insights) {
        insightsList.innerHTML = "";
        data.insights.forEach(item => {
            const li = document.createElement("li");
            li.innerHTML = `<span class="check-icon">✓</span> ${item}`;
            insightsList.appendChild(li);
        });
    }

    // Impact
    const cleanElem = document.getElementById("eco-clean-energy");
    if (cleanElem) cleanElem.innerText = `${data.total_energy_kwh} kWh`;
    const co2Elem = document.getElementById("eco-co2-saved");
    if (co2Elem) co2Elem.innerText = `≈ ${data.co2_avoided_kg} kg`;
    const treesDesc = document.getElementById("eco-trees-desc");
    if (treesDesc) treesDesc.innerText = `planting ${data.trees_per_day} tree${data.trees_per_day > 1 ? 's' : ''} per day`;
}

/**
 * Updates Predictions Studio Page (Scenarios, Dual Curve, 24-hr Table)
 */
function renderPredictionsStudio(data) {
    if (!data) return;

    const baseCap = data.installed_capacity_kw || 5.0;
    const factor3 = 3.0 / baseCap;
    const factor5 = 5.0 / baseCap;
    const factor10 = 10.0 / baseCap;
    const factor15 = 15.0 / baseCap;

    // 1. Scenario Summary Cards
    const sc3 = document.getElementById("scenario-val-3kw");
    if (sc3) sc3.innerText = `${(data.total_energy_kwh * factor3).toFixed(1)} kWh`;
    const sc5 = document.getElementById("scenario-val-5kw");
    if (sc5) sc5.innerText = `${(data.total_energy_kwh * factor5).toFixed(1)} kWh`;
    const sc10 = document.getElementById("scenario-val-10kw");
    if (sc10) sc10.innerText = `${(data.total_energy_kwh * factor10).toFixed(1)} kWh`;
    const sc15 = document.getElementById("scenario-val-15kw");
    if (sc15) sc15.innerText = `${(data.total_energy_kwh * factor15).toFixed(1)} kWh`;

    // 2. Scenario Comparison Chart
    if (scenarioChartInstance && data.hourly_power) {
        const times = data.hourly_times.map((t, i) => {
            const dt = new Date(2000, 0, 1, i);
            return dt.toLocaleTimeString([], { hour: "numeric", hour12: true });
        });
        scenarioChartInstance.data.labels = times;
        scenarioChartInstance.data.datasets[0].data = data.hourly_power.map(p => +(p * factor3).toFixed(2));
        scenarioChartInstance.data.datasets[1].data = data.hourly_power.map(p => +(p * factor5).toFixed(2));
        scenarioChartInstance.data.datasets[2].data = data.hourly_power.map(p => +(p * factor10).toFixed(2));
        scenarioChartInstance.data.datasets[3].data = data.hourly_power.map(p => +(p * factor15).toFixed(2));
        scenarioChartInstance.update();
    }

    // 3. 24-Hour Detailed Breakdown Table
    const studioTbody = document.getElementById("studio-breakdown-tbody");
    if (studioTbody && data.hourly_power) {
        studioTbody.innerHTML = "";
        let cumulativeKwh = 0;
        data.hourly_power.forEach((kw, h) => {
            cumulativeKwh += kw;
            const dt = new Date(2000, 0, 1, h);
            const timeLabel = dt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
            
            // Estimated GHI proxy from capacity and output
            const ghiEst = Math.round((kw / baseCap) * 1000);
            const statusBadge = kw > 0.1 * baseCap 
                ? '<span class="kpi-badge green">Generating</span>' 
                : '<span class="kpi-badge" style="background:#1E293B;color:#64748B;">Standby</span>';

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${timeLabel}</strong></td>
                <td>${kw > 0 ? ghiEst + ' W/m²' : '0 W/m²'}</td>
                <td><strong>${kw.toFixed(2)} kW</strong></td>
                <td>${cumulativeKwh.toFixed(2)} kWh</td>
                <td>${statusBadge}</td>
            `;
            studioTbody.appendChild(tr);
        });
    }
}

/**
 * Exports current 24-hour prediction to downloadable CSV
 */
function exportPredictionCSV() {
    if (!latestPredictionData) {
        alert("Please generate a prediction first!");
        return;
    }

    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Hour,Time,Predicted_Power_kW,Cumulative_Energy_kWh,Location,Capacity_kW,Date\n";

    let cum = 0;
    latestPredictionData.hourly_power.forEach((kw, h) => {
        cum += kw;
        const dt = new Date(2000, 0, 1, h);
        const timeStr = dt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
        csvContent += `${h},"${timeStr}",${kw.toFixed(2)},${cum.toFixed(2)},"${latestPredictionData.location_name}",${latestPredictionData.installed_capacity_kw},"${latestPredictionData.prediction_date}"\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `SolarPredict_${latestPredictionData.short_name || 'Forecast'}_${latestPredictionData.prediction_date}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Fetches SQLite prediction history and populates History Page
 */
async function fetchHistory() {
    const tbody = document.getElementById("history-full-tbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="table-loading">Loading prediction records from SQLite...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/api/history?limit=50`);
        const json = await res.json();
        if (json.status === "success" && json.history) {
            allHistoryRecords = json.history;
            renderHistoryStats(allHistoryRecords);
            renderHistoryTable(allHistoryRecords);
        }
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="table-loading" style="color:#F87171">Failed to load history: ${e.message}</td></tr>`;
    }
}

function renderHistoryStats(records) {
    const countElem = document.getElementById("ribbon-total-runs");
    if (countElem) countElem.innerText = records.length;

    const totalKwh = records.reduce((acc, r) => acc + (r.total_energy_kwh || 0), 0);
    const energyElem = document.getElementById("ribbon-total-energy");
    if (energyElem) energyElem.innerText = `${totalKwh.toFixed(1)} kWh`;

    const avgPeak = records.length > 0 ? (records.reduce((acc, r) => acc + (r.peak_power_kw || 0), 0) / records.length) : 0;
    const peakElem = document.getElementById("ribbon-avg-peak");
    if (peakElem) peakElem.innerText = `${avgPeak.toFixed(1)} kW`;

    const topLocElem = document.getElementById("ribbon-top-loc");
    if (topLocElem && records.length > 0) {
        topLocElem.innerText = records[0].location_name.split(',')[0];
    }
}

function renderHistoryTable(records) {
    const tbody = document.getElementById("history-full-tbody");
    if (!tbody) return;

    if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="table-loading">No prediction records found.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    records.forEach(r => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>#${r.id}</td>
            <td><strong>${r.location_name}</strong></td>
            <td>${r.installed_capacity_kw} kW</td>
            <td>${r.prediction_date}</td>
            <td><strong style="color:#FBBF24;">${r.total_energy_kwh} kWh</strong></td>
            <td>${r.peak_power_kw} kW (${r.peak_time || '12 PM'})</td>
            <td><span class="kpi-badge green">${r.forecast_condition || 'Clear'}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function filterHistoryTable(searchQuery = "", locFilter = "") {
    let filtered = allHistoryRecords.filter(r => {
        const matchesSearch = !searchQuery || 
            r.location_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
            r.prediction_date.includes(searchQuery);
        const matchesLoc = !locFilter || r.location_name.includes(locFilter);
        return matchesSearch && matchesLoc;
    });
    renderHistoryTable(filtered);
}

/**
 * Fetches Model Evaluation metrics and populates Model Metrics Page
 */
async function fetchModelInfo() {
    try {
        const res = await fetch(`${API_BASE}/api/model-info`);
        const json = await res.json();
        if (json.status === "success" && json.metrics) {
            // Update table
            const tbody = document.getElementById("models-comp-tbody");
            if (tbody) {
                tbody.innerHTML = "";
                for (const [name, m] of Object.entries(json.metrics)) {
                    const isChampion = name.includes("Random Forest");
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${name}</strong> ${isChampion ? '<span class="kpi-badge green">Champion</span>' : ''}</td>
                        <td>${m.mae.toFixed(4)}</td>
                        <td>${m.rmse.toFixed(4)}</td>
                        <td><strong>${m.r2.toFixed(4)}</strong></td>
                        <td>${isChampion ? '<span class="kpi-badge gold">Deployed</span>' : '<span class="kpi-badge" style="background:#1E293B;color:#64748B;">Benchmarked</span>'}</td>
                    `;
                    tbody.appendChild(tr);
                }
            }
        }
    } catch (e) {
        console.error("Failed to load model info:", e);
    }
}
