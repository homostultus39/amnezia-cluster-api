from fastapi import APIRouter, HTTPException, status

from src.api.v1.server.logger import logger
from src.api.v1.server.schemas import (
    ServerStatusResponse,
    ServerTrafficResponse,
    RestartServerResponse,
)
from src.services.host_service import HostService
from src.services.management.protocol_factory import (
    create_protocol_service,
    get_active_protocol_name,
    get_protocol_config,
)

router = APIRouter()

try:
    host_service = HostService()
except Exception as exc:
    import sys
    from src.management.logger import configure_logger
    logger = configure_logger("ServerRouter", "red")
    logger.critical(f"Failed to initialize HostService: {exc}")
    sys.exit(1)


@router.get(
    "/status",
    response_model=ServerStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_server_status() -> ServerStatusResponse:
    """Retrieve the current status of the Amnezia server including container state, port, and interface."""
    try:
        protocol_name = get_active_protocol_name()
        protocol_config = get_protocol_config(protocol_name)
        container_name = protocol_config["container_name"]
        interface = protocol_config["interface"]

        is_running = await host_service.is_container_running(container_name)

        if not is_running:
            logger.warning(f"Container {container_name} is not running")
            return ServerStatusResponse(
                status="stopped",
                container_name=container_name,
                port=None,
                interface=interface,
                protocol=protocol_name,
            )

        port = await host_service.get_container_port(container_name, "udp")

        logger.info(f"Server status: {container_name} running on port {port}")

        return ServerStatusResponse(
            status="running",
            container_name=container_name,
            port=port,
            interface=interface,
            protocol=protocol_name,
        )

    except Exception as exc:
        logger.error(f"Failed to get server status: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get(
    "/traffic",
    response_model=ServerTrafficResponse,
    status_code=status.HTTP_200_OK,
)
async def get_server_traffic() -> ServerTrafficResponse:
    """Retrieve aggregated traffic statistics for all peers including bytes and connection metrics."""
    try:
        protocol_name = get_active_protocol_name()
        service = create_protocol_service(protocol_name)
        peers_data = await service.get_peers()

        total_rx_bytes = sum(peer.get("rx_bytes", 0) for peer in peers_data)
        total_tx_bytes = sum(peer.get("tx_bytes", 0) for peer in peers_data)
        total_peers = len(peers_data)
        online_peers = sum(1 for peer in peers_data if peer.get("online", False))

        logger.info(
            f"Traffic retrieved: RX={total_rx_bytes} TX={total_tx_bytes} "
            f"Peers={total_peers} Online={online_peers}"
        )

        return ServerTrafficResponse(
            total_rx_bytes=total_rx_bytes,
            total_tx_bytes=total_tx_bytes,
            total_peers=total_peers,
            online_peers=online_peers,
        )

    except Exception as exc:
        logger.error(f"Failed to get server traffic: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/restart",
    response_model=RestartServerResponse,
    status_code=status.HTTP_200_OK,
)
async def restart_server() -> RestartServerResponse:
    """Restart the Amnezia server container to reload configuration and reset connections."""
    try:
        protocol_name = get_active_protocol_name()
        protocol_config = get_protocol_config(protocol_name)
        container_name = protocol_config["container_name"]

        is_running = await host_service.is_container_running(container_name)

        if not is_running:
            logger.warning(f"Container {container_name} is not running")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container {container_name} is not running",
            )

        await host_service.restart_container(container_name, timeout=10)

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
            detail=str(exc),
        )
