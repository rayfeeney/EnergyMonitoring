import os
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

params = {
    "latitude": float(os.environ["WEATHER_LATITUDE"]),
    "longitude": float(os.environ["WEATHER_LONGITUDE"]),
    "start_date": date(2026, 9, 25).isoformat(),
    "end_date": date(2026, 9, 25).isoformat(),
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
    "models": "era5_seamless",
}

response = requests.get(
    "https://archive-api.open-meteo.com/v1/archive",
    params=params,
    timeout=30,
)

response.raise_for_status()

hourly = response.json()["hourly"]

for index, time_value in enumerate(hourly["time"]):
    print(
        time_value,
        {
            variable: hourly[variable][index]
            for variable in hourly
            if variable != "time"
        },
    )