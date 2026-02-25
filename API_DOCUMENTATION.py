"""
FastAPI Backend - Complete API Documentation

This file contains detailed information about all endpoints, 
data models, and implementation details of the MapLibre routing system.
"""

# ============ DATA MODELS (Pydantic) ============

"""
Runner
------
Represents a delivery driver/runner in the system.

Fields:
  id (int): Unique runner identifier
  name (str): Runner's display name
  latitude (float, alias="lat"): Current latitude
  longitude (float, alias="lon"): Current longitude
  status (str): Current status - "active", "inactive", "busy"

Example:
  {
    "id": 1,
    "name": "Alice",
    "lat": 13.6288,
    "lon": 79.4192,
    "status": "active"
  }
"""

"""
RunnerResponse
--------------
API response wrapper for runner data.

Fields:
  id (int): Runner ID
  name (str): Runner name
  lat (float): Current latitude
  lon (float): Current longitude
  status (str): Runner status
  updated_at (str): ISO 8601 timestamp of last update

Example:
  {
    "id": 1,
    "name": "Alice",
    "lat": 13.6288,
    "lon": 79.4192,
    "status": "active",
    "updated_at": "2026-02-24T17:47:05.767248"
  }
"""

"""
RouteInfo
---------
Route calculation results from OSRM.

Fields:
  distance_km (float): Route distance in kilometers
  duration_min (float): Estimated travel time in minutes
  geometry (dict): GeoJSON LineString representing the route path

Example:
  {
    "distance_km": 2.5,
    "duration_min": 5.3,
    "geometry": {
      "type": "LineString",
      "coordinates": [[79.4192, 13.6288], [79.4200, 13.6350]]
    }
  }
"""

"""
RouteResponse
--------------
API response for routing requests.

Fields:
  success (bool): Whether route calculation succeeded
  route (RouteInfo | null): Route details if successful
  error (str | null): Error message if failed

Example (Success):
  {
    "success": true,
    "route": {
      "distance_km": 2.5,
      "duration_min": 5.3,
      "geometry": {...}
    },
    "error": null
  }

Example (Failure):
  {
    "success": false,
    "route": null,
    "error": "Could not calculate route"
  }
"""

"""
NearestRunnerResponse
---------------------
API response for nearest runner queries.

Fields:
  runner (RunnerResponse): The closest runner details
  distance_km (float): Distance to the runner in kilometers

Example:
  {
    "runner": {
      "id": 1,
      "name": "Alice",
      "lat": 13.6288,
      "lon": 79.4192,
      "status": "active",
      "updated_at": "2026-02-24T17:47:05.767248"
    },
    "distance_km": 0.5
  }
"""

# ============ ENDPOINTS ============

"""
GET /
-----
Root endpoint - returns welcome message

Response:
  {
    "message": "Welcome to MapLibre API. Visit /admin or /user"
  }
"""

"""
GET /admin
----------
Serve the Admin Dashboard HTML page

Returns: HTML content with MapLibre map integration
Response-Type: text/html
"""

"""
GET /user
---------
Serve the User Portal HTML page

Returns: HTML content with MapLibre map integration
Response-Type: text/html
"""

"""
GET /api/runners
----------------
ADMIN API: Retrieve all runners

Description:
  Returns a list of all runners with their current positions and status.
  Useful for admin dashboards to see all active drivers.

Query Parameters: None

Response: 
  Array of RunnerResponse objects
  
Example Response:
  [
    {
      "id": 1,
      "name": "Alice",
      "lat": 13.629442935490651,
      "lon": 79.4193080349858,
      "status": "active",
      "updated_at": "2026-02-24T17:47:05.767248"
    },
    {
      "id": 2,
      "name": "Bob",
      "lat": 13.635254101266382,
      "lon": 79.42054186279198,
      "status": "active",
      "updated_at": "2026-02-24T17:47:05.767255"
    }
  ]

HTTP Status:
  200 OK - Always successful

cURL Example:
  curl http://localhost:8000/api/runners
"""

