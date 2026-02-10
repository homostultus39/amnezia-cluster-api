from fastapi import FastAPI, Depends

from src.management.logger import configure_logger
from src.api.v1.peers.router import router as peers_router
from src.api.v1.server.router import router as server_router
from src.api.v1.deps.middlewares.auth import get_current_api_key


logger = configure_logger("MAIN", "cyan")


app = FastAPI(
    title="Amnezia API",
    version="1.0.0",
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