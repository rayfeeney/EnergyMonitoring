import os
from datetime import datetime, timedelta, timezone
import pymysql

import requests
from dotenv import load_dotenv


load_dotenv()


OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

WEATHER_START_DATE = datetime(2026, 9, 25, tzinfo=timezone.utc).date()

WEATHER_RELOAD_DAYS = 10

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


def start_load_run(cursor, source_name: str) -> int:
    cursor.execute(
        """
        INSERT INTO LoadRun
        (
            SourceName,
            StartedUtc,
            Status
        )
        VALUES (%s, UTC_TIMESTAMP(), 'Running')
        """,
        (source_name,),
    )

    return cursor.lastrowid


def complete_load_run(
    cursor,
    load_run_key: int,
    rows_received: int,
    rows_inserted: int,
    rows_updated: int,
):
    cursor.execute(
        """
        UPDATE LoadRun
        SET CompletedUtc = UTC_TIMESTAMP(),
            RowsReceived = %s,
            RowsInserted = %s,
            RowsUpdated = %s,
            Status = 'Succeeded'
        WHERE LoadRunKey = %s
        """,
        (
            rows_received,
            rows_inserted,
            rows_updated,
            load_run_key,
        ),
    )

    
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

    first_missing_interval = get_first_missing_weather_interval(connection)

    if first_missing_interval is not None:
        start_date = first_missing_interval.date()
    else:
        start_date = (now_utc - timedelta(days=WEATHER_RELOAD_DAYS)).date()

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


def get_reanalysis_weather(connection):
    latitude = float(os.environ["WEATHER_LATITUDE"])
    longitude = float(os.environ["WEATHER_LONGITUDE"])

    now_utc = datetime.now(timezone.utc)

    earliest_recent_interval = get_earliest_recent_interval(connection)

    normal_start_date = (
        now_utc - timedelta(days=WEATHER_RELOAD_DAYS)
    ).date()

    if earliest_recent_interval is not None:
        start_date = min(
            earliest_recent_interval.date(),
            normal_start_date,
        )
    else:
        start_date = normal_start_date

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


def build_reanalysis_rows(weather):
    hourly = weather["hourly"]

    rows = []

    for index, time_value in enumerate(hourly["time"]):
        values = [
            hourly["temperature_2m"][index],
            hourly["relative_humidity_2m"][index],
            hourly["precipitation"][index],
            hourly["cloud_cover"][index],
            hourly["wind_speed_10m"][index],
            hourly["wind_gusts_10m"][index],
            hourly["shortwave_radiation"][index],
            hourly["direct_radiation"][index],
        ]

        # Do not allow incomplete Reanalysis data to replace Recent data.
        if any(value is None for value in values):
            continue

        rows.append(
            {
                "IntervalStartUtc": datetime.fromisoformat(time_value).replace(
                    tzinfo=timezone.utc
                ),
                "TemperatureC": values[0],
                "RelativeHumidityPct": values[1],
                "PrecipitationMm": values[2],
                "CloudCoverPct": values[3],
                "WindSpeedKmh": values[4],
                "WindGustKmh": values[5],
                "ShortwaveRadiationWm2": values[6],
                "DirectRadiationWm2": values[7],
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


def upsert_reanalysis_weather(connection, rows):
    if not rows:
        return

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
            %s, %s, %s, %s, 'Reanalysis'
        )
        ON DUPLICATE KEY UPDATE
            TemperatureC = VALUES(TemperatureC),
            RelativeHumidityPct = VALUES(RelativeHumidityPct),
            PrecipitationMm = VALUES(PrecipitationMm),
            CloudCoverPct = VALUES(CloudCoverPct),
            WindSpeedKmh = VALUES(WindSpeedKmh),
            WindGustKmh = VALUES(WindGustKmh),
            ShortwaveRadiationWm2 = VALUES(ShortwaveRadiationWm2),
            DirectRadiationWm2 = VALUES(DirectRadiationWm2),
            WeatherDataType = 'Reanalysis',
            LoadedAtUtc = UTC_TIMESTAMP()
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

    load_run_key = None

    first_missing_interval = get_first_missing_weather_interval(connection)

    #print(f"First missing weather interval: {first_missing_interval}")
    
    try:
        with connection.cursor() as cursor:
            load_run_key = start_load_run(cursor, "Weather")

        connection.commit()

        weather = get_recent_weather(connection)
        reanalysis_weather = get_reanalysis_weather(connection)

        reanalysis_rows = build_reanalysis_rows(reanalysis_weather)

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

        #print(f"Weather rows received: {len(times)}")
        #print(f"Completed weather rows: {len(completed_times)}")
        #print(f"First interval: {times[0]}")
        #print(f"Last completed interval: {completed_times[-1]}")

        #print()
        #print("Units:")
        #for name, unit in weather["hourly_units"].items():
        #    print(f"  {name}: {unit}")

        rows = build_weather_rows(weather)

        #print()
        #print(f"Weather rows built: {len(rows)}")
        #print("First row:")
        #print(rows[0])
        #print()
        #print("Last row:")
        #print(rows[-1])

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            database_name = cursor.fetchone()[0]

        #print()
        #print(f"Database connection successful: {database_name}")

        upsert_recent_weather(connection, rows)

        print(f"Recent weather rows processed: {len(rows)}")

        upsert_reanalysis_weather(connection, reanalysis_rows)

        print(f"Reanalysis weather rows processed: {len(reanalysis_rows)}")

        with connection.cursor() as cursor:
            complete_load_run(
                cursor,
                load_run_key,
                len(rows) + len(reanalysis_rows),
                0,
                0,
            )

        connection.commit()

    except Exception as exc:
        connection.rollback()

        if load_run_key is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE LoadRun
                    SET CompletedUtc = UTC_TIMESTAMP(),
                        Status = 'Failed',
                        ErrorMessage = %s
                    WHERE LoadRunKey = %s
                    """,
                    (
                        str(exc),
                        load_run_key,
                    ),
                )

            connection.commit()

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()