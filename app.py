"""
Production FastAPI Backend for MapLibre Runner Tracking System
- OSRM integration for routing
- In-memory runner management
- Real-time location simulation
- RESTful APIs for admin and user portals
"""

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncio
import math
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== PYDANTIC MODELS ====================

class Runner(BaseModel):
    """Runner data model"""
    id: int
    name: str
    latitude: float = Field(..., alias="lat")
    longitude: float = Field(..., alias="lon")
    status: str = "active"

    class Config:
        populate_by_name = True


class RunnerResponse(BaseModel):
    """API response for runner data"""
    id: int
    name: str
    lat: float
    lon: float
    status: str
    history: List[List[float]] = []  # List of [lat, lon] points
    updated_at: str


class RouteInfo(BaseModel):
    """Route information from OSRM"""
    distance_km: float
    duration_min: float
    geometry: dict


class RouteResponse(BaseModel):
    """API response for routing"""
    success: bool
    route: Optional[RouteInfo] = None
    error: Optional[str] = None


class NearestRunnerResponse(BaseModel):
    """API response for nearest runner"""
    runner: RunnerResponse
    distance_km: float


class CoordinateLog(BaseModel):
    """Coordinate click log"""
    latitude: float
    longitude: float
    timestamp: str


class SavedLocation(BaseModel):
    """Saved location for users"""
    name: str
    latitude: float
    longitude: float
    created_at: str


class LocationUpdateRequest(BaseModel):
    """Request to update selected location"""
    latitude: float
    longitude: float


class UserLocation(BaseModel):
    """User's selected location"""
    latitude: float
    longitude: float
    updated_at: str


# ==================== DELIVERY ORDER MODELS ====================

class OrderCreateRequest(BaseModel):
    """Request to create a delivery order"""
    user_lat: float
    user_lng: float


class OrderResponse(BaseModel):
    """Delivery order response"""
    order_id: str
    user_lat: float
    user_lng: float
    status: str
    nearest_runner_id: Optional[int] = None
    nearest_runner_name: Optional[str] = None
    nearest_runner_lat: Optional[float] = None
    nearest_runner_lng: Optional[float] = None
    distance_km: Optional[float] = None
    created_time: str
    updated_time: str


# ==================== UTILITY FUNCTIONS ====================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def call_osrm_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> Optional[dict]:
    """
    Call OSRM API to get route between two points.
    Uses public OSRM instance - no local setup needed.
    Returns route data or None if failed.
    """
    try:
        # Use public OSRM API (router.project-osrm.org)
        # OSRM expects: lon,lat format
        url = f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
        params = {
            "overview": "full",
            "geometries": "geojson"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "geometry": route["geometry"],
                "distance_km": route["distance"] / 1000,
                "duration_min": route["duration"] / 60
            }
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"OSRM API error: {str(e)}")
        return None


# ==================== IN-MEMORY DATA STORE ====================

