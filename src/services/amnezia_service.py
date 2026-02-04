import re
import json
import zlib
import base64
import ipaddress
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.management.amnezia_connection import AmneziaConnection
from src.services.management.base_protocol_service import BaseProtocolService
from src.services.management.amnezia_config_generator import AmneziaConfigGenerator
from src.database.models import ClientModel, PeerModel, ProtocolModel, AppType
from src.management.settings import get_settings
from src.management.logger import configure_logger
from src.minio.client import MinioClient

settings = get_settings()
logger = configure_logger("AmneziaService", "green")


class AmneziaService(BaseProtocolService):
    AMNEZIAWG_CLIENT_TEMPLATE = (
        "[Interface]\n"
        "Address = {CLIENT_ADDRESS}/32\n"
        "DNS = {PRIMARY_DNS}, {SECONDARY_DNS}\n"
        "PrivateKey = {CLIENT_PRIVATE_KEY}\n"
        "Jc = {JC}\n"
        "Jmin = {JMIN}\n"
        "Jmax = {JMAX}\n"
        "S1 = {S1}\n"
        "S2 = {S2}\n"
        "H1 = {H1}\n"
        "H2 = {H2}\n"
        "H3 = {H3}\n"
        "H4 = {H4}\n\n"
        "[Peer]\n"
        "PublicKey = {SERVER_PUBLIC_KEY}\n"
        "PresharedKey = {PRESHARED_KEY}\n"
        "AllowedIPs = 0.0.0.0/0, ::/0\n"
        "{ENDPOINT_LINE}"
        "PersistentKeepalive = {KEEPALIVE}\n"
    )

    def __init__(self):
        self.connection = AmneziaConnection()
        self._protocol_name = "amneziawg"
        self.config_storage = MinioClient()
        self.config_generator = AmneziaConfigGenerator()

    @property
    def protocol_name(self) -> str:
        return self._protocol_name

    async def get_clients(self, session: AsyncSession) -> list[dict]:
        wg_dump = await self.connection.get_wg_dump()
        peers_data = self._parse_wg_dump(wg_dump)

        result = await session.execute(
            select(ClientModel).where(
                ClientModel.peers.any(PeerModel.protocol_id == await self._get_protocol_id(session))
            )
        )
        clients = result.scalars().all()

        client_list = []
        for client in clients:
            peers_list = []
            for peer in client.peers:
                wg_peer = peers_data.get(peer.public_key, {})
                peers_list.append({
                    "id": str(peer.id),
                    "public_key": peer.public_key,
                    "allowed_ips": peer.allowed_ips,
                    "endpoint": wg_peer.get("endpoint"),
                    "last_handshake": wg_peer.get("last_handshake"),
                    "traffic": {
                        "received": wg_peer.get("rx_bytes", 0),
                        "sent": wg_peer.get("tx_bytes", 0),
                    },
                    "online": wg_peer.get("online", False),
                    "expires_at": peer.expires_at.isoformat() if peer.expires_at else None,
                    "app_type": peer.app_type,
                    "protocol": self.protocol_name,
                })

            client_list.append({
                "id": str(client.id),
                "username": client.username,
                "peers": peers_list,
            })

        logger.info(f"Retrieved {len(client_list)} clients from AmneziaWG")
        return client_list

    def _parse_wg_dump(self, dump_output: str) -> dict:
        peers = {}
        lines = dump_output.strip().split("\n")

        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < 8:
                continue

            public_key = parts[0]
            endpoint = parts[2] if parts[2] != "(none)" else None
            allowed_ips = parts[3]
            last_handshake_ts = int(parts[4]) if parts[4] != "0" else None
            rx_bytes = int(parts[5])
            tx_bytes = int(parts[6])

            last_handshake = None
            if last_handshake_ts:
                last_handshake = datetime.fromtimestamp(last_handshake_ts)

            online = False
            if last_handshake:
                time_diff = (datetime.now() - last_handshake).total_seconds()
                online = time_diff < 180

            peers[public_key] = {
                "endpoint": endpoint,
                "allowed_ips": allowed_ips.split(","),
                "last_handshake": last_handshake,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "online": online,
            }

        return peers

    async def create_client(
        self,
        session: AsyncSession,
        username: str,
        app_type: str,
        expires_at: Optional[datetime] = None,
    ) -> dict:
        protocol_id = await self._get_protocol_id(session)

        result = await session.execute(
            select(ClientModel).where(ClientModel.username == username)
        )
        client = result.scalar_one_or_none()

        if not client:
            client = ClientModel(username=username)
            session.add(client)
            await session.flush()

        private_key = await self.connection.generate_private_key()
        public_key = await self.connection.generate_public_key(private_key)

        allocated_ip = await self._allocate_ip_address(session)

        server_port = await self._get_server_port()

        peer = PeerModel(
            client_id=client.id,
            allowed_ips=[allocated_ip],
            public_key=public_key,
            protocol_id=protocol_id,
            endpoint=f"{settings.server_public_host}:{server_port}",
            expires_at=expires_at,
            app_type=app_type,
        )
        session.add(peer)
        await session.flush()

        await self._add_peer_to_config(public_key, allocated_ip)
        await self.connection.sync_wg_config()

        config_payload = await self._generate_config_payload(
            app_type, private_key, public_key, allocated_ip, username, server_port
        )

        config_storage = await self._store_config(client.id, config_payload["config"])

        await session.commit()
        logger.info(f"Client created: {username} with IP {allocated_ip}")

        return {
            "id": str(peer.id),
            "public_key": public_key,
            "config": config_payload["config"],
            "config_type": config_payload["type"],
            "config_storage": config_storage,
            "protocol": self.protocol_name,
        }

    async def delete_client(self, session: AsyncSession, peer_id: UUID) -> bool:
        result = await session.execute(
            select(PeerModel).where(PeerModel.id == peer_id)
        )
        peer = result.scalar_one_or_none()

        if not peer:
            logger.warning(f"Peer {peer_id} not found in database for deletion")
            return False

        try:
            await self._remove_peer_from_config(peer.public_key)
            await self._delete_config(peer.client_id)
            await self.connection.sync_wg_config()

            await session.delete(peer)
            await session.commit()

            logger.info(f"Peer {peer_id} deleted successfully from AmneziaWG")
            return True
        except Exception as exc:
            logger.error(f"Failed to delete client {peer_id}: {exc}")
            await session.rollback()
            raise

    async def _get_protocol_id(self, session: AsyncSession) -> UUID:
        result = await session.execute(
            select(ProtocolModel).where(ProtocolModel.name == self.protocol_name)
        )
        protocol = result.scalar_one_or_none()

        if not protocol:
            protocol = ProtocolModel(name=self.protocol_name)
            session.add(protocol)
            await session.flush()

        return protocol.id

    async def _allocate_ip_address(self, session: AsyncSession) -> str:
        wg_config = await self.connection.read_wg_config()
        subnet_match = re.search(r"Address\s*=\s*([\d\.]+/\d+)", wg_config)

        if not subnet_match:
            raise ValueError("Could not find subnet in WireGuard config")

        network = ipaddress.IPv4Network(subnet_match.group(1), strict=False)

        result = await session.execute(
            select(PeerModel.allowed_ips).where(
                PeerModel.protocol_id == await self._get_protocol_id(session)
            )
        )
        used_ips = set()
        for row in result.scalars():
            for ip_str in row:
                ip_obj = ipaddress.IPv4Address(ip_str.split("/")[0])
                used_ips.add(ip_obj)

        for ip in network.hosts():
            if ip not in used_ips and ip != network.network_address + 1:
                return f"{ip}/32"

        raise ValueError("No available IP addresses in subnet")

    async def _add_peer_to_config(self, public_key: str, allowed_ip: str) -> None:
        wg_config = await self.connection.read_wg_config()

        psk = await self.connection.read_preshared_key()

        peer_section = f"\n[Peer]\nPublicKey = {public_key}\nPresharedKey = {psk}\nAllowedIPs = {allowed_ip}\n"
        updated_config = wg_config + peer_section

        await self.connection.write_wg_config(updated_config)

    async def _remove_peer_from_config(self, public_key: str) -> None:
        wg_config = await self.connection.read_wg_config()

        peer_pattern = rf"\[Peer\].*?PublicKey\s*=\s*{re.escape(public_key)}.*?(?=\n\[|$)"
        updated_config = re.sub(peer_pattern, "", wg_config, flags=re.DOTALL)

        await self.connection.write_wg_config(updated_config)

    async def _get_server_port(self) -> int:
        wg_config = await self.connection.read_wg_config()
        match = re.search(r'\[Interface\][\s\S]*?ListenPort\s*=\s*(\d+)', wg_config, re.IGNORECASE)

        if match:
            port = int(match.group(1))
            logger.debug(f"Detected server port: {port}")
            return port

        raise ValueError("ListenPort not found in WireGuard config")

    async def _generate_config_uri(
        self, private_key: str, public_key: str, allowed_ip: str, username: str, server_port: int
    ) -> str:
        server_public_key = await self.connection.read_server_public_key()
        psk = await self.connection.read_preshared_key()

        wg_config = await self.connection.read_wg_config()
        awg_params = self._extract_awg_params(wg_config)

        client_ip = (
            allowed_ip if allowed_ip.endswith("/32") else f"{allowed_ip.split('/')[0]}/32"
        )

        return self.config_generator.generate_amnezia_vpn_config(
            client_private_key=private_key,
            client_public_key=public_key,
            server_public_key=server_public_key,
            psk=psk,
            client_ip=client_ip,
            awg_params=awg_params,
            server_endpoint=settings.server_public_host,
            primary_dns="1.1.1.1",
            secondary_dns="1.0.0.1",
            container_name=settings.amnezia_container_name,
        )

    async def _generate_text_config(
        self, private_key: str, allowed_ip: str, server_port: int
    ) -> str:
        server_public_key = await self.connection.read_server_public_key()
        psk = await self.connection.read_preshared_key()

        wg_config = await self.connection.read_wg_config()
        awg_params = self._extract_awg_params(wg_config)

        endpoint_line = f"Endpoint = {settings.server_public_host}:{server_port}\n"

        text_config = self.AMNEZIAWG_CLIENT_TEMPLATE.format(
            CLIENT_ADDRESS=allowed_ip.split("/")[0],
            PRIMARY_DNS="1.1.1.1",
            SECONDARY_DNS="1.0.0.1",
            CLIENT_PRIVATE_KEY=private_key,
            JC=awg_params.get("Jc", ""),
            JMIN=awg_params.get("Jmin", ""),
            JMAX=awg_params.get("Jmax", ""),
            S1=awg_params.get("S1", ""),
            S2=awg_params.get("S2", ""),
            H1=awg_params.get("H1", ""),
            H2=awg_params.get("H2", ""),
            H3=awg_params.get("H3", ""),
            H4=awg_params.get("H4", ""),
            SERVER_PUBLIC_KEY=server_public_key,
            PRESHARED_KEY=psk,
            ENDPOINT_LINE=endpoint_line,
            KEEPALIVE="25",
        )

        logger.debug("Generated text config for AmneziaWG App")
        return text_config

    async def _generate_config_payload(
        self,
        app_type: str,
        private_key: str,
        public_key: str,
        allowed_ip: str,
        username: str,
        server_port: int,
    ) -> dict:
        if app_type == AppType.AMNEZIA_VPN.value:
            config_uri = await self._generate_config_uri(
                private_key, public_key, allowed_ip, username, server_port
            )
            return {
                "type": AppType.AMNEZIA_VPN.value,
                "config": config_uri,
            }

        if app_type == AppType.AMNEZIA_WG.value:
            text_config = await self._generate_text_config(
                private_key, allowed_ip, server_port
            )
            return {
                "type": AppType.AMNEZIA_WG.value,
                "config": text_config,
            }

        raise ValueError(f"Unsupported app_type: {app_type}")

    async def _store_config(self, client_id: UUID, config: str) -> dict:
        object_name = f"configs/{self.protocol_name}/{client_id}"

        await self.config_storage.upload_text(object_name, config, content_type="text/plain")
        url = await self.config_storage.presigned_get_url(object_name)

        return {
            "bucket": self.config_storage.bucket_name,
            "object": object_name,
            "url": url,
        }

    async def _delete_config(self, client_id: UUID) -> None:
        object_name = f"configs/{self.protocol_name}/{client_id}"

        try:
            await self.config_storage.delete_object(object_name)
        except Exception as exc:
            logger.warning(f"Failed to delete config from MinIO: {exc}")

    def _extract_awg_params(self, wg_config: str) -> dict:
        params = {}
        param_mapping = {
            "Jc": r"Jc\s*=\s*(\d+)",
            "Jmin": r"Jmin\s*=\s*(\d+)",
            "Jmax": r"Jmax\s*=\s*(\d+)",
            "S1": r"S1\s*=\s*(\d+)",
            "S2": r"S2\s*=\s*(\d+)",
            "S3": r"S3\s*=\s*(\d+)",
            "S4": r"S4\s*=\s*(\d+)",
            "H1": r"H1\s*=\s*(\d+)",
            "H2": r"H2\s*=\s*(\d+)",
            "H3": r"H3\s*=\s*(\d+)",
            "H4": r"H4\s*=\s*(\d+)",
            "I1": r"I1\s*=\s*(\d+)",
            "I2": r"I2\s*=\s*(\d+)",
            "I3": r"I3\s*=\s*(\d+)",
            "I4": r"I4\s*=\s*(\d+)",
            "I5": r"I5\s*=\s*(\d+)",
        }

        for key, pattern in param_mapping.items():
            match = re.search(pattern, wg_config)
            if match:
                params[key] = match.group(1)

        return params
