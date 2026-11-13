"""
Flask Application Server for SolarPredict.
Serves the web dashboard, dedicated views, and REST API endpoints.
"""
import os
import sys
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import SUPPORTED_LOCATIONS, DEFAULT_LOCATION, MODEL_METRICS_PATH
from src.database import init_db, get_prediction_history
from src.predict import predict_solar_output

app = Flask(__name__)

# Enable CORS for external/standalone frontend files
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

# Initialize DB upon starting
with app.app_context():
    init_db()

def get_template_context(active_tab="dashboard"):
    """Helper to assemble standard date and location context for pages."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    date_options = [
        {"val": "today", "label": f"Today ({today.strftime('%d %b %Y')})"},
        {"val": "tomorrow", "label": f"Tomorrow ({tomorrow.strftime('%d %b %Y')})"},
        {"val": (today + timedelta(days=2)).strftime("%Y-%m-%d"), "label": (today + timedelta(days=2)).strftime("%a, %d %b %Y")},
        {"val": (today + timedelta(days=3)).strftime("%Y-%m-%d"), "label": (today + timedelta(days=3)).strftime("%a, %d %b %Y")},
        {"val": (today + timedelta(days=4)).strftime("%Y-%m-%d"), "label": (today + timedelta(days=4)).strftime("%a, %d %b %Y")}
    ]

    return {
        "locations": SUPPORTED_LOCATIONS,
        "default_location": DEFAULT_LOCATION,
        "date_options": date_options,
        "current_date_formatted": today.strftime("%d %b %Y"),
        "active_tab": active_tab
    }

@app.route("/")
def index():
    """Renders the main SolarPredict dashboard."""
    return render_template("dashboard.html", **get_template_context("dashboard"))

@app.route("/predictions")
def page_predictions():
    """Renders the dashboard with Predictions view active."""
    return render_template("dashboard.html", **get_template_context("predictions"))

@app.route("/history")
def page_history():
    """Renders the dashboard with History view active."""
    return render_template("dashboard.html", **get_template_context("history"))

@app.route("/locations")
def page_locations():
    """Renders the dashboard with Locations view active."""
    return render_template("dashboard.html", **get_template_context("locations"))

@app.route("/models")
def page_models():
    """Renders the dashboard with Model Metrics view active."""
    return render_template("dashboard.html", **get_template_context("models"))

@app.route("/about")
def page_about():
    """Renders the dashboard with About view active."""
    return render_template("dashboard.html", **get_template_context("about"))

@app.route("/api/locations", methods=["GET"])
def api_locations():
    """Returns the list of supported installation sites."""
    return jsonify({
        "status": "success",
        "locations": SUPPORTED_LOCATIONS
    })

@app.route("/api/predict", methods=["POST"])
def api_predict():
    """
    Main prediction endpoint.
    Accepts JSON: { location: str, capacity_kw: float, date: str }
    """
    try:
        data = request.get_json() or {}
        location_name = data.get("location", DEFAULT_LOCATION["name"])
        
        try:
            capacity_kw = float(data.get("capacity_kw", 5.0))
            if capacity_kw <= 0:
                return jsonify({"status": "error", "message": "Capacity must be a positive number greater than 0."}), 400
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid installed capacity value provided."}), 400

        target_date = data.get("date", "tomorrow")

        # Execute ML prediction pipeline
        result = predict_solar_output(
            location_name=location_name,
            capacity_kw=capacity_kw,
            target_date_str=target_date
        )

        return jsonify({
            "status": "success",
            "data": result
        })

    except Exception as e:
        app.logger.error(f"Prediction error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to generate solar forecast: {str(e)}"
        }), 500

@app.route("/api/history", methods=["GET"])
def api_history():
    """Returns the recent prediction history logs from SQLite."""
    try:
        limit = int(request.args.get("limit", 25))
        history = get_prediction_history(limit=limit)
        return jsonify({
            "status": "success",
            "count": len(history),
            "history": history
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/model-info", methods=["GET"])
def api_model_info():
    """Returns model evaluation comparison and metrics for academic review."""
    import json
    if os.path.exists(MODEL_METRICS_PATH):
        with open(MODEL_METRICS_PATH, "r") as f:
            metrics = json.load(f)
        return jsonify({
            "status": "success",
            "metrics": metrics
        })
    return jsonify({
        "status": "error",
        "message": "Model metrics not found."
    }), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting SolarPredict Flask Server on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
