from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.amnezia_service import AmneziaService
from src.services.management.base_protocol_service import BaseProtocolService
from src.database.models import ClientModel, AppType
from src.database.management.operations.client import get_client_by_username, get_client_by_id, create_client, delete_client as delete_client_op
from src.management.logger import configure_logger

logger = configure_logger("ClientsService", "yellow")


class ClientsService:
    def __init__(self):
        self._services: dict[str, BaseProtocolService] = {
            "amneziawg": AmneziaService(),
        }

    def _get_service(self, protocol: str) -> BaseProtocolService:
        service = self._services.get(protocol.lower())
        if not service:
            logger.error(f"Unsupported protocol requested: {protocol}")
            raise ValueError(f"Unsupported protocol: {protocol}")
        return service

    async def get_clients(self, session: AsyncSession, protocol: Optional[str] = None) -> list[dict]:
        if protocol:
            service = self._get_service(protocol)
            clients = await service.get_clients(session)
        else:
            all_clients = []
            for service in self._services.values():
                try:
                    clients = await service.get_clients(session)
                    all_clients.extend(clients)
                except Exception as e:
                    logger.warning(f"Failed to get clients for {service.protocol_name}: {e}")

            clients = all_clients

        logger.info(f"Retrieved {len(clients)} clients")
        return clients

    async def create_client(
        self,
        session: AsyncSession,
        username: str,
        protocol: str,
        expires_at: Optional[datetime] = None,
    ) -> dict:
        service = self._get_service(protocol)

        client = await get_client_by_username(session, username)

        if not client:
            if not expires_at:
                expires_at = datetime.now() + timedelta(days=30)

            client = await create_client(session, username, expires_at)

        amnezia_vpn_peer = await service.create_peer(
            session=session,
            client=client,
            app_type=AppType.AMNEZIA_VPN.value
        )

        amnezia_wg_peer = await service.create_peer(
            session=session,
            client=client,
            app_type=AppType.AMNEZIA_WG.value
        )

        await session.commit()

        logger.info(f"Client created: {username} with both peer types on protocol {protocol}")

        return {
            "id": str(client.id),
            "amnezia_vpn": {
                "protocol": protocol,
                "config": amnezia_vpn_peer["config"],
                "url": amnezia_vpn_peer["config_url"],
            },
            "amnezia_wg": {
                "protocol": protocol,
                "config": amnezia_wg_peer["config"],
                "url": amnezia_wg_peer["config_url"],
            }
        }

    async def delete_client(self, session: AsyncSession, client_id: UUID, protocol: str = "amneziawg") -> bool:
        service = self._get_service(protocol)

        client = await get_client_by_id(session, client_id)
        if not client:
            logger.warning(f"Client {client_id} not found")
            return False

        for peer in client.peers:
            try:
                await service._remove_peer_from_config(peer.public_key)
                await service._delete_config(peer.client_id)
            except Exception as exc:
                logger.warning(f"Failed to cleanup peer {peer.id} config: {exc}")

        await service.connection.sync_wg_config()

        deleted = await delete_client_op(session, client_id)
        await session.commit()

        if deleted:
            logger.info(f"Client deleted: {client_id}")
        else:
            logger.warning(f"Client {client_id} not found")
        return deleted

    async def cleanup_expired_clients(self, session: AsyncSession) -> int:
        total_deleted = 0

        for service in self._services.values():
            try:
                deleted = await service.cleanup_expired_clients(session)
                total_deleted += deleted
            except Exception as e:
                logger.error(f"Failed to cleanup for {service.protocol_name}: {e}")

        logger.info(f"Cleaned up {total_deleted} expired clients")
        return total_deleted
