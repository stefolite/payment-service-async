import httpx
import asyncio


async def deliver_webhook(
    http_client: httpx.AsyncClient,
    webhook_url: str,
    payload: dict,
) -> None:
    for attempt in range(3):
        try:
            response = await http_client.post(
                url=webhook_url,
                json=payload,
            )
            response.raise_for_status()
            return None

        except httpx.HTTPError:
            if attempt == 2:
                raise

            await asyncio.sleep(2 ** attempt)
