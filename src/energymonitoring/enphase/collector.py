import os
import base64
import urllib.parse
import urllib.request
import json

from dotenv import load_dotenv, set_key
from datetime import datetime, timedelta, timezone
from energymonitoring.database.connection import get_connection


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> tuple[str, str]:
    pair = f"{client_id}:{client_secret}".encode("ascii")
    basic_auth = base64.b64encode(pair).decode("ascii")

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("ascii")

    request = urllib.request.Request(
        "https://api.enphaseenergy.com/oauth/token",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    with urllib.request.urlopen(request) as response:
        token_response = json.loads(response.read().decode("utf-8"))

    return (
        token_response["access_token"],
        token_response["refresh_token"],
    )


def get_production_intervals(
    system_id: str,
    api_key: str,
    access_token: str,
    start_at: int,
    end_at: int,
):
    url = (
        f"https://api.enphaseenergy.com/api/v4/systems/"
        f"{system_id}/telemetry/production_meter"
        f"?key={api_key}&start_at={start_at}&end_at={end_at}"
    )

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))
    

def get_consumption_intervals(
    system_id: str,
    api_key: str,
    access_token: str,
    start_at: int,
    end_at: int,
):
    url = (
        f"https://api.enphaseenergy.com/api/v4/systems/"
        f"{system_id}/telemetry/consumption_meter"
        f"?key={api_key}&start_at={start_at}&end_at={end_at}"
    )

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def get_import_intervals(
    system_id: str,
    api_key: str,
    access_token: str,
    start_at: int,
    end_at: int,
):
    url = (
        f"https://api.enphaseenergy.com/api/v4/systems/"
        f"{system_id}/energy_import_telemetry"
        f"?key={api_key}&start_at={start_at}&end_at={end_at}"
    )

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def get_export_intervals(
    system_id: str,
    api_key: str,
    access_token: str,
    start_at: int,
    end_at: int,
):
    url = (
        f"https://api.enphaseenergy.com/api/v4/systems/"
        f"{system_id}/energy_export_telemetry"
        f"?key={api_key}&start_at={start_at}&end_at={end_at}"
    )

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


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


def main():
    load_dotenv()

    system_id = os.environ["ENPHASE_SYSTEM_ID"]
    api_key = os.environ["ENPHASE_API_KEY"]
    refresh_token = os.environ["ENPHASE_REFRESH_TOKEN"]
    client_id = os.environ["ENPHASE_CLIENT_ID"]
    client_secret = os.environ["ENPHASE_CLIENT_SECRET"]

    access_token, new_refresh_token = get_access_token(
        client_id,
        client_secret,
        refresh_token,
    )
    set_key(
        ".env",
        "ENPHASE_REFRESH_TOKEN",
        new_refresh_token,
    )

    end_time = datetime.now(timezone.utc).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    start_time = end_time - timedelta(days=1)

    production = get_production_intervals(
        system_id,
        api_key,
        access_token,
        int(start_time.timestamp()),
        int(end_time.timestamp()),
    )

    intervals = production.get("intervals", [])

    print(f"Production intervals received: {len(intervals)}")

    consumption = get_consumption_intervals(
        system_id,
        api_key,
        access_token,
        int(start_time.timestamp()),
        int(end_time.timestamp()),
    )

    consumption_intervals = consumption.get("intervals", [])

    print(f"Consumption intervals received: {len(consumption_intervals)}")

    grid_import = get_import_intervals(
        system_id,
        api_key,
        access_token,
        int(start_time.timestamp()),
        int(end_time.timestamp()),
    )

    import_intervals = [
        interval
        for group in grid_import.get("intervals", [])
        for interval in group
    ]

    print(f"Import intervals received: {len(import_intervals)}")

    grid_export = get_export_intervals(
        system_id,
        api_key,
        access_token,
        int(start_time.timestamp()),
        int(end_time.timestamp()),
    )

    export_intervals = [
        interval
        for group in grid_export.get("intervals", [])
        for interval in group
    ]

    print(f"Export intervals received: {len(export_intervals)}")

    combined_intervals = {}

    for row in intervals:
        combined_intervals.setdefault(row["end_at"], {})["ProducedWh"] = row["wh_del"]

    for row in consumption_intervals:
        combined_intervals.setdefault(row["end_at"], {})["ConsumedWh"] = row["enwh"]

    for row in import_intervals:
        combined_intervals.setdefault(row["end_at"], {})["ImportedWh"] = row["wh_imported"]

    for row in export_intervals:
        combined_intervals.setdefault(row["end_at"], {})["ExportedWh"] = row["wh_exported"]

    print(f"Combined intervals: {len(combined_intervals)}")

    sample_end_at = next(iter(combined_intervals))

    sample_interval_end_utc = datetime.fromtimestamp(
        sample_end_at,
        tz=timezone.utc,
    ).replace(tzinfo=None)

    connection = get_connection()

    load_run_key = None
    rows_inserted = 0
    rows_updated = 0
    rows_unchanged = 0
    rows_received = len(combined_intervals)

    try:
        with connection.cursor() as cursor:
            load_run_key = start_load_run(
                cursor,
                "Enphase",
            )
            
            for end_at, values in combined_intervals.items():
                interval_end_utc = datetime.fromtimestamp(
                    end_at,
                    tz=timezone.utc,
                ).replace(tzinfo=None)

                cursor.execute(
                    """
                    INSERT INTO EnphaseInterval
                    (
                        IntervalEndUtc,
                        ProducedWh,
                        ConsumedWh,
                        ImportedWh,
                        ExportedWh
                    )
                    VALUES (%s, %s, %s, %s, %s)

                    ON DUPLICATE KEY UPDATE
                        LoadedUtc = IF(
                            NOT (
                                ProducedWh <=> VALUES(ProducedWh)
                                AND ConsumedWh <=> VALUES(ConsumedWh)
                                AND ImportedWh <=> VALUES(ImportedWh)
                                AND ExportedWh <=> VALUES(ExportedWh)
                            ),
                            CURRENT_TIMESTAMP,
                            LoadedUtc
                        ),
                        ProducedWh = VALUES(ProducedWh),
                        ConsumedWh = VALUES(ConsumedWh),
                        ImportedWh = VALUES(ImportedWh),
                        ExportedWh = VALUES(ExportedWh)
                    """,
                    (
                        interval_end_utc,
                        values.get("ProducedWh"),
                        values.get("ConsumedWh"),
                        values.get("ImportedWh"),
                        values.get("ExportedWh"),
                    ),
                )

                if cursor.rowcount == 1:
                    rows_inserted += 1
                elif cursor.rowcount == 2:
                    rows_updated += 1
                else:
                    rows_unchanged += 1

            complete_load_run(
                cursor,
                load_run_key,
                rows_received,
                rows_inserted,
                rows_updated,
            )

            pass

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