from fastapi import APIRouter, HTTPException, status

from src.api.v1.server.logger import logger
from src.api.v1.server.schemas import (
    ServerStatusResponse,
    ServerTrafficResponse,
    RestartServerResponse,
)
from src.services.host_service import HostService
from src.services.peers_service import get_peers_service
from src.services.management.protocol_factory import get_available_protocols
from src.management.settings import get_settings

router = APIRouter(prefix="/server", tags=["Server"])

settings = get_settings()

try:
    host_service = HostService()
except Exception as exc:
    import sys
    from src.management.logger import configure_logger
    logger = configure_logger("ServerRouter", "red")
    logger.critical(f"Failed to initialize HostService: {exc}")
    sys.exit(1)

peers_service = get_peers_service()


@router.get("/status", response_model=ServerStatusResponse)
async def get_server_status() -> ServerStatusResponse:
    """
    Get the current status of the Amnezia server.
    """
    try:
        container_name = settings.amnezia_container_name
        is_running = await host_service.is_container_running(container_name)

        if not is_running:
            logger.warning(f"Container {container_name} is not running")
            return ServerStatusResponse(
                status="stopped",
                container_name=container_name,
                port=None,
                interface="",
                protocol=settings.default_protocol,
            )

        port = await host_service.get_container_port(container_name, "udp")

        logger.info(f"Server status retrieved: {container_name} is running on port {port}")

        return ServerStatusResponse(
            status="running",
            container_name=container_name,
            port=port,
            interface=settings.amnezia_interface,
            protocol=settings.default_protocol,
        )

    except Exception as exc:
        logger.error(f"Failed to get server status: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get server status: {str(exc)}",
        )


@router.get("/traffic", response_model=ServerTrafficResponse)
async def get_server_traffic() -> ServerTrafficResponse:
    """
    Get total traffic statistics for the server.
    """
    try:
        protocols = get_available_protocols()
        if not protocols:
            raise ValueError("No enabled protocols configured")

        traffic_data = await peers_service.get_total_traffic(protocols[0])

        logger.info(
            f"Traffic retrieved: RX={traffic_data['total_rx_bytes']} "
            f"TX={traffic_data['total_tx_bytes']} "
            f"Peers={traffic_data['total_peers']} "
            f"Online={traffic_data['online_peers']}"
        )

        return ServerTrafficResponse(**traffic_data)

    except Exception as exc:
        logger.error(f"Failed to get server traffic: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get server traffic: {str(exc)}",
        )


@router.post("/restart", response_model=RestartServerResponse)
async def restart_server() -> RestartServerResponse:
    """
    Restart the Amnezia server container.
    """
    try:
        container_name = settings.amnezia_container_name

        is_running = await host_service.is_container_running(container_name)

        if not is_running:
            logger.warning(f"Container {container_name} is not running, cannot restart")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container {container_name} is not running",
            )

        await host_service.run_command(f"docker restart {container_name}", timeout=10000)

        logger.info(f"Server {container_name} restarted successfully")

        return RestartServerResponse(
            status="restarted",
            message=f"Server {container_name} has been restarted successfully",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to restart server: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart server: {str(exc)}",
        )
