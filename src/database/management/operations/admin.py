from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AdminUserModel
from src.management.settings import get_settings
from src.management.security import hash_password


settings = get_settings()

async def get_admin_user_by_username(session: AsyncSession, username: str) -> AdminUserModel | None:
    result = await session.execute(
        select(AdminUserModel).where(AdminUserModel.username == username)
    )
    return result.scalar_one_or_none()

async def create_admin_user(session: AsyncSession, username: str, password: str):
    existing_record = await get_admin_user_by_username(session, username)
    if not existing_record:
        new_admin = AdminUserModel(username=username, pwd_hash=hash_password(password))
        session.add(new_admin)
        await session.commit()