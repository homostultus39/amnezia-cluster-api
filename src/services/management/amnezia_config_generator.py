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
        server_port: int,
        primary_dns: str,
        secondary_dns: str,
        container_name: str,
        description: str = "",
        subnet_address: str = "10.8.1.0",
    ) -> str:
        config_dict = self._build_config_dict(
            client_private_key=client_private_key,
            client_public_key=client_public_key,
            server_public_key=server_public_key,
            psk=psk,
            client_ip=client_ip,
            awg_params=awg_params,
            server_endpoint=server_endpoint,
            server_port=server_port,
            primary_dns=primary_dns,
            secondary_dns=secondary_dns,
            container_name=container_name,
            description=description,
            subnet_address=subnet_address,
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
        server_port: int,
        primary_dns: str,
        secondary_dns: str,
        container_name: str,
        description: str = "",
        subnet_address: str = "10.8.1.0",
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
            "port": str(server_port),
            "protocol_version": "2",
            "subnet_address": subnet_address,
            "transport_proto": "udp",
        }

        config = {
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

        if description:
            config["description"] = description

        return config

    def _create_vpn_link(self, data: dict) -> str:
        json_str = json.dumps(data, indent=4).encode("utf-8")
        compressed_data = zlib.compress(json_str)

        original_data_len = len(json_str)
        header = original_data_len.to_bytes(4, byteorder="big")

        encoded = base64.urlsafe_b64encode(header + compressed_data).decode("utf-8").rstrip("=")
        return f"vpn://{encoded}"

    def decode_vpn_link(self, vpn_link: str) -> dict:
        encoded_data = vpn_link.replace("vpn://", "")
        padding = 4 - (len(encoded_data) % 4)
        if padding != 4:
            encoded_data += "=" * padding

        compressed_data = base64.urlsafe_b64decode(encoded_data)

        original_data_len = int.from_bytes(compressed_data[:4], byteorder="big")
        decompressed_data = zlib.decompress(compressed_data[4:])

        if len(decompressed_data) != original_data_len:
            raise ValueError(
                f"Invalid length: expected {original_data_len}, got {len(decompressed_data)}"
            )

        return json.loads(decompressed_data)

