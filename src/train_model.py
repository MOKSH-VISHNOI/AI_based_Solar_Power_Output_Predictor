"""
Model Training and Evaluation Pipeline for SolarPredict.
Trains Linear Regression, Decision Tree, and Random Forest models,
evaluates them on MAE, RMSE, and R2, and saves the best model with Joblib.
"""
import os
import sys
import json
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from src.config import (
    DATA_PROCESSED_DIR,
    MODEL_FILE_PATH,
    MODEL_METRICS_PATH
)
from src.preprocessing import prepare_features, clamp_power_output, FEATURE_COLUMNS
from src.data_collection import collect_and_prepare_dataset

def evaluate_predictions(y_true, y_pred, ghi, capacity_kw=5.0):
    """
    Evaluates regression predictions after applying physical clamping.
    """
    y_pred_clamped = clamp_power_output(y_pred, ghi, capacity_kw)
    mae = mean_absolute_error(y_true, y_pred_clamped)
    mse = mean_squared_error(y_true, y_pred_clamped)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred_clamped)
    return {
        "mae": round(float(mae), 4),
        "rmse": round(float(rmse), 4),
        "r2": round(float(r2), 4)
    }, y_pred_clamped

def train_and_evaluate_models():
    """
    Trains baseline and ensemble models, compares their test metrics,
    and saves the best model.
    """
    dataset_path = os.path.join(DATA_PROCESSED_DIR, "solar_train_dataset.csv")
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}. Running collection pipeline first...")
        collect_and_prepare_dataset()

    df = pd.read_csv(dataset_path)
    df["time"] = pd.to_datetime(df["time"])
    print(f"Loaded training dataset with {len(df)} hourly records.")

    # Prepare features and target
    X = prepare_features(df)
    y = df["pv_power_kw"].values
    ghi = df["shortwave_radiation"].values

    # Chronological 80/20 train/test split to prevent temporal leakage
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    ghi_test = ghi[split_idx:]

    print(f"Train samples: {len(X_train)} | Test samples: {len(X_test)}")

    # Define Candidate Models
    models = {
        "Linear Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("regressor", LinearRegression())
        ]),
        "Decision Tree Regressor": DecisionTreeRegressor(
            max_depth=12,
            min_samples_leaf=5,
            random_state=42
        ),
        "Random Forest Regressor": RandomForestRegressor(
            n_estimators=100,
            max_depth=16,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1
        )
    }

    results = {}
    best_model_name = None
    best_r2 = -float("inf")

    print("\n" + "="*60)
    print(f"{'Model Name':<28} | {'MAE (kW)':<10} | {'RMSE (kW)':<10} | {'R2 Score':<10}")
    print("-" * 65)

    for name, model in models.items():
        # Train
        model.fit(X_train, y_train)

        # Predict on Test set
        raw_pred = model.predict(X_test)
        metrics, _ = evaluate_predictions(y_test, raw_pred, ghi_test, capacity_kw=5.0)

        results[name] = metrics
        print(f"{name:<28} | {metrics['mae']:<10.4f} | {metrics['rmse']:<10.4f} | {metrics['r2']:<10.4f}")

        # Model selection: maximize R2, tie-break with lowest RMSE
        if (metrics["r2"] > best_r2) or (abs(metrics["r2"] - best_r2) < 1e-5 and metrics["rmse"] < results.get(best_model_name, {}).get("rmse", float("inf"))):
            best_r2 = metrics["r2"]
            best_model_name = name

    print("="*60)
    print(f"Best Performing Model: {best_model_name} (R2 = {best_r2:.4f}, RMSE = {results[best_model_name]['rmse']:.4f})\n")

    # Serialize Best Model and Metadata
    best_estimator = models[best_model_name]
    model_bundle = {
        "model_name": best_model_name,
        "estimator": best_estimator,
        "feature_names": FEATURE_COLUMNS,
        "reference_capacity_kw": 5.0,
        "training_date": datetime.now().isoformat(),
        "all_model_results": results,
        "selected_metrics": results[best_model_name]
    }

    joblib.dump(model_bundle, MODEL_FILE_PATH)
    print(f"Saved best model bundle to: {MODEL_FILE_PATH}")

    # Export metrics JSON for API / UI consumption
    with open(MODEL_METRICS_PATH, "w") as f:
        json.dump(model_bundle["all_model_results"], f, indent=2)
    print(f"Saved metrics to: {MODEL_METRICS_PATH}")

    return model_bundle

if __name__ == "__main__":
    train_and_evaluate_models()
