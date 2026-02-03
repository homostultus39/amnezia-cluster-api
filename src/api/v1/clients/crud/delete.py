from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.crud.logger import logger
from src.api.v1.clients.schemas import DeleteClientResponse
from src.api.v1.deps.exceptions.clients import peer_not_found, protocol_not_supported
from src.database.connection import SessionDep
from src.services.clients_service import ClientsService

router = APIRouter()
clients_service = ClientsService()


@router.delete("/{peer_id}", response_model=DeleteClientResponse)
async def delete_client(
    session: SessionDep,
    peer_id: UUID,
    protocol: str = Query(default="amneziawg", min_length=1, max_length=100),
) -> DeleteClientResponse:
    """
    Delete a client peer from Amnezia and remove its configuration from MinIO.
    """
    try:
        deleted = await clients_service.delete_client(session, peer_id, protocol)
        if not deleted:
            logger.error(f"Peer {peer_id} not found for deletion")
            raise peer_not_found(str(peer_id))
        logger.info(f"Peer {peer_id} deleted successfully")
        return DeleteClientResponse(status="deleted")
    except ValueError as exc:
        logger.error(f"Unsupported protocol {protocol} during deletion of {peer_id}: {exc}")
        raise protocol_not_supported(protocol)
    except SQLAlchemyError as exc:
        logger.error(f"Database error during deletion of {peer_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during deletion of {peer_id}: {exc}")
        if "minio" in str(exc).lower() or "storage" in str(exc).lower():
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete client: {str(exc)}",
        )


