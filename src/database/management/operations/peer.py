from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import PeerModel


async def get_peer_by_id(session: AsyncSession, peer_id: UUID) -> PeerModel | None:
    result = await session.execute(
        select(PeerModel).where(PeerModel.id == peer_id)
    )
    return result.scalar_one_or_none()


async def get_peer_by_id_with_client(
    session: AsyncSession,
    peer_id: UUID
) -> PeerModel | None:
    result = await session.execute(
        select(PeerModel)
        .options(selectinload(PeerModel.client))
        .where(PeerModel.id == peer_id)
    )
    return result.scalar_one_or_none()


async def get_peer_by_public_key(session: AsyncSession, public_key: str) -> PeerModel | None:
    result = await session.execute(
        select(PeerModel).where(PeerModel.public_key == public_key)
    )
    return result.scalar_one_or_none()


async def get_all_peers_by_protocol(session: AsyncSession, protocol_id: UUID) -> list[PeerModel]:
    result = await session.execute(
        select(PeerModel).where(PeerModel.protocol_id == protocol_id)
    )
    return list(result.scalars().all())


async def get_all_peers_by_protocol_with_client(
    session: AsyncSession,
    protocol_id: UUID
) -> list[PeerModel]:
    result = await session.execute(
        select(PeerModel)
        .options(selectinload(PeerModel.client))
        .where(PeerModel.protocol_id == protocol_id)
    )
    return list(result.scalars().all())


async def get_peers_by_client_id(session: AsyncSession, client_id: UUID) -> list[PeerModel]:
    result = await session.execute(
        select(PeerModel).where(PeerModel.client_id == client_id)
    )
    return list(result.scalars().all())


async def get_peers_by_client_id_with_client(
    session: AsyncSession,
    client_id: UUID
) -> list[PeerModel]:
    result = await session.execute(
        select(PeerModel)
        .options(selectinload(PeerModel.client))
        .where(PeerModel.client_id == client_id)
    )
    return list(result.scalars().all())


async def create_peer(
    session: AsyncSession,
    client_id: UUID,
    protocol_id: UUID,
    app_type: str,
    public_key: str,
    allowed_ips: list[str],
    endpoint: str
) -> PeerModel:
    peer = PeerModel(
        client_id=client_id,
        protocol_id=protocol_id,
        app_type=app_type,
        public_key=public_key,
        allowed_ips=allowed_ips,
        endpoint=endpoint
    )
    session.add(peer)
    await session.flush()
    return peer


async def delete_peer(session: AsyncSession, peer_id: UUID) -> bool:
    peer = await get_peer_by_id(session, peer_id)
    if not peer:
        return False

    await session.delete(peer)
    await session.flush()
    return True


async def get_allocated_ips(session: AsyncSession, protocol_id: UUID) -> list[str]:
    result = await session.execute(
        select(PeerModel.allowed_ips).where(PeerModel.protocol_id == protocol_id)
    )
    all_ips = []
    for row in result.scalars():
        all_ips.extend(row)
    return all_ips