"""
GET /api/runners/{runner_id}
----------------------------
ADMIN API: Get specific runner by ID

Description:
  Retrieves detailed information about a single runner.
  Returns 404 if runner does not exist.

Path Parameters:
  runner_id (integer, required): The runner's unique identifier

Response:
  RunnerResponse object

Example Response:
  {
    "id": 1,
    "name": "Alice",
    "lat": 13.629442935490651,
    "lon": 79.4193080349858,
    "status": "active",
    "updated_at": "2026-02-24T17:47:05.767248"
  }

HTTP Status:
  200 OK - Runner found
  404 Not Found - Runner does not exist

cURL Examples:
  curl http://localhost:8000/api/runners/1
  curl http://localhost:8000/api/runners/5
"""

"""
GET /api/user/nearest-runner
-----------------------------
USER API: Find the closest runner to user location

Description:
  Uses the Haversine formula to calculate accurate geographic distance
  between the user's coordinates and all runners. Returns the closest
  runner and the distance in kilometers.
  
  Note: This endpoint does NOT require authentication but does require
  valid geographic coordinates.

Query Parameters:
  lat (float, required): User's latitude (-90 to 90)
  lng (float, required): User's longitude (-180 to 180)

Response:
  NearestRunnerResponse object

Example Response:
  {
    "runner": {
      "id": 1,
      "name": "Alice",
      "lat": 13.629476770853971,
      "lon": 79.41852997316519,
      "status": "active",
      "updated_at": "2026-02-24T17:47:22.328289"
    },
    "distance_km": 0.1
  }

HTTP Status:
  200 OK - Runner found
  400 Bad Request - Invalid coordinates
  404 Not Found - No runners available

Error Examples:
  {
    "detail": "Invalid coordinates"
  }
  
  {
    "detail": "No runners available"
  }

cURL Examples:
  curl "http://localhost:8000/api/user/nearest-runner?lat=13.6288&lng=79.4192"
  curl "http://localhost:8000/api/user/nearest-runner?lat=13.63&lng=79.42"
"""

"""
GET /api/route
---------------
ROUTING API: Calculate driving route between two points

Description:
  Calls the OSRM (Open Source Routing Machine) backend to compute
  the optimal driving route between two geographic coordinates.
  Returns route geometry (GeoJSON), distance, and estimated duration.
  
  IMPORTANT: Requires OSRM to be running at http://localhost:5000
  If OSRM is not available, the endpoint returns success=false.

Query Parameters:
  start_lat (float, required): Starting point latitude (-90 to 90)
  start_lng (float, required): Starting point longitude (-180 to 180)
  end_lat (float, required): Ending point latitude (-90 to 90)
  end_lng (float, required): Ending point longitude (-180 to 180)

Response:
  RouteResponse object

Example Success Response:
  {
    "success": true,
    "route": {
      "distance_km": 0.95,
      "duration_min": 2.3,
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [79.4192, 13.6288],
          [79.4193, 13.6289],
          [79.4200, 13.6350]
        ]
      }
    },
    "error": null
  }

Example Failure Response:
  {
    "success": false,
    "route": null,
    "error": "Could not calculate route"
  }

HTTP Status:
  200 OK - Always returns 200 (check success field)
  400 Bad Request - Invalid coordinates

Error Examples:
  {
    "detail": "Invalid coordinates"
  }

cURL Examples:
  curl "http://localhost:8000/api/route?start_lat=13.6288&start_lng=79.4192&end_lat=13.6350&end_lng=79.4200"
  
  # With response pretty-printing
  curl -s "http://localhost:8000/api/route?start_lat=13.6288&start_lng=79.4192&end_lat=13.6350&end_lng=79.4200" | python3 -m json.tool
"""

"""
GET /api/health
----------------
SYSTEM API: Health check endpoint

Description:
  Returns the health status of the backend service.
  Useful for monitoring and load balancer health checks.

Response:
  {
    "status": "healthy",
    "runners_count": 5,
    "timestamp": "2026-02-24T17:48:18.979934"
  }

HTTP Status:
  200 OK - Backend is healthy

cURL Example:
  curl http://localhost:8000/api/health
"""

# ============ ALGORITHM IMPLEMENTATIONS ============

"""
Haversine Distance Formula
---------------------------

Implementation Location: app.py, function haversine_distance()

Formula:
  a = sin²(Δφ/2) + cos(φ1) × cos(φ2) × sin²(Δλ/2)
  c = 2 × atan2(√a, √(1−a))
  d = R × c

Where:
  φ is latitude, λ is longitude, R is earth's radius (6,371 km)
  Δφ is the difference in latitude
  Δλ is the difference in longitude

Accuracy:
  ± 5-10 meters for Earth-scale distances
  More accurate than simple Euclidean distance

Purpose:
  Calculate accurate great-circle distance between two
  geographic coordinates on Earth's surface.

Example:
  distance_km = haversine_distance(13.6288, 79.4192, 13.6350, 79.4200)
  # Returns approximately 0.95 km
"""