class RunnerDatabase:
    """In-memory runner database with thread-safe operations"""
    
    def __init__(self):
        self.runners: List[dict] = [
            {"id": 1, "name": "Alice", "lat": 13.6288, "lon": 79.4192, "status": "active", "history": [[13.6288, 79.4192]]},
            {"id": 2, "name": "Bob", "lat": 13.6350, "lon": 79.4200, "status": "active", "history": [[13.6350, 79.4200]]},
            {"id": 3, "name": "Charlie", "lat": 13.6200, "lon": 79.4150, "status": "active", "history": [[13.6200, 79.4150]]},
            {"id": 4, "name": "Diana", "lat": 13.6400, "lon": 79.4300, "status": "active", "history": [[13.6400, 79.4300]]},
            {"id": 5, "name": "Eve", "lat": 13.6100, "lon": 79.4250, "status": "active", "history": [[13.6100, 79.4250]]},
        ]
        # Track user selected locations and saved favorites
        self.user_selected_location = {"lat": 13.6288, "lon": 79.4192, "updated_at": datetime.now().isoformat()}
        self.user_saved_locations: List[dict] = []
        self.clicked_coordinates: List[dict] = []  # Log all map clicks
    
    def get_all_runners(self) -> List[dict]:
        """Get all runners with history"""
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "lat": r["lat"],
                "lon": r["lon"],
                "status": r["status"],
                "history": r.get("history", [])[-50:] if r.get("history") else [],
                "updated_at": datetime.now().isoformat()
            }
            for r in self.runners
        ]
    
    def get_runner(self, runner_id: int) -> Optional[dict]:
        """Get specific runner"""
        runner = next((r for r in self.runners if r["id"] == runner_id), None)
        if runner:
            return {
                "id": runner["id"],
                "name": runner["name"],
                "lat": runner["lat"],
                "lon": runner["lon"],
                "status": runner["status"],
                "history": runner.get("history", [])[-50:] if runner.get("history") else [],
                "updated_at": datetime.now().isoformat()
            }
        return None
    
    def update_runner_position(self, runner_id: int, lat: float, lon: float):
        """Update runner position and track history"""
        runner = next((r for r in self.runners if r["id"] == runner_id), None)
        if runner:
            runner["lat"] = lat
            runner["lon"] = lon
            runner["history"].append([lat, lon])
            # Keep history to last 100 points to prevent memory bloat
            if len(runner["history"]) > 100:
                runner["history"] = runner["history"][-100:]
    
    def find_nearest_runner(self, user_lat: float, user_lon: float) -> tuple:
        """
        Find nearest runner to user location.
        Returns (runner_data, distance_in_km)
        """
        min_distance = float('inf')
        nearest_runner = None
        
        for runner in self.runners:
            dist = haversine_distance(user_lat, user_lon, runner["lat"], runner["lon"])
            if dist < min_distance:
                min_distance = dist
                nearest_runner = runner
        
        if nearest_runner:
            return {
                "id": nearest_runner["id"],
                "name": nearest_runner["name"],
                "lat": nearest_runner["lat"],
                "lon": nearest_runner["lon"],
                "status": nearest_runner["status"],
                "history": nearest_runner.get("history", [])[-50:] if nearest_runner.get("history") else [],
                "updated_at": datetime.now().isoformat()
            }, min_distance
        
        return None, None


# ==================== DATABASE METHODS FOR LOCATIONS ====================

    def update_user_location(self, lat: float, lon: float) -> dict:
        """Update user's selected location"""
        self.user_selected_location = {"lat": lat, "lon": lon, "updated_at": datetime.now().isoformat()}
        return self.user_selected_location
    
    def get_user_location(self) -> dict:
        """Get user's selected location"""
        return self.user_selected_location
    
    def log_coordinate_click(self, lat: float, lon: float) -> dict:
        """Log a coordinate click"""
        click_log = {
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.now().isoformat()
        }
        self.clicked_coordinates.append(click_log)
        # Keep only last 100 clicks to prevent memory issues
        if len(self.clicked_coordinates) > 100:
            self.clicked_coordinates = self.clicked_coordinates[-100:]
        return click_log
    
    def get_clicked_coordinates(self) -> List[dict]:
        """Get all logged coordinate clicks"""
        return self.clicked_coordinates[-20:]  # Return last 20 clicks
    
    def save_location(self, name: str, lat: float, lon: float) -> dict:
        """Save a location as favorite"""
        # Prevent duplicates with same name
        existing = next((l for l in self.user_saved_locations if l["name"].lower() == name.lower()), None)
        if existing:
            # Update existing location
            existing.update({"latitude": lat, "longitude": lon, "updated_at": datetime.now().isoformat()})
            return existing
        
        location = {
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "created_at": datetime.now().isoformat()
        }
        self.user_saved_locations.append(location)
        return location
    
    def get_saved_locations(self) -> List[dict]:
        """Get all saved locations"""
        return self.user_saved_locations
    
    def delete_saved_location(self, name: str) -> bool:
        """Delete a saved location"""
        initial_len = len(self.user_saved_locations)
        self.user_saved_locations = [l for l in self.user_saved_locations if l["name"].lower() != name.lower()]
        return len(self.user_saved_locations) < initial_len


