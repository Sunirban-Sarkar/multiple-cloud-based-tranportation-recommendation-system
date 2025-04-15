# Multi-Cloud Transport Recommendation

## Overview

This web application provides users with transport recommendations based on their desired destination and travel preferences (fastest, cheapest, or most environmentally friendly). It automatically attempts to detect the user's origin location (based on IP address) and queries backend services to calculate and display relevant options, including estimated duration, cost, and CO2 impact.

The application is designed with a microservices architecture and intended for deployment across multiple cloud platforms (GCP and Azure in this project) for high availability and resilience, accessed via a unified entry point managed by Azure Traffic Manager.

## Features

* **Destination Input:** User provides the target destination city.
* **Preference Selection:** User chooses between 'Fastest', 'Cheapest', or 'Environment Friendly' route preferences.
* **Automatic Origin Detection:** Attempts to determine the user's starting city based on their public IP address.
* **Microservice Backend:** Utilizes separate services for API orchestration, location lookup, and route calculation.
* **Recommendation Display:** Shows a list of suggested transport modes (e.g., car, bus, train) with details:
  * Estimated Duration (minutes)
  * Estimated Cost (USD)
  * Estimated Environmental Impact (kg CO2)
  * Source Cloud (indicating which backend instance provided the data - useful for multi-cloud debugging)

## Technology Stack

* **Frontend:** HTML, CSS, Vanilla JavaScript
* **Backend:** Python 3
* **API Framework:** Flask
* **WSGI Server:** Gunicorn
* **Web Server / Reverse Proxy:** Nginx
* **Deployment Environment:** Linux VMs (Ubuntu) on GCP & Azure

## Application Architecture

The application follows a microservices pattern:

1. **UI Service (`ui-service/`):** Contains the static frontend files (HTML, CSS, JS) served directly by Nginx. Handles user input and displays results fetched from the API Gateway.
2. **Nginx:** Acts as the web server for static files and a reverse proxy. It listens on port 80 and forwards requests starting with `/api/` to the API Gateway.
3. **API Gateway (`api-gateway/`):** A Flask application acting as the central backend entry point. It receives requests from the frontend (via Nginx proxy), calls the Location and Routing services, aggregates the data, and returns the final response. Typically runs on port 5000 locally within the VM.
4. **Location Service (`location-service/`):** A Flask application responsible for determining the user's origin based on their IP address. Typically runs on port 5001 locally.
5. **Routing Service (`routing-service/`):** A Flask application that takes origin, destination, and preference data to calculate and return transport recommendations. Runs on port 5002 (GCP instance) or 5003 (Azure instance) locally.

**Request Flow (Deployed):**
User Browser -> Azure Traffic Manager DNS -> (GCP or Azure VM Public IP) -> Nginx (Port 80)

* If `/` -> Serves `index.html` from `ui-service/`
* If `/api/route?...` -> Proxies to API Gateway (localhost:5000) -> API Gateway calls Location Service (localhost:5001) & Routing Service (localhost:5002 or 5003) -> Response flows back.

## Local Development Setup

These instructions are for running the application components locally for development purposes, without Nginx or Gunicorn initially.

1. **Clone the Repository:**

    ```bash
    git clone <your-repo-url>
    cd multi-cloud-transport-recommendation
    ```

2. **Set up Python Environment:** (Recommended: Use a virtual environment)

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure Frontend for Local API:**
    * Edit `ui-service/script.js`.
    * Temporarily change the `fetch` call's URL target to point directly to your local API Gateway address (usually `http://127.0.0.1:5000`). For example:

        ```javascript
        // In fetchRecommendations function:
        // const relativeUrl = `/api/route?destination=...`; // Use this for deployment
        const apiUrl = `http://127.0.0.1:5000/api/route?destination=${encodeURIComponent(destination)}&preference=${encodeURIComponent(preference)}`; // Use this for local Flask testing
        console.log("Attempting to fetch local URL:", apiUrl);
        const response = await fetch(apiUrl);
        ```

    * **Remember to change this back to the relative URL (`/api/route...`) before deploying!**

## Running Locally

Run each Flask service in a separate terminal window from the project's root directory:

1. **Terminal 1: Location Service**

    ```bash
    python location-service/app.py
    # Or: FLASK_APP=location-service/app.py flask run --port 5001
    ```

    *(Should indicate running on port 5001)*

2. **Terminal 2: Routing Service**

    ```bash
    python routing-service/app.py
    # Or: FLASK_APP=routing-service/app.py flask run --port 5002
    ```

    *(Should indicate running on port 5002 - adjust port if needed)*

3. **Terminal 3: API Gateway**

    ```bash
    python api-gateway/app.py
    # Or: FLASK_APP=api-gateway/app.py flask run --port 5000
    ```

    *(Should indicate running on port 5000)*

4. **Access the Frontend:**
    * Open the `ui-service/index.html` file directly in your web browser (`file:///path/to/project/ui-service/index.html`).
    * Use the form. API calls should now target your locally running API Gateway on port 5000.

## API Endpoint

### `GET /api/route`

Retrieves transport recommendations.

* **Query Parameters:**
  * `destination` (string, required): The target city name.
  * `preference` (string, required): The user's preference ('fastest', 'cheapest', 'greenest').
  * `test_ip` (string, optional): An IP address to use for location testing instead of the request's source IP.
* **Success Response (200 OK):**

    ```json
    {
      "origin": {
        "ip_address": "1.2.3.4",
        "city": "Origin City Name"
      },
      "notes": [
          "Note about routing calculation if any."
      ],
      "recommendations": [
        {
          "mode": "car",
          "duration_minutes": 120,
          "cost_usd": 25.50,
          "environmental_impact_co2_kg": 15.75,
          "source_cloud": "GCP" // Or "Azure"
        },
        {
          "mode": "train",
          "duration_minutes": 90,
          "cost_usd": 35.00,
          "environmental_impact_co2_kg": 5.20,
          "source_cloud": "GCP" // Or "Azure"
        }
        // ... other recommendations
      ]
    }
    ```

* **Error Response (e.g., 400 Bad Request, 500 Internal Server Error):**

    ```json
    {
      "error": "Detailed error message explaining the issue."
    }
    ```

## Configuration

* **Service Ports:** Ports for backend services (5000, 5001, 5002/5003) are currently hardcoded or set via Flask/Gunicorn startup.
* **Frontend API Target:** The `ui-service/script.js` file needs its `fetch` URL adjusted depending on whether running locally (direct `http://127.0.0.1:5000`) or deployed (relative `/api/route`).

## Future Improvements 

* Containerize services using Docker for easier deployment and consistency.
* Add input validation for destination.
* Integrate real-time traffic data.
* Expand range of transport modes.
* Implement user accounts for saved preferences/history.
* Improve UI/UX.
