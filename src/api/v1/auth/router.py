from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.auth.schemas import LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from src.api.v1.deps.exceptions.auth import invalid_credentials, invalid_token
from src.api.v1.deps.middlewares.auth import bearer_scheme, get_current_admin
from src.database.connection import SessionDep
from src.database.models import AdminUserModel, UserStatus
from src.management.logger import configure_logger
from src.management.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_ttl,
    verify_password,
)
from src.redis.client import RedisClient

router = APIRouter()
logger = configure_logger("Authorization", "magenta")


@router.post("/login", response_model=TokenResponse)
async def login(
    session: SessionDep,
    payload: LoginRequest,
    response: Response,
) -> TokenResponse:
    """
    Authenticate admin by username/password and issue access/refresh JWTs.
    Refresh token is stored in httpOnly cookie for security.
    """
    try:
        result = await session.execute(
            select(AdminUserModel).where(AdminUserModel.username == payload.username)
        )
        admin = result.scalar_one_or_none()

        if not admin or admin.user_status != UserStatus.ACTIVE.value:
            raise invalid_credentials()

        if not verify_password(payload.password, admin.pwd_hash):
            raise invalid_credentials()

        access_token = create_access_token(admin.username)
        refresh_token = create_refresh_token(admin.username)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=get_token_ttl(refresh_token),
        )

        logger.info(f"User {payload.username} logged in successfully")
        return TokenResponse(access_token=access_token)
    except HTTPException as exc:
        logger.error(f"Login failed for {payload.username}: {exc.detail}")
        raise
    except SQLAlchemyError as exc:
        logger.error(f"Database error during login for {payload.username}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during login for {payload.username}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(exc)}",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    session: SessionDep,
    response: Response,
    payload: RefreshRequest,
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
) -> TokenResponse:
    """
    Validate refresh token and issue new access/refresh tokens.
    Refresh token is read from httpOnly cookie (or request body for backward compatibility).
    Blacklisted or invalid tokens are rejected.
    """
    token = refresh_token_cookie or payload.refresh_token

    if not token:
        raise invalid_token()

    try:
        redis_client = RedisClient()
        if await redis_client.is_token_blacklisted(token):
            raise invalid_token()

        data = decode_token(token)
        if data.get("type") != "refresh":
            raise invalid_token()

        subject = data.get("sub")
        if not subject:
            raise invalid_token()

        result = await session.execute(
            select(AdminUserModel).where(AdminUserModel.username == subject)
        )
        admin = result.scalar_one_or_none()

        if not admin or admin.user_status != UserStatus.ACTIVE.value:
            raise invalid_token()

        access_token = create_access_token(subject)
        new_refresh_token = create_refresh_token(subject)

        try:
            ttl = get_token_ttl(token)
            await redis_client.blacklist_token(token, ex=ttl)
        except (ExpiredSignatureError, InvalidTokenError):
            pass

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=get_token_ttl(new_refresh_token),
        )

        logger.info(f"Token refreshed successfully for {subject}")
        return TokenResponse(access_token=access_token)

    except HTTPException as exc:
        logger.error(f"Token refresh failed: {exc.detail}")
        raise
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        logger.error(f"Invalid token during refresh: {exc}")
        raise invalid_token()
    except RedisError as exc:
        logger.error(f"Redis error during refresh: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable",
        )
    except SQLAlchemyError as exc:
        logger.error(f"Database error during refresh: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during refresh: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(exc)}",
        )


@router.post("/logout")
async def logout(
    response: Response,
    payload: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_admin: AdminUserModel = Depends(get_current_admin),
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
) -> dict:
    """
    Revoke the current access token and refresh token by adding them to Redis blacklist.
    Refresh token is read from httpOnly cookie (or request body for backward compatibility).
    """
    try:
        redis_client = RedisClient()
        access_token = credentials.credentials if credentials else ""

        if access_token:
            try:
                ttl = get_token_ttl(access_token)
                await redis_client.blacklist_token(access_token, ex=ttl)
            except (ExpiredSignatureError, InvalidTokenError):
                pass

        refresh_token = refresh_token_cookie or payload.refresh_token
        if refresh_token:
            try:
                ttl = get_token_ttl(refresh_token)
                await redis_client.blacklist_token(refresh_token, ex=ttl)
            except (ExpiredSignatureError, InvalidTokenError):
                pass

        response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")

        logger.info(f"User {current_admin.username} logged out successfully")
        return {"status": "logged_out"}
    except RedisError as exc:
        logger.error(f"Redis error during logout for {current_admin.username}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during logout for {current_admin.username}: {exc}")
        raise

