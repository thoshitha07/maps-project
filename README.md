# Tirupati Mapping System - FastAPI Backend

A production-grade FastAPI web application for real-time runner tracking and route visualization using MapLibre GL and OpenStreetMap.

## Project Structure

```
/home/toshitha/maps/
├── app.py                  # FastAPI backend application
├── requirements.txt        # Python dependencies
├── templates/
│   ├── admin.html         # Admin dashboard (runner tracking)
│   └── users.html         # User portal (route calculation)
└── README.md              # This file
```

## Features

### Admin Dashboard (`GET /admin`)
- Monitor multiple runners in real-time
- Live runner tracking with location updates
- Clickable runner list to view details
- Visual markers on map

### User Portal (`GET /user`)
- Find nearest runner to user location
- Calculate driving route using OSRM
- Display travel distance and time
- Real-time route visualization

### RESTful API Endpoints

#### Runner Management
- `GET /api/runners` - Get all runners with current positions
- `GET /api/runners/{runner_id}` - Get specific runner details

#### User Location Services
- `GET /api/user/nearest-runner?lat=X&lng=Y` - Find closest runner using Haversine distance
- `GET /api/route?start_lat=&start_lng=&end_lat=&end_lng=` - Calculate route via OSRM

#### System
- `GET /api/health` - Health check endpoint
- `GET /` - API info

## Installation & Setup

### 1. Install Dependencies
```bash
cd /home/toshitha/maps
pip install -r requirements.txt
```

### 2. Run the FastAPI App
```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Or simply:
```bash
python3 app.py
```

The app will start on `http://localhost:8000`

## Access Points

- **Admin Dashboard**: http://localhost:8000/admin
- **User Portal**: http://localhost:8000/user
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

## Technologies Used

- **Backend**: FastAPI + Uvicorn
- **Data Validation**: Pydantic
- **Frontend**: MapLibre GL JS
- **Map Data**: OpenStreetMap (OSM)
- **Routing Engine**: OSRM (optional, for routing)
- **Distance Calculation**: Haversine formula

## Architecture

### Data Models (Pydantic)
```python
Runner:
  - id: integer
  - name: string
  - lat: float (latitude)
  - lon: float (longitude)
  - status: string

RunnerResponse:
  - (Runner fields) + updated_at: ISO timestamp

RouteInfo:
  - distance_km: float
  - duration_min: float
  - geometry: GeoJSON

NearestRunnerResponse:
  - runner: RunnerResponse
  - distance_km: float
```

### Distance Calculation
Uses the Haversine formula to calculate accurate geographic distances between coordinates:
```
distance = 2 * R * arcsin(sqrt(sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)))
```
Where R = 6371 km (Earth's radius)

### Background Tasks
- Automatic runner position updates every 3 seconds
- Simulates realistic movement with random lat/lon changes
- Non-blocking async implementation

### Error Handling
- Input validation for coordinates (latitude: ±90°, longitude: ±180°)
- OSRM API failure handling with graceful degradation
- JSON error responses with proper HTTP status codes
- CORS enabled for frontend access

## Configuration

Edit `app.py` to customize:

**Line ~51**: Initial runner data
```python
self.runners = [
    {"id": 1, "name": "Alice", "lat": 13.6288, "lon": 79.4192, "status": "active"},
    ...
]
```

**Line ~208**: Update interval
```python
await asyncio.sleep(3)  # Change to desired seconds
```

**Line ~399**: Server port (also pass --port 8000 to uvicorn)

## Runner Simulation

The backend automatically simulates runner movements:
- Each runner moves slightly every 3 seconds
- Random +/- 0.001° change in lat/lon (approximately ±100 meters)
- Positions update continuously without manual intervention

## API Response Examples

### Get All Runners
```bash
curl http://localhost:8000/api/runners
```
Response:
```json
[
  {
    "id": 1,
    "name": "Alice",
    "lat": 13.6288,
    "lon": 79.4192,
    "status": "active",
    "updated_at": "2026-02-24T17:47:05.767248"
  }
]
```

### Find Nearest Runner
```bash
curl "http://localhost:8000/api/user/nearest-runner?lat=13.6288&lng=79.4192"
```
Response:
```json
{
  "runner": {
    "id": 1,
    "name": "Alice",
    "lat": 13.6288,
    "lon": 79.4192,
    "status": "active",
    "updated_at": "2026-02-24T17:47:05.767248"
  },
  "distance_km": 0.1
}
```

### Calculate Route (requires OSRM)
```bash
curl "http://localhost:8000/api/route?start_lat=13.6288&start_lng=79.4192&end_lat=13.6350&end_lng=79.4200"
```
Response:
```json
{
  "success": true,
  "route": {
    "distance_km": 0.95,
    "duration_min": 2.3,
    "geometry": {
      "type": "LineString",
      "coordinates": [[79.4192, 13.6288], ...]
    }
  }
}
```

## Dependencies

- **fastapi** (0.104.1) - Web framework
- **uvicorn** (0.24.0) - ASGI server
- **pydantic** (2.5.0) - Data validation
- **requests** (2.31.0) - HTTP client for OSRM
- **python-multipart** (0.0.6) - Form data support

## License

Open Source

## Next Steps

1. **Enable OSRM Routing** (optional)
   - Install OSRM locally or use a hosted instance
   - Update OSRM URL in `app.py` line ~96

2. **Production Deployment**
   - Replace `--reload` with production settings
   - Use strong CORS configuration
   - Deploy with Gunicorn or similar

3. **Database Integration**
   - Replace in-memory storage with PostgreSQL/MongoDB
   - Add persistence for runner history

4. **Authentication**
   - Add JWT token validation
   - Implement role-based access control

5. **Real-time Updates**
   - Implement WebSocket support for live updates
   - Add server-sent events (SSE) for frontend push notifications

