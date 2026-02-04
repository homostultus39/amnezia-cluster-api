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
        mtu: str = "1376",
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
            mtu=mtu,
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
        mtu: str = "1376",
    ) -> dict:
        client_ip_plain = client_ip.split("/", 1)[0]

        wireguard_config = self._build_wireguard_config(
            client_ip=client_ip_plain,
            client_private_key=client_private_key,
            server_public_key=server_public_key,
            psk=psk,
            server_endpoint=server_endpoint,
            server_port=server_port,
            awg_params=awg_params,
        )

        last_config = {
            **awg_params,
            "allowed_ips": ["0.0.0.0/0", "::/0"],
            "clientId": client_public_key,
            "client_ip": client_ip_plain,
            "client_priv_key": client_private_key,
            "client_pub_key": client_public_key,
            "config": wireguard_config,
            "hostName": server_endpoint,
            "mtu": mtu,
            "persistent_keep_alive": "25",
            "port": server_port,
            "psk_key": psk,
            "server_pub_key": server_public_key,
        }

        awg_config = {
            **awg_params,
            "last_config": json.dumps(last_config, indent=4),
            "port": str(server_port),
            "protocol_version": "2",
            "subnet_address": subnet_address,
            "transport_proto": "udp",
        }

        config = {
            "containers": [
                {
                    "awg": awg_config,
                    "container": container_name,
                }
            ],
            "defaultContainer": container_name,
        }

        if description:
            config["description"] = description

        config["dns1"] = primary_dns
        config["dns2"] = secondary_dns
        config["hostName"] = server_endpoint

        return config

    def _create_vpn_link(self, data: dict) -> str:
        json_str = json.dumps(data, indent=4).encode("utf-8")
        compressed_data = zlib.compress(json_str, level=8)

        original_data_len = len(json_str)
        header = original_data_len.to_bytes(4, byteorder="big")

        encoded = base64.b64encode(header + compressed_data).decode("utf-8").rstrip("=")
        return f"vpn://{encoded}"

    def decode_vpn_link(self, vpn_link: str) -> dict:
        encoded_data = vpn_link.replace("vpn://", "")
        padding = 4 - (len(encoded_data) % 4)
        if padding != 4:
            encoded_data += "=" * padding

        compressed_data = base64.b64decode(encoded_data)

        original_data_len = int.from_bytes(compressed_data[:4], byteorder="big")
        decompressed_data = zlib.decompress(compressed_data[4:])

        if len(decompressed_data) != original_data_len:
            raise ValueError(
                f"Invalid length: expected {original_data_len}, got {len(decompressed_data)}"
            )

        return json.loads(decompressed_data)

    def _build_wireguard_config(
        self,
        *,
        client_ip: str,
        client_private_key: str,
        server_public_key: str,
        psk: str,
        server_endpoint: str,
        server_port: int,
        awg_params: dict,
    ) -> str:
        return (
            "[Interface]\n"
            f"Address = {client_ip}/32\n"
            "DNS = $PRIMARY_DNS, $SECONDARY_DNS\n"
            f"PrivateKey = {client_private_key}\n"
            f"Jc = {awg_params.get('Jc', '')}\n"
            f"Jmin = {awg_params.get('Jmin', '')}\n"
            f"Jmax = {awg_params.get('Jmax', '')}\n"
            f"S1 = {awg_params.get('S1', '')}\n"
            f"S2 = {awg_params.get('S2', '')}\n"
            f"S3 = {awg_params.get('S3', '')}\n"
            f"S4 = {awg_params.get('S4', '')}\n"
            f"H1 = {awg_params.get('H1', '')}\n"
            f"H2 = {awg_params.get('H2', '')}\n"
            f"H3 = {awg_params.get('H3', '')}\n"
            f"H4 = {awg_params.get('H4', '')}\n"
            f"I1 = {awg_params.get('I1', '')}\n"
            f"I2 = {awg_params.get('I2', '')}\n"
            f"I3 = {awg_params.get('I3', '')}\n"
            f"I4 = {awg_params.get('I4', '')}\n"
            f"I5 = {awg_params.get('I5', '')}\n"
            "\n"
            "[Peer]\n"
            f"PublicKey = {server_public_key}\n"
            f"PresharedKey = {psk}\n"
            "AllowedIPs = 0.0.0.0/0, ::/0\n"
            f"Endpoint = {server_endpoint}:{server_port}\n"
            "PersistentKeepalive = 25\n"
        )

