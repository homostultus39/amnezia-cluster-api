import hashlib

from src.management.logger import configure_logger
from src.redis.connection import get_redis_client

logger = configure_logger("RedisClient", "red")


class RedisClient:
    def __init__(self) -> None:
        self._client = get_redis_client()

    def _token_key(self, token: str) -> str:
        digest = hashlib.sha256(token.encode()).hexdigest()
        return f"jwt:blacklist:{digest}"

    async def blacklist_token(self, token: str, ex: int) -> None:
        """
        Add token to blacklist with TTL.

        Args:
            token: JWT token to blacklist
            ex: Expiration time in seconds (required)
        """
        key = self._token_key(token)
        await self._client.set(key, "1", ex=ex)
        logger.info(f"Token blacklisted with TTL {ex}s")

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is in blacklist.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        key = self._token_key(token)
        return await self._client.exists(key) == 1