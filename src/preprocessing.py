"""
Preprocessing and Feature Engineering for SolarPredict.
Handles time transformations, cyclical encodings, and feature alignment.
"""
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
    "temperature_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "wind_speed_10m",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos"
]

def add_cyclical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds cyclical sine and cosine encodings for hour and month
    to ensure smooth circular continuity across midnight and year boundaries.
    """
    df = df.copy()
    if "hour" in df.columns:
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    if "month" in df.columns:
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12.0)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12.0)
    return df

def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares and selects the exact feature matrix X required for model training or inference.
    """
    df = df.copy()

    # Fill any missing radiation columns with 0 if absent
    for col in ["shortwave_radiation", "direct_normal_irradiance", "diffuse_radiation"]:
        if col not in df.columns:
            df[col] = 0.0

    # Ensure cyclical features are present
    if "hour_sin" not in df.columns:
        df = add_cyclical_features(df)

    # Validate all required columns exist
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")

    return df[FEATURE_COLUMNS]

def clamp_power_output(y_pred: np.ndarray, ghi: np.ndarray, capacity_kw: float) -> np.ndarray:
    """
    Applies strict physical domain rules:
    1. If Global Horizontal Irradiance (GHI) <= 0, power is strictly 0.0 kW (nighttime).
    2. Clamps negative predictions to 0.0.
    3. Clamps maximum prediction to rated installed capacity (kW).
    """
    clamped = np.copy(y_pred)
    clamped[clamped < 0.0] = 0.0
    clamped[clamped > capacity_kw] = capacity_kw
    # Nighttime zero clamp
    clamped[ghi <= 1.0] = 0.0
    return clamped
