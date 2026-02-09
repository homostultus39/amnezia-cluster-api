import bcrypt
import secrets


def hash_api_key(api_key: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(api_key.encode(), salt).decode()


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    return bcrypt.checkpw(api_key.encode(), api_key_hash.encode())


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


