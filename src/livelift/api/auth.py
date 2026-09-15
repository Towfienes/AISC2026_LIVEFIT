"""Xác thực đường GHI — MỘT cơ chế duy nhất cho MỌI endpoint ghi.

Vì sao tệp này tồn tại (kiểm toán 14/09/2026, trước khi mở địa chỉ công khai
cho hội đồng). Đến hôm đó chỉ 3 endpoint ghi (``comments``/``ticks``/
``reactions``) tham chiếu ``IngestAuth`` đặt ngay trong ``routes/events.py``;
**12 endpoint ghi còn lại không có gì**. Người lạ biết URL có thể:

* ``POST /sessions/{id}/end`` — **kết thúc một phiên thí nghiệm đang chạy**,
  tức xoá sổ tính hợp lệ khoa học của phiên đó (khối đang đo bị cắt giữa
  chừng, ``end_ts`` là một sự thật không ghi đè được);
* ``POST /sessions/{id}/actions/execute|override`` — bắn can thiệp vào phiên
  của người khác, làm hỏng thẳng bản ghi ngẫu nhiên hoá;
* ``POST /demo/seed`` — làm ngập kho bằng dữ liệu mẫu;
* ``POST /replays/youtube`` — bắt máy chủ tải video YouTube bất kỳ (đòn bẩy
  khuếch đại tài nguyên: yt-dlp + tối đa 20.000 bình luận mỗi lần gọi).

BA QUYẾT ĐỊNH THIẾT KẾ, và lý lẽ của từng cái
---------------------------------------------

**1. Gắn ở CẤP ỨNG DỤNG, không phải cấp route.** ``create_app`` truyền
``dependencies=[Depends(require_write_auth)]`` vào ``FastAPI(...)``, nên hàm
này chạy cho MỌI route — kể cả route ai đó thêm vào ngày mai. Cách cũ (dán
``dependencies=[IngestAuth]`` lên từng route) hỏng theo kiểu tệ nhất: quên dán
là một lỗ hổng **im lặng**, không ai thấy gì cả — và đó đúng là chuyện đã xảy
ra với 12 endpoint. Ở đây quên là **lỗi an toàn**: route ghi nào không khai
báo mức bảo vệ sẽ rơi về mức NGẶT NHẤT (:data:`MUC_MAC_DINH` = ``"token"``),
và cổng kiểm thử ``tests/test_bao_ve_ghi.py`` đọc thẳng bảng định tuyến của
ứng dụng nên bộ test chuyển đỏ.

**2. Token rỗng ⇒ MỞ.** Đúng quy ước ``INGEST_TOKEN`` đang có: không có bí
mật nào thì không có cổng nào. Đó là chế độ phát triển cục bộ và là điều giữ
cho toàn bộ bộ kiểm thử chạy được mà không phải đính header ở 1.000 chỗ. Một
bản triển khai công khai PHẢI đặt ``INGEST_TOKEN`` — ``.env.example`` và
``docs/competition/sang-tao-tre-2026/08-VA-XAC-THUC.md`` nói rõ.

**3. "Khoá sạch" không phải là đáp án — hai mức bảo vệ, chia theo THIỆT HẠI
THẬT.** Giám khảo mở địa chỉ công khai và phải bấm thử được wizard, nếu không
sản phẩm thành ảnh tĩnh. Nhưng mở toang thì mất điểm an toàn. Nên:

* :data:`MUC_TOKEN` — **luôn cần token** khi token được đặt. Dành cho đường
  nạp dữ liệu của bộ thu (``comments``/``ticks``/``reactions``: một bản ghi
  giả bơm vào phiên thật là một điểm dữ liệu sai trong bài báo) và cho
  ``replays/youtube`` (tốn tài nguyên, tải nội dung bên ngoài theo URL người
  lạ đưa).
* :data:`MUC_DEMO` — **token HOẶC phạm vi demo**. Không có token thì yêu cầu
  vẫn đi qua, nhưng chỉ được chạm vào dữ liệu MẪU, và bị giới hạn tần suất.

Ranh giới "dữ liệu mẫu" không do client tự khai: cờ ``is_demo`` ghi-một-lần
(``store._SESSION_WRITE_ONCE``) và **máy chủ** là bên đặt nó. Cụ thể, một
phiên sinh ra từ yêu cầu KHÔNG có token trên bản trưng bày công khai được ghi
``is_demo=True`` — đó là sự thật: không buổi phát nào diễn ra, người tạo nó là
một khách vãng lai. Nhờ vậy dữ liệu của khách **không bao giờ** lọt vào kết
quả khoa học thật (mọi đường gộp kết quả đã tự loại ``is_demo``), mà giám khảo
vẫn chạy được trọn vẹn wizard → lịch gán → phát → ghim → kết thúc trên phiên
của chính mình.

Điều KHÔNG làm, và vì sao: không thêm trường ``is_demo`` vào ``SessionCreate``
(client vẫn không giả mạo được — hợp đồng OpenAPI không đổi, gate
``tests/test_demo_that.py`` giữ nguyên); không đổi một dòng nào của logic gán
ngẫu nhiên, phân tích hay khoá tiền đăng ký.
"""

