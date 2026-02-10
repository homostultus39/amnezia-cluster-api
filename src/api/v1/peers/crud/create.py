from fastapi import APIRouter, HTTPException, status

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import CreatePeerRequest, CreatePeerResponse
from src.management.constants import AppType
from src.services.management.protocol_factory import create_protocol_service

router = APIRouter()


@router.post(
    "/",
    response_model=CreatePeerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_peer(payload: CreatePeerRequest) -> CreatePeerResponse:
    """
    Create a new peer with the specified application type.

    Args:
        payload: CreatePeerRequest containing:
            - app_type: Application type (amnezia_vpn or amnezia_wg)
            - allocated_ip: Optional IP address. If not provided, automatically allocated from subnet

    Returns:
        CreatePeerResponse with peer configuration details

    Raises:
        HTTPException 400: Invalid app_type or IP allocation failure
        HTTPException 500: Protocol service error or configuration generation failure

    Example:
        Request:
            POST /peers/
            {
                "app_type": "amnezia_vpn",
                "allocated_ip": "10.8.1.5"
            }

        Response:
            {
                "public_key": "PUBLIC_KEY_B64",
                "private_key": "PRIVATE_KEY_B64",
                "allocated_ip": "10.8.1.5/32",
                "endpoint": "vpn.example.com:51820",
                "app_type": "amnezia_vpn",
                "protocol": "amneziawg2",
                "config": "vpn://[base64-encoded-json]",
                "created_at": "2026-02-10T12:00:00Z"
            }
    """
    try:
        service = create_protocol_service("amneziawg2")

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
            detail="Failed to create peer configuration",
        )
