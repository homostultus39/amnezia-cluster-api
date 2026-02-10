from functools import lru_cache

import httpx
from datetime import datetime, timezone

from src.management.logger import configure_logger
from src.management.settings import get_settings
from src.services.management.protocol_factory import (
    create_protocol_service,
    get_available_protocols,
)


logger = configure_logger("PeersService", "cyan")


class PeersService:
    def __init__(self):
        self.settings = get_settings()

    def _get_service(self, protocol: str):
        try:
            return create_protocol_service(protocol)
        except ValueError as exc:
            logger.error(str(exc))
            raise

    async def create_peer(
        self,
        protocol: str,
        app_type: str,
        allocated_ip: str | None = None,
    ) -> dict:
        service = self._get_service(protocol)
        return await service.create_peer(app_type=app_type, allocated_ip=allocated_ip)

    async def delete_peer(self, protocol: str, public_key: str) -> bool:
        service = self._get_service(protocol)
        return await service.delete_peer(public_key=public_key)

    async def get_peers(self, protocol: str) -> list[dict]:
        service = self._get_service(protocol)
        return await service.get_peers()

    async def get_peer_status(self, protocol: str, public_key: str) -> dict:
        peer = await self._get_peer(protocol, public_key)
        return {
            "public_key": peer["public_key"],
            "endpoint": peer.get("endpoint"),
            "last_handshake": peer.get("last_handshake"),
            "online": peer.get("online", False),
        }

    async def get_peers_status(
        self,
        protocol: str,
        online_only: bool | None = None,
    ) -> list[dict]:
        peers = await self.get_peers(protocol)
        if online_only is True:
            peers = [peer for peer in peers if peer.get("online", False)]
        if online_only is False:
            peers = [peer for peer in peers if not peer.get("online", False)]
        return [
            {
                "public_key": peer["public_key"],
                "endpoint": peer.get("endpoint"),
                "last_handshake": peer.get("last_handshake"),
                "online": peer.get("online", False),
            }
            for peer in peers
        ]

    async def get_peer_traffic(self, protocol: str, public_key: str) -> dict:
        peer = await self._get_peer(protocol, public_key)
        return self._to_peer_traffic(peer)

    async def get_all_peers_traffic(self, protocol: str) -> dict[str, dict]:
        peers = await self.get_peers(protocol)
        return {
            peer["public_key"]: self._to_peer_traffic(peer)
            for peer in peers
        }

    async def get_total_traffic(self, protocol: str) -> dict[str, int]:
        peers = await self.get_peers(protocol)
        return self._build_total_traffic(peers)

    async def get_status_snapshot(self, protocol: str) -> dict:
        peers = await self.get_peers(protocol)
        return {
            "protocol": protocol,
            "peers": peers,
            "server_traffic": self._build_total_traffic(peers),
        }

    async def sync_peers_status(
        self,
        central_api_url: str,
        api_key: str,
        protocols: list[str] | None = None,
    ) -> int:
        target_protocols = protocols or get_available_protocols()
        payloads = []

        for protocol in target_protocols:
            snapshot = await self.get_status_snapshot(protocol)
            snapshot["sync_timestamp"] = datetime.now(timezone.utc).isoformat()
            payloads.append(snapshot)

        if not payloads:
            logger.debug("No protocols to sync")
            return 0

        headers = {"X-API-Key": api_key}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for payload in payloads:
                response = await client.post(
                    f"{central_api_url}/clusters/{self.settings.cluster_id}/peers/status",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

        logger.debug(f"Synced peer status for {len(payloads)} protocol(s)")
        return len(payloads)

    async def _get_peer(self, protocol: str, public_key: str) -> dict:
        peers = await self.get_peers(protocol)
        for peer in peers:
            if peer.get("public_key") == public_key:
                return peer
        raise ValueError(f"Peer {public_key} not found for protocol {protocol}")

    def _to_peer_traffic(self, peer: dict) -> dict:
        return {
            "public_key": peer["public_key"],
            "endpoint": peer.get("endpoint"),
            "allowed_ips": peer.get("allowed_ips", []),
            "last_handshake": peer.get("last_handshake"),
            "rx_bytes": int(peer.get("rx_bytes", 0)),
            "tx_bytes": int(peer.get("tx_bytes", 0)),
            "online": bool(peer.get("online", False)),
            "persistent_keepalive": int(peer.get("persistent_keepalive", 0)),
        }

    def _build_total_traffic(self, peers: list[dict]) -> dict[str, int]:
        total_rx = sum(int(peer.get("rx_bytes", 0)) for peer in peers)
        total_tx = sum(int(peer.get("tx_bytes", 0)) for peer in peers)
        return {
            "total_rx_bytes": total_rx,
            "total_tx_bytes": total_tx,
            "total_peers": len(peers),
            "online_peers": sum(1 for peer in peers if peer.get("online", False)),
        }

@lru_cache
def get_peers_service() -> PeersService:
    return PeersService()
