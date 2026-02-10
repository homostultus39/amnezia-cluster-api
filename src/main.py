from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends

from src.management.logger import configure_logger
from src.api.v1.peers.router import router as peers_router
from src.api.v1.server.router import router as server_router
from src.api.v1.deps.middlewares.auth import get_current_api_key
from src.management.security import get_api_key_storage
from src.services.management.protocol_factory import (
    get_available_protocols,
    load_protocol_config,
)

logger = configure_logger("MAIN", "cyan")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Amnezia API...")
    load_protocol_config()
    logger.info(f"Loaded protocols: {get_available_protocols()}")
    api_key = get_api_key_storage().get_api_key()
    logger.info(f"The API key was successfully installed: {api_key}")
    yield
    logger.info("Shutting down Amnezia API...")


app = FastAPI(
    title="Amnezia API",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api/v1",
    swagger_ui_parameters={"persistAuthorization": True},
)


app.include_router(
    peers_router,
    dependencies=[Depends(get_current_api_key)]
)

app.include_router(
    server_router,
    dependencies=[Depends(get_current_api_key)]
)

@app.get("/health")
async def health_check():
    return {
        "app": "Amnezia API",
        "status": "running"
    }