from __future__ import annotations

import logging
import math
import secrets
import time
import uuid
from collections import deque
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from fastapi import HTTPException
from starlette.requests import HTTPConnection

from livelift.config import get_settings

logger = logging.getLogger("livelift.api.auth")

MucBaoVe = Literal["token", "demo"]

MUC_TOKEN: MucBaoVe = "token"  # noqa: S105 — tên MỨC bảo vệ, không phải bí mật
"""Luôn cần ``Authorization: Bearer <INGEST_TOKEN>`` khi token được đặt."""

MUC_DEMO: MucBaoVe = "demo"
"""Cần token, HOẶC (chế độ trưng bày bật) chỉ chạm vào dữ liệu mẫu."""

MUC_MAC_DINH: MucBaoVe = MUC_TOKEN
"""Mức của một route ghi QUÊN khai báo. Ngặt nhất — quên phải là lỗi an toàn."""

PHUONG_THUC_GHI: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
"""Phương thức HTTP làm thay đổi trạng thái. GET/HEAD/OPTIONS đi thẳng qua:
mọi đường ĐỌC cố ý để mở (mã nguồn AGPL công khai, giám khảo tự kiểm chứng)."""

_THUOC_TINH_MUC = "__livelift_muc_bao_ve__"
"""Tên thuộc tính gắn lên hàm xử lý route. Đặt trên CHÍNH hàm (không phải một
bảng tra cứu riêng) để mức bảo vệ nằm ngay cạnh route nó bảo vệ — đọc route là
thấy, không phải nhớ mở tệp thứ hai."""


# ---------------------------------------------------------------------------
# Khai báo mức bảo vệ trên từng route
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def chi_token(fn: F) -> F:
    """Đánh dấu route ghi này LUÔN đòi token (:data:`MUC_TOKEN`)."""
    setattr(fn, _THUOC_TINH_MUC, MUC_TOKEN)
    return fn


def cho_phep_demo(fn: F) -> F:
    """Đánh dấu route ghi này chấp nhận khách không token trong phạm vi DEMO.

    Đặt decorator NGOÀI ``@router.post(...)`` (tức ở trên nó): FastAPI trả về
    chính hàm gốc sau khi đăng ký, nên thuộc tính rơi đúng vào đối tượng hàm
    mà bảng định tuyến đang giữ.
    """
    setattr(fn, _THUOC_TINH_MUC, MUC_DEMO)
    return fn


def muc_bao_ve_cua(endpoint: Any) -> MucBaoVe | None:
    """Mức đã khai báo của một hàm xử lý, hoặc ``None`` nếu chưa khai báo."""
    muc = getattr(endpoint, _THUOC_TINH_MUC, None)
    return muc if muc in (MUC_TOKEN, MUC_DEMO) else None


def _moi_route(node: Any) -> list[Any]:
    """Duyệt ĐỆ QUY bảng định tuyến, trả về các route lá.

    Từ FastAPI 0.141 ``app.routes`` không còn dàn phẳng: mỗi lần
    ``include_router`` để lại một nút bọc (``_IncludedRouter``) giữ router gốc
    ở ``original_router``. Một vòng lặp một tầng trên ``app.routes`` vì thế
    thấy đúng 0 route ghi — nghĩa là một cổng kiểm thử viết theo kiểu ấy sẽ
    XANH VĨNH VIỄN mà chẳng kiểm gì cả. Phải đi hết cây.
    """
    con = getattr(node, "routes", None)
    if con is None:
        goc = getattr(node, "original_router", None)
        con = getattr(goc, "routes", None) if goc is not None else None
    if con is None:
        return [node]
    ket: list[Any] = []
    for c in con:
        ket.extend(_moi_route(c))
    return ket


