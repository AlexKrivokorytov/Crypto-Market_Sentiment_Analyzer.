import httpx
from typing import Optional


class HttpClient:
    """
    Singleton HTTP client wrapper.
    Reusing a single AsyncClient across the app enables TCP connection pooling,
    reducing latency and resource exhaustion significantly compared to opening
    new clients per request.
    """

    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(timeout=10.0)
        return cls._client

    @classmethod
    async def close(cls) -> None:
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None


# Global helper function for convenience
def get_shared_client() -> httpx.AsyncClient:
    return HttpClient.get_client()
