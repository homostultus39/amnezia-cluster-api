from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import UpdatePeerRequest, UpdatePeerResponse
from src.services.management.protocol_factory import create_protocol_service
from src.api.v1.peers.utils import resolve_active_protocol_name


router = APIRouter()


@router.patch(
    "/{public_key}",
    response_model=UpdatePeerResponse,
    status_code=status.HTTP_200_OK,
)
async def update_peer(
    public_key: str,
    payload: UpdatePeerRequest,
) -> UpdatePeerResponse:
    """Recreate a peer with a new application type while preserving its allocated IP address."""
    try:
        protocol_name = resolve_active_protocol_name()
        service = create_protocol_service(protocol_name)
        peers_data = await service.get_peers()

        old_peer = None
        for peer in peers_data:
            if peer["public_key"] == public_key:
                old_peer = peer
                break

        if not old_peer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Peer {public_key[:16]}... not found",
            )

        old_allocated_ip = (
            old_peer["allowed_ips"][0]
            if old_peer.get("allowed_ips")
            else None
        )

        await service.delete_peer(public_key)

        result = await service.create_peer(
            app_type=payload.app_type.value,
            allocated_ip=old_allocated_ip,
        )

        logger.info(
            f"Peer {public_key[:16]}... updated: "
            f"{result['app_type']} ip={result['allocated_ip']}"
        )

        return UpdatePeerResponse(
            old_public_key=public_key,
            new_public_key=result["public_key"],
            allocated_ip=result["allocated_ip"],
            app_type=result["app_type"],
            protocol=result["protocol"],
            config=result["config"],
        )

    except HTTPException:
        raise
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Failed to update peer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
