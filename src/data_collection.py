"""
Data Collection Module for SolarPredict.
Fetches historical meteorological and solar irradiance data from Open-Meteo
and pairs it with PVGIS reference solar generation for the reference site (Indore, MP).
"""
import os
import sys
import time
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
import pandas as pd
import numpy as np
from src.config import (
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    DEFAULT_LOCATION,
    OPEN_METEO_ARCHIVE_URL
)

def fetch_open_meteo_history(latitude=22.7196, longitude=75.8577, start_date="2024-01-01", end_date="2024-12-31"):
    """
    Fetches 1 year of hourly historical weather and solar data from Open-Meteo Archive.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "cloud_cover",
            "wind_speed_10m",
            "shortwave_radiation",
            "direct_normal_irradiance",
            "diffuse_radiation"
        ],
        "timezone": "Asia/Kolkata"
    }

    print(f"Fetching Open-Meteo archive data for ({latitude}, {longitude}) from {start_date} to {end_date}...")
    response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    hourly = data["hourly"]
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    return df

def calculate_pvgis_reference_power(df: pd.DataFrame, capacity_kw=5.0, tilt_deg=23.0, loss_pct=14.0):
    """
    Calculates reference PV power (kW) using the standard PVGIS / IEC empirical PV model:
    P(t) = P_peak * (G(t) / 1000) * [1 - gamma * (T_cell(t) - 25)] * (1 - loss)
    T_cell = T_ambient + G(t) * ((NOCT - 20) / 800)
    gamma = 0.004 / degC (standard crystalline silicon temperature coefficient)
    NOCT = 45 degC (Nominal Operating Cell Temperature)
    """
    df = df.copy()
    G = df["shortwave_radiation"].values.astype(float)  # Global Horizontal Irradiance (W/m2)
    T_amb = df["temperature_2m"].values.astype(float)

    # Cell temperature modeling
    NOCT = 45.0
    gamma = 0.004  # 0.4% loss per degC above 25 degC
    T_cell = T_amb + G * ((NOCT - 20.0) / 800.0)

    # Derating efficiency factor
    temp_derating = 1.0 - gamma * (T_cell - 25.0)
    temp_derating = np.clip(temp_derating, 0.70, 1.05)  # Physical bounds

    # System losses (14% standard)
    system_efficiency = (1.0 - (loss_pct / 100.0))

    # Raw hourly power (kW)
    power_kw = capacity_kw * (G / 1000.0) * temp_derating * system_efficiency

    # Physical clamping: nighttime and capacity bounds
    power_kw[G <= 1.0] = 0.0
    power_kw = np.clip(power_kw, 0.0, capacity_kw)

    df["pv_power_kw"] = np.round(power_kw, 3)
    df["pv_power_normalized"] = np.round(df["pv_power_kw"] / capacity_kw, 4)
    return df

def collect_and_prepare_dataset():
    """
    Executes the data collection pipeline:
    1. Fetches or loads raw Open-Meteo historical data for Indore.
    2. Computes reference PV power generation.
    3. Saves raw and processed datasets.
    """
    raw_csv_path = os.path.join(DATA_RAW_DIR, "indore_historical_weather_2024.csv")
    processed_csv_path = os.path.join(DATA_PROCESSED_DIR, "solar_train_dataset.csv")

    lat = DEFAULT_LOCATION["latitude"]
    lon = DEFAULT_LOCATION["longitude"]
    cap = DEFAULT_LOCATION["default_capacity_kw"]

    try:
        df_weather = fetch_open_meteo_history(latitude=lat, longitude=lon)
        df_weather.to_csv(raw_csv_path, index=False)
        print(f"Saved raw weather data to: {raw_csv_path}")
    except Exception as e:
        print(f"Error fetching from Open-Meteo ({e}). Checking for cached raw file...")
        if os.path.exists(raw_csv_path):
            df_weather = pd.read_csv(raw_csv_path)
            df_weather["time"] = pd.to_datetime(df_weather["time"])
        else:
            raise RuntimeError(f"Cannot fetch or load raw dataset: {e}")

    # Add reference PV generation
    df_solar = calculate_pvgis_reference_power(df_weather, capacity_kw=cap)

    # Add temporal columns
    df_solar["hour"] = df_solar["time"].dt.hour
    df_solar["month"] = df_solar["time"].dt.month
    df_solar["day"] = df_solar["time"].dt.day

    # Save processed training dataset
    df_solar.to_csv(processed_csv_path, index=False)
    print(f"Processed training dataset saved to: {processed_csv_path} ({len(df_solar)} records)")
    return processed_csv_path

if __name__ == "__main__":
    collect_and_prepare_dataset()
