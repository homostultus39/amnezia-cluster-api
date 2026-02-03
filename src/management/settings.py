from functools import lru_cache
from urllib.parse import quote_plus
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    minio_host: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "amnezia-configs"
    minio_secure: bool = False
    minio_presigned_expires_seconds: int = 3600

    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_minutes: int = 43200
    jwt_blacklist_ex: int = 3600
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    server_public_host: str
    protocols_enabled: Optional[str] = None

    amnezia_container_name: str
    amnezia_interface: str
    amnezia_config_path: str

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

@lru_cache
def get_settings():
    return Settings()