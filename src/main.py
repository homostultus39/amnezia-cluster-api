from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from alembic import command
from alembic.config import Config

from src.management.logger import configure_logger
from src.api.v1.auth.router import router as auth_router
from src.api.v1.clients.router import router as clients_router
from src.api.v1.peers.router import router as peers_router
from src.api.v1.server.router import router as server_router
from src.api.v1.deps.middlewares.auth import get_current_api_key
from src.database.management.default.api_key_data import create_default_api_key
from src.database.management.default.protocol_data import create_default_protocols


logger = configure_logger("MAIN", "cyan")

def run_migrations():
    logger.info("Running migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations applied successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    logger.info("Migrations applied successfully.")
    logger.info("Creating default protocols...")
    await create_default_protocols()
    logger.info("Default protocols created successfully.")
    logger.info("Creating default API key...")
    await create_default_api_key()
    logger.info("Default API key created successfully.")
    logger.info("Initialization completed successfully.")
    yield

app = FastAPI(
    title="Amnezia API",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api/v1",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authorization"]
)

app.include_router(
    clients_router,
    prefix="/clients",
    tags=["Clients"],
    dependencies=[Depends(get_current_api_key)]
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