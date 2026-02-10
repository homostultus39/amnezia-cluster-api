from typing import Optional, List

from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import ListPeerResponse, AppType
from src.services.management.protocol_factory import create_protocol_service
from src.api.v1.peers.utils import resolve_active_protocol_name

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
    """List all peers with their status and traffic statistics. Optional filters by app_type and online status."""
    try:
        if app_type:
            try:
                AppType(app_type)
            except ValueError:
                raise ValueError(f"Invalid app_type: {app_type}")

        protocol_name = resolve_active_protocol_name()
        service = create_protocol_service(protocol_name)
        peers_data = await service.get_peers()

        peers = []
        for peer in peers_data:
            if app_type and peer.get("app_type") and peer.get("app_type") != app_type:
                continue

            if online_only and not peer.get("online"):
                continue

            peers.append(
                ListPeerResponse(
                    public_key=peer["public_key"],
                    allocated_ip=peer["allowed_ips"][0] if peer.get("allowed_ips") else "N/A",
                    protocol=protocol_name,
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
            detail=str(exc),
        )
