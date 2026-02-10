import yaml
import importlib
from pathlib import Path
from typing import Type

from src.management.logger import configure_logger
from src.management.settings import get_settings
from src.services.management.base_protocol_service import BaseProtocolService


logger = configure_logger("ProtocolFactory", "cyan")

_protocol_config: dict[str, dict] = {}


def load_protocol_config(config_path: str | None = None) -> None:
    settings = get_settings()
    if config_path is None:
        config_path = settings.protocol_config_path

    config_file = Path(config_path)
    _protocol_config.clear()
    if not config_file.exists():
        logger.warning(f"Protocol config file {config_path} not found, using defaults")
        _protocol_config["amneziawg2"] = {
            "service_class": "src.services.protocols.amneziawg2.amneziawg2_service.AmneziaWG2Service",
            "enabled": True,
        }
        return

    try:
        with open(config_file, "r") as file_handle:
            config = yaml.safe_load(file_handle) or {}
            protocols = config.get("protocols", {})
            normalized_protocols = {
                str(name).lower(): value for name, value in protocols.items()
            }
            _protocol_config.update(normalized_protocols)
            logger.info(f"Loaded {len(_protocol_config)} protocol(s) from {config_path}")
    except Exception as exc:
        logger.error(f"Failed to load protocol config from {config_path}: {exc}")
        raise


def reload_protocol_config(config_path: str | None = None) -> None:
    load_protocol_config(config_path=config_path)


def get_available_protocols() -> list[str]:
    if not _protocol_config:
        load_protocol_config()

    return [
        name
        for name, config in _protocol_config.items()
        if config.get("enabled", True)
    ]


def get_protocol_config(protocol_name: str) -> dict:
    if not _protocol_config:
        load_protocol_config()

    normalized_name = protocol_name.lower()
    if normalized_name not in _protocol_config:
        available = get_available_protocols()
        raise ValueError(
            f"Unsupported protocol: {protocol_name}. Available protocols: {available}"
        )

    return _protocol_config[normalized_name]


def create_protocol_service(protocol_name: str) -> BaseProtocolService:
    if not _protocol_config:
        load_protocol_config()

    normalized_name = protocol_name.lower()
    if normalized_name not in _protocol_config:
        available = get_available_protocols()
        raise ValueError(
            f"Unsupported protocol: {protocol_name}. Available protocols: {available}"
        )

    config = _protocol_config[normalized_name]
    if not config.get("enabled", True):
        raise ValueError(f"Protocol {protocol_name} is disabled")

    try:
        service_class_path = config["service_class"]
        module_path, class_name = service_class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        service_class: Type[BaseProtocolService] = getattr(module, class_name)

        instance = service_class(protocol_name=normalized_name)
        logger.debug(f"Created service instance for protocol: {normalized_name}")
        return instance
    except ImportError as exc:
        logger.error(f"Failed to import service class for {protocol_name}: {exc}")
        raise ValueError(f"Failed to load protocol service for {protocol_name}: {exc}")
    except AttributeError as exc:
        logger.error(f"Service class not found for {protocol_name}: {exc}")
        raise ValueError(f"Service class not found for {protocol_name}: {exc}")
    except Exception as exc:
        logger.error(f"Failed to create service instance for {protocol_name}: {exc}")
        raise ValueError(f"Failed to create protocol service for {protocol_name}: {exc}")
