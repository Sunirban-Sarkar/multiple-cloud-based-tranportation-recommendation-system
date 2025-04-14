import os
import random
from flask import Flask, request, jsonify
from geopy.distance import geodesic # Import geodesic distance calculation

app = Flask(__name__)

# Determine the 'source' cloud from an environment variable
# Default to 'GCP' if not set. We'll set this when running multiple instances.
CLOUD_SOURCE = os.getenv('CLOUD_PROVIDER', 'GCP')
PORT_TO_USE = int(os.getenv('PORT', 5002)) # Allow port override via env var

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    """
    Generates mock transportation recommendations scaled by distance.
    Takes origin/destination coordinates and preference as input.
    Simulates data coming from a specific cloud provider (GCP/Azure).
    """
    origin_lat = request.args.get('origin_lat')
    origin_lon = request.args.get('origin_lon')
    dest_lat = request.args.get('dest_lat')
    dest_lon = request.args.get('dest_lon')
    preference = request.args.get('preference', 'fastest') # fastest, cheapest, greenest

    if not all([origin_lat, origin_lon, dest_lat, dest_lon]):
        return jsonify({"error": "Missing origin or destination coordinates"}), 400

    print(f"Routing Service ({CLOUD_SOURCE}): Received request from ({origin_lat},{origin_lon}) to ({dest_lat},{dest_lon}), preference: {preference}")

    # --- Calculate Distance ---
    try:
        origin_point = (float(origin_lat), float(origin_lon))
        dest_point = (float(dest_lat), float(dest_lon))
        # Calculate the distance using geodesic which is accurate on an ellipsoid (Earth)
        distance_km = geodesic(origin_point, dest_point).km
        print(f"Routing Service ({CLOUD_SOURCE}): Calculated distance: {distance_km:.2f} km")
    except ValueError:
        print(f"Error: Invalid coordinate format received: lat={origin_lat}, lon={origin_lon} / lat={dest_lat}, lon={dest_lon}")
        return jsonify({"error": "Invalid coordinate format"}), 400
    except Exception as e:
        # Catch potential errors during distance calculation
        print(f"Error calculating distance: {e}")
        return jsonify({"error": "Could not calculate distance"}), 500

    # --- MOCK DATA GENERATION (Distance-Aware) ---
    options = []
    possible_modes = ["car", "bus", "train", "bicycle", "walking", "scooter"]
    # Don't offer walking/bicycle for very long distances
    if distance_km > 200:
        possible_modes = ["car", "bus", "train"]
    elif distance_km > 50:
        possible_modes = ["car", "bus", "train", "bicycle", "scooter"]

    num_options = random.randint(1, min(len(possible_modes), 4)) # Generate 1 to 4 options
    selected_modes = random.sample(possible_modes, num_options) if possible_modes else []

    for i, mode in enumerate(selected_modes):

        # --- Estimate Duration based on Distance & Mode ---
        # Rough average speed assumptions (km/h) - ADJUST THESE AS NEEDED!
        avg_speed_kph = 50 # Default/fallback
        if mode == "car":
            avg_speed_kph = 70 + random.uniform(-10, 10) # Add slight speed variance
        elif mode == "train":
             # Trains are faster over long distances, slower for short hops (incl. station time)
            avg_speed_kph = 50 + (distance_km * 0.05) + random.uniform(-15, 15)
            avg_speed_kph = max(30, min(avg_speed_kph, 120)) # Cap speed range
        elif mode == "bus":
            avg_speed_kph = 40 + random.uniform(-5, 5)
        elif mode == "bicycle":
            avg_speed_kph = 15 + random.uniform(-3, 3)
        elif mode == "walking":
            avg_speed_kph = 5 + random.uniform(-0.5, 0.5)
        elif mode == "scooter":
             avg_speed_kph = 12 + random.uniform(-2, 2)

        # Calculate estimated base duration in hours, then minutes
        if avg_speed_kph <= 0:
             estimated_minutes = float('inf') # Avoid division by zero
        else:
             estimated_hours = distance_km / avg_speed_kph
             estimated_minutes = estimated_hours * 60

        # Add randomness *around* the estimate (e.g., +/- 30%)
        # Make randomness factor smaller for very short distances?
        random_factor = random.uniform(0.7, 1.3)
        base_duration = estimated_minutes * random_factor

        # Ensure minimum duration (e.g., 5 mins) and handle infinite case
        if base_duration == float('inf'):
             base_duration = 99999 # Assign a very large number if speed was 0
        base_duration = max(5, base_duration)

        # --- Simulate Cost and Emissions (Still basic, could be distance-based) ---
        # Example: Make cost slightly distance dependent
        cost_factor = 0.01 + (distance_km * 0.0005) # Small base + per km factor
        base_cost = (random.uniform(0.5, 1.5) * base_duration * cost_factor) if mode not in ["bicycle", "walking"] else 0
        base_cost = round(max(0.5, base_cost), 2) if base_cost > 0 else 0 # Min cost $0.50 if not free

        # Example: Make emissions slightly distance dependent (grams CO2 per km)
        emissions_factor_g_km = 0
        if mode == "car": emissions_factor_g_km = random.uniform(100, 200)
        elif mode == "bus": emissions_factor_g_km = random.uniform(30, 80) # Per passenger estimate is lower
        elif mode == "train": emissions_factor_g_km = random.uniform(10, 50)
        elif mode == "scooter": emissions_factor_g_km = random.uniform(5, 20)

        base_emissions_kg = (distance_km * emissions_factor_g_km / 1000) * random.uniform(0.8, 1.2)
        base_emissions_kg = round(max(0, base_emissions_kg), 2)


        # --- Adjust based on user preference ---
        final_duration = base_duration * (0.85 if preference == 'fastest' else random.uniform(1.0, 1.15))
        final_cost = base_cost * (0.80 if preference == 'cheapest' else random.uniform(1.0, 1.2))
        # Ensure cost doesn't become negative if base was 0
        final_cost = max(0, final_cost) if base_cost == 0 else max(0.5, final_cost)

        final_emissions = base_emissions_kg * (0.70 if preference == 'greenest' else random.uniform(1.0, 1.3))
        final_emissions = max(0, final_emissions)


        options.append({
            "id": f"{mode}-{i+1}-{CLOUD_SOURCE}-{random.randint(100,999)}",
            "mode": mode,
            "duration_minutes": int(final_duration), # Convert to integer minutes
            "cost_usd": round(final_cost, 2),
            "environmental_impact_co2_kg": round(final_emissions, 2),
            "estimated_distance_km": round(distance_km, 1), # Include distance
            "source_cloud": CLOUD_SOURCE
        })

    # Sort results based on preference
    if preference == 'fastest':
        options.sort(key=lambda x: x['duration_minutes'])
    elif preference == 'cheapest':
        # Sort primarily by cost, secondarily by duration
        options.sort(key=lambda x: (x['cost_usd'], x['duration_minutes']))
    elif preference == 'greenest':
        # Prioritize zero emission, then lowest emission, then time
        options.sort(key=lambda x: (x['environmental_impact_co2_kg'] > 0, x['environmental_impact_co2_kg'], x['duration_minutes']))

    print(f"Routing Service ({CLOUD_SOURCE}): Returning {len(options)} recommendations.")
    return jsonify({"recommendations": options})

# Simple health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({"status": "ok", "source": CLOUD_SOURCE}), 200

if __name__ == '__main__':
    print(f"Starting Routing Service ({CLOUD_SOURCE}) on http://127.0.0.1:{PORT_TO_USE}")
    # Use host='0.0.0.0' to make it accessible on your network if needed
    app.run(host='0.0.0.0', port=PORT_TO_USE, debug=True) # Keep debug=True for development