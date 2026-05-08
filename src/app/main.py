from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.logging import configure_logging
from src.app.settings import get_settings
from src.app.api.v1.routes_upload import router as files_router
from src.app.api.v1.routes_chat import router as chat_router


def create_app() -> FastAPI:
    s = get_settings()
    configure_logging(s.app_log_level)

    app = FastAPI(title="Audit Agent Service", version="2.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(files_router)
    app.include_router(chat_router)
    return app


app = create_app()
