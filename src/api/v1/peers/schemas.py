from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class AppType(str, Enum):
    """Types of applications for creating new peers"""
    AMNEZIA_VPN = "amnezia_vpn"
    AMNEZIA_WG = "amnezia_wg"

class CreatePeerRequest(BaseModel):
    app_type: AppType = Field(..., description="Application type for peer configuration")
    allocated_ip: Optional[str] = Field(
        None,
        description="IP address to allocate to the peer. If not provided, auto-allocated from subnet"
    )


class CreatePeerResponse(BaseModel):
    public_key: str
    private_key: str
    allocated_ip: str
    endpoint: str
    app_type: str
    protocol: str
    config: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ListPeerResponse(BaseModel):
    public_key: str
    allocated_ip: str
    app_type: Optional[str] = None
    protocol: str
    endpoint: str
    is_online: bool = Field(alias="online")
    last_handshake: Optional[datetime] = None
    rx_bytes: int = 0
    tx_bytes: int = 0
    created_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class UpdatePeerRequest(BaseModel):
    app_type: AppType = Field(..., description="New application type for peer configuration")


class UpdatePeerResponse(BaseModel):
    old_public_key: str
    new_public_key: str
    allocated_ip: str
    app_type: str
    protocol: str
    config: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DeletePeerResponse(BaseModel):
    status: str = "deleted"
    public_key: str
    message: str = "Peer successfully removed from configuration"
