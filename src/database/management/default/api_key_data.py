from src.database.connection import sessionmaker
from src.database.management.operations.api_key import create_api_key
from src.management.logger import configure_logger
from src.management.security import generate_api_key, hash_api_key
from src.management.settings import get_settings

settings = get_settings()
logger = configure_logger("APIKeySetup", "magenta")


async def create_default_api_key() -> str:
    async with sessionmaker() as session:
        if settings.admin_api_key:
            api_key = settings.admin_api_key
            await create_api_key(session, hash_api_key(api_key))
            return api_key

        api_key = generate_api_key()
        await create_api_key(session, hash_api_key(api_key))
        logger.info("Generated API key on startup")
        logger.info(f"API key: {api_key}")
        return api_key

