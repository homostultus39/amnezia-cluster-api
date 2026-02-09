
import uuid
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import func, String, DateTime, Boolean, UUID, ForeignKey, JSON, UniqueConstraint

from src.database.base import Base

class UUIDMixin:
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

class APIKeyModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_keys"

    api_key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

class ProtocolModel(Base, UUIDMixin):
    __tablename__ = "protocols"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

class ClientModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clients"

    username: Mapped[str] = mapped_column(String(255), index=True, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    peers: Mapped[list["PeerModel"]] = relationship("PeerModel", back_populates="client", cascade="all, delete-orphan")

class AppType(Enum):
    AMNEZIA_VPN = "amnezia_vpn"
    AMNEZIA_WG = "amnezia_wg"

class PeerModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "peers"
    __table_args__ = (
        UniqueConstraint("client_id", "app_type", name="uq_peers_client_app_type"),
    )
    
    app_type: Mapped[AppType] = mapped_column(String(50), default=AppType.AMNEZIA_VPN.value, nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    allowed_ips: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    public_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    protocol_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("protocols.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    last_handshake: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    client: Mapped["ClientModel"] = relationship("ClientModel", back_populates="peers")