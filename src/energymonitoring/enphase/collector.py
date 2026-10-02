import os
import base64
import urllib.parse
import urllib.request
import json
import argparse
import time

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


def get_battery_intervals(
    system_id: str,
    api_key: str,
    access_token: str,
    start_at: int,
    end_at: int,
):
    url = (
        f"https://api.enphaseenergy.com/api/v4/systems/"
        f"{system_id}/telemetry/battery"
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
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start-date",
        type=str,
        help="Historical backfill start date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="Historical backfill end date in YYYY-MM-DD format.",
    )

    args = parser.parse_args()

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
    if bool(args.start_date) != bool(args.end_date):
        parser.error(
            "--start-date and --end-date must be supplied together."
        )

    if args.start_date and args.end_date:
        start_time = datetime.strptime(
            args.start_date,
            "%Y-%m-%d",
        ).replace(tzinfo=timezone.utc)

        end_time = datetime.strptime(
            args.end_date,
            "%Y-%m-%d",
        ).replace(tzinfo=timezone.utc)

        if end_time <= start_time:
            parser.error(
                "--end-date must be later than --start-date."
            )

        chunk_days = 1

    else:
        end_time = datetime.now(timezone.utc).replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        start_time = end_time - timedelta(days=1)
        chunk_days = 1

    intervals = []
    consumption_intervals = []
    import_intervals = []
    export_intervals = []
    battery_intervals = []

    chunk_start = start_time

    while chunk_start < end_time:
        chunk_end = min(
            chunk_start + timedelta(days=chunk_days),
            end_time,
        )

        print(
            f"Retrieving Enphase data "
            f"{chunk_start.isoformat()} to {chunk_end.isoformat()}"
        )

        production = get_production_intervals(
            system_id,
            api_key,
            access_token,
            int(chunk_start.timestamp()),
            int(chunk_end.timestamp()),
        )

        intervals.extend(
            production.get("intervals", [])
        )

        consumption = get_consumption_intervals(
            system_id,
            api_key,
            access_token,
            int(chunk_start.timestamp()),
            int(chunk_end.timestamp()),
        )

        consumption_intervals.extend(
            consumption.get("intervals", [])
        )

        grid_import = get_import_intervals(
            system_id,
            api_key,
            access_token,
            int(chunk_start.timestamp()),
            int(chunk_end.timestamp()),
        )

        import_intervals.extend(
            interval
            for group in grid_import.get("intervals", [])
            for interval in group
        )

        grid_export = get_export_intervals(
            system_id,
            api_key,
            access_token,
            int(chunk_start.timestamp()),
            int(chunk_end.timestamp()),
        )

        export_intervals.extend(
            interval
            for group in grid_export.get("intervals", [])
            for interval in group
        )

        battery = get_battery_intervals(
            system_id,
            api_key,
            access_token,
            int(chunk_start.timestamp()),
            int(chunk_end.timestamp()),
        )

        battery_intervals.extend(
            battery.get("intervals", [])
        )

        chunk_start = chunk_end

        if chunk_start < end_time:
            print("Waiting 60 seconds before next Enphase API batch...")
            time.sleep(60)

    print(f"Production intervals received: {len(intervals)}")
    print(f"Consumption intervals received: {len(consumption_intervals)}")
    print(f"Import intervals received: {len(import_intervals)}")
    print(f"Export intervals received: {len(export_intervals)}")
    print(f"Battery intervals received: {len(battery_intervals)}")

    combined_intervals = {}

    for row in intervals:
        combined_intervals.setdefault(row["end_at"], {})["ProducedWh"] = row["wh_del"]

    for row in consumption_intervals:
        combined_intervals.setdefault(row["end_at"], {})["ConsumedWh"] = row["enwh"]

    for row in import_intervals:
        combined_intervals.setdefault(row["end_at"], {})["ImportedWh"] = row["wh_imported"]

    for row in export_intervals:
        combined_intervals.setdefault(row["end_at"], {})["ExportedWh"] = row["wh_exported"]

    for row in battery_intervals:
        end_at = row["end_at"]

        combined_intervals.setdefault(end_at, {})["ChargedWh"] = (
            row.get("charge", {}).get("enwh")
        )
        combined_intervals.setdefault(end_at, {})["DischargedWh"] = (
            row.get("discharge", {}).get("enwh")
        )
        combined_intervals.setdefault(end_at, {})["BatterySocPct"] = (
            row.get("soc", {}).get("percent")
        )

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

            # Commit the LoadRun record separately so that it survives
            # a rollback if the subsequent data load fails.
            connection.commit()

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
                        ExportedWh,
                        ChargedWh,
                        DischargedWh,
                        BatterySocPct
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)

                    ON DUPLICATE KEY UPDATE
                        LoadedUtc = IF(
                            NOT (
                                ProducedWh <=> VALUES(ProducedWh)
                                AND ConsumedWh <=> VALUES(ConsumedWh)
                                AND ImportedWh <=> VALUES(ImportedWh)
                                AND ExportedWh <=> VALUES(ExportedWh)
                                AND ChargedWh <=> VALUES(ChargedWh)
                                AND DischargedWh <=> VALUES(DischargedWh)
                                AND BatterySocPct <=> VALUES(BatterySocPct)
                            ),
                            CURRENT_TIMESTAMP,
                            LoadedUtc
                        ),
                        ProducedWh = VALUES(ProducedWh),
                        ConsumedWh = VALUES(ConsumedWh),
                        ImportedWh = VALUES(ImportedWh),
                        ExportedWh = VALUES(ExportedWh),
                        ChargedWh = VALUES(ChargedWh),
                        DischargedWh = VALUES(DischargedWh),
                        BatterySocPct = VALUES(BatterySocPct)
                    """,
                    (
                        interval_end_utc,
                        values.get("ProducedWh"),
                        values.get("ConsumedWh"),
                        values.get("ImportedWh"),
                        values.get("ExportedWh"),
                        values.get("ChargedWh"),
                        values.get("DischargedWh"),
                        values.get("BatterySocPct"),
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