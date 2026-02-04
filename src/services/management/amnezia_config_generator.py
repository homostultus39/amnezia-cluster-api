import base64
import json
import zlib


class AmneziaConfigGenerator:
    def generate_amnezia_vpn_config(
        self,
        *,
        client_private_key: str,
        client_public_key: str,
        server_public_key: str,
        psk: str,
        client_ip: str,
        awg_params: dict,
        server_endpoint: str,
        primary_dns: str,
        secondary_dns: str,
        container_name: str,
    ) -> str:
        config_dict = self._build_config_dict(
            client_private_key=client_private_key,
            client_public_key=client_public_key,
            server_public_key=server_public_key,
            psk=psk,
            client_ip=client_ip,
            awg_params=awg_params,
            server_endpoint=server_endpoint,
            primary_dns=primary_dns,
            secondary_dns=secondary_dns,
            container_name=container_name,
        )
        return self._create_vpn_link(config_dict)

    def _build_config_dict(
        self,
        *,
        client_private_key: str,
        client_public_key: str,
        server_public_key: str,
        psk: str,
        client_ip: str,
        awg_params: dict,
        server_endpoint: str,
        primary_dns: str,
        secondary_dns: str,
        container_name: str,
    ) -> dict:
        awg_config = {
            "client_priv_key": client_private_key,
            "client_pub_key": client_public_key,
            "server_pub_key": server_public_key,
            "psk_key": psk,
            "client_ip": client_ip,
            "allowed_ips": "0.0.0.0/0, ::/0",
            "persistent_keep_alive": "25",
            **awg_params,
        }

        return {
            "hostName": server_endpoint,
            "defaultContainer": container_name,
            "dns1": primary_dns,
            "dns2": secondary_dns,
            "containers": [
                {
                    "container": container_name,
                    "awg": awg_config,
                }
            ],
        }

    def _create_vpn_link(self, data: dict) -> str:
        json_str = json.dumps(data, separators=(",", ":"))
        compressed = zlib.compress(json_str.encode("utf-8"), level=8)
        encoded = base64.urlsafe_b64encode(compressed).decode("utf-8").rstrip("=")
        return f"vpn://{encoded}"

