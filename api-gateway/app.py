import os
import random
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Configuration ---
# Get service URLs from environment variables or use defaults for local testing
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://127.0.0.1:5001")

# Define multiple routing service endpoints (these would be your deployed URLs later)
ROUTING_SERVICE_URLS_STR = os.getenv("ROUTING_SERVICE_URLS", "http://127.0.0.1:5002,http://127.0.0.1:5003")
ROUTING_SERVICE_URLS = [url.strip() for url in ROUTING_SERVICE_URLS_STR.split(',')]

# Simple Geocoding Simulation (City Name -> Lat/Lon)
CITY_COORDINATES = {
    "new york": {"latitude": 40.7128, "longitude": -74.0060},
    "los angeles": {"latitude": 34.0522, "longitude": -118.2437},
    "london": {"latitude": 51.5074, "longitude": -0.1278},
    "tokyo": {"latitude": 35.6895, "longitude": 139.6917},
    "sydney": {"latitude": -33.8688, "longitude": 151.2093},
    "kolkata": {"latitude": 22.5726, "longitude": 88.3639},
    "mumbai": {"latitude": 19.0760, "longitude": 72.8777},
}

# --- Helper Functions ---
def get_coordinates_for_city(city_name):
    """Looks up coordinates for a city name (case-insensitive)."""
    return CITY_COORDINATES.get(city_name.lower())

def check_service_health(url):
    """Performs a very basic health check on a service URL."""
    try:
        # Use the /health endpoint we added to the routing service
        health_url = f"{url.rstrip('/')}/health"
        response = requests.get(health_url, timeout=1.5) # Short timeout for health check
        return response.status_code == 200 and response.json().get("status") == "ok"
    except requests.exceptions.RequestException as e:
        print(f"Health check failed for {url}: {e}")
        return False

# --- API Routes ---
@app.route('/api/route', methods=['GET'])
def get_route_recommendations():
    """
    Main endpoint to get transportation recommendations.
    1. Gets origin from Location Service.
    2. Gets destination coordinates via geocoding simulation.
    3. Selects a healthy Routing Service instance.
    4. Calls Routing Service for recommendations.
    5. Returns combined results.
    """
    dest_city_name = request.args.get('destination')
    preference = request.args.get('preference', 'fastest')
    test_ip = request.args.get('test_ip') # Optional: for overriding IP in location lookup

    if not dest_city_name:
        return jsonify({"error": "Destination city parameter ('destination') is required"}), 400

    # 1. Get Origin Coordinates from Location Service
    origin_coords = None
    location_warning = None
    try:
        location_params = {}
        if test_ip:
            location_params['ip'] = test_ip
        print(f"API Gateway: Calling Location Service at {LOCATION_SERVICE_URL}")
        location_resp = requests.get(f"{LOCATION_SERVICE_URL}/location", params=location_params, timeout=5)
        location_resp.raise_for_status() # Check for HTTP errors
        origin_data = location_resp.json()
        location_warning = origin_data.get("warning") # Capture warnings (e.g., default used)

        # Check if valid coordinates were returned (even if default)
        if origin_data.get("latitude") is not None and origin_data.get("longitude") is not None:
             origin_coords = {
                 "city": origin_data.get("city", "Unknown"),
                 "latitude": origin_data["latitude"],
                 "longitude": origin_data["longitude"]
             }
             print(f"API Gateway: Received origin: {origin_coords.get('city')}")
        else:
            # This case should ideally not happen if location service returns default coords
             print("API Gateway: Location service response missing coordinates.")
             # Fallback handled below

    except requests.exceptions.Timeout:
        print("API Gateway Error: Request to Location Service timed out.")
        return jsonify({"error": "Failed to get origin location: Request timed out"}), 504
    except requests.exceptions.RequestException as e:
        print(f"API Gateway Error: Could not connect to Location Service: {e}")
        # Decide if we should proceed with a default origin or fail
        # For now, we let origin_coords remain None and handle it later
        location_warning = f"Could not contact Location Service ({e}). Origin unknown."
        # Optionally return 503 Service Unavailable if origin is critical
        # return jsonify({"error": f"Could not contact Location Service: {e}"}), 503

    # Handle case where origin couldn't be determined
    if origin_coords is None:
         print("API Gateway: Origin coordinates could not be determined. Using default.")
         # Using a default origin (e.g., London) if location service failed completely
         origin_coords = {"latitude": 51.5074, "longitude": -0.1278, "city": "London (Default Origin)"}
         if not location_warning: # Add a warning if none exists yet
             location_warning = "Origin location could not be determined; using default."


    # 2. Get Destination Coordinates (Geocoding Simulation)
    dest_coords = get_coordinates_for_city(dest_city_name)
    if not dest_coords:
        return jsonify({"error": f"Could not find coordinates for destination city: {dest_city_name}"}), 404 # Not Found

    # 3. Select a Healthy Routing Service (Basic Load Balancing + Health Check)
    available_routing_services = [url for url in ROUTING_SERVICE_URLS if check_service_health(url)]

    if not available_routing_services:
        print("API Gateway Error: No healthy Routing Service instances available.")
        return jsonify({"error": "Recommendation service is temporarily unavailable"}), 503 # Service Unavailable

    # Randomly choose from the healthy ones
    selected_routing_url = random.choice(available_routing_services)
    print(f"API Gateway: Selected healthy Routing Service: {selected_routing_url}")

    # 4. Call Selected Routing Service
    try:
        routing_params = {
            "origin_lat": origin_coords["latitude"],
            "origin_lon": origin_coords["longitude"],
            "dest_lat": dest_coords["latitude"],
            "dest_lon": dest_coords["longitude"],
            "preference": preference
        }
        routing_resp = requests.get(f"{selected_routing_url}/recommendations", params=routing_params, timeout=10)
        routing_resp.raise_for_status() # Check for HTTP errors from routing service
        recommendations_data = routing_resp.json()

    except requests.exceptions.Timeout:
        print(f"API Gateway Error: Request to Routing Service ({selected_routing_url}) timed out.")
        return jsonify({"error": "Fetching recommendations timed out"}), 504
    except requests.exceptions.RequestException as e:
        print(f"API Gateway Error: Could not get recommendations from {selected_routing_url}: {e}")
        # Try to return error from downstream service if possible
        error_details = "Unknown error communicating with recommendation service."
        status_code = 503 # Service Unavailable by default
        if e.response is not None:
            status_code = e.response.status_code
            try:
                error_details = e.response.json().get("error", error_details)
            except ValueError:
                error_details = e.response.text[:200] # Limit error text length
        return jsonify({"error": "Failed to get recommendations", "details": error_details}), status_code

    # 5. Combine Results and Return
    final_response = {
        "origin": origin_coords,
        "destination_requested": dest_city_name,
        "destination_coords": dest_coords,
        "preference": preference,
        "recommendations": recommendations_data.get("recommendations", []),
        "notes": []
    }
    if location_warning:
        final_response["notes"].append(location_warning)

    return jsonify(final_response)


if __name__ == '__main__':
    print("Starting API Gateway on http://127.0.0.1:5000")
    # Use host='0.0.0.0' if you need to access it from other devices on your network
    app.run(host='0.0.0.0', port=5000, debug=True)