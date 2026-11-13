"""
Database management for SolarPredict using SQLite.
Stores installation details and logged prediction runs.
"""
import sqlite3
import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import DATABASE_PATH, SUPPORTED_LOCATIONS

def get_db_connection():
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables and seeds default locations if not already present."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Installations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS installations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        short_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        default_capacity_kw REAL DEFAULT 5.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Prediction history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prediction_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        installed_capacity_kw REAL NOT NULL,
        prediction_date TEXT NOT NULL,
        total_energy_kwh REAL NOT NULL,
        peak_power_kw REAL NOT NULL,
        peak_time TEXT NOT NULL,
        effective_sunshine_hours REAL NOT NULL,
        forecast_condition TEXT,
        avg_cloud_cover REAL,
        model_name TEXT NOT NULL,
        co2_avoided_kg REAL,
        trees_equivalent REAL,
        hourly_predictions_json TEXT NOT NULL,
        weather_summary_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed default locations
    for loc in SUPPORTED_LOCATIONS:
        cursor.execute("""
        INSERT OR IGNORE INTO installations (code, name, short_name, latitude, longitude, default_capacity_kw)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            loc["id"],
            loc["name"],
            loc["short_name"],
            loc["latitude"],
            loc["longitude"],
            loc["default_capacity_kw"]
        ))

    conn.commit()
    conn.close()

def save_prediction_record(data):
    """
    Saves a completed prediction run into prediction_history.
    """
    init_db()  # Ensure tables exist
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO prediction_history (
        location_name, latitude, longitude, installed_capacity_kw,
        prediction_date, total_energy_kwh, peak_power_kw, peak_time,
        effective_sunshine_hours, forecast_condition, avg_cloud_cover,
        model_name, co2_avoided_kg, trees_equivalent,
        hourly_predictions_json, weather_summary_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("location_name"),
        data.get("latitude"),
        data.get("longitude"),
        data.get("installed_capacity_kw"),
        data.get("prediction_date"),
        data.get("total_energy_kwh"),
        data.get("peak_power_kw"),
        data.get("peak_time"),
        data.get("effective_sunshine_hours"),
        data.get("forecast_condition"),
        data.get("avg_cloud_cover"),
        data.get("model_name", "Random Forest Regressor"),
        data.get("co2_avoided_kg"),
        data.get("trees_equivalent"),
        json.dumps(data.get("hourly_predictions", [])),
        json.dumps(data.get("weather_summary", {}))
    ))

    prediction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return prediction_id

def get_prediction_history(limit=20):
    """
    Fetches recent prediction records.
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, location_name, installed_capacity_kw, prediction_date,
           total_energy_kwh, peak_power_kw, peak_time, forecast_condition,
           co2_avoided_kg, created_at
    FROM prediction_history
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
