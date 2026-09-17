"""Gate phản biện 17/09 — nhóm web-khác: bộ thu bình luận, nhập đơn CSV, wizard
chạy thử, báo cáo phiên chạy thử.

Năm lỗi đã được hai người phản biện xác nhận độc lập hoặc thấy tận mắt khi chạy
đầu-cuối trên trình duyệt:

K1  ``IngestPanel`` giữ nền tảng/link/form của phiên trước khi đổi phiên trên
    bàn: ô chọn hiện "YouTube" nhưng gửi ``mo_phong`` (máy chủ trả 422), và link
    buổi live của phiên A được điền sẵn cho phiên B (bấm là B thu bình luận A).
K2  ``OrdersPanel`` đọc tệp bằng ``readAsText(f, "utf-8")`` — tệp CSV Excel lưu
    bằng bảng mã 1258 bị giải mã hỏng IM LẶNG, máy chủ báo "thiếu cột" cho một
    tệp mở bằng Excel thấy đủ cột.
K3  ``getPlatforms`` hỏng một lần lúc gắn ⇒ khung bộ thu chết vĩnh viễn, im lặng.
K4  wizard ``/chay-phien`` không tạo được phiên chạy thử: buổi tập bằng sản phẩm
    mẫu + link example.com thành phiên THẬT, nguồn Mô phỏng không bao giờ được mời.
K5  báo cáo phiên chạy thử chỉ ghi "PHIÊN THÍ NGHIỆM", không nói chạy thử hay bình
    luận tổng hợp; bàn trợ live không nói tên nguồn Mô phỏng khi bộ thu đang chạy.

Như các gate web khác: ĐỌC MÃ NGUỒN để giữ bất biến cấu trúc, và CHẠY THẬT các
hàm thuần (tách nguyên văn khỏi .tsx, node ≥ 22 tự bỏ chú thích kiểu) trên DỮ
LIỆU THẬT của máy chủ — danh sách nền tảng của ``/platforms``, trạng thái bộ thu
Mô phỏng đã chạy thật, báo cáo thật, và nội dung CSV được chính máy chủ nhập.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "src"
INGEST = SRC / "components" / "IngestPanel.tsx"
ORDERS = SRC / "components" / "OrdersPanel.tsx"
WIZARD = SRC / "app" / "chay-phien" / "page.tsx"
BAO_CAO = SRC / "app" / "bao-cao" / "[id]" / "page.tsx"
API_TS = SRC / "lib" / "api.ts"
TYPES_TS = SRC / "lib" / "types.ts"


# ---------------------------------------------------------------------------
# tiện ích đọc nguồn
# ---------------------------------------------------------------------------
def read(p: Path) -> str:
    assert p.exists(), f"không tìm thấy {p}"
    return p.read_text(encoding="utf-8")


def code(src: str) -> str:
    """Nguồn đã bỏ chú thích — chú thích được phép nhắc phản-mẫu bị cấm."""
    src = re.sub(r"\{/\*.*?\*/\}", " ", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<![:\w\"'])//.*$", " ", src)


def function_body(src: str, name: str) -> str:
    m = re.search(rf"(?m)^(?:export default )?(?:async )?function {name}\b", src)
    assert m, f"không còn hàm {name}"
    return src[m.start() : src.index("\n}\n", m.start()) + 2]


def _statement_end(src: str, start: int) -> int:
    """Vị trí ngay sau dấu ``;`` kết thúc câu lệnh bắt đầu ở ``start`` (bỏ qua
    ngoặc và chuỗi)."""
    depth = 0
    quote: str | None = None
    i = start
    while i < len(src):
        ch = src[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ";" and depth == 0:
            return i + 1
        i += 1
    raise AssertionError("câu lệnh không kết thúc")


def extract(src: str, name: str) -> str:
    """Khai báo cấp tệp ``function``/``const``/``type`` tên ``name``, nguyên văn."""
    m = re.search(rf"(?m)^function {name}\(", src)
    if m:
        return src[m.start() : src.index("\n}\n", m.start()) + 2]
    m = re.search(rf"(?m)^(?:const|type) {name}\b", src)
    assert m, f"không còn khai báo {name}"
    return src[m.start() : _statement_end(src, m.start())] + "\n"


def js(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def node_eval(tmp_path: Path, path: Path, names: list[str], expr: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("không có node — bỏ qua phần chạy thử hàm thuần")
    src = read(path)
    module = "\n".join(extract(src, n) for n in names)
    script = tmp_path / f"{path.stem}_pure.mts"
    script.write_text(module + f"\nconsole.log(JSON.stringify({expr}));\n", encoding="utf-8")
    out = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if out.returncode != 0 and "strip-types" in out.stderr and "bad option" in out.stderr:
        pytest.skip("node quá cũ, chưa bỏ được chú thích kiểu")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# máy chủ thật
# ---------------------------------------------------------------------------
@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    with TestClient(create_app(store=InMemoryStore())) as c:
        yield c
    get_settings.cache_clear()


def _tao_phien(client: TestClient, **kw) -> dict:
    body = {"platform": "youtube", "planned_duration_min": 30, **kw}
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _cho_bo_thu_dung(client: TestClient, sid: str, timeout: float = 30.0) -> dict:
    han = time.monotonic() + timeout
    while True:
        st = client.get(f"/sessions/{sid}/ingest").json()
        if not st["running"] and st["state"] != "chua_bat":
            return st
        assert time.monotonic() < han, f"bộ thu Mô phỏng không chạy xong: {st}"
        time.sleep(0.02)


@pytest.fixture
def phien_chay_thu_da_thu_mo_phong(client):
    """Phiên CHẠY THỬ đã chạy trọn một buổi Mô phỏng thật qua HTTP."""
    s = _tao_phien(client, dry_run=True)
    sid = s["session_id"]
    r = client.post(
        f"/sessions/{sid}/ingest", json={"platform": "mo_phong", "source": "ngan x1000"}
    )
    assert r.status_code == 202, r.text
    st = _cho_bo_thu_dung(client, sid)
    assert st["comments_posted"] > 0, "tiền đề: nguồn Mô phỏng phải thật sự ghi bình luận"
    return client, sid, st


INGEST_PURE = [
    "THU_DUOC",
    "NEN_TANG_MO_PHONG",
    "TEN_NGUON",
    "nenTangChoPhep",
    "mucDangChon",
    "nenTangMacDinh",
    "nhanNguon",
    "canDocLaiNenTang",
]


# ===========================================================================
# K1 — đổi phiên trên bàn: không mang nền tảng, link, form, cờ bận sang phiên khác
# ===========================================================================
def test_k1_nen_tang_mo_phong_khong_bao_gio_duoc_gui_tu_phien_that(client, tmp_path):
    platforms = client.get("/platforms").json()
    assert "mo_phong" in {p["platform"] for p in platforms}, "tiền đề: máy chủ có nguồn Mô phỏng"
    that = _tao_phien(client)
    r = client.post(
        f"/sessions/{that['session_id']}/ingest", json={"platform": "mo_phong", "source": ""}
    )
    assert r.status_code == 422, "tiền đề: gửi mo_phong cho phiên thật là lỗi người dùng thấy"

    got = node_eval(
        tmp_path,
        INGEST,
        INGEST_PURE,
        f"""(() => {{
          const list = {js(platforms)};
          const phienThat = nenTangChoPhep(false);
          const phienThu = nenTangChoPhep(true);
          return {{
            thatMoiMoPhong: phienThat.includes("mo_phong"),
            // Phiên A (chạy thử) đã chọn Mô phỏng, đổi sang phiên thật B:
            conChonMoPhong: mucDangChon(list, "mo_phong", phienThat),
            chonLai: nenTangMacDinh(list, {js(that["platform"])}, phienThat),
            thuVanChon: mucDangChon(list, "mo_phong", phienThu)?.platform ?? null,
            chuaDocDanhSach: nenTangMacDinh(null, "youtube", phienThat),
            khongCoTrenMayChu: mucDangChon(list.filter((p) => p.platform !== "youtube"),
                                           "youtube", phienThat),
          }};
        }})()""",
    )
    assert got["thatMoiMoPhong"] is False
    assert got["conChonMoPhong"] is None, (
        "phiên thật mà mục đang chọn vẫn là mo_phong ⇒ nút Bật mở và gửi mo_phong trong khi ô "
        "chọn hiện YouTube"
    )
    assert got["chonLai"] == that["platform"], (
        "đổi sang phiên thật phải chọn lại nền tảng của phiên"
    )
    assert got["thuVanChon"] == "mo_phong", "phiên chạy thử vẫn được chọn Mô phỏng"
    assert got["chuaDocDanhSach"] == "", "chưa đọc được danh sách thì không đoán nền tảng"
    assert got["khongCoTrenMayChu"] is None


def test_k1_bo_nho_bo_thu_gan_theo_ma_phien_va_phan_hoi_muon_bi_bo_qua():
    src = code(read(INGEST))
    wrapper = function_body(src, "IngestPanel")
    assert "<BoThuPhien key={props.sessionId}" in wrapper, (
        "phần có trạng thái phải gắn lại theo mã phiên — bàn trợ live đổi phiên mà không gắn lại "
        "panel, nên link buổi live của phiên A từng được điền sẵn cho phiên B"
    )
    assert "useState" not in wrapper, "vỏ ngoài không được giữ trạng thái nào qua các phiên"

    body = function_body(src, "BoThuPhien")
    for state in (
        'const [platform, setPlatform] = useState<string>("")',
        'const [source, setSource] = useState("")',
        "const [moForm, setMoForm] = useState(false)",
        "const [busy, setBusy] = useState(false)",
        "const [status, setStatus] = useState<IngestStatus | null>(null)",
    ):
        assert state in body, f"trạng thái của MỘT phiên phải nằm trong BoThuPhien: {state}"

    bat = body[body.index("const batDau") : body.index("const tat")]
    assert "if (!chon) return;" in bat
    assert "platform: chon.platform as IngestPlatform" in bat, (
        "gửi đúng nền tảng ô chọn đang hiện (mục đã kiểm còn được phép), không gửi state thô"
    )
    assert bat.count("conSong.current") >= 3, "phản hồi về sau khi đổi phiên không được ghi đè"
    tat = body[body.index("const tat") : body.index("const state: IngestState")]
    assert tat.count("conSong.current") >= 3
    refresh = body[body.index("const refresh") : body.index("const batDau")]
    assert "if (conSong.current) setStatus(st)" in refresh
    assert 'value={chon ? platform : ""}' in body, "ô chọn không được hiện một mục khác mục sẽ gửi"


# ===========================================================================
# K3 — danh sách nền tảng tải hỏng: nói ra, cho thử lại, tự đọc lại
# ===========================================================================
def test_k3_doc_lai_danh_sach_nen_tang_khi_hong_hoac_chua_san_sang(client, tmp_path):
    platforms = client.get("/platforms").json()
    got = node_eval(
        tmp_path,
        INGEST,
        INGEST_PURE,
        f"""(() => {{
          const list = {js(platforms)};
          const sanSang = list.find((p) => p.ready);
          const chuaSanSang = {{ ...sanSang, ready: false, missing: ["YOUTUBE_API_KEY"] }};
          return [
            canDocLaiNenTang(null, true, null),
            canDocLaiNenTang(null, false, null),
            canDocLaiNenTang(list, true, sanSang),
            canDocLaiNenTang(list, false, chuaSanSang),
            canDocLaiNenTang(list, false, sanSang),
          ];
        }})()""",
    )
    assert got == [True, True, True, True, False], (
        "lỗi một lần lúc gắn không được thành lỗi vĩnh viễn; đã đọc được và sẵn sàng thì thôi hỏi"
    )


def test_k3_loi_tai_danh_sach_nen_tang_duoc_noi_ra_voi_nut_thu_lai():
    raw = read(INGEST)
    src = code(raw)
    assert "setPlatforms([])" not in src, (
        "lỗi tải từng biến thành danh sách rỗng: ô chọn trống, nút khoá, không câu nào giải thích"
    )
    body = function_body(src, "BoThuPhien")
    tai = body[body.index("const taiNenTang") : body.index("const choPhep")]
    catch = tai[tai.index("catch") :]
    assert "setPlatformsErr(true)" in catch
    assert "setPlatformsErr(false)" in tai[: tai.index("catch")]

    assert "const canDocLai = canDocLaiNenTang(platforms, platformsErr, chon);" in body
    poll = body[body.index("if (!canDocLai) return;") - 40 :][:260]
    assert "setInterval(() => void taiNenTang(), POLL_NEN_TANG_MS)" in poll
    assert "clearInterval" in poll

    at = body.index("Chưa đọc được danh sách nền tảng từ máy chủ")
    khoi = body[body.rindex("{hienForm", 0, at) : body.index("</Callout>", at)]
    assert "platforms == null && platformsErr" in khoi
    assert "onClick={() => void taiNenTang()}" in khoi
    assert "Thử lại" in khoi

    at = body.index("Máy chủ chưa có bộ thu nào dùng được cho phiên này")
    assert (
        "platforms != null && luaChon.length === 0" in body[body.rindex("{hienForm", 0, at) : at]
    ), "đọc được danh sách mà không có nền tảng nào được mời thì cũng phải nói, không để form chết"


# ===========================================================================
# K5 (bàn) — bộ thu đang chạy luôn nói tên nguồn; Mô phỏng nói là tổng hợp
# ===========================================================================
def test_k5_dong_trang_thai_noi_nguon_mo_phong_la_binh_luan_tong_hop(
    phien_chay_thu_da_thu_mo_phong, tmp_path
):
    client, _sid, st = phien_chay_thu_da_thu_mo_phong
    platforms = client.get("/platforms").json()
    ten_youtube = next(p["ten"] for p in platforms if p["platform"] == "youtube")
    got = node_eval(
        tmp_path,
        INGEST,
        INGEST_PURE,
        f"""[
          nhanNguon({js(st["platform"])}, {js(platforms)}),
          nhanNguon("youtube", {js(platforms)}),
          nhanNguon("facebook", null),
          nhanNguon(null, {js(platforms)}),
        ]""",
    )
    mo_phong, youtube, facebook_chua_doc, khong_co = got
    assert mo_phong["tongHop"] is True
    for chu in ("Mô phỏng", "tổng hợp", "không phải khách thật"):
        assert chu in mo_phong["ten"], f"nguồn Mô phỏng phải nói {chu!r}: {mo_phong['ten']!r}"
    assert youtube == {"ten": ten_youtube, "tongHop": False}
    assert facebook_chua_doc == {"ten": "Facebook Live", "tongHop": False}
    assert khong_co is None

    body = function_body(code(read(INGEST)), "BoThuPhien")
    assert (
        'const nguon = status && state !== "chua_bat" '
        "? nhanNguon(status.platform, platforms) : null;"
    ) in body
    dong = body[body.index("const dongTrangThai") : body.index("const hienForm")]
    assert "Nguồn: {nguon.ten}" in dong
    assert "nguon.tongHop" in dong, "nguồn tổng hợp phải nổi bật"
    assert "text-warn-ink" in dong, "nguồn tổng hợp phải nổi bật"
    # Dòng trạng thái hiện ở CẢ chế độ gọn của bàn trợ live: nó đứng NGAY SAU điều
    # kiện tiêu đề đã đóng, trong khối đầu của <section>, không nằm sau !compact.
    ret = " ".join(body[body.rindex("return (") :].split())
    assert ret.count("{dongTrangThai}") == 1
    assert re.search(
        r'<section[^>]*> <div className="[^"]*"> <div className="min-w-0"> '
        r"\{!compact && !hideTitle && \( <p[^>]*>Nguồn bình luận</p> \)\} \{dongTrangThai\}",
        ret,
    ), "dòng trạng thái (có tên nguồn) phải hiện cả ở chế độ gọn"


# ===========================================================================
# K2 — nhập đơn: tệp CSV bảng mã 1258 của Excel không bị giải mã hỏng im lặng
# ===========================================================================
CSV_EXCEL = "mã đơn,thời gian,tổng tiền\nDH001,17/09/2026 20:05,125000\n"


def excel_cp1258(text: str) -> bytes:
    """Byte Excel trên Windows tiếng Việt ghi cho "CSV (Comma delimited)": bảng mã
    1258 chỉ có chữ mang dấu phụ (ơ, ô, ê, đ…), dấu THANH là ký tự tổ hợp riêng."""
    out = bytearray()
    for ch in unicodedata.normalize("NFC", text):
        try:
            out += ch.encode("cp1258")
            continue
        except UnicodeEncodeError:
            pass
        d = unicodedata.normalize("NFD", ch)
        goc = unicodedata.normalize("NFC", d[:2])
        if len(d) > 2 and len(goc) == 1:
            out += goc.encode("cp1258") + d[2:].encode("cp1258")
        else:
            out += d.encode("cp1258")
    return bytes(out)


ORDERS_PURE = ["BangMa", "docChuTuByte", "ghiChuBangMa", "canhBaoTieuDe"]


def test_k2_tep_csv_bang_ma_1258_duoc_doc_dung_va_may_chu_nhap_duoc(client, tmp_path):
    cp = excel_cp1258(CSV_EXCEL)
    with pytest.raises(UnicodeDecodeError):
        cp.decode("utf-8")
    # Thứ readAsText(f, "utf-8") từng đưa vào ô dán: byte hỏng thành "�", KHÔNG báo lỗi.
    hong = cp.decode("utf-8", errors="replace")
    assert "�" in hong

    sid = _tao_phien(client, platform="facebook")["session_id"]
    r = client.post(f"/sessions/{sid}/orders/import", json={"csv": hong})
    assert r.status_code == 422
    assert "thiếu cột" in r.json()["detail"], (
        "tiền đề: máy chủ chỉ nói 'thiếu cột', không nói nguyên nhân là bảng mã"
    )

    utf8 = CSV_EXCEL.encode("utf-8")
    bom = b"\xef\xbb\xbf" + utf8
    utf16 = b"\xff\xfe" + CSV_EXCEL.encode("utf-16-le")
    got = node_eval(
        tmp_path,
        ORDERS,
        ORDERS_PURE,
        f"""(() => {{
          const doc = (b) => docChuTuByte(new Uint8Array(b));
          const cp = doc({js(list(cp))});
          return {{
            cp,
            utf8: doc({js(list(utf8))}),
            bom: doc({js(list(bom))}),
            utf16: doc({js(list(utf16))}),
            ghiChuCp: ghiChuBangMa(cp.bangMa, "don.csv"),
            ghiChuUtf8: ghiChuBangMa("utf-8", "don.csv"),
            nfc: cp.chu === cp.chu.normalize("NFC"),
          }};
        }})()""",
    )
    assert got["cp"] == {"chu": CSV_EXCEL, "bangMa": "windows-1258"}
    assert got["nfc"], "1258 cho dấu thanh tổ hợp — phải chuẩn hoá NFC như tên cột máy chủ"
    assert got["utf8"] == {"chu": CSV_EXCEL, "bangMa": "utf-8"}
    assert got["bom"] == {"chu": CSV_EXCEL, "bangMa": "utf-8"}, "BOM không được lọt vào tên cột"
    assert got["utf16"] == {"chu": CSV_EXCEL, "bangMa": "utf-16le"}
    assert "1258" in got["ghiChuCp"]
    assert "CSV UTF-8" in got["ghiChuCp"]
    assert got["ghiChuUtf8"] is None

    r = client.post(f"/sessions/{sid}/orders/import", json={"csv": got["cp"]["chu"].strip()})
    assert r.status_code == 200, r.text
    assert r.json()["nhap_moi"] == 1, "chữ đọc lại từ tệp 1258 phải được máy chủ nhận đủ cột"


def test_k2_dong_ten_cot_hong_duoc_noi_nguyen_nhan_truoc_khi_nhap(tmp_path):
    hong = excel_cp1258(CSV_EXCEL).decode("utf-8", errors="replace")
    mat_dau = CSV_EXCEL.encode("cp1252", errors="replace").decode("cp1252")  # Excel máy Anh
    tab = CSV_EXCEL.replace(",", "\t")
    cham_phay = CSV_EXCEL.replace(",", ";")
    got = node_eval(
        tmp_path,
        ORDERS,
        ORDERS_PURE,
        f"[{', '.join(js(x) for x in (hong, mat_dau, tab, cham_phay, CSV_EXCEL, '', 'ts,gross'))}]"
        ".map(canhBaoTieuDe)",
    )
    loi_hong, loi_mat_dau, loi_tab, loi_cham_phay, dung, rong, ascii_ = got
    for loi in (loi_hong, loi_mat_dau):
        assert loi, "dòng tên cột mất dấu phải được cảnh báo"
        assert "CSV UTF-8" in loi, "dòng tên cột mất dấu phải nói cách lưu lại"
    assert loi_tab
    assert "TAB" in loi_tab
    assert loi_cham_phay
    assert "chấm phẩy" in loi_cham_phay
    assert (dung, rong, ascii_) == (None, None, None), "tệp đúng không được bị cảnh báo"


def test_k2_orders_panel_doc_byte_va_chuan_hoa_truoc_khi_gui():
    src = code(read(ORDERS))
    body = function_body(src, "OrdersPanel")
    on_file = body[body.index("const onFile") : body.index("const tieuDeLoi")]
    assert "reader.readAsArrayBuffer(f)" in on_file, (
        'readAsText(f, "utf-8") nuốt lỗi bảng mã im lặng — phải đọc byte rồi tự dò'
    )
    assert "readAsText(" not in src
    assert "docChuTuByte(new Uint8Array(reader.result))" in on_file
    assert "setFileNote(ghiChuBangMa(bangMa, f.name))" in on_file
    assert "new TextDecoder(bangMa, { fatal })" in function_body(src, "docChuTuByte")
    assert 'doc("utf-8", true)' in src, "UTF-8 phải thử ở chế độ NGHIÊM (fatal)"
    submit = body[body.index("const submit") : body.index("const coDon")]
    assert 'csv.normalize("NFC").trim()' in submit, "nội dung dán tay cũng phải chuẩn hoá NFC"
    assert "const tieuDeLoi = useMemo(() => canhBaoTieuDe(csv), [csv]);" in body
    assert "{tieuDeLoi ? (" in body
    assert "{fileName && fileNote ? (" in body


# ===========================================================================
# K4 — wizard tạo được phiên CHẠY THỬ; bước 4 nói vì sao không có Mô phỏng
# ===========================================================================
WIZARD_PURE = ["isSampleUrl", "sampleUrlFor", "choPhepMoPhong", "chayThuHieuLuc"]


def test_k4_link_mau_mac_dinh_chay_thu_va_phien_tao_ra_moi_nguon_mo_phong(client, tmp_path):
    got = node_eval(
        tmp_path,
        WIZARD,
        WIZARD_PURE,
        """[
          chayThuHieuLuc(null, isSampleUrl(sampleUrlFor("ao-khoac-du-2-lop"))),
          chayThuHieuLuc(undefined, isSampleUrl("https://shopee.vn/ao-khoac")),
          chayThuHieuLuc(false, true),
          chayThuHieuLuc(true, false),
        ]""",
    )
    assert got == [True, False, False, True], (
        "link mẫu example.com ⇒ chọn sẵn Chạy thử; người bán đã tự chọn thì theo đúng lựa chọn"
    )

    # Đúng thân yêu cầu wizard gửi (makeSession), cờ lấy từ chayThuHieuLuc ở trên.
    s = _tao_phien(
        client,
        title="Tập dượt với sản phẩm mẫu",
        mode="auto",
        planned_duration_min=90,
        dry_run=got[0],
    )
    assert (s["dry_run"], s["is_demo"]) == (True, False)
    assert node_eval(tmp_path, WIZARD, WIZARD_PURE, f"choPhepMoPhong({js(s)})") is True, (
        "phiên chạy thử tạo từ wizard phải được mời nguồn Mô phỏng ở bước 4"
    )
    r = client.post(
        f"/sessions/{s['session_id']}/ingest", json={"platform": "mo_phong", "source": "ngan x1000"}
    )
    assert r.status_code == 202, r.text
    client.post(f"/sessions/{s['session_id']}/ingest/stop")


def _step(src: str, n: int) -> str:
    start = src.index(f"{{step === {n} ? (")
    nxt = src.find(f"{{step === {n + 1} ? (", start)
    return src[start : nxt if nxt != -1 else len(src)]


def test_k4_wizard_gui_dry_run_va_giai_thich_o_buoc_4():
    raw = read(WIZARD)
    src = code(raw)
    make = src[src.index("const makeSession") : src.index("const cancelAndEdit")]
    assert "dry_run: chayThu," in make, "createSession phải khai cờ chạy thử LÚC TẠO"
    assert "const dungLinkMau = products.some((p) => isSampleUrl(urlOf(p.product_id)));" in src
    assert "const chayThu = chayThuHieuLuc(form.chayThu, dungLinkMau);" in src
    assert "chayThu: s.dry_run === true," in src, "mở lại phiên đã tạo: cờ là của máy chủ"
    assert "chayThu: saved.form.chayThu ?? null" in src, "bản nháp cũ không có trường chayThu"

    s2 = _step(src, 2)
    for title, value in (
        ('title="Buổi thật"', "false"),
        ('title="Chạy thử (không tính vào kết quả)"', "true"),
    ):
        at = s2.index(title)
        card = s2[s2.rindex("<ChoiceCard", 0, at) : at]
        assert f"onClick={{() => setForm({{ ...form, chayThu: {value} }})}}" in card, title

    body_ts = code(read(API_TS))
    create = body_ts[body_ts.index("export function createSession") :][:400]
    assert "dry_run?: boolean;" in create

    s4 = _step(src, 4)
    at = s4.index("<IngestPanel")
    truoc = s4[s4.rindex("<CheckRow", 0, at) : at]
    assert "choPhepMoPhong(session) ?" in truoc
    assert "Không thấy nguồn Mô phỏng vì đây là buổi thật" in " ".join(truoc.split())
    assert "không phải khách thật" in " ".join(truoc.split())


# ===========================================================================
# K5 (báo cáo) — phiên chạy thử và bình luận tổng hợp được dán nhãn
# ===========================================================================
BAO_CAO_PURE = ["CoChayThu", "coChayThuTu", "nguonGocBaoCao"]


def test_k5_bao_cao_phien_chay_thu_dan_nhan_chay_thu_va_binh_luan_tong_hop(
    phien_chay_thu_da_thu_mo_phong, tmp_path
):
    client, sid, st = phien_chay_thu_da_thu_mo_phong
    chi_tiet = client.get(f"/sessions/{sid}").json()
    bc = client.get(f"/sessions/{sid}/bao-cao").json()
    assert bc["is_demo"] is False, "tiền đề: phiên chạy thử không có chip DEMO"

    that_sid = _tao_phien(client)["session_id"]
    chi_tiet_that = client.get(f"/sessions/{that_sid}").json()
    bc_that = client.get(f"/sessions/{that_sid}/bao-cao").json()
    cu = {k: v for k, v in chi_tiet.items() if k != "dry_run"}
    bc_cu = {k: v for k, v in bc_that.items() if k != "binh_luan_tong_hop"}

    got = node_eval(
        tmp_path,
        BAO_CAO,
        BAO_CAO_PURE,
        f"""[
          nguonGocBaoCao({js(bc)}, coChayThuTu({js(chi_tiet)})),
          nguonGocBaoCao({js(bc_that)}, coChayThuTu({js(chi_tiet_that)})),
          coChayThuTu({js(cu)}),
          coChayThuTu(null),
          nguonGocBaoCao({js(bc_cu)}, "khong-ro"),
          nguonGocBaoCao({{ ...{js(bc_cu)}, is_demo: true }}, "khong-ro"),
          nguonGocBaoCao({js(bc_that)}, null),
        ]""",
    )
    chay_thu, that, may_chu_cu, hong, khong_ro, demo, dang_doc = got
    assert chay_thu == {"chayThu": True, "tongHop": st["comments_posted"], "khongRoChayThu": False}
    assert that == {"chayThu": False, "tongHop": 0, "khongRoChayThu": False}
    assert (may_chu_cu, hong) == ("khong-ro", "khong-ro"), "không đọc được cờ thì KHÔNG đoán"
    assert khong_ro == {"chayThu": False, "tongHop": None, "khongRoChayThu": True}, (
        "máy chủ cũ không gửi số bình luận tổng hợp thì là không rõ, không phải 0"
    )
    assert demo["khongRoChayThu"] is False, "phiên mẫu đã có chip DEMO"
    assert dang_doc["khongRoChayThu"] is False, "đang đọc cờ thì chưa nói gì"


def test_k5_trang_bao_cao_doc_co_chay_thu_va_ve_nhan():
    raw = read(BAO_CAO)
    src = code(raw)
    body = function_body(src, "BaoCaoPage")
    load = body[body.index("const load") : body.index("useEffect(")]
    assert "Promise.all([" in load
    assert "getBaoCao(sessionId)" in load
    assert 'getSessionDetail(sessionId).then(coChayThuTu, (): CoChayThu => "khong-ro")' in load, (
        "thông tin phiên hỏng không được làm hỏng báo cáo — chỉ khiến cờ là không rõ"
    )
    assert "const nguonGoc = data ? nguonGocBaoCao(data, coChayThu) : null;" in body

    header = body[body.index("<PageHeader") : body.index("</PageHeader>")]
    at = header.index("CHẠY THỬ — không tính vào kết quả gộp")
    assert "{nguonGoc?.chayThu ? (" in header[at - 200 : at]
    assert "<span aria-hidden>◐</span>" in header[at - 120 : at], "nhãn trạng thái có hình + chữ"
    at = header.index("CÓ BÌNH LUẬN TỔNG HỢP")
    assert "{soTongHop > 0 ? (" in header[at - 200 : at]
    # Câu giải thích ngay dưới dòng `nhan`, CHỈ khi đã có báo cáo.
    children = header[header.index("{data ? (") :]
    assert children.index("{data.nhan}") < children.index("<NhanNguonGoc")
    assert (
        "<NhanNguonGoc nguonGoc={nguonGoc} tongBinhLuan={data.tong_quan.tong_binh_luan} />"
        in children
    )

    nhan = function_body(src, "NhanNguonGoc")
    flat = " ".join(nhan.split())
    at = flat.index("Phiên chạy thử — không tính vào kết quả gộp.")
    assert "{nguonGoc.chayThu ? (" in flat[at - 120 : at]
    at = flat.index("bình luận do nguồn Mô phỏng soạn")
    assert "{soTongHop > 0 ? (" in flat[at - 200 : at]
    assert "không phải khách thật" in flat
    at = flat.index("Chưa đọc được phiên này có phải buổi chạy thử hay không")
    assert "{nguonGoc.khongRoChayThu ? (" in flat[at - 200 : at]

    assert "binh_luan_tong_hop?: number;" in code(read(TYPES_TS))
