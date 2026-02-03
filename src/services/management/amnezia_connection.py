import asyncio
import docker
from typing import Optional
from src.management.settings import get_settings
from src.management.logger import configure_logger

settings = get_settings()
logger = configure_logger("AmneziaConnection", "blue")


class DockerError(Exception):
    pass


class AmneziaConnection:
    def __init__(self, container_name: Optional[str] = None):
        self.container_name = container_name or settings.amnezia_container_name
        self.interface = settings.amnezia_interface
        self.config_path = settings.amnezia_config_path
        try:
            self.docker_client = docker.from_env()
        except Exception as exc:
            logger.error(f"Failed to initialize Docker client: {exc}")
            raise DockerError(f"Docker client initialization failed: {exc}")

    async def run_command(self, cmd: str, check: bool = True) -> tuple[str, str]:
        logger.debug(f"Executing in {self.container_name}: {cmd}")

        try:
            container = await asyncio.to_thread(self.docker_client.containers.get, self.container_name)
            
            exec_result = await asyncio.to_thread(
                container.exec_run,
                cmd=["sh", "-c", cmd],
                stdout=True,
                stderr=True,
                demux=True
            )
            
            exit_code, (stdout, stderr) = exec_result
            stdout_decoded = stdout.decode().strip() if stdout else ""
            stderr_decoded = stderr.decode().strip() if stderr else ""

            if check and exit_code != 0:
                logger.error(
                    f"Command failed with code {exit_code}: {stderr_decoded}"
                )
                raise DockerError(
                    f"Command failed: {stderr_decoded or 'Unknown error'}"
                )

            return stdout_decoded, stderr_decoded

        except docker.errors.NotFound:
            logger.error(f"Container {self.container_name} not found")
            raise DockerError(f"Container {self.container_name} not found")
        except Exception as exc:
            logger.error(f"Docker API error: {exc}")
            raise DockerError(f"Docker API error: {exc}")

    async def read_file(self, path: str) -> str:
        stdout, _ = await self.run_command(f"cat {path}")
        return stdout

    async def write_file(self, path: str, content: str) -> None:
        escaped_content = content.replace("'", "'\\''")
        cmd = f"cat > {path} <<'EOF'\n{escaped_content}\nEOF"
        await self.run_command(cmd)
        logger.debug(f"File written: {path}")

    async def get_wg_dump(self) -> str:
        stdout, _ = await self.run_command(f"wg show {self.interface} dump")
        return stdout

    async def sync_wg_config(self) -> None:
        config_file = f"{self.config_path}/{self.interface}.conf"
        cmd = f"wg syncconf {self.interface} <(wg-quick strip {config_file})"
        await self.run_command(cmd)
        logger.info(f"WireGuard config synchronized for {self.interface}")

    async def read_wg_config(self) -> str:
        config_file = f"{self.config_path}/{self.interface}.conf"
        return await self.read_file(config_file)

    async def write_wg_config(self, content: str) -> None:
        config_file = f"{self.config_path}/{self.interface}.conf"
        await self.write_file(config_file, content)
        logger.info(f"WireGuard config written to {config_file}")

    async def generate_private_key(self) -> str:
        stdout, _ = await self.run_command("wg genkey")
        return stdout

    async def generate_public_key(self, private_key: str) -> str:
        cmd = f"echo '{private_key}' | wg pubkey"
        stdout, _ = await self.run_command(cmd)
        return stdout

    async def read_server_public_key(self) -> str:
        key_file = f"{self.config_path}/wireguard_server_public_key.key"
        return await self.read_file(key_file)

    async def read_preshared_key(self) -> str:
        key_file = f"{self.config_path}/wireguard_psk.key"
        return await self.read_file(key_file)
