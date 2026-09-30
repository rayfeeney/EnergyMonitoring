import os
from datetime import datetime, timedelta, timezone
import pymysql

import requests
from dotenv import load_dotenv


load_dotenv()


OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

WEATHER_START_DATE = datetime(2026, 9, 25, tzinfo=timezone.utc).date()

REANALYSIS_LOOKBACK_DAYS = 10

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "direct_radiation",
]


def get_weather_date_range(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                MIN(IntervalStartUtc),
                MAX(IntervalStartUtc)
            FROM WeatherHourly
            """
        )

        return cursor.fetchone()


def get_first_missing_weather_interval(connection):
    start_datetime = datetime.combine(
        WEATHER_START_DATE,
        datetime.min.time(),
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                CASE
                    WHEN MIN(IntervalStartUtc) IS NULL
                        OR MIN(IntervalStartUtc) > %s
                    THEN %s

                    ELSE
                    (
                        SELECT MIN(w1.IntervalStartUtc + INTERVAL 1 HOUR)
                        FROM WeatherHourly w1
                        LEFT JOIN WeatherHourly w2
                            ON w2.IntervalStartUtc =
                               w1.IntervalStartUtc + INTERVAL 1 HOUR
                        WHERE w1.IntervalStartUtc >= %s
                          AND w1.IntervalStartUtc + INTERVAL 1 HOUR
                                < TIMESTAMP(CURRENT_DATE, MAKETIME(HOUR(UTC_TIMESTAMP()), 0, 0))
                          AND w2.IntervalStartUtc IS NULL
                    )
                END AS FirstMissingInterval
            FROM WeatherHourly
            """,
            (
                start_datetime,
                start_datetime,
                start_datetime,
            ),
        )

        return cursor.fetchone()[0]

    