def liet_ke_route_ghi(app: Any) -> list[dict[str, Any]]:
    """Mọi route GHI của một ứng dụng, kèm mức bảo vệ đã khai báo.

    Đọc thẳng bảng định tuyến THẬT của ứng dụng, không phải một danh sách chép
    tay sẽ lệch đi sau route thứ 16. Đây là nguồn dữ liệu cho cổng kiểm thử
    "route ghi mới mà quên gắn xác thực ⇒ bộ test đỏ".
    """
    ket_qua: list[dict[str, Any]] = []
    for route in _moi_route(app):
        methods = getattr(route, "methods", None) or set()
        ghi = sorted(PHUONG_THUC_GHI & set(methods))
        if not ghi:
            continue
        endpoint = getattr(route, "endpoint", None)
        ket_qua.append(
            {
                "path": getattr(route, "path_format", getattr(route, "path", "")),
                "methods": ghi,
                "endpoint": getattr(endpoint, "__name__", "?"),
                "muc": muc_bao_ve_cua(endpoint),
            }
        )
    return sorted(ket_qua, key=lambda r: (r["path"], r["methods"]))


# ---------------------------------------------------------------------------
# Thông báo lỗi — tiếng Việt, nói được phải làm gì, KHÔNG lộ thông tin hệ thống
# ---------------------------------------------------------------------------

LOI_THIEU_XAC_THUC = (
    "Thiếu hoặc sai token ingest — cần header 'Authorization: Bearer <INGEST_TOKEN>'"
)
"""Giữ NGUYÊN VĂN câu đã dùng từ trước cho comments/ticks: bộ thu, tài liệu
vận hành và test hồi quy đều đang khớp theo câu này."""

CHI_PHIEN_DEMO = (
    "Phiên này là dữ liệu THẬT — bản trưng bày công khai chỉ cho thao tác trên phiên DEMO. "
    "Hãy tạo phiên của riêng bạn bằng POST /sessions (phiên đó là phiên demo, thao tác thoải "
    "mái), hoặc dùng một phiên có nhãn DEMO. Người vận hành ghi vào phiên thật bằng header "
    "'Authorization: Bearer <INGEST_TOKEN>'."
)

LOI_TON_TAI_NGUYEN = (
    "Thao tác này cần token ghi. Đây là đường tốn tài nguyên máy chủ (tải và phân tích video "
    "theo địa chỉ người gọi đưa) nên bản trưng bày công khai không mở — xem các phiên phân "
    "tích đã có sẵn trong danh sách phiên."
)


def _thong_bao_qua_nhanh(gioi_han: int, don_vi: str, cho_giay: int) -> str:
    return (
        f"Bạn đang gửi quá nhanh — bản trưng bày công khai nhận tối đa {gioi_han} lượt ghi "
        f"mỗi {don_vi} từ một địa chỉ, để một người không làm ngập buổi demo của người khác. "
        f"Chờ {cho_giay} giây rồi thử lại."
    )


# ---------------------------------------------------------------------------
# Giới hạn tần suất cho đường ghi MỞ
# ---------------------------------------------------------------------------
#
# Vì sao làm ở đây chứ không ở Caddy: ``docker/Caddyfile`` mới thêm HẠN GIỜ
# (dial/response_header) — đó là chuyện khác, không phải giới hạn tần suất.
# Chỉ thị ``rate_limit`` KHÔNG có trong bản Caddy tiêu chuẩn (``caddy:2-alpine``
# mà compose đang dùng); nó là mô-đun bên thứ ba phải dựng lại ảnh mới có. Đặt
# ở đây thì bản triển khai nào cũng được bảo vệ, kể cả khi ai đó chạy uvicorn
# trần không qua Caddy — và chỉ ở đây mới biết yêu cầu này CÓ token hay không,
# để bộ thu của chính đội (bắn một bình luận mỗi giây) không bao giờ bị chặn.

_TTL_KHOA_S = 3600.0
"""Khoá không có lượt nào trong ngần này giây thì bị dọn (chống phình bộ nhớ
khi có người xoay vòng địa chỉ)."""


