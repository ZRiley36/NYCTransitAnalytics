"""GTFS Utilities for interpreting route IDs, trip IDs, and stop IDs"""

# NYC MTA Route ID to Route Name Mapping
# Based on standard MTA subway line identifiers
ROUTE_NAME_MAP = {
    # Numbered Lines (IRT)
    "1": "1 Train",
    "2": "2 Train",
    "3": "3 Train",
    "4": "4 Train",
    "5": "5 Train",
    "6": "6 Train",
    "7": "7 Train",
    # Letter Lines (IND/BMT)
    "A": "A Train",
    "B": "B Train",
    "C": "C Train",
    "D": "D Train",
    "E": "E Train",
    "F": "F Train",
    "G": "G Train",
    "J": "J Train",
    "L": "L Train",
    "M": "M Train",
    "N": "N Train",
    "Q": "Q Train",
    "R": "R Train",
    "W": "W Train",
    "Z": "Z Train",
    # Special Services
    "GS": "S Train (Franklin Avenue Shuttle)",
    "FS": "S Train (Rockaway Park Shuttle)",
    "H": "S Train (Rockaway Park Shuttle - alternate)",
    # Staten Island Railway
    "SI": "SIR (Staten Island Railway)",
}

# Direction Mapping (from trip_id patterns)
DIRECTION_MAP = {
    "N": "Northbound",
    "S": "Southbound",
    "E": "Eastbound",
    "W": "Westbound",
}


def get_route_name(route_id: str) -> str:
    """
    Get human-readable route name from route ID
    
    Args:
        route_id: Route identifier (e.g., "1", "A", "GS")
        
    Returns:
        Human-readable route name
    """
    return ROUTE_NAME_MAP.get(route_id, f"Route {route_id}")


def parse_trip_id(trip_id: str) -> dict:
    """
    Parse NYC MTA trip ID to extract information
    
    NYC MTA trip ID format: {departure_time}_{route_id}..{direction}{destination_code}
    Example: "081750_1..N03R"
    - 081750: Departure time (08:17:50)
    - 1: Route ID (1 Train)
    - N: Direction (Northbound)
    - 03: Destination code
    - R: Route variant indicator
    
    Args:
        trip_id: Trip identifier string
        
    Returns:
        Dictionary with parsed trip information
    """
    if not trip_id or "." not in trip_id:
        return {"raw": trip_id, "error": "Invalid trip ID format"}
    
    try:
        parts = trip_id.split("_")
        if len(parts) < 2:
            return {"raw": trip_id, "error": "Invalid trip ID format"}
        
        departure_time = parts[0]
        route_and_direction = parts[1]
        
        # Extract route ID and direction
        route_dir_parts = route_and_direction.split("..")
        if len(route_dir_parts) < 2:
            return {"raw": trip_id, "error": "Invalid route/direction format"}
        
        route_id = route_dir_parts[0]
        direction_code = route_dir_parts[1][0] if route_dir_parts[1] else None
        destination_code = route_dir_parts[1][1:] if len(route_dir_parts[1]) > 1 else None
        
        # Parse time
        if len(departure_time) >= 6:
            hour = departure_time[:2]
            minute = departure_time[2:4]
            second = departure_time[4:6] if len(departure_time) >= 6 else "00"
            formatted_time = f"{hour}:{minute}:{second}"
        else:
            formatted_time = departure_time
        
        return {
            "raw": trip_id,
            "departure_time": formatted_time,
            "route_id": route_id,
            "route_name": get_route_name(route_id),
            "direction": DIRECTION_MAP.get(direction_code, direction_code) if direction_code else None,
            "direction_code": direction_code,
            "destination_code": destination_code,
        }
    except Exception as e:
        return {"raw": trip_id, "error": f"Failed to parse: {str(e)}"}


def interpret_vehicle_update(vehicle: dict) -> dict:
    """
    Interpret a vehicle update with human-readable information
    
    Args:
        vehicle: Vehicle update dictionary from GTFS-RT feed
        
    Returns:
        Dictionary with interpreted information
    """
    interpreted = vehicle.copy()
    
    # Add route name
    if "route_id" in vehicle and vehicle["route_id"]:
        interpreted["route_name"] = get_route_name(vehicle["route_id"])
    
    # Parse trip ID
    if "trip_id" in vehicle and vehicle["trip_id"]:
        trip_info = parse_trip_id(vehicle["trip_id"])
        interpreted["trip_info"] = trip_info
    
    # Convert timestamp to readable format
    if "timestamp" in vehicle and vehicle["timestamp"]:
        from datetime import datetime
        try:
            dt = datetime.fromtimestamp(vehicle["timestamp"])
            interpreted["timestamp_readable"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    return interpreted


def get_stop_name(stop_id: str) -> str:
    """
    Get stop name from stop ID
    
    Note: For accurate stop names, you need to download the GTFS static feed
    from https://new.mta.info/developers and parse the stops.txt file.
    
    Args:
        stop_id: Stop identifier
        
    Returns:
        Stop name (or ID if not available)
    """
    # This would require GTFS static data
    # For now, just return the ID
    return f"Stop {stop_id}"


# GTFS Static Data URLs for reference
GTFS_STATIC_URLS = {
    "mta": "https://new.mta.info/document/16142",
    "subway": "http://web.mta.info/developers/data/nyct/subway/google_transit.zip",
    "bus": "http://web.mta.info/developers/data/nyct/bus/google_transit.zip",
}

