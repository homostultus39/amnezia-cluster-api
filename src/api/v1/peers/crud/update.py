from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import UpdatePeerRequest, UpdatePeerResponse
from src.services.management.protocol_factory import create_protocol_service

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
    """
    Update peer configuration by recreating it with a new application type.

    This endpoint removes the peer from the current configuration and creates a new one
    with the specified app_type, preserving the allocated IP address.

    Args:
        public_key: The public key of the peer to update (in URL path)
        payload: UpdatePeerRequest containing:
            - app_type: New application type (amnezia_vpn or amnezia_wg)

    Returns:
        UpdatePeerResponse with old and new peer keys and configuration

    Raises:
        HTTPException 404: Peer not found
        HTTPException 400: Invalid app_type
        HTTPException 500: Protocol service error

    Example:
        Request:
            PATCH /peers/PUBLIC_KEY_B64
            {
                "app_type": "amnezia_wg"
            }

        Response:
            {
                "old_public_key": "OLD_KEY_B64",
                "new_public_key": "NEW_KEY_B64",
                "allocated_ip": "10.8.1.5/32",
                "app_type": "amnezia_wg",
                "protocol": "amneziawg2",
                "config": "[wireguard-config-text]",
                "created_at": "2026-02-10T12:00:00Z"
            }
    """
    try:
        service = create_protocol_service("amneziawg2")
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
            detail="Failed to update peer configuration",
        )
