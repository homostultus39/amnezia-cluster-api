from uuid import UUID


def get_config_object_name(protocol: str, client_id: str | UUID, app_type: str) -> str:
    return f"configs/{protocol}/{client_id}/{app_type}"
