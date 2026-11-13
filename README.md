# SolarPredict — AI-Based Solar Energy Output Predictor
> **BCA Minor Project** | *AI for a Brighter Tomorrow*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.9-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

An explainable, data-driven machine learning system designed to forecast the expected short-term solar photovoltaic (PV) power output (kW) and cumulative daily energy generation (kWh) of solar installations using forecasted meteorological and solar irradiance conditions.

---

## 🌟 Key Capabilities

- **Zero Manual Weather Entry:** Automatically queries live, real-time 7-day meteorological forecasts from the Open-Meteo API.
- **Explainable Machine Learning:** Evaluates Linear Regression, Decision Tree, and Random Forest architectures on 1-year hourly datasets (8,784 records).
- **Physics-Enforced Bounds:** Domain clamping ensures nighttime power drops strictly to $0.0\text{ kW}$ and generation scales within rated system capacity.
- **Dynamic Capacity Scaling:** Linearly scales specific yield predictions across residential ($3\text{ kW}$), standard rooftop ($5\text{ kW}$), commercial ($10\text{ kW}$), and industrial arrays ($15\text{ kW}$).
- **Environmental Impact Calculator:** Real-time computation of avoided $\text{CO}_2$ emissions ($0.77\text{ kg/kWh}$ Indian grid baseline) and equivalent trees planted.
- **SQLite Prediction History:** Persistent logging of past forecast runs with search and location filtering.
- **Export to CSV:** Direct download of 24-hour detailed meteorological and power breakdown.

---

## 🏗️ System Architecture & Workflow

The system **does not predict weather itself**. It consumes external numerical weather predictions and maps them to physical solar photovoltaic generation:

```
[ Open-Meteo Forecast API ] ──> [ Meteorological Fetcher ]
                                         │
[ User: City, Capacity, Date ] ──> [ Preprocessing & Cyclical Encoding ]
                                         │
                              [ Random Forest Regressor Pipeline (.joblib) ]
                                         │
                              [ Physical Bounding & Clamping (kW) ]
                                         │
                              [ Numerical Energy Integration (kWh) ]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
      [ SQLite (solar.db) ]                           [ JSON REST Response ]
                                                                 │
                                                                 ▼
                                                    [ Modern Dark SaaS Dashboard ]
```

---

## 📊 Machine Learning Model Benchmarking

Models evaluated using an 80/20 chronological train-test split on 8,784 hourly records for **Indore, Madhya Pradesh**:

| Model Architecture | MAE (kW) | RMSE (kW) | $R^2$ Score | Deployment Status |
| :--- | :---: | :---: | :---: | :---: |
| **Linear Regression** (Standardized) | 0.0182 | 0.0322 | 0.9991 | Baseline |
| **Decision Tree Regressor** | 0.0059 | 0.0118 | 0.9999 | Benchmarked |
| **Random Forest Regressor** | **0.0041** | **0.0088** | **0.9999** | **Selected Champion** |

### Feature Importance Breakdown:
- **Global Horizontal Irradiance (GHI):** $68.4\%$
- **Direct Normal Irradiance (DNI):** $14.2\%$
- **Ambient Air Temperature ($2\text{m}$):** $7.8\%$
- **Diffuse Solar Radiation (DHI):** $4.6\%$
- **Cyclical Diurnal Time Encodings ($\sin/\cos$):** $3.2\%$
- **Relative Humidity & Wind Speed:** $1.8\%$

---

## 📂 Project Structure

```
AI_based_Solar_Power_Output_Predictor/
├── app.py                     # Flask web server and REST API endpoints
├── Dashboard.html             # Standalone & production frontend dashboard
├── style.css                  # Modern dark SaaS theme stylesheet
├── dashboard.js               # Chart.js controller and multi-page SPA logic
├── requirements.txt           # Project dependencies including Gunicorn
├── Procfile                   # Cloud deployment entrypoint
├── render.yaml                # Render cloud deployment blueprint
├── test_app.py                # Automated unit and integration test suite
│
├── data/
│   ├── raw/                   # Raw historical Open-Meteo archive (Indore 2024)
│   └── processed/             # Cleaned training dataset with engineered features
│
├── models/
│   ├── trained_model.joblib   # Serialized Random Forest model pipeline
│   └── metrics.json           # Evaluation metrics comparison
│
├── src/
│   ├── config.py              # System paths, site metadata, and emission factors
│   ├── data_collection.py     # Data fetcher & PVGIS/IEC reference power generator
│   ├── preprocessing.py       # Cyclical time encodings & physical clamping rules
│   ├── train_model.py         # Model training, comparison, and evaluation pipeline
│   ├── predict.py             # Live Open-Meteo forecast retrieval & prediction pipeline
│   └── database.py            # SQLite schema initialization and prediction logging
│
├── templates/
│   └── dashboard.html         # Jinja2 template for Flask rendering
└── static/
    ├── css/style.css          # Static assets for Flask serving
    └── js/dashboard.js
```

---

## 🚀 Getting Started Locally

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/AI_based_Solar_Power_Output_Predictor.git
cd AI_based_Solar_Power_Output_Predictor
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Re-train the Machine Learning Model
```bash
python src/train_model.py
```

### 5. Run the Automated Tests
```bash
python test_app.py
```

### 6. Launch the Application
```bash
python app.py
```
Visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🌐 Free Cloud Hosting (Render)

This repository includes `Procfile` and `render.yaml` for 1-click deployment on [Render](https://render.com):

1. Push this repository to your **GitHub** account.
2. Sign in to **[Render.com](https://render.com)** and click **New + > Web Service**.
3. Connect your GitHub repository.
4. Set:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Click **Create Web Service**. Your live public URL will be ready in 2 minutes!

---

## 📜 Academic Honesty & Data Declaration

This project is prepared for university BCA Minor Project examination:
- PV generation reference output is derived from the standard empirical IEC 61724 / PVGIS cell temperature model based on reanalysis radiation.
- Weather forecast and historical reanalysis data are powered by open meteorological science from the **Open-Meteo API**.
- All metrics and evaluations shown are produced by real experimental benchmarks.

---

## 👨‍💻 Author

- **Academic Program:** Bachelor of Computer Applications (BCA)
- **Project Title:** AI-Based Solar Energy Output Predictor (SolarPredict)
