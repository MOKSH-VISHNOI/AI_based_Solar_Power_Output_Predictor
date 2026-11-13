"""
Comprehensive automated test suite for SolarPredict.
Validates model predictions, physical bounds, database queries, and Flask API endpoints.
"""
import unittest
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from src.predict import predict_solar_output
from src.config import MODEL_FILE_PATH, DATABASE_PATH

class TestSolarPredict(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        app.config["TESTING"] = True

    def test_model_file_exists(self):
        """Verifies trained model bundle is present on disk."""
        self.assertTrue(os.path.exists(MODEL_FILE_PATH), f"Model file missing at {MODEL_FILE_PATH}")

    def test_database_exists(self):
        """Verifies SQLite database is initialized."""
        self.assertTrue(os.path.exists(DATABASE_PATH), f"Database missing at {DATABASE_PATH}")

    def test_prediction_output_structure_and_bounds(self):
        """Verifies predict pipeline returns all expected fields and honors physical bounds."""
        res = predict_solar_output("Indore, Madhya Pradesh", 5.0, "tomorrow")
        self.assertIn("total_energy_kwh", res)
        self.assertIn("peak_power_kw", res)
        self.assertIn("hourly_power", res)
        self.assertEqual(len(res["hourly_power"]), 24)

        # Physical bounds check
        for p in res["hourly_power"]:
            self.assertGreaterEqual(p, 0.0, "Power output cannot be negative")
            self.assertLessEqual(p, 5.0, "Power cannot exceed installed capacity")

        # Nighttime check (0:00 to 4:00 AM should be 0 kW)
        for h in range(4):
            self.assertEqual(res["hourly_power"][h], 0.0, f"Night power at hour {h} should be 0 kW")

        # Energy should equal sum of hourly power
        expected_energy = round(sum(res["hourly_power"]), 1)
        self.assertAlmostEqual(res["total_energy_kwh"], expected_energy, places=1)

    def test_api_index_and_page_routes(self):
        """Verifies GET / and all dedicated page routes return HTTP 200."""
        routes = ["/", "/predictions", "/history", "/locations", "/models", "/about"]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed")
            self.assertIn(b"SolarPredict", response.data)

    def test_api_locations(self):
        """Verifies GET /api/locations returns JSON list with enriched solar data."""
        response = self.client.get("/api/locations")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(len(data["locations"]), 0)
        self.assertIn("solar_rating", data["locations"][0])

    def test_api_predict(self):
        """Verifies POST /api/predict handles request and returns expected JSON."""
        payload = {
            "location": "Indore, Madhya Pradesh",
            "capacity_kw": 5.0,
            "date": "tomorrow"
        }
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertIn("total_energy_kwh", res["data"])
        self.assertIn("peak_power_kw", res["data"])

    def test_api_history(self):
        """Verifies GET /api/history returns logged predictions."""
        response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertIsInstance(res["history"], list)

    def test_api_model_info(self):
        """Verifies GET /api/model-info returns evaluation metrics."""
        response = self.client.get("/api/model-info")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertIn("Random Forest Regressor", res["metrics"])
        self.assertIn("Linear Regression", res["metrics"])

if __name__ == "__main__":
    unittest.main()
