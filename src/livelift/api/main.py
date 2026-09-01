"""LiveLift API application factory.

Run:  uvicorn livelift.api.main:app --reload
Env:  STORE_BACKEND=memory (default) | postgres  ·  see .env.example
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from livelift import __version__
from livelift.api.routes import actions, demo, events, redirect, replays, reports, sessions, ws
from livelift.api.store import Store, build_store


def create_app(store: Store | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = store if store is not None else build_store()
        yield
        app.state.store.close()

    app = FastAPI(
        title="LiveLift API",
        version=__version__,
        description=(
            "Nền tảng thí nghiệm vận hành cho livestream thương mại — "
            "REST + WebSocket cho bàn trung control (AISC'26)"
        ),
        lifespan=lifespan,
    )

    origins = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str | None]:
        from livelift.nlp.intent import classifier_info

        info = classifier_info()
        return {
            "status": "ok",
            "store_backend": app.state.store.backend,
            # provenance: which intent classifier is live (trained model vs
            # keyword baseline) — numbers must carry their source
            "intent_backend": info["backend"],
        }

    app.include_router(sessions.router, tags=["sessions"])
    app.include_router(events.router, tags=["events"])
    app.include_router(actions.router, tags=["actions"])
    app.include_router(redirect.router, tags=["redirect"])
    app.include_router(reports.router, tags=["reports"])
    app.include_router(replays.router, tags=["replays"])
    app.include_router(demo.router, tags=["demo"])
    app.include_router(ws.router)
    return app


app = create_app()
