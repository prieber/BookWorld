"""
api.py
 
BookWorld REST API: exposes the final aggregated data (sales_by_country)
produced by pipeline.py. Protected routes require a Bearer token, read
from the BOOKWORLD_API_TOKEN environment variable (see .env.example).
"""
from flask import Flask, jsonify, request
from functools import wraps
from dotenv import load_dotenv
import sqlite3
import pandas as pd
import os

# Load variables from .env into the process environment (does nothing if
# .env doesn't exist, e.g. in a CI environment where the variable is set
# some other way)
load_dotenv()

app = Flask(__name__)

# Path to the final database, produced by pipeline.py
DB_PATH = "output_pipeline/bookworld_final.db"

# Expected token, read from the environment
SECRET_TOKEN = os.getenv("BOOKWORLD_API_TOKEN")

def require_token(route_function):
    """
    Decorator that protects a route with a simple token check.
    Expects a header "Authorization: Bearer <token>" matching
    BOOKWORLD_API_TOKEN. Returns 401 if missing or incorrect.

    Header only (no URL query paramter fallback):
    this is the standard practice for a production REST API.
    """
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing (or malformed) Authorization header"}), 401

        token = auth_header.removeprefix("Bearer ")
        if token != SECRET_TOKEN:
            return jsonify({"error": "Invalid token"}), 401

        return route_function(*args, **kwargs)

    return wrapper


def run_query(query):
    """Run a SQL query against the final database and return a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@app.route("/health", methods=["GET"])
def health():
    """Check whether the API is running."""
    return jsonify({"status": "ok"})


@app.route("/sales-by-country", methods=["GET"])
@require_token
def sales_by_country():
    """Return the aggregated sales by country. Requires a valid Bearer token."""
    if not os.path.exists(DB_PATH):
        return jsonify({
            "error": f"Database not found ({DB_PATH}). Run pipeline.py first."
        }), 503

    query_sales_by_country = """
        SELECT *
        FROM sales_by_country
    """

    try:
        df_sales_by_country = run_query(query_sales_by_country)
    except Exception as e:
        return jsonify({
            "error": f"Could not read sales_by_country: {e}"
        }), 500

    return jsonify(df_sales_by_country.to_dict(orient="records"))


if __name__ == "__main__":
    app.run(debug=True)
