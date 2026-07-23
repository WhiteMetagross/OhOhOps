"""OhOhOps FastAPI application entrypoint.

``create_app()`` is the single construction path shared by uvicorn and tests:
it configures logging, applies CORS for the Next.js dashboard, attaches the
lifespan (which builds shared clients), and registers the versioned API router.

Run locally from the ``backend/`` directory:
    uvicorn app.main:app --reload
or:
    python -m app.main
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="OhOhOps",
        description="Autonomous SRE & infrastructure orchestration framework.",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
