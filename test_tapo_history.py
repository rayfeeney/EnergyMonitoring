import asyncio
import os
from datetime import date

from dotenv import load_dotenv
from tapo import ApiClient
from tapo.requests import EnergyDataInterval


async def main():
    load_dotenv()

    client = ApiClient(
        os.environ["TAPO_USERNAME"],
        os.environ["TAPO_PASSWORD"],
    )

    device = await client.p110(
        os.environ["TAPO_DEVICE_1_IP"]
    )

    result = await device.get_energy_data(
        EnergyDataInterval.Hourly,
        date(2026, 10, 1),
        date(2026, 10, 1),
    )

    print(f"Rows returned: {len(result.entries)}")

    if result.entries:
        print(f"First: {result.entries[0].to_dict()}")
        print(f"Last:  {result.entries[-1].to_dict()}")


if __name__ == "__main__":
    asyncio.run(main())