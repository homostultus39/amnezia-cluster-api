from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.crud.logger import logger
from src.api.v1.clients.schemas import CreateClientRequest, CreateClientResponse
from src.api.v1.deps.exceptions.clients import (
    config_generation_failed,
    invalid_app_type,
    ip_allocation_failed,
    protocol_not_supported,
    storage_error,
)
from src.database.connection import SessionDep
from src.services.clients_service import ClientsService

router = APIRouter()
clients_service = ClientsService()


@router.post("/", response_model=CreateClientResponse)
async def create_client(
    payload: CreateClientRequest,
    session: SessionDep = Depends(),
) -> CreateClientResponse:
    """
    Create a new client and generate a configuration for the requested app type.
    Configuration is stored in MinIO under the user UUID and returned with a presigned URL.
    """
    try:
        result = await clients_service.create_client(
            session=session,
            username=payload.username,
            protocol=payload.protocol,
            app_type=payload.app_type.value,
            expires_at=payload.expires_at,
        )
        logger.info(f"Client {payload.username} created successfully")
        return CreateClientResponse(**result)
    except ValueError as exc:
        error_msg = str(exc).lower()
        logger.error(f"Validation error during client creation for {payload.username}: {error_msg}")
        if "protocol" in error_msg:
            raise protocol_not_supported(payload.protocol)
        if "app_type" in error_msg:
            raise invalid_app_type(payload.app_type.value)
        if "ip" in error_msg:
            raise ip_allocation_failed(str(exc))
        raise config_generation_failed(str(exc))
    except SQLAlchemyError as exc:
        logger.error(f"Database error during client creation for {payload.username}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        error_msg = str(exc).lower()
        logger.error(f"Unexpected error during client creation for {payload.username}: {error_msg}")
        if "minio" in error_msg or "storage" in error_msg:
            raise storage_error("upload", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client: {str(exc)}",
        )


