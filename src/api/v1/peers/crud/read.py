from typing import Optional, List

from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import ListPeerResponse, AppType
from src.services.management.protocol_factory import create_protocol_service

router = APIRouter()


@router.get(
    "/",
    response_model=List[ListPeerResponse],
    status_code=status.HTTP_200_OK,
)
async def list_peers(
    app_type: Optional[str] = None,
    online_only: Optional[bool] = False,
) -> List[ListPeerResponse]:
    """
    List all peers with their current status and traffic statistics.

    Args:
        app_type: Optional filter by application type (amnezia_vpn or amnezia_wg)
        online_only: If true, return only online peers. Defaults to false

    Returns:
        List of ListPeerResponse objects with peer information

    Raises:
        HTTPException 400: Invalid app_type filter
        HTTPException 500: Protocol service error

    Example:
        Request:
            GET /peers/
            GET /peers/?app_type=amnezia_vpn&online_only=true

        Response:
            [
                {
                    "public_key": "PUBLIC_KEY_B64",
                    "allocated_ip": "10.8.1.5/32",
                    "app_type": "amnezia_vpn",
                    "protocol": "amneziawg2",
                    "endpoint": "vpn.example.com:51820",
                    "is_online": true,
                    "last_handshake": "2026-02-10T12:00:00Z",
                    "rx_bytes": 1024000,
                    "tx_bytes": 2048000,
                    "created_at": "2026-02-10T10:00:00Z"
                }
            ]
    """
    try:
        if app_type:
            try:
                AppType(app_type)
            except ValueError:
                raise ValueError(f"Invalid app_type: {app_type}")

        service = create_protocol_service("amneziawg2")
        peers_data = await service.get_peers()

        peers = []
        for peer in peers_data:
            if app_type and peer.get("app_type") != app_type:
                continue

            if online_only and not peer.get("online"):
                continue

            peers.append(
                ListPeerResponse(
                    public_key=peer["public_key"],
                    allocated_ip=peer["allowed_ips"][0] if peer.get("allowed_ips") else "N/A",
                    protocol="amneziawg2",
                    endpoint=peer.get("endpoint") or "N/A",
                    online=peer.get("online", False),
                    last_handshake=peer.get("last_handshake"),
                    rx_bytes=peer.get("rx_bytes", 0),
                    tx_bytes=peer.get("tx_bytes", 0),
                )
            )

        logger.info(f"Listed {len(peers)} peers")
        return peers

    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Failed to list peers: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve peers",
        )
