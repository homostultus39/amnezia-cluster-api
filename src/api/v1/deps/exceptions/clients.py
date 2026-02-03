from fastapi import HTTPException, status


def client_not_found(username: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Client '{username}' not found",
    )


def peer_not_found(peer_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Peer with ID '{peer_id}' not found",
    )


def client_already_exists(username: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Client '{username}' already exists",
    )


def protocol_not_supported(protocol: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Protocol '{protocol}' is not supported",
    )


def invalid_app_type(app_type: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid app type: '{app_type}'",
    )


def config_generation_failed(reason: str = "Unknown error") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to generate configuration: {reason}",
    )


def ip_allocation_failed(reason: str = "No available IP addresses") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to allocate IP address: {reason}",
    )


def storage_error(operation: str, reason: str = "Unknown error") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Storage operation '{operation}' failed: {reason}",
    )
