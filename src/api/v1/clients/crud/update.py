from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.schemas import UpdateClientRequest, UpdateClientResponse
from src.api.v1.deps.exceptions.clients import peer_not_found
from src.database.connection import SessionDep
from src.database.models import PeerModel

router = APIRouter()


@router.patch("/{peer_id}", response_model=UpdateClientResponse)
async def update_client(
    peer_id: UUID,
    payload: UpdateClientRequest,
    session: SessionDep = Depends(),
) -> UpdateClientResponse:
    """
    Update client peer metadata such as display name or expiration time.
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
        raise peer_not_found(str(peer_id))

    try:
        if payload.name is not None:
            peer.name = payload.name
        if payload.expires_at is not None:
            peer.expires_at = payload.expires_at

        await session.commit()
        return UpdateClientResponse(status="updated")
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )


