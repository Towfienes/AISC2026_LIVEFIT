#!/usr/bin/env python3
"""MỘT lệnh để trả lời: "có lên sóng trước hội đồng được không?"

Vì sao có tệp này
-----------------
Thể lệ Bảng C §8 (docs/competition/sang-tao-tre-2026/BRIEF-THE-LE.md) viết:
sản phẩm phải chạy được trên môi trường trực tuyến **ổn định ít nhất 48 GIỜ
trước thời điểm kiểm tra** và suốt phiên chấm; không truy cập được **do lỗi
chủ quan** thì **điểm vận hành có thể bị tính 0**. "Lỗi chủ quan" là những thứ
đội biết trước mà không kiểm: kho đang chạy trên RAM, thư mục build thiếu CSS,
bản sao lưu gần nhất đã 9 ngày, trang chủ trống trơn vì chưa nạp dữ liệu mẫu.

Các script sẵn có mỗi cái soi một mảnh — ``chay_local.py`` lo khởi động,
``gate_css_web.py`` lo CSS, ``kiem_chung_ben_vung.py`` lo tính bền vững. Tệp
này KHÔNG làm lại việc của chúng: nó **hỏi một hệ thống ĐANG CHẠY** (dựng bằng
docker compose hay bằng chay_local.py đều được) đúng những câu mà giám khảo sẽ
vô tình kiểm hộ trong 5 phút đầu, rồi trả về một phán quyết duy nhất.

Mỗi phép thử tự nói ba điều: ĐO ĐƯỢC GÌ · NGƯỠNG NÀO · SỬA RA SAO. Không phép
thử nào báo ĐẠT dựa trên phỏng đoán; cái gì không đo được thì báo KHÔNG ĐO
ĐƯỢC, không báo ĐẠT.

Cách chạy
---------
Máy mình, hai cổng tách rời (mặc định — đúng bố cục của chay_local.py)::

    .venv/Scripts/python scripts/kiem_tra_truoc_demo.py

Máy chủ công khai, mọi thứ đi qua Caddy một cổng::

    python scripts/kiem_tra_truoc_demo.py --goc https://livelift.example.com

Trỏ tay từng phần::

    python scripts/kiem_tra_truoc_demo.py --api http://127.0.0.1:8000 \
                                          --web http://127.0.0.1:3000

Mã thoát
--------
0 = SẴN SÀNG LÊN SÓNG (không có phép thử CHẶN nào trượt)
1 = CHƯA SẴN SÀNG — có phép thử CHẶN trượt, bảng in rõ lệnh sửa
2 = không nối được tới API (sai địa chỉ, hoặc hệ thống chưa bật)

Cờ ``--khat-khe`` nâng mọi CẢNH BÁO lên thành CHẶN — dùng cho lần kiểm cuối
trước buổi chấm, khi không còn chỗ cho "tạm chấp nhận được".
"""

from __future__ import annotations

import argparse
import http.client
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.console import configure  # noqa: E402

# --- Ngưỡng ----------------------------------------------------------------
#
# Mọi con số dưới đây là NGƯỠNG VẬN HÀNH, không phải sở thích. Nguồn gốc:
#
# CSS_TOI_THIEU_BYTE / CSS_TOKEN — lấy NGUYÊN từ scripts/chay_local.py để hai
#   cổng không bao giờ lệch nhau. Bản CSS thật đo được ~62 KB (13/09/2026);
#   mọi dạng hỏng đã gặp đều nhỏ hơn 10 KB.
# BACKUP_CU_CANH_BAO_GIO — docker/backup.sh chạy mỗi ngày một lần lúc 02:00,
#   nên một bản sao lưu khoẻ mạnh không bao giờ quá 24 giờ tuổi. 36 giờ cho
#   phép trượt một chu kỳ (máy chủ vừa khởi động lại) mà chưa kêu; quá 36 giờ
#   nghĩa là vòng lặp sao lưu đã chết và không ai biết.
# BACKUP_CU_CHAN_GIO — 48 giờ: đúng bằng cửa sổ mà thể lệ đòi hệ thống phải
#   đứng vững. Sao lưu cũ hơn thế thì không còn là lưới an toàn cho kỳ chấm.
# TRE_CHAM_MS — người xem bỏ trang khi chờ quá ~1 giây; 1500 ms là mốc "vẫn
#   dùng được nhưng phải xem lại" cho một VPS 1 vCPU ở xa.
CSS_TOI_THIEU_BYTE = 10 * 1024
CSS_TOKEN_BAT_BUOC = ("--canvas", "--brand")
BACKUP_CU_CANH_BAO_GIO = 36
BACKUP_CU_CHAN_GIO = 48
TRE_CHAM_MS = 1500
HET_GIO_S = 10

