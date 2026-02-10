from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import DeletePeerResponse
from src.services.management.protocol_factory import create_protocol_service

router = APIRouter()


@router.delete(
    "/{public_key}",
    response_model=DeletePeerResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_peer(public_key: str) -> DeletePeerResponse:
    """
    Delete a peer and remove it from the protocol configuration.

    Args:
        public_key: The public key of the peer to delete (in URL path)

    Returns:
        DeletePeerResponse confirming deletion

    Raises:
        HTTPException 404: Peer not found
        HTTPException 500: Protocol service error

    Example:
        Request:
            DELETE /peers/PUBLIC_KEY_B64

        Response:
            {
                "status": "deleted",
                "public_key": "PUBLIC_KEY_B64",
                "message": "Peer successfully removed from configuration"
            }
    """
    try:
        service = create_protocol_service("amneziawg2")
        deleted = await service.delete_peer(public_key)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Peer {public_key[:16]}... not found",
            )

        logger.info(f"Peer {public_key[:16]}... deleted")

        return DeletePeerResponse(
            status="deleted",
            public_key=public_key,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to delete peer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete peer",
        )
