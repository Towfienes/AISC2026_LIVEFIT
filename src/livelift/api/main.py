"""LiveLift API application factory.

Run:  uvicorn livelift.api.main:app --reload
Env:  STORE_BACKEND=memory (default) | postgres  ·  see .env.example
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from livelift import __version__
from livelift.api import autopilot
from livelift.api.routes import actions, demo, events, redirect, replays, reports, sessions, ws
from livelift.api.store import Store, attach_snapshot, build_store, durability_info


def create_app(store: Store | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Snapshotting is attached ONLY to a store the app built itself: an
        # injected store belongs to the caller (tests, scripts), and a test
        # suite that silently wrote snapshot files to the data directory would
        # be a surprise nobody asked for.
        owned = store is None
        app.state.store = build_store() if owned else store
        app.state.snapshot = attach_snapshot(app.state.store) if owned else None
        # Server-side executor for mode='auto' sessions. Until 12/09 nothing
        # ever called /actions/execute, so every auto session ended with
        # compliance 0.0 and no estimate, silently (incident 12/09).
        app.state.autopilot_task = autopilot.start(app.state.store)
        try:
            yield
        finally:
            await autopilot.stop(app.state.autopilot_task)
            if app.state.snapshot is not None:
                app.state.snapshot.stop()
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
    def health() -> dict[str, Any]:
        from livelift.api import service
        from livelift.nlp.intent import classifier_info

        info = classifier_info()
        return {
            "status": "ok",
            "store_backend": app.state.store.backend,
            # provenance: which intent classifier is live (trained model vs
            # keyword baseline) — numbers must carry their source
            "intent_backend": info["backend"],
            # Data safety, stated out loud: storage_mode / durable /
            # storage_warning answer "if this process dies now, what do I
            # lose?". Before the incident of 11/09/2026 nothing on the wire
            # answered that, and 13 real sessions went missing unannounced.
            **durability_info(app.state.store),
            # Gói DEMO-THẬT: mode/"mode_counts"/"mode_note" nói kho này đang
            # chứa dữ liệu mẫu hay dữ liệu thật (hay cả hai) — nguồn dữ liệu
            # cho chip DEMO/THẬT trên web. Người dùng phải LUÔN biết mình đang
            # nhìn loại dữ liệu nào (yêu cầu phản biện #2-3).
            **service.data_mode(app.state.store),
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