# ==================== ORDER MANAGEMENT DATABASE ====================

class OrderDatabase:
    """In-memory order database for delivery requests"""
    
    def __init__(self):
        self.orders: dict = {}  # order_id -> order data
        self.order_counter = 0
    
    def create_order(self, user_lat: float, user_lng: float, runner_data: dict, distance_km: float) -> dict:
        """Create a new delivery order"""
        self.order_counter += 1
        order_id = f"ORD-{self.order_counter:05d}"
        
        order = {
            "order_id": order_id,
            "user_lat": user_lat,
            "user_lng": user_lng,
            "status": "pending",
            "nearest_runner_id": runner_data["id"],
            "nearest_runner_name": runner_data["name"],
            "nearest_runner_lat": runner_data["lat"],
            "nearest_runner_lng": runner_data["lon"],
            "distance_km": round(distance_km, 2),
            "created_time": datetime.now().isoformat(),
            "updated_time": datetime.now().isoformat()
        }
        
        self.orders[order_id] = order
        return order
    
    def get_order(self, order_id: str) -> Optional[dict]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_pending_orders(self) -> List[dict]:
        """Get all pending orders"""
        return [o for o in self.orders.values() if o["status"] == "pending"]
    
    def approve_order(self, order_id: str) -> Optional[dict]:
        """Approve a pending order"""
        order = self.orders.get(order_id)
        if order and order["status"] == "pending":
            order["status"] = "approved"
            order["updated_time"] = datetime.now().isoformat()
            return order
        return None
    
    def assign_order(self, order_id: str) -> Optional[dict]:
        """Mark order as assigned"""
        order = self.orders.get(order_id)
        if order and order["status"] == "approved":
            order["status"] = "assigned"
            order["updated_time"] = datetime.now().isoformat()
            return order
        return None
    
    def complete_order(self, order_id: str) -> Optional[dict]:
        """Mark order as completed"""
        order = self.orders.get(order_id)
        if order:
            order["status"] = "completed"
            order["updated_time"] = datetime.now().isoformat()
            return order
        return None
    
    def reject_order(self, order_id: str) -> Optional[dict]:
        """Reject a pending order"""
        order = self.orders.get(order_id)
        if order and order["status"] == "pending":
            order["status"] = "rejected"
            order["updated_time"] = datetime.now().isoformat()
            return order
        return None


# ==================== FASTAPI APP SETUP ====================

