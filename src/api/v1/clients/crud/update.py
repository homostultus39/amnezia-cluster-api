from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.logger import logger
from src.api.v1.clients.schemas import UpdateClientRequest, UpdateClientResponse
from src.api.v1.deps.exceptions.clients import peer_not_found
from src.database.connection import SessionDep
from src.database.models import PeerModel

router = APIRouter()


@router.patch("/{peer_id}", response_model=UpdateClientResponse)
async def update_client(
    session: SessionDep,
    peer_id: UUID,
    payload: UpdateClientRequest,
) -> UpdateClientResponse:
    """
    Update client peer metadata such as expiration time.
    """
    try:
        result = await session.execute(
            select(PeerModel).where(PeerModel.id == peer_id)
        )
        peer = result.scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )

    if not peer:
        logger.error(f"Peer {peer_id} not found for update")
        raise peer_not_found(str(peer_id))

    try:
        if payload.expires_at is not None:
            peer.expires_at = payload.expires_at

        await session.commit()
        logger.info(f"Peer {peer_id} updated successfully")
        return UpdateClientResponse(status="updated")
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.error(f"Database error during peer {peer_id} update: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during peer {peer_id} update: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update peer: {str(exc)}",
        )


