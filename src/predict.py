"""
Inference and Prediction Pipeline for SolarPredict.
Fetches future weather forecasts from Open-Meteo, generates ML power predictions,
integrates daily energy, calculates KPIs, and generates data-driven insights.
"""
import os
import sys
import json
from datetime import datetime, date, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
import numpy as np
import pandas as pd
import joblib

from src.config import (
    MODEL_FILE_PATH,
    SUPPORTED_LOCATIONS,
    DEFAULT_LOCATION,
    OPEN_METEO_FORECAST_URL,
    GRID_EMISSION_FACTOR_KG_PER_KWH,
    TREE_CO2_ABSORPTION_KG_PER_DAY
)
from src.preprocessing import prepare_features, clamp_power_output
from src.database import save_prediction_record

# Weather code (WMO) to friendly text and icons
WMO_WEATHER_MAP = {
    0: ("Clear", "☀️"),
    1: ("Mainly Clear", "🌤️"),
    2: ("Partly Cloudy", "⛅"),
    3: ("Cloudy", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Depositing Rime Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"),
    53: ("Moderate Drizzle", "🌦️"),
    55: ("Dense Drizzle", "🌧️"),
    61: ("Slight Rain", "🌦️"),
    63: ("Moderate Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    80: ("Rain Showers", "🌦️"),
    81: ("Moderate Showers", "🌧️"),
    82: ("Violent Showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
}

_LOADED_MODEL_BUNDLE = None

def get_model_bundle():
    """Caches and returns the trained model bundle."""
    global _LOADED_MODEL_BUNDLE
    if _LOADED_MODEL_BUNDLE is None:
        if not os.path.exists(MODEL_FILE_PATH):
            raise FileNotFoundError(f"Trained model not found at {MODEL_FILE_PATH}. Please train the model first.")
        _LOADED_MODEL_BUNDLE = joblib.load(MODEL_FILE_PATH)
    return _LOADED_MODEL_BUNDLE

def resolve_location(location_name: str):
    """Matches a location string to supported coordinates."""
    if not location_name:
        return DEFAULT_LOCATION
    for loc in SUPPORTED_LOCATIONS:
        if loc["name"].lower() == location_name.lower() or loc["id"].lower() in location_name.lower():
            return loc
    # Fallback to Indore
    return DEFAULT_LOCATION

def fetch_weather_forecast(latitude: float, longitude: float, forecast_days: int = 7) -> pd.DataFrame:
    """
    Fetches hourly weather forecast from Open-Meteo.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": forecast_days,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "cloud_cover",
            "wind_speed_10m",
            "shortwave_radiation",
            "direct_normal_irradiance",
            "diffuse_radiation",
            "weather_code"
        ],
        "timezone": "Asia/Kolkata"
    }

    resp = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df["hour"] = df["time"].dt.hour
    df["month"] = df["time"].dt.month
    df["date_str"] = df["time"].dt.strftime("%Y-%m-%d")
    return df

def map_weather_condition(code: int, cloud_cover: float):
    """Returns friendly condition description and emoji icon."""
    if code in WMO_WEATHER_MAP:
        return WMO_WEATHER_MAP[code]
    if cloud_cover < 15:
        return ("Clear", "☀️")
    elif cloud_cover < 40:
        return ("Partly Cloudy", "⛅")
    else:
        return ("Cloudy", "☁️")

def generate_insights(total_energy: float, peak_power: float, peak_time: str, avg_cloud: float, capacity_kw: float):
    """Generates explainable, data-driven analytical bullet insights."""
    insights = []

    # Overall generation quality
    cf = total_energy / (capacity_kw * 8.0) if capacity_kw > 0 else 0
    if cf >= 0.55:
        insights.append("Good solar generation expected tomorrow.")
    elif cf >= 0.35:
        insights.append("Moderate solar generation expected tomorrow.")
    else:
        insights.append("Lower solar output expected due to subdued radiation conditions.")

    # Peak timing
    insights.append(f"Peak output of {peak_power:.1f} kW expected around {peak_time}.")

    # Cloud cover impact
    if avg_cloud > 30:
        insights.append(f"Cloud cover ({avg_cloud:.0f}%) may slightly reduce output in the afternoon.")
    elif avg_cloud > 60:
        insights.append(f"Dense cloud cover ({avg_cloud:.0f}%) will notably suppress peak potential.")
    else:
        insights.append("Minimal cloud obstruction expected during peak daylight hours.")

    # Atmosphere / overall conditions
    if avg_cloud < 25:
        insights.append("Ideal conditions for solar energy production.")
    else:
        insights.append("Atmospheric conditions remain suitable for steady generation.")

    return insights

def predict_solar_output(location_name: str, capacity_kw: float, target_date_str: str = "tomorrow"):
    """
    Main end-to-end prediction execution:
    1. Resolves coordinates
    2. Fetches forecast from Open-Meteo
    3. Runs trained model
    4. Computes KPIs, hourly power curve, 5-day estimates, insights, and eco impact
    5. Logs record to SQLite
    """
    loc = resolve_location(location_name)
    capacity_kw = float(capacity_kw)
    if capacity_kw <= 0:
        capacity_kw = 5.0

    # Resolve target date
    today = date.today()
    if target_date_str == "today":
        selected_date = today
    elif target_date_str == "tomorrow" or not target_date_str:
        selected_date = today + timedelta(days=1)
    else:
        try:
            selected_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today + timedelta(days=1)

    selected_date_str = selected_date.strftime("%Y-%m-%d")

    # 1. Fetch Forecast
    df_forecast = fetch_weather_forecast(loc["latitude"], loc["longitude"], forecast_days=7)

    # 2. Load ML Model
    bundle = get_model_bundle()
    estimator = bundle["estimator"]
    ref_capacity = bundle.get("reference_capacity_kw", 5.0)

    # 3. Filter for target date
    df_target = df_forecast[df_forecast["date_str"] == selected_date_str].copy()
    if df_target.empty or len(df_target) < 24:
        # Fallback to the second available day
        available_dates = df_forecast["date_str"].unique()
        selected_date_str = available_dates[1] if len(available_dates) > 1 else available_dates[0]
        df_target = df_forecast[df_forecast["date_str"] == selected_date_str].copy()

    # 4. Feature Preparation & Model Prediction
    X_target = prepare_features(df_target)
    raw_power_5kw = estimator.predict(X_target)

    # Linear capacity scaling
    scaling_ratio = capacity_kw / ref_capacity
    scaled_power = raw_power_5kw * scaling_ratio

    # Domain Clamping
    ghi_target = df_target["shortwave_radiation"].values
    hourly_power = clamp_power_output(scaled_power, ghi_target, capacity_kw)
    hourly_power = [round(float(p), 2) for p in hourly_power]

    # 5. Calculate Energy & KPIs
    total_energy_kwh = round(float(sum(hourly_power)), 1)
    peak_power_kw = round(float(max(hourly_power)), 1)
    peak_idx = int(np.argmax(hourly_power))
    peak_hour = int(df_target["hour"].iloc[peak_idx])

    # Peak hour format (e.g. "12:00 PM")
    dt_peak = datetime(2000, 1, 1, peak_hour)
    peak_time_str = dt_peak.strftime("%I:00 %p").lstrip("0")

    # Effective sunshine hours: hours where power > 10% capacity
    sun_hours_count = sum(1 for p in hourly_power if p >= (0.10 * capacity_kw))
    effective_sun_hours = round(float(sun_hours_count), 1)

    # Daytime weather condition summary (hours 6 to 18)
    daytime_df = df_target[(df_target["hour"] >= 6) & (df_target["hour"] <= 18)]
    avg_cloud = float(daytime_df["cloud_cover"].mean()) if not daytime_df.empty else float(df_target["cloud_cover"].mean())
    mode_wmo = int(daytime_df["weather_code"].mode()[0]) if not daytime_df.empty else 0
    cond_text, cond_icon = map_weather_condition(mode_wmo, avg_cloud)

    # Environmental Impact
    co2_avoided_kg = round(total_energy_kwh * GRID_EMISSION_FACTOR_KG_PER_KWH, 1)
    trees_equiv = round(co2_avoided_kg / TREE_CO2_ABSORPTION_KG_PER_DAY, 1)
    trees_per_day_int = max(1, round(trees_equiv))

    # Insights
    insights = generate_insights(total_energy_kwh, peak_power_kw, peak_time_str, avg_cloud, capacity_kw)

    # 6. Hourly Weather Forecast Table (displaying 6 AM, 9 AM, 12 PM, 3 PM, 6 PM, 9 PM)
    selected_hours = [6, 9, 12, 15, 18, 21]
    weather_table = []
    for h in selected_hours:
        row_match = df_target[df_target["hour"] == h]
        if not row_match.empty:
            r = row_match.iloc[0]
            w_text, w_icon = map_weather_condition(int(r["weather_code"]), float(r["cloud_cover"]))
            h_dt = datetime(2000, 1, 1, h)
            weather_table.append({
                "time": h_dt.strftime("%I %p").lstrip("0"),
                "temperature": f"{int(round(r['temperature_2m']))}°C",
                "cloud_cover": f"{int(round(r['cloud_cover']))}%",
                "wind_speed": f"{round(float(r['wind_speed_10m']), 1)} m/s",
                "condition": w_text,
                "icon": w_icon
            })

    # 7. 5-Day Daily Energy Estimates (Today, Tomorrow, Day+2, Day+3, Day+4)
    daily_estimates = []
    unique_dates = df_forecast["date_str"].unique()[:5]
    for i, d_str in enumerate(unique_dates):
        df_d = df_forecast[df_forecast["date_str"] == d_str]
        if len(df_d) >= 24:
            X_d = prepare_features(df_d)
            raw_d = estimator.predict(X_d) * scaling_ratio
            clamped_d = clamp_power_output(raw_d, df_d["shortwave_radiation"].values, capacity_kw)
            d_energy = round(float(sum(clamped_d)), 1)
            
            # Label
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            if d_obj == today:
                label = "Today"
            elif d_obj == today + timedelta(days=1):
                label = "Tomorrow"
            else:
                label = d_obj.strftime("%a")

            daily_estimates.append({
                "date": d_str,
                "label": label,
                "energy_kwh": d_energy,
                "is_selected": (d_str == selected_date_str)
            })

    # Calculate vs previous day comparison percentage for the first KPI badge
    prev_day_energy = daily_estimates[0]["energy_kwh"] if daily_estimates else total_energy_kwh
    if prev_day_energy > 0:
        pct_diff = round(((total_energy_kwh - prev_day_energy) / prev_day_energy) * 100)
    else:
        pct_diff = 0
    pct_diff_str = f"+{pct_diff}%" if pct_diff >= 0 else f"{pct_diff}%"

    result = {
        "location_name": loc["name"],
        "short_name": loc.get("short_name", loc["name"]),
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "installed_capacity_kw": capacity_kw,
        "prediction_date": selected_date_str,
        "prediction_date_formatted": selected_date.strftime("%d %b %Y"),
        "total_energy_kwh": total_energy_kwh,
        "vs_previous_day_pct": pct_diff_str,
        "peak_power_kw": peak_power_kw,
        "peak_time": peak_time_str,
        "effective_sunshine_hours": effective_sun_hours,
        "forecast_condition": cond_text,
        "avg_cloud_cover": round(avg_cloud),
        "co2_avoided_kg": co2_avoided_kg,
        "trees_equivalent": trees_equiv,
        "trees_per_day": trees_per_day_int,
        "hourly_times": [f"{h}:00" for h in range(24)],
        "hourly_power": hourly_power,
        "weather_table": weather_table,
        "daily_estimates": daily_estimates,
        "insights": insights,
        "model_name": bundle["model_name"]
    }

    # Save to SQLite
    try:
        save_prediction_record(result)
    except Exception as e:
        print(f"Database logging note: {e}")

    return result
