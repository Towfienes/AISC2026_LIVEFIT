"""Tóm tắt 3 câu — máy soạn câu TẤT ĐỊNH cho màn kết quả (AI-LAYER lớp 0, S2).

Ba câu tiếng Việt cho mỗi bản kết quả: (1) KẾT LUẬN đúng trạng thái,
(2) BẰNG CHỨNG chính, (3) VIỆC NÊN LÀM tiếp. Toàn bộ là template có kiểm
soát — KHÔNG gọi LLM, không mô hình sinh: mọi con số trong câu đều chép từ
tham số đầu vào (chính là các trường của ``ExperimentSummary`` /
``KetQuaThiNghiem`` / ``BaoCaoTongQuan``), phép tính duy nhất được phép là
định dạng (làm tròn, %, phút) và hiệu số so với NGƯỠNG THIẾT KẾ đã tiền đăng
ký (cần thêm mấy phiên/khối). Mỗi câu mang ``refs`` — đường dẫn JSON của
từng con số — để UI hover ra nguồn (triết lý không-bịa-số ngay trên văn xuôi).

Điều kiện bắt buộc từ phản biện khoa học (ưu tiên #6): CẢ BA trạng thái —
DƯƠNG / NULL / CHƯA ĐỦ ĐIỀU KIỆN — được soạn công phu ngang nhau; câu NULL
phải nói rõ "chưa đủ bằng chứng là một kết quả hợp lệ", không được viết như
một lời xin lỗi. Khóa §7 (``RESULTS_FREEZE_UNTIL``) đứng TRÊN mọi template:
khi ``khoa=True`` không câu nào được chứa ước lượng/KTC/p — chỉ số vận hành.

Huy hiệu bằng chứng (spec AI-LAYER N2): ``thi_nghiem`` CHỈ dành cho câu mà
con số đến từ analyze_outer trên thiết kế ước lượng được — gọi với
``estimable=False`` thì không một câu nào được mang huy hiệu đó (có test
chốt chặn trong ``tests/test_narrate.py``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "BADGE_QUAN_SAT",
    "BADGE_THIEU_DU_LIEU",
    "BADGE_THI_NGHIEM",
    "Cau",
    "tom_tat_gop",
    "tom_tat_phien",
    "trang_thai_ket_luan",
]

BADGE_THI_NGHIEM = "thi_nghiem"
"""Con số trong câu đến từ estimator tiền đăng ký (analyze_outer) — có KTC."""

BADGE_QUAN_SAT = "quan_sat"
"""Số đếm/mô tả vận hành — không suy diễn nhân quả."""

BADGE_THIEU_DU_LIEU = "thieu_du_lieu"
"""Tuyên bố thiếu kèm con số cần thêm — không hạ ngưỡng, không nội suy."""

#: Đơn vị của biến kết quả chính (tiền đăng ký §4.1) — một chỗ, mọi câu dùng chung.
DON_VI = "lượt nhấp trên mỗi 1000 giây·người xem"


@dataclass(frozen=True)
class Cau:
    """Một câu tóm tắt: văn bản + huy hiệu bằng chứng + nguồn của từng số."""

    text: str
    badge: str
    refs: tuple[str, ...] = ()


def trang_thai_ket_luan(estimable: bool, ci_low: float | None, ci_high: float | None) -> str:
    """Phân loại kết quả vào đúng một trạng thái kết luận.

    ``duong``/``am`` — KTC 95% loại 0 (về phía dương/âm); ``null`` — ước lượng
    được nhưng KTC còn chứa 0; ``thieu`` — thiết kế không ước lượng được.
    Cùng một luật với máy sinh demo vàng (routes/demo._trang_thai_ket_qua).
    """
    if not estimable:
        return "thieu"
    if ci_low is not None and ci_low > 0:
        return "duong"
    if ci_high is not None and ci_high < 0:
        return "am"
    return "null"


def _p_text(p_value: float | None, n_draws: int | None) -> str:
    """p-value với SÀN trung thực: kiểm định hoán vị không nói được p nhỏ hơn
    1/(số lần vẽ + 1) — in sàn thay vì một con số chính-xác-giả (cùng luật với
    ``formatP`` phía web)."""
    if p_value is None:
        return "p chưa công bố"
    floor = 1.0 / (n_draws + 1) if n_draws else None
    if floor is not None and p_value <= floor * 1.001:
        return f"p < {floor:.4f}"
    return f"p = {p_value:.4f}"


def _ktc(ci_low: float | None, ci_high: float | None) -> str:
    lo = "—" if ci_low is None else f"{ci_low:+.3f}"
    hi = "—" if ci_high is None else f"{ci_high:+.3f}"
    return f"KTC 95% [{lo}; {hi}]"


def _cham(text: str) -> str:
    """Bảo đảm câu kết thúc bằng dấu chấm — lý do máy chủ có câu có, câu không."""
    t = text.strip()
    return t if t.endswith((".", "!", "?", "…")) else t + "."


def _cau_ket_luan(
    st: str,
    estimate: float | None,
    ci_low: float | None,
    ci_high: float | None,
    ref_goc: str,
) -> Cau:
    """Câu 1 cho trạng thái ước lượng được (duong/am/null) — dùng chung cho
    bản gộp và bản từng phiên."""
    refs = (f"{ref_goc}estimate", f"{ref_goc}ci_low", f"{ref_goc}ci_high")
    if st == "duong":
        return Cau(
            text=(
                f"Hệ thống tạo thêm {estimate:+.3f} {DON_VI} so với khi tắt "
                f"({_ktc(ci_low, ci_high)} — không chứa 0)."
            ),
            badge=BADGE_THI_NGHIEM,
            refs=refs,
        )
    if st == "am":
        return Cau(
            text=(
                f"Hệ thống làm GIẢM {abs(estimate or 0.0):.3f} {DON_VI} "
                f"({_ktc(ci_low, ci_high)} — không chứa 0); tác dụng ngược cũng là "
                "một phép đo thật, cần xem lại chiến lược ghim trước khi chạy tiếp."
            ),
            badge=BADGE_THI_NGHIEM,
            refs=refs,
        )
    return Cau(
        text=(
            "Chưa đủ bằng chứng để kết luận hệ thống làm tăng hay giảm lượt nhấp "
            f"(ước lượng {estimate:+.3f}, {_ktc(ci_low, ci_high)} còn chứa 0) — "
            "và đó là một kết quả hợp lệ, không phải thất bại."
        ),
        badge=BADGE_THI_NGHIEM,
        refs=refs,
    )


def _cau_bang_chung(
    n_blocks: int,
    n_on: int,
    n_off: int,
    p_value: float | None,
    n_draws: int | None,
    ref_goc: str,
    n_sessions: int | None = None,
) -> Cau:
    pham_vi = f" từ {n_sessions} phiên" if n_sessions is not None else ""
    ve_lai = f"kiểm định hoán vị {n_draws} lần vẽ lại cho " if n_draws else ""
    return Cau(
        text=(
            f"Bằng chứng: {n_blocks} khối đo được ({n_on} BẬT / {n_off} TẮT)"
            f"{pham_vi}; {ve_lai}{_p_text(p_value, n_draws)}."
        ),
        badge=BADGE_THI_NGHIEM,
        refs=(
            f"{ref_goc}n_blocks",
            f"{ref_goc}n_on",
            f"{ref_goc}n_off",
            f"{ref_goc}p_value",
            f"{ref_goc}n_draws",
        ),
    )


# ---------------------------------------------------------------------------
# Bản GỘP — /experiment/summary
# ---------------------------------------------------------------------------


def tom_tat_gop(
    *,
    estimable: bool,
    n_sessions: int,
    n_blocks: int,
    n_on: int,
    n_off: int,
    khoa: bool = False,
    ly_do_khoa: str | None = None,
    estimate: float | None = None,
    ci_low: float | None = None,
    ci_high: float | None = None,
    p_value: float | None = None,
    n_draws: int | None = None,
    valid_clicks: int | None = None,
    measured_cv: float | None = None,
    measured_compliance: float | None = None,
    power_table: Sequence[dict[str, Any]] = (),
    message: str | None = None,
    nguong_phien: int = 2,
    nguong_khoi: int = 8,
) -> list[Cau]:
    """Ba câu cho bản gộp mọi phiên. Luôn trả về ĐÚNG 3 câu.

    ``khoa=True`` (tiền đăng ký §7): các tham số suy diễn bị bỏ qua kể cả khi
    được truyền — không câu nào chứa ước lượng/KTC/p trong cửa sổ khóa.
    """
    nhap = f", {valid_clicks} lượt nhấp hợp lệ" if valid_clicks is not None else ""

    if khoa:
        return [
            Cau(
                text=_cham(
                    "Chưa công bố được kết luận: "
                    + (ly_do_khoa or "ước lượng hiệu ứng đang bị khóa theo tiền đăng ký §7")
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=("message",),
            ),
            Cau(
                text=(
                    f"Số liệu vận hành tích lũy: {n_sessions} phiên, {n_blocks} khối "
                    f"đo được ({n_on} BẬT / {n_off} TẮT){nhap}."
                ),
                badge=BADGE_QUAN_SAT,
                refs=("n_sessions", "n_blocks", "n_on", "n_off", "valid_clicks"),
            ),
            Cau(
                text=(
                    "Việc nên làm: tiếp tục chạy phiên theo lịch đã bốc thăm; tới ngày "
                    f"mở khóa, ước lượng chạy một lần trên toàn bộ {n_blocks} khối tích "
                    "lũy mà chưa ai nhìn trộm giữa chừng."
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=("n_blocks",),
            ),
        ]

    if not estimable:
        thieu_gi: list[str] = []
        if n_sessions < nguong_phien:
            thieu_gi.append(f"thêm {nguong_phien - n_sessions} phiên")
        if n_blocks < nguong_khoi:
            thieu_gi.append(f"thêm {nguong_khoi - n_blocks} khối đo được")
        if thieu_gi:
            viec = (
                "Việc nên làm: chạy thêm phiên có lịch bốc thăm trước giờ phát — cần "
                + " và ".join(thieu_gi)
                + f" để đạt ngưỡng ước lượng ({nguong_phien} phiên, {nguong_khoi} khối)."
            )
        else:
            viec = (
                "Việc nên làm: chạy thêm phiên có lịch bốc thăm trước giờ phát để mỗi "
                "nhánh BẬT/TẮT có thêm khối đo được — thiết kế hiện tại chưa kiểm định nổi."
            )
        return [
            Cau(
                text=_cham(
                    "Thiết kế chưa đủ điều kiện để ước lượng tác động: "
                    + (
                        message
                        or (
                            f"chưa đạt ngưỡng tối thiểu {nguong_phien} phiên "
                            f"và {nguong_khoi} khối đo được"
                        )
                    )
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=("message", "estimable"),
            ),
            Cau(
                text=(
                    f"Hiện trạng đo được: {n_sessions} phiên trong mẫu, {n_blocks} khối "
                    f"({n_on} BẬT / {n_off} TẮT){nhap}."
                ),
                badge=BADGE_QUAN_SAT,
                refs=("n_sessions", "n_blocks", "n_on", "n_off", "valid_clicks"),
            ),
            Cau(text=viec, badge=BADGE_THIEU_DU_LIEU, refs=("n_sessions", "n_blocks")),
        ]

    st = trang_thai_ket_luan(True, ci_low, ci_high)
    cau1 = _cau_ket_luan(st, estimate, ci_low, ci_high, ref_goc="")
    cau2 = _cau_bang_chung(
        n_blocks, n_on, n_off, p_value, n_draws, ref_goc="", n_sessions=n_sessions
    )

    if st in ("duong", "am"):
        if measured_compliance is not None:
            duoi = (
                f"; tuân thủ đo được {measured_compliance * 100:.0f}% — giữ kỷ luật thao "
                "tác khối BẬT để ước lượng không bị pha loãng thêm"
            )
            refs3: tuple[str, ...] = ("measured_compliance",)
        elif measured_cv is not None:
            duoi = f"; CV đo được {measured_cv:.2f} — thêm khối sẽ thu hẹp khoảng tin cậy"
            refs3 = ("measured_cv",)
        else:
            duoi = ""
            refs3 = ("n_blocks",)
        cau3 = Cau(
            text=(
                "Việc nên làm: giữ nguyên thiết kế và cách vận hành ở phiên tới, tích "
                f"lũy thêm khối để thu hẹp khoảng tin cậy{duoi}."
            ),
            badge=BADGE_QUAN_SAT,
            refs=refs3,
        )
    else:  # null — câu "cần thêm bao nhiêu" giải từ bảng lực với CV ĐO ĐƯỢC
        row = next(iter(power_table), None)
        if row is not None and int(row.get("n_sessions", 0)) > n_sessions:
            them = int(row["n_sessions"]) - n_sessions
            cau3 = Cau(
                text=(
                    f"Việc nên làm: tích lũy thêm ~{them} phiên (đủ {row['n_sessions']} "
                    f"phiên, mỗi phiên ~{row['blocks_per_session']} khối đo) để phát hiện "
                    f"được hiệu ứng cỡ {row['mde_relative'] * 100:.0f}% với CV đo được "
                    f"{row['cv']:.2f}; nếu chuỗi vẫn null, hiệu ứng thật (nếu có) nhỏ hơn "
                    "ngưỡng đó."
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=(
                    "power_table[0].n_sessions",
                    "power_table[0].blocks_per_session",
                    "power_table[0].mde_relative",
                    "power_table[0].cv",
                    "n_sessions",
                ),
            )
        else:
            cau3 = Cau(
                text=(
                    "Việc nên làm: tiếp tục tích lũy khối cùng thiết kế; nếu chuỗi vẫn "
                    f"null, hiệu ứng thật (nếu có) nhỏ hơn ngưỡng phát hiện của "
                    f"{n_blocks} khối hiện tại."
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=("n_blocks",),
            )
    return [cau1, cau2, cau3]


# ---------------------------------------------------------------------------
# Bản TỪNG PHIÊN — /sessions/{id}/bao-cao
# ---------------------------------------------------------------------------

#: Tiền tố đường dẫn JSON của khối nhân quả trong BaoCaoOut.
_KQ = "ket_qua_thi_nghiem."


def tom_tat_phien(
    *,
    loai_phien: str,
    tong_binh_luan: int,
    luot_nhap_hop_le: int | None = None,
    thoi_luong_s: float | None = None,
    khoa: bool = False,
    ly_do_khoa: str | None = None,
    estimable: bool = False,
    estimate: float | None = None,
    ci_low: float | None = None,
    ci_high: float | None = None,
    p_value: float | None = None,
    n_draws: int | None = None,
    n_blocks: int = 0,
    n_on: int = 0,
    n_off: int = 0,
    message: str | None = None,
    nguong_khoi: int = 4,
) -> list[Cau]:
    """Ba câu cho báo cáo MỘT phiên. Luôn trả về ĐÚNG 3 câu.

    ``loai_phien="quan_sat"``: không có lịch gán ⇒ không câu nào nhân quả và
    không câu nào mang huy hiệu ``thi_nghiem`` — nói thẳng đó là thiết kế,
    không phải thiếu sót của buổi live.
    """
    mo_ta_phan = [f"{tong_binh_luan} bình luận"]
    refs_mo_ta = ["tong_quan.tong_binh_luan"]
    if luot_nhap_hop_le is not None:
        mo_ta_phan.append(f"{luot_nhap_hop_le} lượt nhấp hợp lệ")
        refs_mo_ta.append("tong_quan.luot_nhap_hop_le")
    else:
        mo_ta_phan.append("lượt nhấp qua link đo: THIẾU nguồn")
        refs_mo_ta.append("tong_quan.thieu.luot_nhap")
    if thoi_luong_s is not None:
        mo_ta_phan.append(f"thời lượng {thoi_luong_s / 60:.0f} phút")
        refs_mo_ta.append("tong_quan.thoi_luong_s")
    mo_ta = ", ".join(mo_ta_phan)

    if loai_phien == "quan_sat":
        return [
            Cau(
                text=(
                    "Phiên quan sát — không có lịch bốc thăm BẬT/TẮT nên không tồn tại "
                    "số nhân quả nào cho phiên này; hệ thống nói thẳng điều đó thay vì "
                    "trả một con số không có nguồn."
                ),
                badge=BADGE_QUAN_SAT,
                refs=("loai_phien",),
            ),
            Cau(text=f"Ghi nhận mô tả: {mo_ta}.", badge=BADGE_QUAN_SAT, refs=tuple(refs_mo_ta)),
            Cau(
                text=(
                    "Việc nên làm: muốn đo tác động thật, chạy phiên có bốc thăm BẬT/TẮT "
                    f"trước giờ phát — cần ít nhất {nguong_khoi} khối đo được để có ước "
                    "lượng đầu tiên."
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=("loai_phien",),
            ),
        ]

    if khoa:
        return [
            Cau(
                text=_cham(
                    "Chưa công bố được kết luận: "
                    + (ly_do_khoa or "ước lượng hiệu ứng đang bị khóa theo tiền đăng ký §7")
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=(f"{_KQ}ly_do_khoa",),
            ),
            Cau(
                text=(
                    f"Số liệu vận hành của phiên: {n_blocks} khối đo được ({n_on} BẬT / "
                    f"{n_off} TẮT), {mo_ta}."
                ),
                badge=BADGE_QUAN_SAT,
                refs=(f"{_KQ}n_blocks", f"{_KQ}n_on", f"{_KQ}n_off", *refs_mo_ta),
            ),
            Cau(
                text=(
                    "Việc nên làm: tiếp tục chạy phiên theo lịch; tới ngày mở khóa, "
                    f"{n_blocks} khối của phiên này vào ước lượng gộp mà chưa ai nhìn "
                    "trộm giữa chừng."
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=(f"{_KQ}n_blocks",),
            ),
        ]

    if not estimable:
        return [
            Cau(
                text=_cham(
                    "Thiết kế chưa đủ điều kiện để ước lượng tác động: "
                    + (message or f"chưa đủ {nguong_khoi} khối đo được cho một ước lượng")
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=(f"{_KQ}message", f"{_KQ}estimable"),
            ),
            Cau(
                text=(f"Hiện trạng đo được: {n_blocks} khối ({n_on} BẬT / {n_off} TẮT), {mo_ta}."),
                badge=BADGE_QUAN_SAT,
                refs=(f"{_KQ}n_blocks", f"{_KQ}n_on", f"{_KQ}n_off", *refs_mo_ta),
            ),
            Cau(
                text=(
                    "Việc nên làm: phiên tới kéo dài thời lượng để có ít nhất "
                    f"{nguong_khoi} khối đo được (mỗi khối là một lượt so sánh BẬT/TẮT); "
                    "phần mô tả của phiên này vẫn dùng được nguyên vẹn."
                ),
                badge=BADGE_THIEU_DU_LIEU,
                refs=(f"{_KQ}n_blocks",),
            ),
        ]

    st = trang_thai_ket_luan(True, ci_low, ci_high)
    cau1 = _cau_ket_luan(st, estimate, ci_low, ci_high, ref_goc=_KQ)
    cau2 = _cau_bang_chung(n_blocks, n_on, n_off, p_value, n_draws, ref_goc=_KQ)
    if st in ("duong", "am"):
        cau3 = Cau(
            text=(
                "Việc nên làm: lặp lại đúng thiết kế này ở phiên tới — một phiên chưa "
                f"phải chuỗi; {n_blocks} khối hiện có mới đến từ một buổi, kết luận gộp "
                "nhiều phiên nằm ở trang Kết quả."
            ),
            badge=BADGE_QUAN_SAT,
            refs=(f"{_KQ}n_blocks",),
        )
    else:
        cau3 = Cau(
            text=(
                f"Việc nên làm: một phiên {n_blocks} khối chỉ phát hiện nổi hiệu ứng "
                "rất lớn — tích lũy thêm phiên cùng thiết kế rồi đọc bản gộp; nếu chuỗi "
                "vẫn null, hiệu ứng thật (nếu có) nhỏ hơn ngưỡng phát hiện."
            ),
            badge=BADGE_THIEU_DU_LIEU,
            refs=(f"{_KQ}n_blocks",),
        )
    return [cau1, cau2, cau3]
