import asyncio
import os

from dotenv import load_dotenv

from energymonitoring.tapo.client import get_p110

from datetime import datetime, timedelta, timezone

from tapo.requests import EnergyDataInterval, PowerDataInterval

async def main():
    load_dotenv()

    ip_address = os.environ["TAPO_DEVICE_1_IP"]

    print(f"Connecting to Tapo P110 at {ip_address}...")

    device = await get_p110(ip_address)

    device_info = await device.get_device_info()

    print("\nDevice")
    print(f"Nickname: {device_info.nickname}")
    print(f"Model:    {device_info.model}")

    current_power = await device.get_current_power()

    print("\nCurrent power")
    print(current_power.to_dict())

    energy_usage = await device.get_energy_usage()

    print("\nEnergy usage")
    print(energy_usage.to_dict())

    now = datetime.now(timezone.utc)

    print("\nHourly energy history")

    hourly_energy = await device.get_energy_data(
        EnergyDataInterval.Hourly,
        now
    )

    print(hourly_energy.to_dict())

    print("\n5-minute power history")

    power_history = await device.get_power_data(
        PowerDataInterval.Every5Minutes,
        now - timedelta(hours=12),
        now
    )

    print(power_history.to_dict())
    
if __name__ == "__main__":
    asyncio.run(main())