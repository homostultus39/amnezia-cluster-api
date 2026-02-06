from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ClientModel, PeerModel


async def get_client_by_id(session: AsyncSession, client_id: UUID) -> ClientModel | None:
    result = await session.execute(
        select(ClientModel).where(ClientModel.id == client_id)
    )
    return result.scalar_one_or_none()


async def get_client_by_username(session: AsyncSession, username: str) -> ClientModel | None:
    result = await session.execute(
        select(ClientModel).where(ClientModel.username == username)
    )
    return result.scalar_one_or_none()


async def get_all_clients_with_protocol(session: AsyncSession, protocol_id: UUID) -> list[ClientModel]:
    result = await session.execute(
        select(ClientModel).where(
            ClientModel.peers.any(PeerModel.protocol_id == protocol_id)
        )
    )
    return list(result.scalars().all())


async def create_client(session: AsyncSession, username: str, expires_at: datetime) -> ClientModel:
    client = ClientModel(username=username, expires_at=expires_at)
    session.add(client)
    await session.flush()
    return client


async def update_client_expires_at(session: AsyncSession, client_id: UUID, expires_at: datetime) -> ClientModel:
    client = await get_client_by_id(session, client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    client.expires_at = expires_at
    await session.flush()
    return client


async def delete_client(session: AsyncSession, client_id: UUID) -> bool:
    client = await get_client_by_id(session, client_id)
    if not client:
        return False

    await session.delete(client)
    await session.flush()
    return True


async def get_expired_clients(session: AsyncSession, protocol_id: UUID) -> list[ClientModel]:
    result = await session.execute(
        select(ClientModel).where(
            ClientModel.expires_at < datetime.now(),
            ClientModel.peers.any(PeerModel.protocol_id == protocol_id)
        )
    )
    return list(result.scalars().all())
