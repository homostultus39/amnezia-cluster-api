from sqlalchemy import select
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ProtocolModel
from src.management.settings import get_settings


settings = get_settings()

async def get_protocol_by_name(session: AsyncSession, name: str) -> ProtocolModel | None:
    result = await session.execute(
        select(ProtocolModel).where(ProtocolModel.name == name)
    )
    return result.scalar_one_or_none()

async def create_protocols(session: AsyncSession, protocols: List[str]) -> str:
    for protocol_name in protocols:
        existing_query = await get_protocol_by_name(session, protocol_name)
        if not existing_query:
            new_proto = ProtocolModel(name=protocol_name)
            session.add(new_proto)
    await session.commit()