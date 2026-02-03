from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select

from src.api.v1.deps.exceptions.auth import invalid_token, inactive_user
from src.database.connection import SessionDep
from src.database.models import AdminUserModel, UserStatus
from src.management.security import decode_token
from src.redis.client import RedisClient

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AdminUserModel:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise invalid_token()

    token = credentials.credentials
    redis_client = RedisClient()

    if await redis_client.is_token_blacklisted(token):
        raise invalid_token()

    if not await redis_client.is_token_active(token, "access"):
        raise invalid_token()

    try:
        payload = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        raise invalid_token()

    if payload.get("type") != "access":
        raise invalid_token()

    username = payload.get("sub")
    if not username:
        raise invalid_token()

    result = await session.execute(
        select(AdminUserModel).where(AdminUserModel.username == username)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise invalid_token()

    if admin.user_status != UserStatus.ACTIVE.value:
        raise inactive_user()

    return admin