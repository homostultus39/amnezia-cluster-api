from fastapi import Header

from src.api.v1.deps.exceptions.auth import invalid_api_key
from src.database.connection import SessionDep
from src.database.management.operations.api_key import get_api_key_by_plain_key
from src.database.models import APIKeyModel


async def get_current_api_key(
    session: SessionDep,
    api_key: str | None = Header(None, alias="X-API-Key"),
) -> APIKeyModel:
    if not api_key:
        raise invalid_api_key()

    record = await get_api_key_by_plain_key(session, api_key)
    if not record:
        raise invalid_api_key()

    return record