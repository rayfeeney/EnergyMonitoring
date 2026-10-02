import argparse
import asyncio
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from tapo import ApiClient
from tapo.requests import EnergyDataInterval, PowerDataInterval

from energymonitoring.database.connection import get_connection


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).replace(tzinfo=None)


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        help="First UTC date to backload (YYYY-MM-DD).",
    )

    parser.add_argument(
        "--end-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        help="Last UTC date to backload (YYYY-MM-DD).",
    )

    return parser.parse_args()


def get_or_create_device(cursor, device_name: str, model: str, ip_address: str) -> int:
    cursor.execute(
        """
        SELECT TapoDeviceKey
        FROM TapoDevice
        WHERE DeviceName = %s
        """,
        (device_name,),
    )

    row = cursor.fetchone()

    if row:
        cursor.execute(
            """
            UPDATE TapoDevice
            SET Model = %s,
                IpAddress = %s,
                IsActive = 1
            WHERE TapoDeviceKey = %s
            """,
            (
                model,
                ip_address,
                row["TapoDeviceKey"],
            ),
        )

        return row["TapoDeviceKey"]

    cursor.execute(
        """
        INSERT INTO TapoDevice
        (
            DeviceName,
            Model,
            IpAddress,
            IsActive
        )
        VALUES (%s, %s, %s, 1)
        """,
        (
            device_name,
            model,
            ip_address,
        ),
    )

    return cursor.lastrowid


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


async def main():
    args = parse_arguments()

    if (args.start_date is None) != (args.end_date is None):
        raise ValueError(
            "--start-date and --end-date must be supplied together."
        )

    if (
        args.start_date is not None
        and args.end_date < args.start_date
    ):
        raise ValueError(
            "--end-date cannot be before --start-date."
        )

    backload_mode = args.start_date is not None

    if backload_mode:
        backload_start_utc = datetime.combine(
            args.start_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        backload_end_utc = datetime.combine(
            args.end_date + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

    load_dotenv()

    username = os.environ["TAPO_USERNAME"]
    password = os.environ["TAPO_PASSWORD"]

    device_ips = [
        os.environ["TAPO_DEVICE_1_IP"],
        os.environ["TAPO_DEVICE_2_IP"],
    ]

    client = ApiClient(username, password)

    for ip_address in device_ips:
        print(f"Connecting to Tapo P110 at {ip_address}...")

        device = await client.p110(ip_address)

        device_info = await device.get_device_info()

        print(f"Device: {device_info.nickname}")
        print(f"Model:  {device_info.model}")

        now = datetime.now(timezone.utc)

        if backload_mode:
            hourly_entries = []

            request_date = args.start_date - timedelta(days=1)
            final_request_date = args.end_date + timedelta(days=1)

            while request_date <= final_request_date:
                hourly_energy = await device.get_energy_data(
                    EnergyDataInterval.Hourly,
                    request_date,
                    request_date,
                )

                hourly_entries.extend(hourly_energy.entries)

                request_date += timedelta(days=1)
        else:
            hourly_energy = await device.get_energy_data(
                EnergyDataInterval.Hourly,
                now,
            )

            hourly_entries = hourly_energy.entries

        if backload_mode:
            power_entries = []

            chunk_start_utc = backload_start_utc

            while chunk_start_utc < backload_end_utc:
                chunk_end_utc = min(
                    chunk_start_utc + timedelta(hours=12),
                    backload_end_utc,
                )

                power_history = await device.get_power_data(
                    PowerDataInterval.Every5Minutes,
                    chunk_start_utc,
                    chunk_end_utc,
                )

                power_entries.extend(power_history.entries)

                chunk_start_utc = chunk_end_utc
        else:
            power_history = await device.get_power_data(
                PowerDataInterval.Every5Minutes,
                now - timedelta(hours=12),
                now,
            )

            power_entries = power_history.entries

        current_hour_utc = now.replace(
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None,
        )

        connection = get_connection()

        load_run_key = None
        rows_inserted = 0
        rows_updated = 0
        rows_unchanged = 0

        rows_received = (
            len(hourly_entries)
            + len(power_entries)
        )

        try:
            with connection.cursor() as cursor:
                load_run_key = start_load_run(
                    cursor,
                    f"Tapo:{device_info.nickname}",
                )

                # Commit the LoadRun record separately so that it survives
                # a rollback if the subsequent data load fails.
                connection.commit()

                device_key = get_or_create_device(
                                    cursor,
                    device_info.nickname,
                    device_info.model,
                    ip_address,
                )

                for entry in hourly_entries:
                    row = entry.to_dict()

                    hour_start_utc = parse_utc(
                        row["start_date_time"]
                    )

                    if backload_mode:
                        if not (
                            backload_start_utc.replace(tzinfo=None)
                            <= hour_start_utc
                            < backload_end_utc.replace(tzinfo=None)
                        ):
                            continue

                    # Only store completed hourly intervals.
                    if hour_start_utc >= current_hour_utc:
                        continue

                    cursor.execute(
                        """
                        INSERT INTO TapoEnergyHourly
                        (
                            TapoDeviceKey,
                            HourStartUtc,
                            EnergyWh
                        )
                        VALUES (%s, %s, %s)

                        ON DUPLICATE KEY UPDATE
                            LoadedUtc = IF(EnergyWh <> VALUES(EnergyWh), CURRENT_TIMESTAMP, LoadedUtc),
                            EnergyWh = VALUES(EnergyWh)
                        """,
                        (
                            device_key,
                            hour_start_utc,
                            row["energy"],
                        ),
                    )

                    if cursor.rowcount == 1:
                        rows_inserted += 1
                    elif cursor.rowcount == 2:
                        rows_updated += 1
                    else:
                        rows_unchanged += 1

                for entry in power_entries:
                    row = entry.to_dict()

                    cursor.execute(
                        """
                        INSERT INTO TapoPowerReading
                        (
                            TapoDeviceKey,
                            ReadingUtc,
                            PowerWatts
                        )
                        VALUES (%s, %s, %s)

                        ON DUPLICATE KEY UPDATE
                            LoadedUtc = IF(PowerWatts <> VALUES(PowerWatts), CURRENT_TIMESTAMP, LoadedUtc),
                            PowerWatts = VALUES(PowerWatts)
                        """,
                        (
                            device_key,
                            parse_utc(row["start_date_time"]),
                            row["power"],
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

            connection.commit()

            print(f"Hourly energy rows received: {len(hourly_entries)}")
            print(f"5-minute power rows received: {len(power_entries)}")
            print(f"Rows inserted: {rows_inserted}")
            print(f"Rows updated: {rows_updated}")
            print(f"Rows unchanged: {rows_unchanged}")

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
    asyncio.run(main())