import httpx


async def ping(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/version")
    response.raise_for_status()
