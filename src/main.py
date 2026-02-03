from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends

from src.database.connection import init_database
from src.api.v1.auth.router import router as auth_router
from src.api.v1.clients.router import router as clients_router
from src.api.v1.deps.middlewares.auth import get_current_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
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
    prefix="/clients",
    tags=["Clients"],
    dependencies=[Depends(get_current_admin)]
)
app.include_router(
    clients_router,
    prefix="/auth",
    tags=["Authorization"]
)

@app.get("/health")
async def health_check():
    return {
        "app": "Amnezia API",
        "status": "running"
    }