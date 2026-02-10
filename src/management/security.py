import re
import secrets
from pathlib import Path
from functools import lru_cache

from src.management.logger import configure_logger
from src.management.settings import get_settings


logger = configure_logger("APIKeyStorage", "yellow")


class APIKeyStorage:
    def __init__(self, env_file_path: str = ".env"):
        self.env_file_path = Path(env_file_path)
        self.settings = get_settings()
        self._api_key: str | None = None

    def get_api_key(self) -> str:
        if self._api_key:
            return self._api_key

        if self.settings.admin_api_key:
            self._api_key = self.settings.admin_api_key
            return self._api_key

        env_key = self._read_from_env_file()
        if env_key:
            self._api_key = env_key
            return self._api_key

        api_key = self._generate_api_key()
        self._write_to_env_file(api_key)
        self._api_key = api_key
        return api_key

    def _generate_api_key(self) -> str:
        return secrets.token_urlsafe(32)

    def _read_from_env_file(self) -> str | None:
        if not self.env_file_path.exists():
            return None

        try:
            with open(self.env_file_path, "r") as file_handle:
                for line in file_handle:
                    line = line.strip()
                    if line.startswith("ADMIN_API_KEY="):
                        match = re.match(r'ADMIN_API_KEY=["\']?([^"\']+)["\']?', line)
                        if match:
                            return match.group(1)
        except Exception as exc:
            logger.warning(f"Failed to read ADMIN_API_KEY from .env: {exc}")

        return None

    def _write_to_env_file(self, api_key: str) -> None:
        try:
            if self.env_file_path.exists():
                with open(self.env_file_path, "r") as file_handle:
                    content = file_handle.read()
                    if "ADMIN_API_KEY=" in content:
                        return

            with open(self.env_file_path, "a") as file_handle:
                file_handle.write(f"\nADMIN_API_KEY={api_key}\n")
        except Exception as exc:
            logger.warning(f"Failed to write ADMIN_API_KEY to .env: {exc}")

    def verify_api_key(self, provided_key: str) -> bool:
        stored_key = self.get_api_key()
        return provided_key == stored_key
    
@lru_cache
def get_api_key_storage() -> APIKeyStorage:
    return APIKeyStorage()