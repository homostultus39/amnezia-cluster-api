from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.schemas import ClientResponse
from src.api.v1.deps.exceptions.clients import protocol_not_supported
from src.database.connection import SessionDep
from src.minio.client import MinioClient
from src.services.clients_service import ClientsService

router = APIRouter()
clients_service = ClientsService()
minio_client = MinioClient()


@router.get("/", response_model=list[ClientResponse])
async def get_clients(
    session: SessionDep = Depends(),
    protocol: str | None = Query(default=None, min_length=1, max_length=100),
) -> list[ClientResponse]:
    """
    Retrieve all clients or filter by protocol.
    Adds a presigned URL for the stored configuration in MinIO.
    """
    try:
        clients = await clients_service.get_clients(session, protocol)

        for client in clients:
            client_id = client.get("id")
            for peer in client.get("peers", []):
                if not client_id:
                    peer["config_url"] = None
                    continue

                object_name = f"configs/{peer['protocol']}/{client_id}"
                try:
                    peer["config_url"] = await minio_client.presigned_get_url(object_name)
                except Exception:
                    peer["config_url"] = None

        return [ClientResponse(**client) for client in clients]

    except HTTPException:
        raise
    except ValueError:
        if protocol:
            raise protocol_not_supported(protocol)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request parameters",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clients: {str(exc)}",
        )


