"""
Configuration and constants for the SolarPredict project.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATABASE_PATH = os.path.join(BASE_DIR, "database", "solar.db")
MODEL_FILE_PATH = os.path.join(MODELS_DIR, "trained_model.joblib")
MODEL_METRICS_PATH = os.path.join(MODELS_DIR, "metrics.json")

# Ensure required directories exist
for directory in [DATA_RAW_DIR, DATA_PROCESSED_DIR, MODELS_DIR, os.path.dirname(DATABASE_PATH)]:
    os.makedirs(directory, exist_ok=True)

# Primary Reference Site: Indore, Madhya Pradesh
DEFAULT_LOCATION = {
    "name": "Indore, Madhya Pradesh",
    "short_name": "Indore, MP",
    "latitude": 22.7196,
    "longitude": 75.8577,
    "elevation": 553,
    "default_capacity_kw": 5.0,
    "panel_tilt_deg": 23.0,     # Standard optimal tilt angle ~ latitude
    "panel_azimuth_deg": 0.0,   # South facing
    "system_loss_pct": 14.0,    # Standard PV system losses (inverter, cabling, soiling)
    "annual_ghi_kwh_m2": 1980,
    "solar_rating": "Very High",
    "desc": "Primary model reference installation site. Excellent solar insolation with over 300 clear sunshine days annually."
}

# Predefined locations for the user dropdown & Locations page
SUPPORTED_LOCATIONS = [
    {
        "id": "indore",
        "name": "Indore, Madhya Pradesh",
        "short_name": "Indore, MP",
        "latitude": 22.7196,
        "longitude": 75.8577,
        "elevation": 553,
        "default_capacity_kw": 5.0,
        "panel_tilt_deg": 23.0,
        "annual_ghi_kwh_m2": 1980,
        "solar_rating": "Very High",
        "desc": "Primary model reference installation site. Excellent solar insolation with over 300 clear sunshine days annually."
    },
    {
        "id": "bhopal",
        "name": "Bhopal, Madhya Pradesh",
        "short_name": "Bhopal, MP",
        "latitude": 23.2599,
        "longitude": 77.4126,
        "elevation": 527,
        "default_capacity_kw": 5.0,
        "panel_tilt_deg": 23.0,
        "annual_ghi_kwh_m2": 1940,
        "solar_rating": "High",
        "desc": "Central India plateau with high average daily solar radiation and steady seasonal yields."
    },
    {
        "id": "jaipur",
        "name": "Jaipur, Rajasthan",
        "short_name": "Jaipur, RJ",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "elevation": 431,
        "default_capacity_kw": 5.0,
        "panel_tilt_deg": 27.0,
        "annual_ghi_kwh_m2": 2150,
        "solar_rating": "Exceptional",
        "desc": "Arid desert gateway with the highest direct normal irradiance (DNI) in Northern India."
    },
    {
        "id": "delhi",
        "name": "New Delhi, Delhi",
        "short_name": "New Delhi",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "elevation": 216,
        "default_capacity_kw": 5.0,
        "panel_tilt_deg": 28.0,
        "annual_ghi_kwh_m2": 1820,
        "solar_rating": "High",
        "desc": "Northern plains climate subject to distinct winter haze and intense summer solar generation peaks."
    },
    {
        "id": "mumbai",
        "name": "Mumbai, Maharashtra",
        "short_name": "Mumbai, MH",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "elevation": 14,
        "default_capacity_kw": 5.0,
        "panel_tilt_deg": 19.0,
        "annual_ghi_kwh_m2": 1850,
        "solar_rating": "Moderate-High",
        "desc": "Coastal tropical environment with elevated relative humidity and heavy monsoon seasonality."
    },
    {
        "id": "bengaluru",
        "name": "Bengaluru, Karnataka",
        "short_name": "Bengaluru, KA",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "elevation": 920,
        "default_capacity_kw": 5.0,
        "panel_tilt_deg": 13.0,
        "annual_ghi_kwh_m2": 1920,
        "solar_rating": "High",
        "desc": "High-altitude Deccan plateau with moderate ambient temperatures that maintain high cell efficiency."
    }
]

# Grid Emission Factor (India Central Electricity Authority standard baseline ~0.77 kg CO2 / kWh)
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.77

# CO2 absorbed per mature tree per day (~20 kg/year / 365 days)
TREE_CO2_ABSORPTION_KG_PER_DAY = 20.0 / 365.0

# Open-Meteo APIs
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