class GioiHanTanSuat:
    """Đếm theo cửa sổ trượt, khoá theo (địa chỉ gọi, nhóm endpoint).

    Trong tiến trình, không cần Redis: quy mô thí điểm là một tiến trình API.
    Nhiều tiến trình thì mỗi tiến trình giữ hạn riêng — vẫn là trần, chỉ lỏng
    hơn theo số tiến trình; nói thẳng ở đây để không ai tưởng nó là hạn toàn
    cục.
    """

    def __init__(self, so_khoa_toi_da: int = 20_000) -> None:
        self._lich_su: dict[tuple[str, str], deque[float]] = {}
        self._so_khoa_toi_da = so_khoa_toi_da

    def xin_luot(self, khoa: tuple[str, str], gioi_han: int, cua_so_s: float, now: float) -> int:
        """0 = cho qua (đã ghi nhận lượt); > 0 = số giây phải chờ."""
        if gioi_han <= 0:
            return 0  # 0 hoặc âm = tắt giới hạn (ghi rõ trong .env.example)
        if len(self._lich_su) >= self._so_khoa_toi_da:
            self._don_rac(now)
        lich = self._lich_su.setdefault(khoa, deque())
        han = now - cua_so_s
        while lich and lich[0] <= han:
            lich.popleft()
        if len(lich) >= gioi_han:
            return max(1, math.ceil(lich[0] + cua_so_s - now))
        lich.append(now)
        return 0

    def xoa_het(self) -> None:
        """Dọn sạch — dùng cho kiểm thử và cho lệnh khởi động lại."""
        self._lich_su.clear()

    def _don_rac(self, now: float) -> None:
        cu = [k for k, v in self._lich_su.items() if not v or now - v[-1] > _TTL_KHOA_S]
        for k in cu:
            del self._lich_su[k]


def dia_chi_goi(conn: HTTPConnection) -> str:
    """Địa chỉ người gọi, đọc qua Caddy.

    Lấy phần tử CUỐI của ``X-Forwarded-For``, không phải phần tử đầu. Caddy
    **nối thêm** địa chỉ của bên nó thật sự nhận gói tin vào cuối header, nên
    phần tử cuối là thứ duy nhất người gọi không tự bịa được; phần tử đầu thì
    ai cũng đặt được bằng một dòng curl và như vậy giới hạn tần suất trở thành
    trang trí.
    """
    xff = conn.headers.get("x-forwarded-for", "")
    phan = [p.strip() for p in xff.split(",") if p.strip()]
    if phan:
        return phan[-1]
    client = conn.client
    return client.host if client else "khong-ro"


def _bo_dem(conn: HTTPConnection) -> GioiHanTanSuat:
    state = conn.app.state
    bo = getattr(state, "gioi_han_ghi", None)
    if not isinstance(bo, GioiHanTanSuat):
        bo = GioiHanTanSuat()
        state.gioi_han_ghi = bo
    return bo


_NHOM_GIEO = frozenset({"/demo/seed", "/demo/seed-vang"})
"""Hai đường gieo dữ liệu mẫu: mỗi lần gọi sinh hàng nghìn bản ghi, nên chúng
có trần RIÊNG, tính theo giờ, chứ không nằm chung với trần theo phút."""


# ---------------------------------------------------------------------------
# Dependency: một hàm, áp cho mọi route
# ---------------------------------------------------------------------------


def _co_token_dung(conn: HTTPConnection, token: str) -> bool:
    """So sánh theo thời gian hằng — tránh rò rỉ token qua thời gian phản hồi."""
    gui = conn.headers.get("authorization", "")
    return secrets.compare_digest(gui, f"Bearer {token}")


def _tu_choi(conn: HTTPConnection, ma: int, chi_tiet: str, ly_do: str) -> HTTPException:
    # Ghi nhật ký ĐỦ để truy vết mà KHÔNG ghi token người gọi đưa (nhật ký có
    # thể bị đọc bởi nhiều người hơn số người được biết bí mật).
    logger.warning(
        "Từ chối ghi %s %s (%s) từ %s",
        conn.scope.get("method"),
        conn.scope.get("path"),
        ly_do,
        dia_chi_goi(conn),
    )
    return HTTPException(status_code=ma, detail=chi_tiet)


def _pham_vi_demo_hop_le(conn: HTTPConnection) -> None:
    """Khách không token chỉ được chạm vào phiên MẪU.

    Route không gắn với phiên nào (``/products``, ``/shortlinks``,
    ``/sessions``, ``/demo/*``) đi qua: ``/sessions`` sinh ra phiên demo (xem
    :func:`ghi_khong_token`), ``/demo/*`` theo định nghĩa là dữ liệu mẫu, còn
    hai đường danh mục bị chặn bằng giới hạn tần suất (và được ghi vào phần
    "rủi ro còn lại": danh mục sản phẩm dùng chung toàn hệ thống là một khoảng
    trống kiến trúc có sẵn, không phải thứ tầng xác thực này sinh ra).
    """
    path_params = conn.scope.get("path_params") or {}
    session_id = path_params.get("session_id")
    if not session_id:
        return
    try:
        uuid.UUID(str(session_id))
    except (ValueError, AttributeError, TypeError):
        return  # mã phiên sai định dạng: để route trả 404 tiếng Việt của nó
    store = getattr(conn.app.state, "store", None)
    if store is None:  # pragma: no cover — chỉ xảy ra nếu lifespan chưa chạy
        raise _tu_choi(conn, 401, LOI_THIEU_XAC_THUC, "chưa có kho để kiểm tra phạm vi")
    session = store.get_session(session_id)
    if session is None:
        return  # không tồn tại: để route trả 404, đừng biến 404 thành 403
    if not session.get("is_demo"):
        raise _tu_choi(conn, 403, CHI_PHIEN_DEMO, "phiên THẬT, khách không có token")


