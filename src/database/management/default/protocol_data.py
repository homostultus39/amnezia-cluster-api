from src.database.connection import sessionmaker
from src.management.settings import get_settings
from src.database.management.operations.protocol import create_protocols

settings = get_settings()

async def create_default_protocols() -> str:
    async with sessionmaker() as session:
        await create_protocols(session, settings.available_protocols)