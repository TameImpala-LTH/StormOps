import httpx
import json

locations = [
    ('Kolkata', 22.5726, 88.3639),
    ('Mumbai', 19.0760, 72.8777),
    ('Delhi', 28.6139, 77.2090),
    ('Darjeeling', 27.0410, 88.2663),
    ('Paris', 48.8566, 2.3522),
]

for name, lat, lon in locations:
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,weather_code,cloud_cover,wind_speed_10m',
        'hourly': 'temperature_2m,precipitation_probability,precipitation,rain,showers,weather_code,cloud_cover,wind_speed_10m',
        'forecast_days': 2,
        'timezone': 'auto'
    }
    r = httpx.get(url, params=params, timeout=15.0)
    data = r.json()
    curr = data.get('current', {})
    hourly = data.get('hourly', {})
    times = hourly.get('time', [])
    probs = hourly.get('precipitation_probability', [])
    precips = hourly.get('precipitation', [])
    codes = hourly.get('weather_code', [])
    clouds = hourly.get('cloud_cover', [])
    
    tz = data.get("timezone")
    print(f"=== {name} (tz: {tz}) ===")
    print("Raw Current:", json.dumps(curr))
    print("First 6 hourly times:", times[:6])
    print("Hourly probs first 6h:", probs[:6])
    print("Hourly precips first 6h:", precips[:6])
    print("Hourly codes first 6h:", codes[:6])
    print("Hourly clouds first 6h:", clouds[:6])
    if probs and len(probs) >= 24:
        print(f"Max prob day 1 (0..24): {max(probs[:24])}% | Max precip day 1: {max(precips[:24])}mm")
    if probs and len(probs) >= 48:
        print(f"Max prob day 2 (24..48): {max(probs[24:48])}% | Max precip day 2: {max(precips[24:48])}mm")
    print()
