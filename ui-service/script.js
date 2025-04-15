 
// --- DOM Elements ---
const form = document.getElementById('route-form');
const destinationInput = document.getElementById('destination');
const preferenceSelect = document.getElementById('preference');
// const testIpInput = document.getElementById('test_ip'); // Uncomment if using test IP input
const submitButton = document.getElementById('submit-button');

const resultsArea = document.getElementById('results-area');
const originInfoDiv = document.getElementById('origin-info');
const notesInfoDiv = document.getElementById('notes-info');
const recommendationList = document.getElementById('recommendation-list');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error-message');

// --- Configuration ---
// Use the API Gateway URL (update this if you deploy the gateway)
// const API_GATEWAY_URL = 'http://127.0.0.1:5000'; // Default for local dev
const PREFERENCE_STORAGE_KEY = 'transportPreference';

// --- Functions ---

/**
 * Fetches recommendations from the API Gateway.
 * @param {string} destination - The destination city name.
 * @param {string} preference - The user's preference (fastest, cheapest, greenest).
 * @param {string|null} testIp - Optional IP address for testing location service.
 */
async function fetchRecommendations(destination, preference, testIp = null) {
    // Construct the URL with query parameters
    let relativeUrl = `/api/route?destination=${encodeURIComponent(destination)}&preference=${encodeURIComponent(preference)}`; 
       // if (testIp) { // Uncomment if using test IP input
        //     url.searchParams.append('test_ip', testIp);
        // }
    
    const response = await fetch(relativeUrl);

    if (!response.ok) {
        // Try to parse error details from the response body
        let errorData = { message: `Server responded with status: ${response.status}` };
        try {
            const body = await response.json();
            // Use 'error' or 'details' field from API response if available
            errorData.message = body.error || body.details || errorData.message;
        } catch (e) {
            // Response wasn't JSON or parsing failed
            console.warn("Could not parse error response body as JSON.");
        }
        // Throw an error with the extracted message
        const error = new Error(errorData.message);
        error.status = response.status; // Attach status code if needed elsewhere
        throw error;
    }

    return await response.json(); // Parse successful response as JSON
}

/**
 * Renders the results (origin, notes, recommendations) to the page.
 * @param {object} data - The data object received from the API Gateway.
 */
function displayResults(data) {
    // Display Origin Info
    if (data.origin && data.origin.city) {
        originInfoDiv.innerHTML = `<p><strong>Detected Origin:</strong> ${data.origin.city}</p>`;
    } else {
        originInfoDiv.innerHTML = '<p>Origin information not available.</p>';
    }

     // Display Notes/Warnings
    if (data.notes && data.notes.length > 0) {
        notesInfoDiv.innerHTML = data.notes.map(note => `<p>${note}</p>`).join('');
        notesInfoDiv.style.display = 'block';
    } else {
        notesInfoDiv.style.display = 'none';
    }


    // Display Recommendations
    recommendationList.innerHTML = ''; // Clear previous recommendations
    if (data.recommendations && data.recommendations.length > 0) {
        data.recommendations.forEach(rec => {
            const li = document.createElement('li');
            // Simple icons based on mode (could use actual icon library)
            let icon = '';
            if (rec.mode === 'car') icon = '🚗';
            else if (rec.mode === 'bus') icon = '🚌';
            else if (rec.mode === 'train') icon = '🚆';
            else if (rec.mode === 'bicycle') icon = '🚲';
            else if (rec.mode === 'walking') icon = '🚶';
            else if (rec.mode === 'scooter') icon = '🛴';

            li.innerHTML = `
                <div><span class="mode-icon">${icon}</span><strong>Mode:</strong> ${rec.mode}</div>
                <div><strong>Duration:</strong> ${rec.duration_minutes} minutes</div>
                <div><strong>Est. Cost:</strong> $${rec.cost_usd.toFixed(2)}</div>
                <div><strong>CO2 Emissions:</strong> ${rec.environmental_impact_co2_kg.toFixed(2)} kg</div>
                <div class="source">(Source: ${rec.source_cloud || 'Unknown Cloud'})</div>
            `;
            recommendationList.appendChild(li);
        });
    } else {
        recommendationList.innerHTML = '<li>No recommendations found matching your criteria.</li>';
    }
}

/**
 * Displays an error message to the user.
 * @param {string} message - The error message to display.
 */
function displayError(message) {
    errorDiv.textContent = `Error: ${message}`;
    errorDiv.style.display = 'block'; // Make error visible
}

/**
 * Clears previous results and error messages.
 */
function clearResults() {
    recommendationList.innerHTML = '';
    originInfoDiv.innerHTML = '';
    notesInfoDiv.innerHTML = '';
    errorDiv.textContent = '';
    errorDiv.style.display = 'none'; // Hide error div
    resultsArea.style.display = 'none'; // Hide the whole results area initially
}

/**
 * Saves the selected preference to Local Storage.
 */
function savePreference() {
    localStorage.setItem(PREFERENCE_STORAGE_KEY, preferenceSelect.value);
}

/**
 * Loads preference from Local Storage and sets the dropdown value.
 */
function loadPreference() {
    const savedPreference = localStorage.getItem(PREFERENCE_STORAGE_KEY);
    if (savedPreference) {
        preferenceSelect.value = savedPreference;
    }
}


// --- Event Listeners ---

form.addEventListener('submit', async (event) => {
    event.preventDefault(); // Prevent default page reload

    const destination = destinationInput.value.trim();
    const preference = preferenceSelect.value;
    // const testIp = testIpInput.value.trim(); // Uncomment if using test IP input

    if (!destination) {
        displayError("Please enter a destination city.");
        return;
    }

    clearResults(); // Clear old results/errors
    resultsArea.style.display = 'block'; // Show results area
    loadingDiv.style.display = 'flex'; // Show loading spinner
    submitButton.disabled = true; // Disable button during fetch

    try {
        // const data = await fetchRecommendations(destination, preference, testIp || null); // Pass test IP if provided
        const data = await fetchRecommendations(destination, preference);
        displayResults(data);
    } catch (error) {
        console.error('Failed to fetch recommendations:', error);
        displayError(error.message || "An unknown error occurred."); // Display the error message
    } finally {
        loadingDiv.style.display = 'none'; // Hide loading spinner
        submitButton.disabled = false; // Re-enable button
    }
});

// Save preference when the dropdown changes
preferenceSelect.addEventListener('change', savePreference);

// --- Initialization ---

// Load saved preference when the page loads
document.addEventListener('DOMContentLoaded', loadPreference);