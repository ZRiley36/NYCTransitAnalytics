# GTFS-RT Connector Testing Guide

## PowerShell Commands

### Start Connector
```powershell
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/start -Method POST
```

### Stop Connector
```powershell
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/stop -Method POST
```

### Get Status
```powershell
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status -Method GET | Select-Object -ExpandProperty Content
```

### Manual Fetch
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions" -Method POST
```

## Browser Alternative

You can also use a browser or REST client like Postman:

1. **Start Connector**: 
   - URL: `http://localhost:8000/gtfs-rt/start`
   - Method: POST

2. **Check Status**: 
   - URL: `http://localhost:8000/gtfs-rt/status`
   - Method: GET

3. **Manual Fetch**: 
   - URL: `http://localhost:8000/gtfs-rt/fetch?feed_type=vehicle_positions`
   - Method: POST

## Quick Test Script (PowerShell)

```powershell
# Start the connector
Write-Host "Starting GTFS-RT connector..."
Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/start -Method POST | Out-Null

# Wait a bit
Start-Sleep -Seconds 5

# Check status
Write-Host "Checking status..."
$status = Invoke-WebRequest -Uri http://localhost:8000/gtfs-rt/status -Method GET
$status.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Check saved files
Write-Host "`nChecking saved files in ./data/gtfs_rt/:"
Get-ChildItem -Path ./data/gtfs_rt/ -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime
```

