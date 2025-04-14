import os
import requests
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Load environment variables from .env file in the current directory
load_dotenv()

app = Flask(__name__)

# Get the API key from environment variables
IPSTACK_ACCESS_KEY = os.getenv('IPSTACK_API_KEY')
IPSTACK_BASE_URL = "http://api.ipstack.com/" # Use http for free tier

# Default location (e.g., New York) to use if API fails or key is missing
DEFAULT_LOCATION = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "city": "New York (Default)",
    "region_name": "New York",
    "country_name": "United States"
}

@app.route('/location', methods=['GET'])
def get_location():
    """
    Gets location data from IPStack based on IP address.
    Uses 'check' for the requester's IP or allows specifying an IP via query param.
    Returns default location on error or if API key is missing.
    """
    if not IPSTACK_ACCESS_KEY:
        print("Warning: IPSTACK_API_KEY not found in environment variables.")
        warning_msg = "Location API key not configured. Returning default location."
        return jsonify({**DEFAULT_LOCATION, "warning": warning_msg}), 200 # Return 200 but indicate default

    # Use 'check' to get location for the request IP, or use provided 'ip' query param
    # Note: '127.0.0.1' or private IPs often don't resolve well on free tier.
    # 'check' is usually the best option unless testing specific public IPs.
    ip_address = request.args.get('ip', 'check')

    try:
        print(f"Location Service: Requesting location for IP: {ip_address}")
        url = f"{IPSTACK_BASE_URL}{ip_address}?access_key={IPSTACK_ACCESS_KEY}&fields=ip,city,region_name,country_name,latitude,longitude"
        response = requests.get(url, timeout=5) # Add a timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Check for API-specific errors returned in the JSON body
        if data.get("success") is False or not data.get("latitude"):
            error_info = data.get("error", {}).get("info", "Unknown IPStack API error")
            print(f"IPStack API Error: {error_info}")
            warning_msg = f"Could not fetch location from IPStack ({error_info}). Returning default location."
            return jsonify({**DEFAULT_LOCATION, "warning": warning_msg}), 200 # Return 200 but indicate default

        # Successfully got data
        location_info = {
            "ip": data.get("ip"),
            "city": data.get("city"),
            "region_name": data.get("region_name"),
            "country_name": data.get("country_name"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        }
        print(f"Location Service: Successfully found location: {location_info.get('city')}")
        return jsonify(location_info)

    except requests.exceptions.Timeout:
        print("Error: Request to IPStack timed out.")
        warning_msg = "Location service request timed out. Returning default location."
        return jsonify({**DEFAULT_LOCATION, "warning": warning_msg}), 504 # 504 Gateway Timeout might be suitable

    except requests.exceptions.RequestException as e:
        print(f"Error: Network or HTTP error calling IPStack: {e}")
        warning_msg = f"Network error contacting location service ({e}). Returning default location."
        return jsonify({**DEFAULT_LOCATION, "warning": warning_msg}), 503 # 503 Service Unavailable

if __name__ == '__main__':
    # Run on port 5001. debug=True reloads on code changes.
    print("Starting Location Service on http://127.0.0.1:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)