from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import DeletePeerResponse
from src.services.management.protocol_factory import create_protocol_service
from src.api.v1.peers.utils import resolve_active_protocol_name

router = APIRouter()


@router.delete(
    "/{public_key}",
    response_model=DeletePeerResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_peer(public_key: str) -> DeletePeerResponse:
    """Delete a peer and remove it from the protocol configuration."""
    try:
        protocol_name = resolve_active_protocol_name()
        service = create_protocol_service(protocol_name)
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
            detail=str(exc),
        )