def _ap_gioi_han(conn: HTTPConnection) -> None:
    cfg = get_settings()
    route = conn.scope.get("route")
    path = getattr(route, "path_format", conn.scope.get("path", ""))
    if path in _NHOM_GIEO:
        nhom, gioi_han, cua_so_s, don_vi = "gieo", cfg.demo_seed_rate_limit_per_hour, 3600.0, "giờ"
    else:
        nhom, gioi_han, cua_so_s, don_vi = "ghi", cfg.write_rate_limit_per_min, 60.0, "phút"

    cho = _bo_dem(conn).xin_luot((dia_chi_goi(conn), nhom), gioi_han, cua_so_s, time.monotonic())
    if cho:
        exc = _tu_choi(
            conn,
            429,
            _thong_bao_qua_nhanh(gioi_han, don_vi, cho),
            f"vượt trần {gioi_han}/{don_vi} nhóm {nhom}",
        )
        exc.headers = {"Retry-After": str(cho)}
        raise exc


def require_write_auth(conn: HTTPConnection) -> None:
    """Cổng xác thực cho MỌI đường ghi. Gắn ở cấp ứng dụng (``create_app``).

    Thứ tự cố ý:

    1. không phải phương thức ghi ⇒ qua (mọi đường đọc để mở);
    2. ``INGEST_TOKEN`` rỗng ⇒ qua (chế độ phát triển cục bộ);
    3. token đúng ⇒ qua, KHÔNG giới hạn tần suất (bộ thu của đội bắn liên tục);
    4. mức ``token`` hoặc chế độ trưng bày tắt ⇒ 401;
    5. còn lại: giới hạn tần suất TRƯỚC, rồi mới kiểm tra phạm vi demo — phép
       kiểm tra phạm vi phải ĐỌC KHO, nên nếu để nó trước thì chính nó thành
       đòn bẩy làm ngập cơ sở dữ liệu.
    """
    method = conn.scope.get("method")
    # WebSocket không có "method" trong scope ⇒ rơi vào nhánh này. Đó là chủ
    # ý: /ws/{id} chỉ ĐỌC luồng sự kiện; nó được ghi trong "rủi ro còn lại".
    if method not in PHUONG_THUC_GHI:
        return

    conn.state.ghi_khong_token = False
    endpoint = getattr(conn.scope.get("route"), "endpoint", None)
    muc = muc_bao_ve_cua(endpoint) or MUC_MAC_DINH

    cfg = get_settings()
    token = cfg.ingest_token
    if not token:
        return
    if _co_token_dung(conn, token):
        return
    if muc == MUC_TOKEN:
        chi_tiet = LOI_TON_TAI_NGUYEN if _la_duong_ton_tai_nguyen(conn) else LOI_THIEU_XAC_THUC
        raise _tu_choi(conn, 401, chi_tiet, f"mức {muc}, không có token")
    if not cfg.public_demo_writes:
        raise _tu_choi(conn, 401, LOI_THIEU_XAC_THUC, "chế độ trưng bày công khai đang TẮT")

    _ap_gioi_han(conn)
    _pham_vi_demo_hop_le(conn)
    conn.state.ghi_khong_token = True


def _la_duong_ton_tai_nguyen(conn: HTTPConnection) -> bool:
    route = conn.scope.get("route")
    return getattr(route, "path_format", "") == "/replays/youtube"


def ghi_khong_token(conn: HTTPConnection) -> bool:
    """Yêu cầu này đã đi qua cổng mà KHÔNG chứng minh được là người vận hành?

    ``True`` ⇒ khách vãng lai trên bản trưng bày công khai. ``POST /sessions``
    đọc cờ này để ghi ``is_demo=True``: dữ liệu của khách là dữ liệu mẫu, và
    đó là sự thật chứ không phải một nhãn cho tiện.

    Mặc định ``False`` khi không có trạng thái (chưa qua cổng, ví dụ một test
    gọi thẳng hàm xử lý): phía an toàn ở đây là "coi như người vận hành", vì
    đó đúng là hành vi cũ ở chế độ phát triển cục bộ — và một phiên bị ghi
    nhầm thành demo sẽ âm thầm biến mất khỏi kết quả thật.
    """
    return bool(getattr(conn.state, "ghi_khong_token", False))
