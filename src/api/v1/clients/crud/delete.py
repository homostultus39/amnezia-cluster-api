from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.logger import logger
from src.api.v1.clients.schemas import DeleteClientResponse
from src.database.connection import SessionDep
from src.services.clients_service import ClientsService

router = APIRouter()
clients_service = ClientsService()


@router.delete("/{client_id}", response_model=DeleteClientResponse)
async def delete_client(
    session: SessionDep,
    client_id: UUID,
    protocol: str = Query(default="amneziawg", min_length=1, max_length=100),
) -> DeleteClientResponse:
    """
    Delete a client and all associated peers from Amnezia.
    """
    try:
        deleted = await clients_service.delete_client(session, client_id, protocol)
        if not deleted:
            logger.error(f"Client {client_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {client_id} not found",
            )
        logger.info(f"Client {client_id} deleted successfully")
        return DeleteClientResponse(status="deleted")
    except ValueError as exc:
        error_msg = str(exc).lower()
        logger.error(f"Error during client deletion: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except SQLAlchemyError as exc:
        logger.error(f"Database error during deletion of {client_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during deletion of {client_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete client: {str(exc)}",
        )


