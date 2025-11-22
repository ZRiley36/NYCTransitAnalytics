# GTFS-RT Vehicle Update Interpretation Guide

## Understanding Vehicle Updates

### Route ID → Route Name

The `route_id` directly maps to subway lines:

- **Numbered Lines**: `"1"` = 1 Train, `"2"` = 2 Train, etc.
- **Letter Lines**: `"A"` = A Train, `"B"` = B Train, etc.
- **Special Services**: `"GS"` = Franklin Avenue Shuttle

**Quick Reference:**
```
"1" → "1 Train"
"2" → "2 Train"  
"3" → "3 Train"
"A" → "A Train"
"B" → "B Train"
"GS" → "S Train (Franklin Avenue Shuttle)"
```

### Trip ID Format

NYC MTA trip IDs encode information in this format:
```
{departure_time}_{route_id}..{direction}{destination_code}
```

**Example:** `"081750_1..N03R"`

Breaking it down:
- `081750` = Departure time **08:17:50**
- `1` = Route ID (**1 Train**)
- `N` = Direction (**Northbound**)
- `03` = Destination code (internal)
- `R` = Route variant indicator

**Direction Codes:**
- `N` = Northbound
- `S` = Southbound
- `E` = Eastbound
- `W` = Westbound

### Example Vehicle Update

```json
{
  "id": "000003",
  "trip_id": "081750_1..N03R",
  "route_id": "1",
  "position": {
    "latitude": 40.7589,
    "longitude": -73.9851
  },
  "timestamp": 1763494684,
  "current_stop_sequence": 38
}
```

**Interpreted as:**
- **Route**: 1 Train
- **Trip**: Departing 08:17:50, Northbound
- **Position**: GPS coordinates (if available)
- **Stop Sequence**: Currently at stop 38 in the trip
- **Timestamp**: Unix timestamp (convert to readable time)

## Using the API to Interpret Data

### 1. Get Route Names
```bash
GET http://localhost:8000/gtfs/routes
```

### 2. Interpret a Trip ID
```bash
GET http://localhost:8000/gtfs/interpret-trip/081750_1..N03R
```

Returns:
```json
{
  "departure_time": "08:17:50",
  "route_id": "1",
  "route_name": "1 Train",
  "direction": "Northbound",
  "direction_code": "N"
}
```

### 3. Interpret a Vehicle Update
```bash
POST http://localhost:8000/gtfs/interpret-vehicle
Content-Type: application/json

{
  "route_id": "1",
  "trip_id": "081750_1..N03R",
  "timestamp": 1763494684
}
```

### 4. Interpret a Saved File
```bash
GET http://localhost:8000/gtfs/interpret-file/vehicle_positions_20251118_193823.json
```

### 5. List All Saved Files
```bash
GET http://localhost:8000/gtfs/files
```

## Stop Names

For **stop names** (stop_id → station name), you need to download the GTFS static feed:

1. Download: http://web.mta.info/developers/data/nyct/subway/google_transit.zip
2. Extract `stops.txt`
3. Match `stop_id` to `stop_name`

The GTFS static feed contains:
- `stops.txt` - Stop names and locations
- `routes.txt` - Route names and colors
- `trips.txt` - Trip details
- `stop_times.txt` - Stop sequences

## Quick Python Script

```python
from backend.gtfs_utils import interpret_vehicle_update, get_route_name

# Example vehicle update
vehicle = {
    "route_id": "1",
    "trip_id": "081750_1..N03R",
    "timestamp": 1763494684,
    "current_stop_sequence": 38
}

# Interpret it
interpreted = interpret_vehicle_update(vehicle)
print(interpreted)
```

## Visual Examples

### Northbound 1 Train
```json
{
  "route_id": "1",
  "trip_id": "081750_1..N03R",
  "route_name": "1 Train",
  "trip_info": {
    "direction": "Northbound",
    "departure_time": "08:17:50"
  }
}
```

### Southbound A Train  
```json
{
  "route_id": "A",
  "trip_id": "092000_A..S02R",
  "route_name": "A Train",
  "trip_info": {
    "direction": "Southbound",
    "departure_time": "09:20:00"
  }
}
```

