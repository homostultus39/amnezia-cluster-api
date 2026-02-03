from src.database.connection import sessionmaker
from src.management.settings import get_settings
from src.database.management.operations.admin import get_admin_user_by_username, create_admin_user

settings = get_settings()

async def create_default_admin_user() -> str:
    async with sessionmaker() as session:
        await create_admin_user(session, settings.admin_username, settings.admin_password)