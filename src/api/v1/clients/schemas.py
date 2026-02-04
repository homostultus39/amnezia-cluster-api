from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.database.models import AppType


class TrafficInfo(BaseModel):
    received: int
    sent: int


class ConfigStorage(BaseModel):
    bucket: str
    object: str
    url: str


class PeerResponse(BaseModel):
    id: str
    public_key: str
    allowed_ips: list[str]
    endpoint: Optional[str]
    last_handshake: Optional[datetime]
    traffic: TrafficInfo
    online: bool
    expires_at: Optional[datetime]
    app_type: str
    protocol: str
    config_url: Optional[str] = None


class ClientResponse(BaseModel):
    id: str
    username: str
    peers: list[PeerResponse]


class CreateClientRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    protocol: str = Field(default="amneziawg", min_length=1, max_length=100)
    app_type: AppType
    expires_at: Optional[datetime] = None


class CreateClientResponse(BaseModel):
    id: str
    public_key: str
    config: str
    config_type: str
    config_storage: ConfigStorage
    protocol: str


class UpdateClientRequest(BaseModel):
    expires_at: Optional[datetime] = None


class DeleteClientResponse(BaseModel):
    status: str


class UpdateClientResponse(BaseModel):
    status: str