"""
Nearest Runner Calculation
---------------------------

Location: app.py, RunnerDatabase.find_nearest_runner()

Algorithm:
  1. Iterate through all runners
  2. Calculate Haversine distance from user to each runner
  3. Keep track of minimum distance and corresponding runner
  4. Return (runner_data, distance) tuple

Complexity:
  Time: O(n) where n = number of runners
  Space: O(1) excluding output

For scaling:
  - Use spatial indexing (R-tree, KD-tree) for 1000+ runners
  - Consider database index optimization
  - Cache results with short TTL for high-load scenarios
"""

# ============ CONFIGURATION ============

"""
Environment Variables / Settings

Port: 8000 (configurable in __main__)
Host: 0.0.0.0 (listen on all interfaces)
OSRM Endpoint: http://localhost:5000 (configurable in call_osrm_route)
Update Interval: 3 seconds (configurable in simulate_runner_movement)
CORS: Enabled for all origins (configurable)
"""

"""
OSRM Routing Service
--------------------

Current Configuration:
  URL: http://localhost:5000
  Profile: driving
  Response Format: GeoJSON
  Overview: full (complete route)

To use remote OSRM:
  Replace:
    url = f"http://localhost:5000/route/v1/driving/..."
  With:
    url = f"https://router.openstreetmap.de/route/v1/driving/..."
  Or any other OSRM instance

OSRM API Reference:
  https://github.com/Project-OSRM/osrm-backend/wiki/API-usage-policy
  https://router.project-osrm.org/
"""

# ============ ERROR HANDLING ============

"""
HTTP Status Codes Used
  200 OK - Request successful
  400 Bad Request - Invalid input parameters (e.g., invalid coordinates)
  404 Not Found - Resource not found (e.g., runner doesn't exist)
  500 Internal Server Error - Unexpected server error

Response Format for Errors:
  {
    "detail": "Error message describing the issue"
  }
"""

# ============ CORS CONFIGURATION ============

"""
CORS Middleware
---------------

Current Configuration:
  allow_origins: ["*"] - Allow requests from any origin
  allow_credentials: true
  allow_methods: ["*"] - Allow all HTTP methods
  allow_headers: ["*"] - Allow all headers

For Production:
  Change allow_origins to specific domain(s):
    allow_origins=["https://example.com", "https://app.example.com"]
"""

# ============ PERFORMANCE CONSIDERATIONS ============

"""
Optimization Tips
-----------------

1. Distance Calculations
   - Cached recently requested runners to reduce calculations
   - Use quadtree/KD-tree for 1000+ runners

2. Database Lookups
   - Consider indexing runner IDs
   - Use cache layer (Redis) for frequently accessed runners

3. OSRM Calls
   - Implement route caching (same start/end should return quickly)
   - Set reasonable timeout (currently 5 seconds)
   - Consider batch routing for multiple routes

4. Backend Processes
   - Current runner update loop: minimal impact (3sec interval)
   - Use asyncio.gather() for parallel operations
   - Monitor memory usage for movement history

5. API Rate Limiting
   - Consider adding rate limits for production
   - Use tokens/quotas for different user types
"""

# ============ TESTING ============

"""
Basic Test Suite
----------------

1. Health Check
   curl http://localhost:8000/api/health

2. Get All Runners
   curl http://localhost:8000/api/runners

3. Get Specific Runner
   curl http://localhost:8000/api/runners/1

4. Find Nearest Runner
   curl "http://localhost:8000/api/user/nearest-runner?lat=13.6288&lng=79.4192"

5. Invalid Coordinates (should return 400)
   curl "http://localhost:8000/api/user/nearest-runner?lat=100&lng=200"

6. Route Calculation (requires OSRM)
   curl "http://localhost:8000/api/route?start_lat=13.6288&start_lng=79.4192&end_lat=13.6350&end_lng=79.4200"

7. Non-existent Runner (should return 404)
   curl http://localhost:8000/api/runners/999
"""