def get_earliest_recent_interval(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT MIN(IntervalStartUtc)
            FROM WeatherHourly
            WHERE WeatherDataType = 'Recent'
            """
        )

        return cursor.fetchone()[0]

        
def get_recent_weather(connection):
    latitude = float(os.environ["WEATHER_LATITUDE"])
    longitude = float(os.environ["WEATHER_LONGITUDE"])

    now_utc = datetime.now(timezone.utc)

    earliest_interval, latest_interval = get_weather_date_range(connection)

    if (
        earliest_interval is None
        or earliest_interval.date() > WEATHER_START_DATE
    ):
        start_date = WEATHER_START_DATE
    else:
        start_date = (latest_interval - timedelta(days=2)).date()

        if start_date < WEATHER_START_DATE:
            start_date = WEATHER_START_DATE

    end_date = now_utc.date()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
    }

    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_reanalysis_weather():
    latitude = float(os.environ["WEATHER_LATITUDE"])
    longitude = float(os.environ["WEATHER_LONGITUDE"])

    now_utc = datetime.now(timezone.utc)

    start_date = (now_utc - timedelta(days=REANALYSIS_LOOKBACK_DAYS)).date()

    if start_date < WEATHER_START_DATE:
        start_date = WEATHER_START_DATE

    end_date = now_utc.date()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
        "models": "era5_seamless",
    }

    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


def build_weather_rows(weather):
    hourly = weather["hourly"]

    current_hour_utc = datetime.now(timezone.utc).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    rows = []

    for index, time_value in enumerate(hourly["time"]):
        interval_start_utc = datetime.fromisoformat(time_value).replace(
            tzinfo=timezone.utc
        )

        if interval_start_utc >= current_hour_utc:
            continue

        rows.append(
            {
                "IntervalStartUtc": interval_start_utc,
                "TemperatureC": hourly["temperature_2m"][index],
                "RelativeHumidityPct": hourly["relative_humidity_2m"][index],
                "PrecipitationMm": hourly["precipitation"][index],
                "CloudCoverPct": hourly["cloud_cover"][index],
                "WindSpeedKmh": hourly["wind_speed_10m"][index],
                "WindGustKmh": hourly["wind_gusts_10m"][index],
                "ShortwaveRadiationWm2": hourly["shortwave_radiation"][index],
                "DirectRadiationWm2": hourly["direct_radiation"][index],
            }
        )

    return rows


def get_database_connection():
    return pymysql.connect(
        host=os.environ["ENERGY_DB_HOST"],
        port=int(os.environ["ENERGY_DB_PORT"]),
        user=os.environ["ENERGY_DB_USER"],
        password=os.environ["ENERGY_DB_PASSWORD"],
        database=os.environ["ENERGY_DB_NAME"],
    )


def upsert_recent_weather(connection, rows):
    sql = """
        INSERT INTO WeatherHourly
        (
            IntervalStartUtc,
            TemperatureC,
            RelativeHumidityPct,
            PrecipitationMm,
            CloudCoverPct,
            WindSpeedKmh,
            WindGustKmh,
            ShortwaveRadiationWm2,
            DirectRadiationWm2,
            WeatherDataType
        )
        VALUES
        (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, 'Recent'
        )
        ON DUPLICATE KEY UPDATE
            TemperatureC =
                IF(WeatherDataType = 'Reanalysis',
                   TemperatureC, VALUES(TemperatureC)),
            RelativeHumidityPct =
                IF(WeatherDataType = 'Reanalysis',
                   RelativeHumidityPct, VALUES(RelativeHumidityPct)),
            PrecipitationMm =
                IF(WeatherDataType = 'Reanalysis',
                   PrecipitationMm, VALUES(PrecipitationMm)),
            CloudCoverPct =
                IF(WeatherDataType = 'Reanalysis',
                   CloudCoverPct, VALUES(CloudCoverPct)),
            WindSpeedKmh =
                IF(WeatherDataType = 'Reanalysis',
                   WindSpeedKmh, VALUES(WindSpeedKmh)),
            WindGustKmh =
                IF(WeatherDataType = 'Reanalysis',
                   WindGustKmh, VALUES(WindGustKmh)),
            ShortwaveRadiationWm2 =
                IF(WeatherDataType = 'Reanalysis',
                   ShortwaveRadiationWm2, VALUES(ShortwaveRadiationWm2)),
            DirectRadiationWm2 =
                IF(WeatherDataType = 'Reanalysis',
                   DirectRadiationWm2, VALUES(DirectRadiationWm2)),
            WeatherDataType =
                IF(WeatherDataType = 'Reanalysis',
                   'Reanalysis', 'Recent'),
            LoadedAtUtc =
                IF(WeatherDataType = 'Reanalysis',
                   LoadedAtUtc, UTC_TIMESTAMP())
    """

    values = [
        (
            row["IntervalStartUtc"].replace(tzinfo=None),
            row["TemperatureC"],
            row["RelativeHumidityPct"],
            row["PrecipitationMm"],
            row["CloudCoverPct"],
            row["WindSpeedKmh"],
            row["WindGustKmh"],
            row["ShortwaveRadiationWm2"],
            row["DirectRadiationWm2"],
        )
        for row in rows
    ]

    with connection.cursor() as cursor:
        cursor.executemany(sql, values)

    connection.commit()


def main():
    connection = get_database_connection()

    first_missing_interval = get_first_missing_weather_interval(connection)

    print(f"First missing weather interval: {first_missing_interval}")
    
    try:
        weather = get_recent_weather(connection)
        reanalysis_weather = get_reanalysis_weather()

        reanalysis_times = reanalysis_weather["hourly"]["time"]
        reanalysis_temperatures = reanalysis_weather["hourly"]["temperature_2m"]

        available_reanalysis = [
            time_value
            for time_value, temperature
            in zip(reanalysis_times, reanalysis_temperatures)
            if temperature is not None
        ]

        print()
        print(f"Reanalysis rows received: {len(reanalysis_times)}")
        print(f"Reanalysis rows available: {len(available_reanalysis)}")

        if available_reanalysis:
            print(f"First available reanalysis: {available_reanalysis[0]}")
            print(f"Last available reanalysis: {available_reanalysis[-1]}")

        hourly = weather["hourly"]
        times = hourly["time"]

        current_hour_utc = datetime.now(timezone.utc).replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        completed_times = [
            value
            for value in times
            if datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            < current_hour_utc
        ]

        print(f"Weather rows received: {len(times)}")
        print(f"Completed weather rows: {len(completed_times)}")
        print(f"First interval: {times[0]}")
        print(f"Last completed interval: {completed_times[-1]}")

        print()
        print("Units:")
        for name, unit in weather["hourly_units"].items():
            print(f"  {name}: {unit}")

        rows = build_weather_rows(weather)

        print()
        print(f"Weather rows built: {len(rows)}")
        print("First row:")
        print(rows[0])
        print()
        print("Last row:")
        print(rows[-1])

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            database_name = cursor.fetchone()[0]

        print()
        print(f"Database connection successful: {database_name}")

        upsert_recent_weather(connection, rows)

        print(f"Recent weather rows processed: {len(rows)}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()