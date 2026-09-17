"""Nguồn bình luận MÔ PHỎNG — kiểm thử đầu-cuối không cần nền tảng (17/09/2026).

Vì sao có tệp này
-----------------
Bộ thu chạy nền (:mod:`livelift.api.ingest_jobs`) chỉ có ba client thật —
YouTube, Facebook, Shopee — và cả ba cần khoá mà máy của nhóm chưa có. Không có
nguồn nào thì không ai chạy được TRỌN đường ống (bộ thu → lọc thông tin cá nhân
→ phân loại ý định → WebSocket → Bàn trợ live) để kiểm thử hay trình diễn.

:class:`MoPhongLiveClient` có đúng giao diện của các client kia
(``iter_comments``, ``iter_viewers``, ``aclose``, ``last_error``) và phát lại
một kịch bản bình luận theo nhịp thời gian thật, nhân với một hệ số tăng tốc.

Luật trung thực (không thương lượng)
------------------------------------
* Kịch bản ``mo_phong_kich_ban.jsonl`` là dữ liệu TỔNG HỢP 100%: do tác tử AI
  soạn ngày 17/09/2026, không chép từ người thật. Dòng đầu là bản ghi meta khai
  báo điều đó; :func:`doc_kich_ban` TỪ CHỐI một tệp không khai báo
  ``"du_lieu_tong_hop": true`` — tệp mất lời khai nguồn gốc thì không được phát.
* Mọi bình luận mang ``platform="sim"`` nên luôn phân biệt được với dữ liệu thật.
* Máy chủ chỉ cho bật nguồn này trên phiên CHẠY THỬ (``dry_run``) hoặc phiên MẪU
  (``is_demo``) — xem :func:`livelift.api.ingest_jobs.cho_phep_mo_phong`.

Tất định
--------
* ``ext_id`` = ``sim-<số thứ tự trong tệp>``: phát lại vào cùng phiên (bấm tắt
  rồi bật lại, API tự nối lại, chạy ``ngan`` rồi ``mac_dinh``) KHÔNG nhân đôi
  bình luận — kho bỏ bản trùng theo ``(platform, ext_id)``.
* Số người xem sinh từ ``random.Random`` có seed cố định: hai lần chạy cho cùng
  một chuỗi số. Chỉ ``ts_utc`` khác nhau — nó là thời điểm PHÁT, đúng như một
  buổi live thật.

Nguồn (``source_id``)
---------------------
``""`` (kịch bản mặc định) · ``"ngan"`` (3 phút đầu) · thêm ``"x10"`` để phát
nhanh gấp 10 lần, ví dụ ``"ngan x10"`` hoặc chỉ ``"x10"``. Người bán gõ có dấu
(``"Ngắn x10"``, ``"mặc định"``) cũng được nhận; dạng lưu vào job luôn là tên
không dấu.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
import unicodedata
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from livelift.ingest.base import RawComment, RawTick

PLATFORM_SIM = "sim"
"""Nhãn nền tảng của mọi bản ghi mô phỏng (``EventPlatform`` đã có sẵn "sim")."""

TEP_KICH_BAN = Path(__file__).with_name("mo_phong_kich_ban.jsonl")

KICH_BAN_MAC_DINH = "mac_dinh"
NGAN_DEN_GIAY = 180.0
KICH_BAN_DUNG_SAN: dict[str, str] = {
    KICH_BAN_MAC_DINH: "Toàn bộ kịch bản một buổi live bán quần áo",
    "ngan": "3 phút đầu của kịch bản mặc định — đủ để thử nhanh",
}

HE_SO_TOI_THIEU = 1.0
HE_SO_TOI_DA = 1000.0
"""Giới hạn cho hệ số gõ từ trình duyệt. Test gọi thẳng lớp với hệ số lớn hơn."""

NHIP_NGUOI_XEM_S = 30.0
"""Một điểm người xem mỗi 30 giây kịch bản — cùng nhịp YouTube/Facebook."""

SEED_MAC_DINH = 20260917

_TOKEN_HE_SO = re.compile(r"^[x×*](\d+(?:[.,]\d+)?)$")


# ---------------------------------------------------------------------------
# Kịch bản
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DongBinhLuan:
    stt: int
    """Vị trí trong tệp (0 = bình luận đầu tiên) — gốc của ``ext_id``."""
    t: float
    """Giây tính từ đầu buổi (nhịp giả lập)."""
    text: str
    nhom: str
    """Ý định người soạn nhắm tới — KHÔNG phải nhãn vàng."""
    co_pii_gia: bool = False


@dataclass(frozen=True)
class KichBan:
    ten: str
    meta: dict[str, Any]
    dong: tuple[DongBinhLuan, ...]
    thoi_luong_tep_s: float
    """Độ dài của CẢ tệp — ``ngan`` là 3 phút đầu của cùng buổi, nên dùng chung
    đường cong người xem với ``mac_dinh``."""

    @property
    def thoi_luong_s(self) -> float:
        return self.dong[-1].t if self.dong else 0.0

    @staticmethod
    def ext_id(dong: DongBinhLuan) -> str:
        return f"sim-{dong.stt:04d}"


def doc_tep_kich_ban(path: Path = TEP_KICH_BAN) -> tuple[dict[str, Any], tuple[DongBinhLuan, ...]]:
    """Đọc và KIỂM tệp kịch bản. ``ValueError`` tiếng Việt nếu tệp sai.

    Kiểm: dòng đầu là meta khai ``du_lieu_tong_hop: true`` và có ``nguon_goc``;
    ``so_dong`` khớp số dòng thật; ``t`` không giảm; câu không rỗng.
    """
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError as exc:
        raise ValueError(f"Không đọc được tệp kịch bản mô phỏng ({type(exc).__name__}).") from exc
    if not lines:
        raise ValueError("Tệp kịch bản mô phỏng rỗng.")
    try:
        meta = json.loads(lines[0])
        ban_ghi = [json.loads(ln) for ln in lines[1:]]
    except ValueError as exc:
        raise ValueError("Tệp kịch bản mô phỏng không phải JSONL hợp lệ.") from exc
    if (
        not isinstance(meta, dict)
        or meta.get("loai") != "meta"
        or meta.get("du_lieu_tong_hop") is not True
        or not str(meta.get("nguon_goc") or "").strip()
    ):
        raise ValueError(
            "Tệp kịch bản mô phỏng thiếu lời khai dữ liệu tổng hợp và nguồn gốc ở dòng đầu "
            "— từ chối phát."
        )
    dong: list[DongBinhLuan] = []
    t_truoc = 0.0
    for i, r in enumerate(ban_ghi, start=2):
        text = str(r.get("text") or "") if isinstance(r, dict) else ""
        try:
            t = float(r["t"])  # type: ignore[index]
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Kịch bản mô phỏng: dòng {i} thiếu thời điểm t.") from None
        if not text.strip():
            raise ValueError(f"Kịch bản mô phỏng: dòng {i} không có chữ.")
        if t < t_truoc:
            raise ValueError(f"Kịch bản mô phỏng: dòng {i} có t lùi về trước.")
        t_truoc = t
        dong.append(
            DongBinhLuan(
                stt=len(dong),
                t=t,
                text=text,
                nhom=str(r.get("nhom") or "khac"),
                co_pii_gia=bool(r.get("co_pii_gia", False)),
            )
        )
    if meta.get("so_dong") != len(dong):
        raise ValueError(
            f"Kịch bản mô phỏng: meta khai {meta.get('so_dong')} dòng nhưng tệp có {len(dong)}."
        )
    return meta, tuple(dong)


@lru_cache(maxsize=4)
def _doc_tep_co_dem(path: Path) -> tuple[dict[str, Any], tuple[DongBinhLuan, ...]]:
    return doc_tep_kich_ban(path)


def doc_kich_ban(ten: str = KICH_BAN_MAC_DINH, path: Path = TEP_KICH_BAN) -> KichBan:
    """Kịch bản dựng sẵn theo tên (``mac_dinh`` | ``ngan``)."""
    ten = ten or KICH_BAN_MAC_DINH
    if ten not in KICH_BAN_DUNG_SAN:
        raise ValueError(_loi_ten(ten))
    meta, dong = _doc_tep_co_dem(path)
    thoi_luong_tep = dong[-1].t if dong else 0.0
    if ten == "ngan":
        dong = tuple(d for d in dong if d.t <= NGAN_DEN_GIAY)
    return KichBan(ten=ten, meta=dict(meta), dong=dong, thoi_luong_tep_s=thoi_luong_tep)


def _loi_ten(ten: str) -> str:
    return (
        f"Không có kịch bản mô phỏng tên {ten!r}. Để trống để phát cả buổi mẫu, "
        "hoặc gõ: ngắn (3 phút đầu)."
    )


# ---------------------------------------------------------------------------
# Nguồn: tên kịch bản + hệ số tăng tốc
# ---------------------------------------------------------------------------


def _bo_dau(s: str) -> str:
    """``"Ngắn"`` → ``"Ngan"``: người bán gõ tiếng Việt có dấu."""
    tach = unicodedata.normalize("NFD", s)
    khong_dau = "".join(ch for ch in tach if unicodedata.category(ch) != "Mn")
    return khong_dau.replace("đ", "d").replace("Đ", "D")


def phan_tich_nguon(source: str) -> tuple[str, float | None]:
    """``"ngan x10"`` → ``("ngan", 10.0)``; ``""`` → ``("mac_dinh", None)``.

    Nhận cả chữ có dấu (``"Ngắn x10"``, ``"mặc định"``). ``ValueError`` tiếng
    Việt khi tên không có hoặc hệ số ngoài
    [:data:`HE_SO_TOI_THIEU`, :data:`HE_SO_TOI_DA`].
    """
    chuoi = _bo_dau((source or "").strip().lower())
    chuoi = re.sub(r"\bmac[\s_-]*dinh\b", KICH_BAN_MAC_DINH, chuoi)
    ten: str | None = None
    he_so: float | None = None
    for token in chuoi.split():
        m = _TOKEN_HE_SO.match(token)
        if m is not None:
            if he_so is not None:
                raise ValueError("Chỉ ghi một hệ số tăng tốc, ví dụ: ngắn x10.")
            he_so = float(m.group(1).replace(",", "."))
            if not HE_SO_TOI_THIEU <= he_so <= HE_SO_TOI_DA:
                raise ValueError(
                    f"Hệ số tăng tốc phải từ {HE_SO_TOI_THIEU:g} đến {HE_SO_TOI_DA:g} "
                    "(ví dụ x10 là nhanh gấp 10 lần)."
                )
            continue
        if ten is not None:
            raise ValueError(
                "Nguồn mô phỏng chỉ gồm tên kịch bản và hệ số tăng tốc, ví dụ: ngắn x10."
            )
        ten = token
    ten = ten or KICH_BAN_MAC_DINH
    if ten not in KICH_BAN_DUNG_SAN:
        raise ValueError(_loi_ten(ten))
    return ten, he_so


def chuan_hoa_nguon_mo_phong(source: str) -> str:
    """Dạng chuẩn để lưu vào job: ``""`` | ``"ngan"`` | ``"ngan x10"``."""
    if not (source or "").strip():
        return ""
    ten, he_so = phan_tich_nguon(source)
    return ten if he_so is None else f"{ten} x{he_so:g}"


# ---------------------------------------------------------------------------
# Người xem: chuỗi tất định
# ---------------------------------------------------------------------------


def chuoi_nguoi_xem(
    kich_ban: KichBan, seed: int = SEED_MAC_DINH, nhip_s: float = NHIP_NGUOI_XEM_S
) -> list[int]:
    """Số người xem tại mỗi mốc ``k * nhip_s`` (k = 0 … hết kịch bản).

    Hình dạng tính trên CẢ tệp: tăng nhanh trong 1/4 đầu buổi lên khoảng gấp
    đôi, rồi rơi dần; nhiễu Gauss ~6% từ ``random.Random`` có seed cố định ⇒
    tất định. Kịch bản ``ngan`` nhận đúng phần đầu của chuỗi ``mac_dinh``.
    """
    goc = float(kich_ban.meta.get("nguoi_xem_goc") or 60)
    so_diem_tep = int(kich_ban.thoi_luong_tep_s // nhip_s) + 1
    so_diem = min(so_diem_tep, int(kich_ban.thoi_luong_s // nhip_s) + 1)
    rng = random.Random(seed)
    ket: list[int] = []
    for k in range(so_diem):
        tien_do = k / (so_diem_tep - 1) if so_diem_tep > 1 else 0.0
        # Lên từ 1× tới 2× trong 1/4 đầu, rồi rơi dần về 1,1× lúc kết thúc.
        hinh = 1.0 + 4.0 * tien_do if tien_do < 0.25 else 2.0 - 0.9 * (tien_do - 0.25) / 0.75
        ket.append(max(1, round(goc * hinh * (1.0 + rng.gauss(0.0, 0.06)))))
    return ket


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def _gio_utc() -> datetime:
    return datetime.now(UTC)


class MoPhongLiveClient:
    """Client "nền tảng" phát lại kịch bản tổng hợp — cùng giao diện client thật.

    ``he_so`` là hệ số tăng tốc mặc định; hệ số ghi trong ``source_id``
    (``"x10"``) được ưu tiên. ``ngu``/``dong_ho``/``gio_utc`` tiêm được để test
    kiểm nhịp phát mà không phải chờ thật.
    """

    def __init__(
        self,
        he_so: float = 1.0,
        *,
        seed: int = SEED_MAC_DINH,
        tep: Path = TEP_KICH_BAN,
        nhip_nguoi_xem_s: float = NHIP_NGUOI_XEM_S,
        ngu: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        dong_ho: Callable[[], float] = time.monotonic,
        gio_utc: Callable[[], datetime] = _gio_utc,
    ) -> None:
        if not he_so > 0:
            raise ValueError("Hệ số tăng tốc của nguồn mô phỏng phải lớn hơn 0.")
        self._he_so = float(he_so)
        self._seed = seed
        self._tep = tep
        self._nhip_nguoi_xem_s = nhip_nguoi_xem_s
        self._ngu = ngu
        self._dong_ho = dong_ho
        self._gio_utc = gio_utc
        self._da_dong = False
        self.last_error: str | None = None

    def _chuan_bi(self, source_id: str) -> tuple[KichBan, float]:
        try:
            ten, he_so = phan_tich_nguon(source_id)
            kich_ban = doc_kich_ban(ten, self._tep)
        except ValueError as exc:
            self.last_error = str(exc)
            raise
        self.last_error = None
        return kich_ban, (he_so if he_so is not None else self._he_so)

    async def _cho_toi(self, bat_dau: float, giay_thuc: float) -> None:
        """Ngủ tới mốc ``bat_dau + giay_thuc`` (bù trễ tích luỹ, không trôi nhịp)."""
        con_lai = bat_dau + giay_thuc - self._dong_ho()
        if con_lai > 0:
            await self._ngu(con_lai)

    async def iter_comments(self, source_id: str = "") -> AsyncIterator[RawComment]:
        kich_ban, he_so = self._chuan_bi(source_id)
        bat_dau = self._dong_ho()
        for dong in kich_ban.dong:
            await self._cho_toi(bat_dau, dong.t / he_so)
            if self._da_dong:
                return
            yield RawComment(
                platform=PLATFORM_SIM,
                ext_id=KichBan.ext_id(dong),
                ts_utc=self._gio_utc(),
                text=dong.text,
                author_ext_id=None,
            )

    async def iter_viewers(self, source_id: str = "") -> AsyncIterator[RawTick]:
        kich_ban, he_so = self._chuan_bi(source_id)
        chuoi = chuoi_nguoi_xem(kich_ban, self._seed, self._nhip_nguoi_xem_s)
        bat_dau = self._dong_ho()
        for k, so_nguoi in enumerate(chuoi):
            await self._cho_toi(bat_dau, k * self._nhip_nguoi_xem_s / he_so)
            if self._da_dong:
                return
            yield RawTick(platform=PLATFORM_SIM, ts_utc=self._gio_utc(), viewers=float(so_nguoi))

    async def aclose(self) -> None:
        self._da_dong = True
