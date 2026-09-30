import requests

url = "https://archive-api.open-meteo.com/v1/archive"

params = {
    "latitude": 50.811086,
    "longitude": -0.035890,
    "start_date": "2026-09-20",
    "end_date": "2026-09-25",
    "models": "era5_seamless",
    "hourly": ",".join(
        [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "cloud_cover",
            "wind_speed_10m",
            "wind_gusts_10m",
            "shortwave_radiation",
            "direct_radiation",
        ]
    ),
    "timezone": "UTC",
}

response = requests.get(url, params=params, timeout=30)

print("HTTP status:", response.status_code)
print("Request URL:", response.url)
print()
print(response.text)