# Mọi cách một lần gọi HTTP có thể hỏng, gom một chỗ.
#
# Bắt RỘNG là cố ý. Chính tệp này sinh ra để thay vết ngăn xếp bằng một câu
# tiếng Việt, nên nó không được phép tự đổ vết ngăn xếp ra màn hình vì một địa
# chỉ gõ sai. urllib.error.URLError, socket.timeout, ConnectionError và
# ssl.SSLError đều là con của OSError; riêng một URL méo (vd cổng không phải
# số) ném http.client.InvalidURL — con của ValueError, KHÔNG phải OSError, nên
# phải liệt kê riêng. Thiếu đúng nhánh đó là bảng kiểm chết giữa chừng
# (bắt được khi tự thử ngày 14/09/2026).
LOI_MANG = (OSError, http.client.HTTPException, ValueError)

DAT = "ĐẠT"
TRUOT = "TRƯỢT"
CANH_BAO = "CẢNH BÁO"
KHONG_DO = "KHÔNG ĐO ĐƯỢC"

# Ký hiệu kèm theo mỗi trạng thái — kênh thứ hai ngoài màu chữ, để bảng vẫn
# đọc được khi dán vào tài liệu đen trắng.
DAU = {DAT: "✓", TRUOT: "✕", CANH_BAO: "!", KHONG_DO: "?"}


@dataclass
class KetQua:
    """Kết quả một phép thử."""

    ten: str
    trang_thai: str
    chi_tiet: str
    # chan=True: trượt phép thử này là KHÔNG được lên sóng.
    chan: bool = True
    cach_sua: str = ""


@dataclass
class Soat:
    """Gom kết quả và quyết định phán quyết cuối."""

    khat_khe: bool = False
    ket_qua: list[KetQua] = field(default_factory=list)

    def them(
        self,
        ten: str,
        trang_thai: str,
        chi_tiet: str,
        *,
        chan: bool = True,
        cach_sua: str = "",
    ) -> KetQua:
        kq = KetQua(ten=ten, trang_thai=trang_thai, chi_tiet=chi_tiet, chan=chan, cach_sua=cach_sua)
        self.ket_qua.append(kq)
        dau = DAU.get(trang_thai, "·")
        print(f"  {dau} {ten}: {chi_tiet}")
        if trang_thai in (TRUOT, CANH_BAO, KHONG_DO) and cach_sua:
            print(f"      → {cach_sua}")
        return kq

    def hong(self) -> list[KetQua]:
        """Những phép thử đủ nghiêm trọng để CHẶN việc lên sóng."""
        xau = []
        for kq in self.ket_qua:
            # Hai lý do KHÁC NHAU, cố ý giữ thành hai nhánh: một phép thử
            # trượt-và-chặn luôn là lỗi; còn cảnh báo chỉ thành lỗi ở chế độ
            # khắt khe. Gộp lại thành một biểu thức `or` thì ngắn hơn nhưng
            # đọc không ra ý.
            if kq.trang_thai == TRUOT and kq.chan:  # noqa: SIM114
                xau.append(kq)
            elif self.khat_khe and kq.trang_thai in (CANH_BAO, KHONG_DO):
                xau.append(kq)
        return xau


# --- Tiện ích HTTP ---------------------------------------------------------


