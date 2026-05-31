import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(
            "https://api.alternative.me/fng/",
            params={"limit": 8, "format": "json"},
        )
        print(resp.status_code, resp.text)

asyncio.run(main())
