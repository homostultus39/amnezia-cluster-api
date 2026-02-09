from functools import lru_cache
from urllib.parse import quote_plus
from typing import Optional, List, Annotated
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode


class Settings(BaseSettings):

    development: bool

    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    postgres_db: str

    redis_password: str
    redis_host: str
    redis_port: int
    redis_db: int = 0

    minio_internal_host: str
    minio_public_host: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "amnezia-configs"
    minio_secure: bool = False
    minio_presigned_expires_seconds: int = 3600

    admin_api_key: str | None = None

    server_public_host: str
    server_display_name: str = "AmneziaWG Server"
    protocols_enabled: Optional[str] = None

    amnezia_container_name: str
    amnezia_interface: str
    amnezia_config_path: str

    available_protocols: Annotated[List[str], NoDecode] = []

    default_protocol: str = "amneziawg"
    primary_dns: str = "1.1.1.1"
    secondary_dns: str = "1.0.0.1"
    persistent_keepalive_seconds: int = 25
    peer_online_threshold_seconds: int = 180
    client_default_expiration_days: int = 30
    default_subnet_address: str = "10.8.1.0"
    awg_junk_params: str = '{"Jc": "5", "Jmin": "10", "Jmax": "50", "S1": "0", "S2": "0", "S3": "0", "S4": "0", "H1": "", "H2": "", "H3": "", "H4": "", "I1": "", "I2": "", "I3": "", "I4": "", "I5": ""}'
    
    model_config = SettingsConfigDict(
        env_file = ".env",
        extra="ignore"
    )

    @property
    def postgres_url(self) -> str:
        encoded_password = quote_plus(self.postgres_password)
        return f"postgresql+asyncpg://{self.postgres_user}:{encoded_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_sync_url(self) -> str:
        encoded_password = quote_plus(self.postgres_password)
        return f"postgresql+psycopg2://{self.postgres_user}:{encoded_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @field_validator('available_protocols', mode='before')
    @classmethod
    def parse_protocols(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return v
        return []

    @model_validator(mode='after')
    def validate_protocols(self):
        if not self.available_protocols:
            raise ValueError("available_protocols cannot be empty. Please set AVAILABLE_PROTOCOLS in .env")

        if self.default_protocol not in self.available_protocols:
            raise ValueError(
                f"default_protocol '{self.default_protocol}' must be in available_protocols: {self.available_protocols}"
            )

        return self


@lru_cache
def get_settings():
    return Settings()