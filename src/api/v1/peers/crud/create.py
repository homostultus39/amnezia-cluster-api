from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import CreatePeerRequest, CreatePeerResponse
from src.services.management.protocol_factory import create_protocol_service
from src.api.v1.peers.utils import resolve_active_protocol_name

router = APIRouter()


@router.post(
    "/",
    response_model=CreatePeerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_peer(payload: CreatePeerRequest) -> CreatePeerResponse:
    """Create a new peer with the specified application type and optional IP allocation."""
    try:
        protocol_name = resolve_active_protocol_name()
        service = create_protocol_service(protocol_name)

        result = await service.create_peer(
            app_type=payload.app_type.value,
            allocated_ip=payload.allocated_ip,
        )

        logger.info(
            f"Peer created: {result['public_key'][:16]}... "
            f"app_type={result['app_type']} ip={result['allocated_ip']}"
        )

        return CreatePeerResponse(
            public_key=result["public_key"],
            private_key=result["private_key"],
            allocated_ip=result["allocated_ip"],
            endpoint=result["endpoint"],
            app_type=result["app_type"],
            protocol=result["protocol"],
            config=result["config"],
        )

    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Failed to create peer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
