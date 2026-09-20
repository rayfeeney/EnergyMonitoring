import os

from tapo import ApiClient


def get_tapo_client() -> ApiClient:
    username = os.environ["TAPO_USERNAME"]
    password = os.environ["TAPO_PASSWORD"]

    return ApiClient(username, password)


async def get_p110(ip_address: str):
    client = get_tapo_client()
    return await client.p110(ip_address)