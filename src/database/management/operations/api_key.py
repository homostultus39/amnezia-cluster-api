from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import APIKeyModel
from src.management.security import verify_api_key


async def get_active_api_key(session: AsyncSession) -> APIKeyModel | None:
    result = await session.execute(select(APIKeyModel))
    return result.scalars().first()


async def delete_all_api_keys(session: AsyncSession) -> None:
    await session.execute(delete(APIKeyModel))
    await session.commit()


async def create_api_key(session: AsyncSession, api_key_hash: str) -> APIKeyModel:
    await delete_all_api_keys(session)
    api_key = APIKeyModel(api_key_hash=api_key_hash)
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key


async def get_api_key_by_plain_key(session: AsyncSession, api_key: str) -> APIKeyModel | None:
    result = await session.execute(select(APIKeyModel))
    for record in result.scalars().all():
        if verify_api_key(api_key, record.api_key_hash):
            return record
    return None