def _mo(url: str, *, timeout: int = HET_GIO_S, theo_chuyen_huong: bool = True):
    """GET một URL. Trả (status, headers, body_bytes, latency_ms).

    KHÔNG ném lỗi khi máy chủ trả 4xx/5xx — mã lỗi cũng là dữ liệu cần đo.
    Chỉ ném khi không nối được (đó mới là "hệ thống không tồn tại").
    """
    # S310: địa chỉ do chính người vận hành truyền vào qua --api/--web/--goc,
    # không phải dữ liệu từ bên ngoài.
    req = urllib.request.Request(  # noqa: S310
        url, headers={"User-Agent": "LiveLift-kiem-tra-truoc-demo/1.0"}
    )
    # Chứng chỉ tự ký trên máy chủ thử nghiệm không nên làm hỏng cả bảng kiểm;
    # phép thử HTTPS riêng bên dưới mới là chỗ phán xét chuyện chứng chỉ.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    class _KhongTheoChuyenHuong(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):  # noqa: ANN002, ANN003
            return None

    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    if not theo_chuyen_huong:
        handlers.append(_KhongTheoChuyenHuong())
    opener = urllib.request.build_opener(*handlers)

    t0 = time.perf_counter()
    try:
        with opener.open(req, timeout=timeout) as r:
            body = r.read()
            ms = (time.perf_counter() - t0) * 1000
            return r.status, dict(r.headers), body, ms
    except urllib.error.HTTPError as e:  # 4xx/5xx — vẫn là câu trả lời
        body = e.read()
        ms = (time.perf_counter() - t0) * 1000
        return e.code, dict(e.headers), body, ms


