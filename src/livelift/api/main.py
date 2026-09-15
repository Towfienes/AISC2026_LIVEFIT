"""LiveLift API application factory.

Run:  uvicorn livelift.api.main:app --reload
Env:  STORE_BACKEND=memory (default) | postgres  ·  see .env.example
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from livelift import __version__
from livelift.api import autopilot
from livelift.api.auth import GioiHanTanSuat, require_write_auth
from livelift.api.routes import actions, demo, events, redirect, replays, reports, sessions, ws
from livelift.api.store import (
    Store,
    StoreUnavailableError,
    attach_snapshot,
    build_store,
    storage_health,
)

log = logging.getLogger("livelift.api")


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
        # XÁC THỰC ĐƯỜNG GHI, GẮN MỘT LẦN CHO CẢ ỨNG DỤNG (gói VÁ-XÁC-THỰC,
        # 14/09/2026). Trước hôm đó mỗi route tự dán `dependencies=[IngestAuth]`
        # và 12 trong 15 endpoint ghi quên dán — một lỗ hổng IM LẶNG: không có
        # gì trong mã, trong test hay trong log nói rằng chúng đang mở. Gắn ở
        # đây thì route nào cũng đi qua cổng, kể cả route thêm vào ngày mai;
        # route ghi không khai báo mức bảo vệ rơi về mức ngặt nhất (đòi token)
        # và cổng tests/test_bao_ve_ghi.py bắt nó ngay. Mọi đường ĐỌC vẫn mở —
        # cổng chỉ chặn POST/PUT/PATCH/DELETE.
        dependencies=[Depends(require_write_auth)],
    )

    # Bộ đếm giới hạn tần suất sống theo ỨNG DỤNG, không phải theo module: hai
    # ứng dụng trong cùng một tiến trình (bộ kiểm thử dựng hàng chục) không
    # được dùng chung hạn mức của nhau.
    app.state.gioi_han_ghi = GioiHanTanSuat()

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

    # Kho chết ⇒ 503 CÓ NGHĨA, không phải 500 trần (sự cố 13/09/2026).
    #
    # Ngày 13/09/2026 PostgreSQL chết giữa lúc chạy: GET /sessions treo 30 giây
    # rồi trả "Internal Server Error" — không một chữ nào nói rằng cơ sở dữ
    # liệu đã chết, nên người vận hành đi tìm lỗi ở API. Bộ xử lý này bắt
    # StoreUnavailableError từ BẤT KỲ route nào (không route nào phải nhớ tự
    # bắt) và trả 503: đúng mã cho "phụ thuộc bên dưới không có", kèm câu tiếng
    # Việt nói rõ chuyện gì và phải làm gì.
    @app.exception_handler(StoreUnavailableError)
    async def _store_unavailable(request: Request, exc: StoreUnavailableError) -> JSONResponse:
        log.error(
            "Kho dữ liệu không trả lời trên %s %s: %s",
            request.method,
            request.url.path,
            exc.cause_text or exc.message,
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": exc.message,
                # Nguyên văn lỗi driver: để gỡ rối, KHÔNG thay cho câu tiếng
                # Việt ở trên (nó là tiếng Anh và không nói phải làm gì).
                "cause": exc.cause_text or None,
                "storage_ok": False,
            },
            # Retry-After: nói bằng giao thức rằng đây là sự cố tạm thời của
            # phụ thuộc, không phải một yêu cầu sai.
            headers={"Retry-After": "5"},
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        from livelift.api import service
        from livelift.config import get_settings
        from livelift.nlp.intent import classifier_info

        info = classifier_info()
        cfg = get_settings()
        # Data safety, stated out loud: storage_mode / durable /
        # storage_warning answer "if this process dies now, what do I
        # lose?". Before the incident of 11/09/2026 nothing on the wire
        # answered that, and 13 real sessions went missing unannounced.
        #
        # Và từ sự cố 13/09/2026: câu trả lời phải được KIỂM TRA, không phải
        # suy ra từ tên backend. storage_health() hỏi kho một câu rẻ, có hạn
        # giờ, có đệm ngắn — rồi mới dám nói durable=true.
        storage = storage_health(
            app.state.store,
            timeout_s=cfg.health_ping_timeout_s,
            cache_s=cfg.health_ping_cache_s,
        )
        # Gói DEMO-THẬT: mode/"mode_counts"/"mode_note" nói kho này đang
        # chứa dữ liệu mẫu hay dữ liệu thật (hay cả hai) — nguồn dữ liệu
        # cho chip DEMO/THẬT trên web. Người dùng phải LUÔN biết mình đang
        # nhìn loại dữ liệu nào (yêu cầu phản biện #2-3).
        #
        # Đếm phiên là một lần ĐỌC KHO thật, nên khi kho chết nó cũng chết
        # theo. /health không được sập cùng: nói "không đếm được" là sự thật,
        # còn ném 500 thì xóa luôn phần thân đang giải thích vì sao hỏng.
        #
        # Ping vừa nói kho chết thì KHÔNG thử đếm nữa: lần đếm đó chắc chắn
        # thất bại, nhưng nó thất bại sau cả hạn giờ của pool — cộng vào là
        # /health lại chậm đúng vào lúc người ta cần nó nhanh nhất.
        khong_dem_duoc = {
            "mode": "unknown",
            "mode_counts": None,
            "mode_note": "Chưa đếm được phiên vì kho dữ liệu không trả lời — xem storage_warning.",
        }
        if storage["storage_ok"] is False:
            data_mode = khong_dem_duoc
        else:
            try:
                data_mode = service.data_mode(app.state.store)
            except StoreUnavailableError:
                data_mode = khong_dem_duoc
        # Mã HTTP: 200 kèm status="degraded", KHÔNG phải 503.
        #
        # Lý do: thân của /health chính là lời giải thích sự cố. Trả 503 thì
        # trang web (và mọi phép thử đơn giản dùng response.ok) vứt thân đi và
        # chỉ còn biết "máy chủ hỏng" — đúng cái nhầm lẫn ngày 13/09, khi người
        # vận hành không phân biệt được API chết với cơ sở dữ liệu chết. Bản
        # thân TIẾN TRÌNH API vẫn khỏe và vẫn phục vụ được; thứ chết là kho, và
        # điều đó được nói bằng status/durable/storage_ok/storage_warning —
        # những trường máy đọc được. Cổng cho giám sát là `status != "ok"`.
        # Các route ĐỌC KHO thì ngược lại: chúng thật sự không làm được việc,
        # nên chúng trả 503 (xem _store_unavailable ở trên).
        return {
            "status": "ok" if storage["storage_ok"] is not False else "degraded",
            "store_backend": app.state.store.backend,
            # provenance: which intent classifier is live (trained model vs
            # keyword baseline) — numbers must carry their source
            "intent_backend": info["backend"],
            **storage,
            **data_mode,
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
