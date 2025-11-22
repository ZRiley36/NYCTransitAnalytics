"""API endpoint to interpret GTFS-RT vehicle updates"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from gtfs_utils import interpret_vehicle_update, get_route_name, parse_trip_id
import json
from pathlib import Path

router = APIRouter(prefix="/gtfs", tags=["GTFS"])


@router.get("/routes")
def get_all_routes():
    """Get all available route names"""
    from gtfs_utils import ROUTE_NAME_MAP
    return {
        "routes": [
            {"route_id": rid, "route_name": name}
            for rid, name in ROUTE_NAME_MAP.items()
        ]
    }


@router.get("/interpret-trip/{trip_id}")
def interpret_trip(trip_id: str):
    """Interpret a trip ID"""
    result = parse_trip_id(trip_id)
    return result


@router.post("/interpret-vehicle")
def interpret_vehicle(vehicle: Dict[str, Any]):
    """Interpret a vehicle update"""
    try:
        interpreted = interpret_vehicle_update(vehicle)
        return interpreted
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error interpreting vehicle: {str(e)}")


@router.get("/interpret-file/{filename}")
def interpret_file(filename: str):
    """Interpret a saved vehicle positions file"""
    filepath = Path("./data/gtfs_rt") / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Interpret all vehicles
        if "vehicles" in data:
            interpreted_vehicles = [
                interpret_vehicle_update(vehicle)
                for vehicle in data["vehicles"]
            ]
            
            return {
                "header": data.get("header", {}),
                "vehicle_count": len(interpreted_vehicles),
                "vehicles": interpreted_vehicles[:50],  # Limit to first 50
                "total_vehicles": len(interpreted_vehicles),
            }
        else:
            return data
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.get("/files")
def list_files():
    """List all saved GTFS-RT files"""
    data_dir = Path("./data/gtfs_rt")
    
    if not data_dir.exists():
        return {"files": []}
    
    files = []
    for filepath in sorted(data_dir.glob("*.json"), reverse=True):
        files.append({
            "filename": filepath.name,
            "size": filepath.stat().st_size,
            "modified": filepath.stat().st_mtime,
        })
    
    return {"files": files[:20]}  # Latest 20 files

