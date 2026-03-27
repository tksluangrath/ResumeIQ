from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import lifespan
from api.models import HealthResponse
from api.routers import auth, history, improve, match, suggest
from config import get_settings

APP_VERSION = "0.4.0"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Resume Match API",
        version=APP_VERSION,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(match.router)
    app.include_router(improve.router)
    app.include_router(suggest.router)
    app.include_router(auth.router)
    app.include_router(history.router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=APP_VERSION, env=settings.APP_ENV)

    return app


app = create_app()
