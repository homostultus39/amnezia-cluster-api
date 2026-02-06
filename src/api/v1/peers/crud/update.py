from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import UpdatePeerRequest, PeerResponse
from src.database.connection import SessionDep
from src.database.management.operations.peer import get_peer_by_id_with_client
from src.services.utils.config_storage import get_config_object_name
from src.minio.client import MinioClient
from src.services.peers_service import PeersService
from src.services.amnezia_service import AmneziaService

router = APIRouter()
peers_service = PeersService()
minio_client = MinioClient()
amnezia_service = AmneziaService()


@router.patch("/{peer_id}", response_model=PeerResponse)
async def update_peer(
    peer_id: UUID,
    session: SessionDep,
    payload: UpdatePeerRequest,
) -> PeerResponse:
    """
    Update a peer by removing the old configuration and creating a new one.
    """
    try:
        peer = await get_peer_by_id_with_client(session, peer_id)

        if not peer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Peer {peer_id} not found",
            )

        if not payload.app_type and not payload.protocol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided for update",
            )

        old_app_type = peer.app_type
        old_protocol = "amneziawg"
        client = peer.client

        await amnezia_service.remove_peer_from_config(peer.public_key)
        await amnezia_service.connection.sync_wg_config()

        await session.delete(peer)
        await session.flush()

        new_app_type = payload.app_type.value if payload.app_type else old_app_type
        new_protocol = payload.protocol if payload.protocol else old_protocol

        service = peers_service._get_service(new_protocol)
        new_peer_data = await service.create_peer(
            session=session,
            client=client,
            app_type=new_app_type,
        )

        new_peer = new_peer_data["peer"]
        wg_dump = await service.connection.get_wg_dump()
        peers_data = service._parse_wg_dump(wg_dump)

        await session.commit()

        object_name = get_config_object_name(new_protocol, client.id, new_app_type)
        config_url = await minio_client.presigned_get_url(object_name)

        wg_peer = peers_data.get(new_peer.public_key, {})

        logger.info(f"Peer {peer_id} updated successfully")

        return PeerResponse(
            id=str(new_peer.id),
            client_id=str(client.id),
            username=client.username,
            app_type=new_app_type,
            protocol=new_protocol,
            endpoint=wg_peer.get("endpoint") or new_peer.endpoint,
            public_key=new_peer.public_key,
            online=wg_peer.get("online", False),
            last_handshake=wg_peer.get("last_handshake"),
            url=config_url,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(f"Database error: {exc}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update peer: {str(exc)}",
        )