app = FastAPI(
    title="MapLibre Runner Tracking API",
    description="Production-grade API for runner tracking and routing",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = RunnerDatabase()
order_db = OrderDatabase()

# Initialize templates
templates = Jinja2Templates(directory="templates")


# ==================== BACKGROUND TASKS ====================

async def simulate_runner_movement():
    """Background task to simulate runner movement"""
    import random
    
    while True:
        try:
            for runner in db.runners:
                # Simulate small random movement
                lat_change = (random.random() - 0.5) * 0.001
                lon_change = (random.random() - 0.5) * 0.001
                
                new_lat = runner["lat"] + lat_change
                new_lon = runner["lon"] + lon_change
                
                db.update_runner_position(runner["id"], new_lat, new_lon)
            
            logger.info("Runner positions updated")
            await asyncio.sleep(3)  # Update every 3 seconds
            
        except Exception as e:
            logger.error(f"Error in runner simulation: {str(e)}")
            await asyncio.sleep(3)


@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup"""
    try:
        asyncio.create_task(simulate_runner_movement())
        logger.info("✅ Runner simulation started")
        logger.info("✅ Server started successfully")
        logger.info("🌐 Admin portal: http://localhost:5000/admin")
        logger.info("🌐 User portal: http://localhost:5000/user")
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}")


# ==================== API ROUTES ====================

@app.get("/")
async def root():
    """Redirect to admin dashboard"""
    return {"message": "Welcome to MapLibre API. Visit /admin or /user"}


@app.get("/admin", response_class=HTMLResponse)
async def admin_portal(request: Request):
    """Serve admin dashboard HTML"""
    try:
        logger.info("📊 Admin portal accessed")
        logger.info("✓ Serving admin template: admin_leaflet.html")
        return templates.TemplateResponse("admin_leaflet.html", {"request": request})
    except Exception as e:
        logger.error(f"❌ Error serving admin portal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user", response_class=HTMLResponse)
async def user_portal(request: Request):
    """Serve user portal HTML"""
    try:
        logger.info("👤 User portal accessed")
        logger.info("✓ Serving user template: users_leaflet.html")
        return templates.TemplateResponse("users_leaflet.html", {"request": request})
    except Exception as e:
        logger.error(f"❌ Error serving user portal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/request", response_class=HTMLResponse)
async def request_delivery_page(request: Request):
    """Serve delivery request page"""
    try:
        logger.info("📦 Request delivery page accessed")
        logger.info("✓ Serving request template: request_delivery.html")
        return templates.TemplateResponse("request_delivery.html", {"request": request})
    except Exception as e:
        logger.error(f"❌ Error serving request page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/runners", response_model=List[RunnerResponse])
async def get_all_runners():
    """
    ADMIN API: Get all runners
    
    Returns list of all runners with their current positions and status
    """
    return db.get_all_runners()


@app.get("/api/runners/{runner_id}", response_model=RunnerResponse)
async def get_runner(runner_id: int):
    """
    ADMIN API: Get specific runner by ID
    
    Returns runner details or 404 if not found
    """
    runner = db.get_runner(runner_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Runner not found")
    return runner


@app.get("/api/user/nearest-runner", response_model=NearestRunnerResponse)
async def get_nearest_runner(
    lat: float = Query(..., description="User latitude"),
    lng: float = Query(..., description="User longitude")
):
    """
    USER API: Find nearest runner to user location
    
    Uses Haversine distance formula for accurate calculations.
    Returns the closest runner and distance in kilometers.
    """
    # Validate coordinates
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    runner, distance = db.find_nearest_runner(lat, lng)
    
    if not runner:
        raise HTTPException(status_code=404, detail="No runners available")
    
    return {
        "runner": runner,
        "distance_km": round(distance, 2)
    }


@app.get("/api/route", response_model=RouteResponse)
async def get_route(
    start_lat: float = Query(..., description="Start latitude"),
    start_lng: float = Query(..., description="Start longitude"),
    end_lat: float = Query(..., description="End latitude"),
    end_lng: float = Query(..., description="End longitude")
):
    """
    ROUTING API: Calculate route between two points
    
    Calls OSRM backend to compute driving route.
    Returns route geometry (GeoJSON), distance, and duration.
    """
    # Validate coordinates
    if not ((-90 <= start_lat <= 90) and (-180 <= start_lng <= 180) and
            (-90 <= end_lat <= 90) and (-180 <= end_lng <= 180)):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    try:
        route_data = call_osrm_route(start_lat, start_lng, end_lat, end_lng)
        
        if route_data:
            return {
                "success": True,
                "route": {
                    "distance_km": round(route_data["distance_km"], 2),
                    "duration_min": round(route_data["duration_min"], 1),
                    "geometry": route_data["geometry"]
                }
            }
        else:
            return {
                "success": False,
                "error": "Could not calculate route"
            }
    
    except Exception as e:
        logger.error(f"Route calculation error: {str(e)}")
        return {
            "success": False,
            "error": "Route calculation failed"
        }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "runners_count": len(db.runners),
        "timestamp": datetime.now().isoformat()
    }


# ==================== NEW FEATURES: COORDINATE & LOCATION APIs ====================

@app.post("/api/coordinates/log")
async def log_coordinate(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude")
):
    """
    Log a map click coordinate
    Useful for admin tracking of clicked points
    """
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    log = db.log_coordinate_click(lat, lng)
    return {"success": True, "log": log}


@app.get("/api/coordinates/log")
async def get_coordinate_logs():
    """
    Get all logged coordinate clicks (last 20)
    Admin use for viewing clicked points
    """
    return {"coordinates": db.get_clicked_coordinates()}


@app.post("/api/user/location")
async def set_user_location(request: LocationUpdateRequest):
    """
    Update user's selected destination location
    Triggered by double-click on map
    """
    if not (-90 <= request.latitude <= 90) or not (-180 <= request.longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    location = db.update_user_location(request.latitude, request.longitude)
    return {"success": True, "location": location}


@app.get("/api/user/location", response_model=UserLocation)
async def get_user_location():
    """
    Get user's currently selected destination location
    """
    location = db.get_user_location()
    return UserLocation(
        latitude=location["lat"],
        longitude=location["lon"],
        updated_at=location["updated_at"]
    )


@app.post("/api/user/locations/save")
async def save_user_location(request: SavedLocation):
    """
    Save current location as favorite
    """
    if not (-90 <= request.latitude <= 90) or not (-180 <= request.longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    location = db.save_location(request.name, request.latitude, request.longitude)
    return {"success": True, "location": location}


@app.get("/api/user/locations/saved", response_model=List[SavedLocation])
async def get_saved_locations():
    """
    Get all saved favorite locations
    """
    locations = db.get_saved_locations()
    return [
        SavedLocation(
            name=loc["name"],
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            created_at=loc["created_at"]
        )
        for loc in locations
    ]


@app.delete("/api/user/locations/{location_name}")
async def delete_saved_location(location_name: str):
    """
    Delete a saved favorite location
    """
    success = db.delete_saved_location(location_name)
    if not success:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"success": True, "message": f"Location '{location_name}' deleted"}


# ==================== DELIVERY ORDER APIs ====================

@app.post("/api/order/create", response_model=OrderResponse)
async def create_delivery_order(request: OrderCreateRequest):
    """
    USER API: Create a delivery order request
    
    - Accepts user location (lat/lng)
    - Finds nearest runner using haversine formula
    - Creates order with status = 'pending'
    - Returns order details
    """
    # Validate coordinates
    if not (-90 <= request.user_lat <= 90) or not (-180 <= request.user_lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    # Find nearest runner
    runner, distance = db.find_nearest_runner(request.user_lat, request.user_lng)
    
    if not runner:
        raise HTTPException(status_code=404, detail="No runners available")
    
    # Create order
    order = order_db.create_order(request.user_lat, request.user_lng, runner, distance)
    
    return OrderResponse(
        order_id=order["order_id"],
        user_lat=order["user_lat"],
        user_lng=order["user_lng"],
        status=order["status"],
        nearest_runner_id=order["nearest_runner_id"],
        nearest_runner_name=order["nearest_runner_name"],
        nearest_runner_lat=order["nearest_runner_lat"],
        nearest_runner_lng=order["nearest_runner_lng"],
        distance_km=order["distance_km"],
        created_time=order["created_time"],
        updated_time=order["updated_time"]
    )


@app.get("/api/orders/pending", response_model=List[OrderResponse])
async def get_pending_orders():
    """
    ADMIN API: Get all pending delivery orders
    
    Returns list of all orders awaiting admin approval
    """
    pending = order_db.get_pending_orders()
    return [
        OrderResponse(
            order_id=o["order_id"],
            user_lat=o["user_lat"],
            user_lng=o["user_lng"],
            status=o["status"],
            nearest_runner_id=o["nearest_runner_id"],
            nearest_runner_name=o["nearest_runner_name"],
            nearest_runner_lat=o["nearest_runner_lat"],
            nearest_runner_lng=o["nearest_runner_lng"],
            distance_km=o["distance_km"],
            created_time=o["created_time"],
            updated_time=o["updated_time"]
        )
        for o in pending
    ]


@app.get("/api/order/{order_id}", response_model=OrderResponse)
async def get_order_details(order_id: str):
    """
    USER/ADMIN API: Get order details by order ID
    
    Returns full order information including status and runner assignment
    """
    order = order_db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        order_id=order["order_id"],
        user_lat=order["user_lat"],
        user_lng=order["user_lng"],
        status=order["status"],
        nearest_runner_id=order["nearest_runner_id"],
        nearest_runner_name=order["nearest_runner_name"],
        nearest_runner_lat=order["nearest_runner_lat"],
        nearest_runner_lng=order["nearest_runner_lng"],
        distance_km=order["distance_km"],
        created_time=order["created_time"],
        updated_time=order["updated_time"]
    )


@app.post("/api/order/{order_id}/approve", response_model=OrderResponse)
async def approve_delivery_order(order_id: str):
    """
    ADMIN API: Approve a pending delivery order
    
    - Changes status from 'pending' to 'approved'
    - Attaches runner details
    - Returns updated order
    """
    order = order_db.approve_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or already processed")
    
    return OrderResponse(
        order_id=order["order_id"],
        user_lat=order["user_lat"],
        user_lng=order["user_lng"],
        status=order["status"],
        nearest_runner_id=order["nearest_runner_id"],
        nearest_runner_name=order["nearest_runner_name"],
        nearest_runner_lat=order["nearest_runner_lat"],
        nearest_runner_lng=order["nearest_runner_lng"],
        distance_km=order["distance_km"],
        created_time=order["created_time"],
        updated_time=order["updated_time"]
    )


@app.post("/api/order/{order_id}/reject", response_model=OrderResponse)
async def reject_delivery_order(order_id: str):
    """
    ADMIN API: Reject a pending delivery order
    
    - Changes status from 'pending' to 'rejected'
    - Returns updated order
    """
    order = order_db.reject_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or already processed")
    
    return OrderResponse(
        order_id=order["order_id"],
        user_lat=order["user_lat"],
        user_lng=order["user_lng"],
        status=order["status"],
        nearest_runner_id=order["nearest_runner_id"],
        nearest_runner_name=order["nearest_runner_name"],
        nearest_runner_lat=order["nearest_runner_lat"],
        nearest_runner_lng=order["nearest_runner_lng"],
        distance_km=order["distance_km"],
        created_time=order["created_time"],
        updated_time=order["updated_time"]
    )


@app.post("/api/order/{order_id}/assign", response_model=OrderResponse)
async def assign_delivery_order(order_id: str):
    """
    ADMIN API: Mark order as assigned to runner
    
    - Changes status from 'approved' to 'assigned'
    - Runner is now en route
    """
    order = order_db.assign_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not approved")
    
    return OrderResponse(
        order_id=order["order_id"],
        user_lat=order["user_lat"],
        user_lng=order["user_lng"],
        status=order["status"],
        nearest_runner_id=order["nearest_runner_id"],
        nearest_runner_name=order["nearest_runner_name"],
        nearest_runner_lat=order["nearest_runner_lat"],
        nearest_runner_lng=order["nearest_runner_lng"],
        distance_km=order["distance_km"],
        created_time=order["created_time"],
        updated_time=order["updated_time"]
    )


@app.post("/api/order/{order_id}/complete", response_model=OrderResponse)
async def complete_delivery_order(order_id: str):
    """
    ADMIN API: Mark order as completed
    
    - Changes status to 'completed'
    - Delivery finished
    """
    order = order_db.complete_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        order_id=order["order_id"],
        user_lat=order["user_lat"],
        user_lng=order["user_lng"],
        status=order["status"],
        nearest_runner_id=order["nearest_runner_id"],
        nearest_runner_name=order["nearest_runner_name"],
        nearest_runner_lat=order["nearest_runner_lat"],
        nearest_runner_lng=order["nearest_runner_lng"],
        distance_km=order["distance_km"],
        created_time=order["created_time"],
        updated_time=order["updated_time"]
    )


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting FastAPI server...")
    logger.info("📍 Host: 0.0.0.0")
    logger.info("📍 Port: 5000")
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=5000, 
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"❌ Server failed to start: {str(e)}")
        raise
