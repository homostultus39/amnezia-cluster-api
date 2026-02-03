from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


class BaseProtocolService(ABC):
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        pass

    @abstractmethod
    async def get_clients(self, session: AsyncSession) -> list[dict]:
        pass

    @abstractmethod
    async def create_client(
        self,
        session: AsyncSession,
        username: str,
        app_type: str,
        expires_at: Optional[datetime] = None,
    ) -> dict:
        pass

    @abstractmethod
    async def delete_client(self, session: AsyncSession, peer_id: UUID) -> bool:
        pass

    async def cleanup_expired_clients(self, session: AsyncSession) -> int:
        from sqlalchemy import select
        from src.database.models import PeerModel

        result = await session.execute(
            select(PeerModel).where(
                PeerModel.expires_at < datetime.now(),
                PeerModel.protocol_id == await self._get_protocol_id(session)
            )
        )
        expired_peers = result.scalars().all()

        deleted_count = 0
        for peer in expired_peers:
            try:
                await self.delete_client(session, peer.id)
                deleted_count += 1
            except Exception:
                pass

        return deleted_count

    @abstractmethod
    async def _get_protocol_id(self, session: AsyncSession) -> UUID:
        pass