def _json(body: bytes) -> dict:
    try:
        doc = json.loads(body.decode("utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


# --- Từng phép thử ---------------------------------------------------------


def thu_health(s: Soat, api: str) -> dict:
    """Phép thử gốc: API còn sống, và nó tự khai kho của mình thế nào."""
    try:
        status, _, body, ms = _mo(f"{api}/health")
    except LOI_MANG as e:
        s.them(
            "API trả lời",
            TRUOT,
            f"không nối được tới {api}/health — {type(e).__name__}",
            cach_sua="Bật hệ thống: `docker compose up -d` (hoặc `python scripts/chay_local.py`), "
            "rồi chạy lại lệnh này.",
        )
        return {}

    if status != 200:
        s.them(
            "API trả lời",
            TRUOT,
            f"/health trả mã {status} (mong đợi 200)",
            cach_sua="Xem log: `docker compose logs --tail=50 api`",
        )
        return {}

    doc = _json(body)
    s.them("API trả lời", DAT, f"/health trả 200 sau {ms:.0f} ms")

    # -- Kho có BỀN VỮNG không? Đây là phép thử đắt giá nhất của cả bảng. ---
    # Ngày 11/09/2026 hệ thống chạy trên RAM mà vẫn báo xanh: 13 phiên live
    # thật + 17.535 bình luận biến mất lúc 13:05:53, không khôi phục được.
    che_do = doc.get("storage_mode", "?")
    ben_vung = bool(doc.get("durable"))
    if ben_vung:
        s.them("Kho bền vững", DAT, f"storage_mode={che_do}, durable=true")
    else:
        s.them(
            "Kho bền vững",
            CANH_BAO,
            f"storage_mode={che_do}, durable=FALSE — dữ liệu nằm trong RAM",
            # Không CHẶN: một buổi demo thuần đọc vẫn diễn ra được trên RAM, và
            # đội có thể CỐ Ý demo bằng memory+snapshot. Nhưng phải hiện thành
            # chữ để không ai lên sóng THẬT mà tưởng mình đang lưu bền vững.
            chan=False,
            cach_sua="Phiên live THẬT bắt buộc Postgres: `python scripts/bat_postgres.py`, "
            "hoặc dựng bằng `docker compose up -d` (đã đặt STORE_BACKEND=postgres).",
        )

    # -- Kho có ĐANG trả lời không? (khác câu hỏi trên) --------------------
    # Ngày 13/09/2026 PostgreSQL chết hẳn giữa lúc chạy nhưng /health vẫn xanh
    # vì nó chưa bao giờ hỏi cơ sở dữ liệu lấy một câu. Trường storage_ok sinh
    # ra từ đúng sự cố đó — nó là kết quả một cú ping thật, có hạn giờ.
    kho_ok = doc.get("storage_ok")
    ping = doc.get("storage_ping") or {}
    if kho_ok is False:
        vi_sao = ping.get("error") or doc.get("storage_warning") or "kho không trả lời"
        s.them(
            "Kho đang trả lời",
            TRUOT,
            f"storage_ok=false — {vi_sao}",
            cach_sua="`docker compose ps db` và `docker compose logs --tail=50 db`",
        )
    elif kho_ok is True:
        do_tre = ping.get("latency_ms")
        them = f", ping {do_tre:.0f} ms" if isinstance(do_tre, (int, float)) else ""
        s.them("Kho đang trả lời", DAT, f"storage_ok=true{them}")
    else:
        s.them(
            "Kho đang trả lời",
            KHONG_DO,
            "/health không có trường storage_ok",
            chan=False,
            cach_sua="Bản API đang chạy cũ hơn migration 0009 — dựng lại: "
            "`docker compose up -d --build api`",
        )

    return doc


def thu_che_do_du_lieu(s: Soat, doc: dict) -> None:
    """DEMO hay THẬT — và trang có trống trơn không.

    Hai rủi ro ngược chiều nhau, phải bắt cả hai:
      * trang TRỐNG khi hội đồng mở link ngoài giờ live → không có gì để xem;
      * dữ liệu mô phỏng bị hiểu nhầm thành dữ liệu thật → thể lệ Điều 5 cấm,
        và trung thực là thứ đội này đem đi thi.
    """
    che_do = doc.get("mode")
    dem = doc.get("mode_counts") or {}
    so_demo = dem.get("demo")
    so_that = dem.get("real")

    if che_do is None:
        s.them(
            "Chế độ dữ liệu",
            KHONG_DO,
            "/health không có trường mode",
            chan=False,
            cach_sua="Dựng lại api để lấy bản có data_mode(): `docker compose up -d --build api`",
        )
        return

    tong = (so_demo or 0) + (so_that or 0)
    if tong == 0:
        s.them(
            "Trang có dữ liệu để xem",
            TRUOT,
            "kho TRỐNG — hội đồng mở link sẽ thấy một trang không có gì",
            cach_sua="Nạp bộ demo vàng: `curl -X POST http://127.0.0.1:8000/demo/seed-vang` "
            "(hoặc `python scripts/seed_demo_vang.py --backend postgres`).",
        )
    else:
        s.them(
            "Trang có dữ liệu để xem",
            DAT,
            f"{tong} phiên trong kho (thật {so_that or 0} · demo {so_demo or 0})",
        )

    # Nhãn phải khớp với thực tế kho. ModeChip của web đọc đúng trường này.
    if che_do == "demo":
        s.them(
            "Nhãn DEMO/THẬT",
            DAT,
            "mode=demo — giao diện sẽ hiện huy hiệu vàng 'DEMO' ở mọi trang",
        )
    elif che_do == "real":
        s.them("Nhãn DEMO/THẬT", DAT, "mode=real — giao diện hiện 'PHIÊN THẬT'")
    elif che_do == "mixed":
        s.them(
            "Nhãn DEMO/THẬT",
            DAT,
            "mode=mixed — giao diện hiện 'THẬT + DEMO', từng phiên có nhãn riêng",
        )
    else:
        s.them(
            "Nhãn DEMO/THẬT",
            CANH_BAO,
            f"mode={che_do!r} — không xác định được chế độ",
            chan=False,
            cach_sua="ModeChip rơi về nhãn DEMO khi không chắc (an toàn), nhưng nên tìm "
            "nguyên nhân trước buổi chấm.",
        )


def thu_web(s: Soat, web: str) -> None:
    """Trang chủ + phép thử CSS — đúng sự cố 13/09/2026.

    Hôm ấy trang chủ trả 200 hoàn hảo nhưng hiện ra dưới dạng HTML thô không
    CSS, vì ``/_next/static/css/app/layout.css`` trả 404. Một phép thử chỉ hỏi
    "có 200 không" sẽ báo ĐẠT trong khi giám khảo đang nhìn một trang vỡ. Nên
    phép thử này đi tiếp một bước: lấy đường dẫn CSS từ chính HTML, tải về, cân
    và soi hai token của globals.css.
    """
    try:
        status, _, body, ms = _mo(web)
    except LOI_MANG as e:
        s.them(
            "Trang chủ",
            TRUOT,
            f"không nối được tới {web} — {type(e).__name__}",
            cach_sua="`docker compose logs --tail=50 web`",
        )
        return

    if status != 200:
        s.them(
            "Trang chủ",
            TRUOT,
            f"trả mã {status} (mong đợi 200)",
            cach_sua="`docker compose logs --tail=50 web`",
        )
        return

    html = body.decode("utf-8", errors="replace")
    s.them("Trang chủ", DAT, f"trả 200 sau {ms:.0f} ms, {len(body):,} byte")

    if ms > TRE_CHAM_MS:
        s.them(
            "Tốc độ trang chủ",
            CANH_BAO,
            f"{ms:.0f} ms — chậm hơn ngưỡng {TRE_CHAM_MS} ms",
            chan=False,
            cach_sua="Kiểm tra tải máy chủ (`docker stats`); cân nhắc đặt Cloudflare "
            "miễn phí trước VPS để cache tài nguyên tĩnh.",
        )

    # Lấy MỌI tệp CSS mà trang khai báo, không chỉ tệp đầu tiên.
    duong_dan = re.findall(r'href="([^"]+\.css[^"]*)"', html)
    if not duong_dan:
        s.them(
            "CSS của trang chủ",
            TRUOT,
            "HTML không khai báo tệp CSS nào — đây CHÍNH LÀ dạng vỡ ngày 13/09",
            cach_sua="Dựng lại giao diện: `docker compose up -d --build web`, "
            "hoặc `python scripts/gate_css_web.py` để soi kỹ.",
        )
        return

    tong_byte = 0
    token_thay: set[str] = set()
    loi: list[str] = []
    for dd in duong_dan:
        url = urllib.parse.urljoin(web, dd)
        try:
            st, _, css, _ = _mo(url)
        except LOI_MANG as e:
            loi.append(f"{dd} → {type(e).__name__}")
            continue
        if st != 200:
            loi.append(f"{dd} → mã {st}")
            continue
        tong_byte += len(css)
        chu = css.decode("utf-8", errors="replace")
        token_thay.update(t for t in CSS_TOKEN_BAT_BUOC if t in chu)

    thieu_token = [t for t in CSS_TOKEN_BAT_BUOC if t not in token_thay]
    if loi:
        s.them(
            "CSS của trang chủ",
            TRUOT,
            f"{len(loi)} tệp CSS không tải được: {'; '.join(loi[:3])}",
            cach_sua="`docker compose up -d --build web`",
        )
    elif tong_byte < CSS_TOI_THIEU_BYTE:
        s.them(
            "CSS của trang chủ",
            TRUOT,
            f"chỉ {tong_byte:,} byte (< {CSS_TOI_THIEU_BYTE:,}) — bản build hỏng",
            cach_sua="`docker compose up -d --build web`",
        )
    elif thieu_token:
        s.them(
            "CSS của trang chủ",
            TRUOT,
            f"{tong_byte:,} byte nhưng thiếu token {', '.join(thieu_token)} — "
            "không phải CSS của dự án",
            cach_sua="`docker compose up -d --build web`",
        )
    else:
        s.them(
            "CSS của trang chủ",
            DAT,
            f"{tong_byte:,} byte qua {len(duong_dan)} tệp, có {', '.join(CSS_TOKEN_BAT_BUOC)}",
        )


def thu_shortlink(s: Soat, api: str) -> None:
    """/r/{code} — biến kết quả CHÍNH của thí nghiệm.

    Nếu đường này hỏng thì mọi con số tác động trong báo cáo đều vô nghĩa, nên
    nó được kiểm riêng chứ không gộp vào phép thử API chung. Dùng một mã chắc
    chắn KHÔNG tồn tại: ta đang đo "tuyến đường có sống không", và một mã lạ
    phải cho ra câu trả lời có kiểm soát (404/302) chứ không phải 500.
    """
    ma_bia = "kiemtra-khong-ton-tai-000"
    try:
        status, headers, _, _ = _mo(f"{api}/r/{ma_bia}", theo_chuyen_huong=False)
    except LOI_MANG as e:
        s.them(
            "Tuyến shortlink /r/",
            TRUOT,
            f"không nối được — {type(e).__name__}",
            cach_sua="Đây là biến kết quả chính của thí nghiệm. Xem `docker compose logs api`.",
        )
        return

    if status in (301, 302, 303, 307, 308):
        s.them(
            "Tuyến shortlink /r/",
            DAT,
            f"mã lạ trả {status} → {headers.get('Location', '?')} (tuyến sống)",
        )
    elif status == 404:
        s.them("Tuyến shortlink /r/", DAT, "mã lạ trả 404 đúng như mong đợi (tuyến sống)")
    elif status >= 500:
        s.them(
            "Tuyến shortlink /r/",
            TRUOT,
            f"mã lạ làm máy chủ trả {status} — lỗi máy chủ, không phải 404",
            cach_sua="`docker compose logs --tail=50 api`",
        )
    else:
        s.them(
            "Tuyến shortlink /r/",
            CANH_BAO,
            f"mã lạ trả {status} — không phải 404/302 như mong đợi",
            chan=False,
        )


def thu_header_bao_mat(s: Soat, web: str) -> None:
    """Header bảo mật do Caddy chèn (docker/Caddyfile).

    KHÔNG chặn: chạy bằng chay_local.py thì không có Caddy nên header vắng mặt
    là chuyện bình thường. Nhưng trên máy chủ công khai mà vắng thì phải biết.
    """
    try:
        _, headers, _, _ = _mo(web)
    except LOI_MANG:
        return

    can_co = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": None,
    }
    thieu = [h for h in can_co if h not in headers]
    if not thieu:
        s.them(
            "Header bảo mật", DAT, "có đủ X-Content-Type-Options, X-Frame-Options, Referrer-Policy"
        )
    else:
        s.them(
            "Header bảo mật",
            CANH_BAO,
            f"thiếu {', '.join(thieu)}",
            chan=False,
            cach_sua="Header do Caddy chèn — chạy qua `docker compose up -d` (cổng 80) thay vì "
            "gọi thẳng cổng 3000. Nếu đã chạy qua Caddy mà vẫn thiếu: kiểm tra docker/Caddyfile.",
        )


def thu_sao_luu(s: Soat) -> None:
    """Bản sao lưu gần nhất bao nhiêu tuổi, và có đọc được không.

    docker/backup.sh đã tự xác minh mỗi bản dump bằng gzip -t + pg_restore
    --list TRƯỚC khi ghi tên chính thức, nên ở đây chỉ cần soi TUỔI và kích cỡ:
    một tệp 0 byte hoặc một tệp 9 ngày tuổi đều nghĩa là vòng lặp sao lưu đã
    chết mà không ai nhận ra.
    """
    thu_muc = REPO_ROOT / "backups"
    if not thu_muc.is_dir():
        s.them(
            "Sao lưu cơ sở dữ liệu",
            CANH_BAO,
            "chưa có thư mục backups/",
            chan=False,
            cach_sua="Thư mục được tạo khi phân hệ `backup` chạy lần đầu: "
            "`docker compose up -d backup`",
        )
        return

    dumps = sorted(
        thu_muc.glob("livelift-*.dump.gz"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not dumps:
        s.them(
            "Sao lưu cơ sở dữ liệu",
            CANH_BAO,
            "thư mục backups/ chưa có bản dump nào",
            chan=False,
            cach_sua="Ép chạy ngay một bản: xem §7 của docs/competition/sang-tao-tre-2026/"
            "04-TRIEN-KHAI.md (lệnh pg_dump thủ công).",
        )
        return

    moi_nhat = dumps[0]
    tuoi_gio = (time.time() - moi_nhat.stat().st_mtime) / 3600
    co = moi_nhat.stat().st_size
    mo_ta = f"{moi_nhat.name} — {co:,} byte, {tuoi_gio:.1f} giờ tuổi ({len(dumps)} bản đang giữ)"

    if co == 0:
        s.them(
            "Sao lưu cơ sở dữ liệu",
            TRUOT,
            f"{moi_nhat.name} rỗng (0 byte)",
            cach_sua="`docker compose logs --tail=30 backup`",
        )
    elif tuoi_gio > BACKUP_CU_CHAN_GIO:
        s.them(
            "Sao lưu cơ sở dữ liệu",
            TRUOT,
            f"{mo_ta} — cũ hơn {BACKUP_CU_CHAN_GIO} giờ, không còn là lưới an toàn cho kỳ chấm",
            cach_sua="Phân hệ backup nhiều khả năng đã chết: `docker compose ps backup` "
            "và `docker compose logs --tail=30 backup`",
        )
    elif tuoi_gio > BACKUP_CU_CANH_BAO_GIO:
        s.them(
            "Sao lưu cơ sở dữ liệu",
            CANH_BAO,
            f"{mo_ta} — quá {BACKUP_CU_CANH_BAO_GIO} giờ, đã trượt một chu kỳ",
            chan=False,
            cach_sua="`docker compose logs --tail=30 backup`",
        )
    else:
        s.them("Sao lưu cơ sở dữ liệu", DAT, mo_ta)


def thu_bi_mat(s: Soat) -> None:
    """Bí mật không được nằm trong kho mã — thể lệ trọng tâm 8.

    Chỉ kiểm điều KHÔNG THỂ chối cãi và rẻ: git có đang theo dõi .env không.
    Việc quét toàn bộ lịch sử là chuyện của kiểm toán, không phải của một bảng
    kiểm chạy 10 giây trước giờ lên sóng.
    """
    import subprocess

    try:
        # S607: cố ý gọi `git` theo PATH — bảng kiểm chạy trên máy vận hành,
        # không phải trong môi trường cần đường dẫn tuyệt đối.
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],  # noqa: S603, S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        s.them("Bí mật ngoài kho mã", KHONG_DO, "không chạy được git", chan=False)
        return

    if r.returncode == 0:
        s.them(
            "Bí mật ngoài kho mã",
            TRUOT,
            ".env ĐANG BỊ GIT THEO DÕI — mật khẩu sẽ theo kho mã ra ngoài",
            cach_sua="`git rm --cached .env` rồi ĐỔI MỌI mật khẩu/token đã từng nằm trong đó.",
        )
    else:
        s.them("Bí mật ngoài kho mã", DAT, ".env không bị git theo dõi (đã có trong .gitignore)")


def thu_https(s: Soat, goc: str | None) -> None:
    """Chỉ có ý nghĩa khi đang trỏ tới một địa chỉ công khai."""
    if not goc:
        return
    if not goc.startswith("https://"):
        s.them(
            "HTTPS",
            CANH_BAO,
            f"đang kiểm qua {goc.split('://')[0]}:// — không mã hoá",
            chan=False,
            cach_sua="Đặt DOMAIN=<tên-miền> trong .env; Caddy tự xin chứng chỉ Let's Encrypt.",
        )
        return

    host = urllib.parse.urlparse(goc).hostname or ""
    try:
        ctx = ssl.create_default_context()
        with (
            socket.create_connection((host, 443), timeout=HET_GIO_S) as sock,
            ctx.wrap_socket(sock, server_hostname=host) as ss,
        ):
            cert = ss.getpeercert()
    except LOI_MANG as e:
        s.them(
            "HTTPS",
            TRUOT,
            f"chứng chỉ không hợp lệ cho {host} — {type(e).__name__}: {e}",
            cach_sua="Kiểm tra DNS đã trỏ đúng máy chủ và cổng 80/443 đang mở; "
            "`docker compose logs --tail=50 caddy`",
        )
        return

    het_han = cert.get("notAfter", "")
    try:
        han = datetime.strptime(het_han, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
        con_ngay = (han - datetime.now(UTC)).days
    except ValueError:
        s.them("HTTPS", DAT, f"chứng chỉ hợp lệ cho {host}")
        return

    if con_ngay < 7:
        s.them(
            "HTTPS",
            CANH_BAO,
            f"chứng chỉ còn {con_ngay} ngày",
            chan=False,
            cach_sua="Caddy tự gia hạn ở mốc còn 1/3 hạn; nếu không tự gia hạn được thì "
            "cổng 80 đang bị chặn.",
        )
    else:
        s.them("HTTPS", DAT, f"chứng chỉ hợp lệ cho {host}, còn {con_ngay} ngày")


# --- Chạy ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    configure()
    p = argparse.ArgumentParser(
        description="Bảng kiểm một lệnh trước khi demo trước hội đồng.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--goc",
        default=None,
        help="Địa chỉ công khai đi qua Caddy, vd https://livelift.example.com "
        "(API ở {goc}/api, web ở {goc}).",
    )
    p.add_argument("--api", default=None, help="Địa chỉ API (mặc định http://127.0.0.1:8000)")
    p.add_argument("--web", default=None, help="Địa chỉ web (mặc định http://127.0.0.1:3000)")
    p.add_argument(
        "--khat-khe",
        action="store_true",
        help="Nâng mọi CẢNH BÁO thành lỗi CHẶN — dùng cho lần kiểm cuối trước buổi chấm.",
    )
    args = p.parse_args(argv)

    if args.goc:
        goc = args.goc.rstrip("/")
        api = args.api or f"{goc}/api"
        web = args.web or goc
    else:
        goc = None
        api = args.api or "http://127.0.0.1:8000"
        web = args.web or "http://127.0.0.1:3000"
    api = api.rstrip("/")
    web = web.rstrip("/")

    s = Soat(khat_khe=args.khat_khe)

    print("== LiveLift — bảng kiểm trước khi lên sóng ==")
    print(f"   API:  {api}")
    print(f"   Web:  {web}")
    print(f"   Lúc:  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    if args.khat_khe:
        print("   Chế độ KHẮT KHE: cảnh báo cũng bị tính là trượt.")
    print()

    print("-- Máy chủ API --")
    doc = thu_health(s, api)
    if not doc:
        print()
        print("  Không hỏi được API. Mọi phép thử sau đều vô nghĩa — dừng ở đây.")
        return 2
    print()

    print("-- Dữ liệu và nhãn DEMO/THẬT --")
    thu_che_do_du_lieu(s, doc)
    print()

    print("-- Giao diện web --")
    thu_web(s, web)
    print()

    print("-- Tuyến đo lường --")
    thu_shortlink(s, api)
    print()

    print("-- Bảo mật và vận hành --")
    thu_header_bao_mat(s, web)
    thu_https(s, goc)
    thu_sao_luu(s)
    thu_bi_mat(s)
    print()

    # -- Phán quyết --------------------------------------------------------
    dem = {
        t: sum(1 for k in s.ket_qua if k.trang_thai == t) for t in (DAT, TRUOT, CANH_BAO, KHONG_DO)
    }
    hong = s.hong()

    print("=" * 62)
    print(
        f"  {dem[DAT]} đạt · {dem[TRUOT]} trượt · {dem[CANH_BAO]} cảnh báo · "
        f"{dem[KHONG_DO]} không đo được"
    )
    print("=" * 62)

    if hong:
        print()
        print("  CHƯA SẴN SÀNG LÊN SÓNG. Phải sửa xong những mục sau:")
        for kq in hong:
            print(f"    ✕ {kq.ten}: {kq.chi_tiet}")
            if kq.cach_sua:
                print(f"        → {kq.cach_sua}")
        print()
        return 1

    print()
    print("  SẴN SÀNG LÊN SÓNG.")
    if dem[CANH_BAO] or dem[KHONG_DO]:
        print(
            f"  (còn {dem[CANH_BAO]} cảnh báo và {dem[KHONG_DO]} mục không đo được — "
            "đọc lại bảng trên, chúng không chặn nhưng nên biết)"
        )
    print()
    return 0


if __name__ == "__main__":
    # Lưới cuối. Một bảng kiểm sinh ra để THAY vết ngăn xếp bằng câu tiếng Việt
    # thì không được phép tự đổ vết ngăn xếp lên màn hình — nhất là khi nó đang
    # chạy trước mặt hội đồng. Mọi lỗi ngoài dự kiến ra về mã 2 ("không kết
    # luận được"), KHÔNG phải mã 0: im lặng báo xanh là cách hỏng tệ nhất.
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Đã dừng theo yêu cầu (Ctrl-C).")
        raise SystemExit(2) from None
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — cố ý bắt hết, xem ghi chú trên
        print()
        print(f"  BẢNG KIỂM HỎNG GIỮA CHỪNG: {type(e).__name__}: {e}")
        print("  Không kết luận được — coi như CHƯA sẵn sàng cho tới khi chạy lại được.")
        raise SystemExit(2) from None
