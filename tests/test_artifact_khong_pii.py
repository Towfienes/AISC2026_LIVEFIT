"""Cổng: artifact mô hình đã commit KHÔNG mang dữ liệu cá nhân trong từ vựng.

Sự cố 25/09/2026 (P0). ``intent_clf_v2.joblib`` đóng gói 14/09 trên dữ liệu CHƯA
lọc lại tên tài khoản, nên từ vựng TF-IDF của nó chứa 1 token sinh từ tên tài
khoản của một người bình luận (sha256[:12] = ``66bb97b5d495``) cùng các mảnh
``char_wb`` chứa ``@``. Pickle giữ nguyên văn từng chuỗi của từ vựng: artifact
commit vào git là một bản sao dữ liệu người dùng, dù dữ liệu gốc đã lọc sạch.
Không cổng nào bắt được, vì mọi cổng PII chỉ quét tệp văn bản.

Ba lớp kiểm, áp cho MỌI ``*.joblib`` trong ``src/livelift/nlp/model/``:

1. **Quét mẫu** trên mọi chuỗi trong đồ thị đối tượng của artifact (từ vựng và
   mọi thuộc tính khác): không chuỗi nào khớp ``@\\w``, và bộ lọc PII của chính
   sản phẩm (``livelift.ingest.pii.scrub``: SĐT, email, mã đơn, địa chỉ, tên,
   MXH/handle, STK) không sửa chuỗi nào. Trước khi quét, các token placeholder
   ``pii…`` do bộ chuẩn hoá chèn vào (``[ĐỊA CHỈ]`` → ``piiđịachỉ``) được trung hoà,
   vì ``piiđịachỉ nha`` làm mẫu "địa chỉ: …" khớp oan.
2. **Băm đã lộ**: token đã biết (chỉ lưu băm, không lưu chữ) không được quay lại.
3. **Nguồn gốc**: từ vựng ``word`` của artifact ⊆ từ vựng của dữ liệu train HIỆN
   HÀNH (đã lọc), đi qua đúng các bước tiền xử lý của chính artifact. Lớp này bắt
   đúng chỗ (1) mù: analyzer ``word`` bỏ ký tự ``@``, nên tên tài khoản thành một
   "từ" thường. v1: ⊆ 320 câu mẫu do AI soạn (có trong git) — tức v1 không học từ
   bình luận thật nào. v2: cần ``data/labeling`` (ngoài git, chính sách PII) — bỏ
   qua khi không có.
3b. **Nguồn gốc, đã xoá handle**: lớp 3 mù khi tên tài khoản CÒN NẰM trong dữ liệu
   train. Rà 25/09/2026 (làn V1): 4 dòng ``llm_lot1`` còn dạng ``chữ@tên8106`` —
   ``@`` dính liền chữ đứng trước, nên ``SOCIAL_HANDLE_RE`` (lookbehind
   ``(?<![\\w.@])``) và ``EMAIL_RE`` (cần ``.tld``) đều để lọt. Artifact hiện hành
   KHÔNG mang chúng (mỗi tên xuất hiện 1 lần, ``min_df=2`` cắt), nhưng không có gì
   giữ điều đó; lớp 3b giữ: từ vựng ``word`` ⊆ từ của dữ liệu train sau khi xoá mọi
   đoạn ``@tên`` (:func:`bo_handle`).

Đối chứng âm: tiêm token giả vào BẢN SAO từ vựng thì mọi lớp đều đỏ.

Thông báo lỗi CHỈ in băm sha256[:12], không bao giờ in token — chính token có
thể là dữ liệu cá nhân.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from typing import Any

import pytest

from livelift.ingest.pii import scrub
from livelift.nlp import eval_intent as ev
from livelift.nlp.normalize import PII_PLACEHOLDERS, normalize_text

MODEL_DIR = ev.MODEL_V2.parent
ARTIFACTS = sorted(MODEL_DIR.glob("*.joblib"))

AT_WORD_RE = re.compile(r"@\w")
"""Mẫu ``@`` + ký tự chữ: dấu vết của handle (``@ten_tai_khoan``) trong bất kỳ
mảnh n-gram nào, kể cả mảnh quá ngắn để ``SOCIAL_HANDLE_RE`` (≥ 3 ký tự) khớp."""

KNOWN_LEAKED_SHA12: frozenset[str] = frozenset({"66bb97b5d495"})
"""Băm sha256[:12] của token đã lộ (sự cố 25/09/2026). Chỉ lưu băm."""

HANDLE_SPAN_RE = re.compile(r"@\w[\w.\-]*")
"""Đoạn ``@tên`` bất kể chữ đứng trước — rộng hơn ``SOCIAL_HANDLE_RE`` của sản phẩm,
chỉ dùng trong cổng này (xoá đoạn khỏi dữ liệu train trước khi so từ vựng)."""


def bo_handle(text: str) -> str:
    """Xoá mọi đoạn ``@tên`` (kể cả ``ạ@tên8106`` dính liền), giữ chữ quanh nó."""
    return HANDLE_SPAN_RE.sub(" ", text)


PLACEHOLDER_TOKENS: tuple[str, ...] = tuple(
    sorted({normalize_text(p).strip() for p in PII_PLACEHOLDERS} | {"pii_url"}, key=len)[::-1]
)
"""Token nguyên khối mà ``normalize_text`` thay cho placeholder của bộ lọc PII."""


def sha12(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Duyệt artifact
# ---------------------------------------------------------------------------


def cac_vectorizer(obj: Any, path: str = "", pre: tuple[Any, ...] = ()) -> Iterator[tuple]:
    """``(đường dẫn, vectorizer, các bước chạy TRƯỚC nó)`` cho mọi vectorizer.

    "Các bước chạy trước" là các bước đã fit của Pipeline nằm trước bước chứa
    vectorizer — ví dụ ``norm`` (``normalize_batch``) của v2 — để lớp kiểm nguồn
    gốc phân tích dữ liệu train đúng như artifact đã thấy lúc fit.
    """
    if hasattr(obj, "vocabulary_") and hasattr(obj, "build_analyzer"):
        yield path or "/", obj, pre
        return
    if hasattr(obj, "steps"):  # Pipeline
        acc = list(pre)
        for name, step in obj.steps:
            yield from cac_vectorizer(step, f"{path}/{name}", tuple(acc))
            if step is not None and step != "passthrough":
                acc.append(step)
    elif hasattr(obj, "transformer_list"):  # FeatureUnion
        for name, t in obj.transformer_list:
            yield from cac_vectorizer(t, f"{path}/{name}", pre)


def cac_chuoi(obj: Any) -> Iterator[str]:
    """Mọi chuỗi tới được trong đồ thị đối tượng (khoá/giá trị dict, list, tuple,
    set, mảng numpy kiểu chuỗi/object, thuộc tính ``__dict__``)."""
    seen: set[int] = set()
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, str):
            yield o
            continue
        if isinstance(o, (bytes, int, float, bool, type(None))) or id(o) in seen:
            continue
        seen.add(id(o))
        if isinstance(o, dict):
            stack.extend(o.keys())
            stack.extend(o.values())
        elif isinstance(o, (list, tuple, set, frozenset)):
            stack.extend(o)
        elif type(o).__module__ == "numpy" and hasattr(o, "dtype"):
            if getattr(o.dtype, "kind", "") in ("U", "S", "O"):
                stack.extend(o.ravel().tolist())
        elif hasattr(o, "__dict__") and not callable(o):
            stack.extend(vars(o).values())


# ---------------------------------------------------------------------------
# Ba lớp kiểm — hàm thuần, trả băm (không trả token)
# ---------------------------------------------------------------------------


def _trung_hoa_placeholder(token: str) -> str:
    for ph in PLACEHOLDER_TOKENS:
        token = token.replace(ph, " ")
    return token


def ly_do_vi_pham(token: str, known: frozenset[str] = KNOWN_LEAKED_SHA12) -> str | None:
    """Vì sao một chuỗi bị coi là PII (``None`` = sạch)."""
    if sha12(token) in known:
        return "băm-đã-lộ"
    if AT_WORD_RE.search(token):
        return "@\\w"
    kinds = {m.kind for m in scrub(_trung_hoa_placeholder(token)).matches}
    if kinds:
        return "pii:" + ",".join(sorted(kinds))
    return None


def quet(chuoi: Iterable[str], known: frozenset[str] = KNOWN_LEAKED_SHA12) -> list[tuple[str, str]]:
    """``[(sha256[:12], lý do)]`` của mọi chuỗi vi phạm — rỗng mới đạt."""
    out = {(sha12(s), r) for s in chuoi if (r := ly_do_vi_pham(s, known)) is not None}
    return sorted(out)


def tu_ngoai_du_lieu(pipe: Any, texts: list[str]) -> dict[str, list[str]]:
    """Băm các token ``word`` của artifact KHÔNG sinh ra được từ ``texts``.

    Rỗng ⇔ từ vựng từ ⊆ dữ liệu train đưa vào (sau đúng tiền xử lý của artifact).
    """
    out: dict[str, list[str]] = {}
    for path, vec, pre in cac_vectorizer(pipe):
        if vec.analyzer != "word":
            continue
        docs: list[Any] = list(texts)
        for step in pre:
            docs = list(step.transform(docs))
        analyze = vec.build_analyzer()
        seen: set[str] = set()
        for d in docs:
            seen.update(analyze(d))
        missing = sorted(sha12(t) for t in vec.vocabulary_ if t not in seen)
        if missing:
            out[path] = missing
    return out


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def artifacts() -> dict[str, Any]:
    joblib = pytest.importorskip("joblib")
    pytest.importorskip("sklearn")
    if not ARTIFACTS:
        pytest.skip("không có artifact nào trong src/livelift/nlp/model/")
    return {p.name: joblib.load(p) for p in ARTIFACTS}


def _mot_vectorizer_word(pipe: Any) -> Any:
    return next(v for _, v, _ in cac_vectorizer(pipe) if v.analyzer == "word")


# ---------------------------------------------------------------------------
# Cổng
# ---------------------------------------------------------------------------


def test_moi_artifact_trong_thu_muc_model_deu_duoc_quet(artifacts):
    """Không artifact nào lọt ngoài cổng: có vectorizer, có từ vựng để quét."""
    assert set(artifacts) >= {"intent_clf.joblib"}
    for name, pipe in artifacts.items():
        vecs = list(cac_vectorizer(pipe))
        assert vecs, f"{name}: không tìm thấy vectorizer nào — cổng không quét được gì"
        assert all(len(v.vocabulary_) > 0 for _, v, _ in vecs), name


@pytest.mark.parametrize("name", [p.name for p in ARTIFACTS])
def test_tu_vung_va_moi_chuoi_trong_artifact_khong_co_pii(artifacts, name):
    """Lớp 1 + 2: 0 chuỗi khớp ``@\\w``/mẫu PII của sản phẩm/băm đã lộ."""
    vi_pham = quet(cac_chuoi(artifacts[name]))
    assert vi_pham == [], (
        f"{name}: {len(vi_pham)} chuỗi mang PII/handle trong artifact (sha256[:12], lý do): "
        f"{vi_pham[:20]} — đóng gói lại trên dữ liệu đã lọc: "
        "python -m livelift.nlp.eval_intent --save-model"
    )


def test_tu_vung_v1_chi_gom_tu_cua_320_cau_mau_do_ai_soan(artifacts):
    """Lớp 3 cho v1: mọi từ của v1 sinh được từ bộ 320 câu mẫu (có trong git).

    Tức v1 không học từ bình luận thật nào — không có đường cho PII vào v1.
    """
    pipe = artifacts.get("intent_clf.joblib")
    if pipe is None:
        pytest.skip("không có intent_clf.joblib")
    texts = [r.text for r in ev.load_authored(ev.AUTHORED_V1)]
    assert len(texts) == 320
    assert tu_ngoai_du_lieu(pipe, texts) == {}


@pytest.mark.skipif(
    not (ev.GOLD_DIR / "gold.txt").exists(),
    reason="lô nhãn thật ngoài git (chính sách PII) — sinh lại: data/labeling/README.md",
)
def test_tu_vung_v2_chi_gom_tu_cua_du_lieu_train_hien_hanh_da_loc(artifacts):
    """Lớp 3 cho v2: đóng gói trên dữ liệu CŨ (chưa lọc lại) thì đỏ ở đây.

    Đây là lớp bắt được token 14 ký tự của sự cố 25/09 mà không cần biết nó:
    token ấy có 0 lần xuất hiện trong dữ liệu đã lọc.
    """
    pipe = artifacts.get(ev.MODEL_V2.name)
    if pipe is None:
        pytest.skip("không có artifact v2")
    rows = ev.rows_for_packaging(ev.load_gold_lot2(), ev.load_authored() + ev.load_llm_lot())
    ngoai = tu_ngoai_du_lieu(pipe, [r.text for r in rows])
    assert ngoai == {}, (
        f"{ev.MODEL_V2.name}: {sum(map(len, ngoai.values()))} từ trong artifact không có trong "
        f"dữ liệu train hiện hành (sha256[:12]): {ngoai} — artifact cũ hơn dữ liệu; "
        "đóng gói lại: python -m livelift.nlp.eval_intent --save-model"
    )


@pytest.mark.skipif(
    not (ev.GOLD_DIR / "gold.txt").exists(),
    reason="lô nhãn thật ngoài git (chính sách PII) — sinh lại: data/labeling/README.md",
)
def test_tu_vung_v2_khong_co_tu_chi_sinh_ra_tu_ten_tai_khoan_trong_du_lieu(artifacts):
    """Lớp 3b cho v2: không từ nào của artifact CHỈ đến từ một đoạn ``@tên`` của
    dữ liệu train — kể cả tên còn sót trong dữ liệu mà bộ lọc PII chưa bắt."""
    pipe = artifacts.get(ev.MODEL_V2.name)
    if pipe is None:
        pytest.skip("không có artifact v2")
    rows = ev.rows_for_packaging(ev.load_gold_lot2(), ev.load_authored() + ev.load_llm_lot())
    ngoai = tu_ngoai_du_lieu(pipe, [bo_handle(r.text) for r in rows])
    assert ngoai == {}, (
        f"{ev.MODEL_V2.name}: {sum(map(len, ngoai.values()))} từ trong artifact chỉ sinh ra từ "
        f"đoạn @tên của dữ liệu train (sha256[:12]): {ngoai} — lọc handle khỏi dữ liệu rồi "
        "đóng gói lại: python -m livelift.nlp.eval_intent --save-model"
    )


@pytest.mark.skipif(
    not (ev.GOLD_DIR / "gold.txt").exists(),
    reason="lô nhãn thật ngoài git (chính sách PII) — sinh lại: data/labeling/README.md",
)
def test_meta_v2_ghi_dau_van_tay_dung_du_lieu_train_hien_hanh():
    """Sidecar ghi băm dữ liệu train; lệch ⇒ artifact không được đóng gói từ dữ
    liệu hiện hành (ví dụ dữ liệu đã lọc lại mà artifact thì chưa)."""
    meta_path = ev.MODEL_V2.with_suffix(".meta.json")
    if not meta_path.exists():
        pytest.skip("không có meta v2")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    rows = ev.rows_for_packaging(ev.load_gold_lot2(), ev.load_authored() + ev.load_llm_lot())
    assert meta.get("du_lieu_train_sha256") == ev.training_fingerprint(rows)


# ---------------------------------------------------------------------------
# Đối chứng âm — cổng phải ĐỎ khi có PII
# ---------------------------------------------------------------------------

HANDLE_GIA = "@Trần.Thị_Bịa99"
"""Handle bịa (không phải người thật) — cùng dạng YouTube cấp."""


def _ban_sao_co_tiem(pipe: Any, tokens: list[str]) -> Any:
    ban_sao = copy.deepcopy(pipe)
    vec = _mot_vectorizer_word(ban_sao)
    base = max(vec.vocabulary_.values()) + 1
    for i, t in enumerate(tokens):
        vec.vocabulary_[t] = base + i
    return ban_sao


@pytest.mark.parametrize("name", [p.name for p in ARTIFACTS])
def test_doi_chung_am_tiem_handle_gia_vao_ban_sao_thi_cong_do(artifacts, name):
    pipe = artifacts[name]
    tiem = [HANDLE_GIA.lower(), " @tr", "0901234567", "ban.gia@example.com"]
    ban_sao = _ban_sao_co_tiem(pipe, tiem)
    vi_pham = quet(cac_chuoi(ban_sao))
    ly_do = {r for _, r in vi_pham}
    assert {sha12(t) for t in tiem} <= {h for h, _ in vi_pham}
    assert "@\\w" in ly_do
    assert any(r.startswith("pii:") for r in ly_do)
    # Bản gốc không bị đụng tới.
    assert all(t not in _mot_vectorizer_word(pipe).vocabulary_ for t in tiem)


def test_doi_chung_am_tu_sinh_tu_handle_da_mat_at_bi_lop_nguon_goc_bat(artifacts):
    """Analyzer ``word`` bỏ ``@``: ``@TranThiBia99`` thành từ ``tranthibia99`` —
    lớp 1 không thấy, lớp 3 phải thấy."""
    pipe = artifacts["intent_clf.joblib"]
    tu_gia = "tranthibia99"
    assert ly_do_vi_pham(tu_gia) is None  # đúng là lớp 1 mù với dạng này
    ban_sao = _ban_sao_co_tiem(pipe, [tu_gia])
    texts = [r.text for r in ev.load_authored(ev.AUTHORED_V1)]
    ngoai = tu_ngoai_du_lieu(ban_sao, texts)
    assert sha12(tu_gia) in {h for v in ngoai.values() for h in v}


def test_doi_chung_am_handle_dinh_lien_con_trong_du_lieu_bi_lop_3b_bat(artifacts):
    """Lớp 3 mù khi tên tài khoản CÒN NẰM trong dữ liệu train: ``ạ@tranthibia99``
    (dính liền chữ đứng trước — bộ lọc PII hiện hành để lọt, xem ``bo_handle``) cho
    từ ``tranthibia99`` có thật trong dữ liệu, nên ⊆ vẫn đúng. Lớp 3b so với dữ liệu
    đã xoá mọi đoạn ``@tên`` thì phải thấy."""
    pipe = artifacts["intent_clf.joblib"]
    tu_gia = "tranthibia99"
    texts = [r.text for r in ev.load_authored(ev.AUTHORED_V1)] + [f"chào ạ@{tu_gia} nha"]
    ban_sao = _ban_sao_co_tiem(pipe, [tu_gia])
    assert tu_ngoai_du_lieu(ban_sao, texts) == {}  # đúng là lớp 3 mù với dạng này
    ngoai = tu_ngoai_du_lieu(ban_sao, [bo_handle(t) for t in texts])
    assert sha12(tu_gia) in {h for v in ngoai.values() for h in v}
    # Bản gốc v1 qua lớp 3b sạch: xoá handle không làm rơi từ hợp lệ nào.
    assert tu_ngoai_du_lieu(pipe, [bo_handle(t) for t in texts]) == {}


def test_bo_handle_xoa_ca_handle_dinh_lien_nhung_giu_chu_quanh_no():
    assert bo_handle("chào ạ@tranthibia99 nha").split() == ["chào", "ạ", "nha"]
    assert bo_handle("@Trần.Thị_Bịa99 ơi").split() == ["ơi"]
    assert bo_handle("giá 50k @ 1 cái").split() == ["giá", "50k", "@", "1", "cái"]


def test_doi_chung_am_bam_da_lo_bi_bat_ma_khong_can_luu_chu():
    """Token không khớp mẫu nào vẫn bị bắt khi băm của nó nằm trong danh sách."""
    assert all(re.fullmatch(r"[0-9a-f]{12}", h) for h in KNOWN_LEAKED_SHA12)
    gia = "tokengiadelamdoichung"
    assert ly_do_vi_pham(gia) is None
    assert quet([gia]) == []
    known = KNOWN_LEAKED_SHA12 | {sha12(gia)}
    assert ly_do_vi_pham(gia, known) == "băm-đã-lộ"
    assert quet(["chào shop", gia], known) == [(sha12(gia), "băm-đã-lộ")]


def test_placeholder_cua_bo_chuan_hoa_khong_bi_coi_la_pii():
    """``piiđịachỉ nha`` là placeholder, không phải địa chỉ — nếu cổng báo oan ở
    đây thì người ta sẽ nới cổng, và cổng nới là cổng chết."""
    assert "piiđịachỉ" in PLACEHOLDER_TOKENS
    assert "pii_url" in PLACEHOLDER_TOKENS
    assert quet(["piiđịachỉ nha", "piiđịachỉ được", "piisđt", "piimxh ơi"]) == []
    # ...nhưng một địa chỉ thật đứng sau placeholder vẫn bị bắt.
    assert quet(["piitên số 12 đường lê lợi"]) != []


def test_thong_bao_loi_khong_in_token():
    vi_pham = quet([HANDLE_GIA])
    assert vi_pham
    assert all(HANDLE_GIA not in f"{h}{r}" for h, r in vi_pham)


def test_chuoi_ngoai_tu_vung_cung_duoc_quet():
    """``cac_chuoi`` đi qua cả thuộc tính lồng (ví dụ ``classes_``), không chỉ
    ``vocabulary_``."""

    class _Gia:
        def __init__(self) -> None:
            self.classes_ = ["hoi_gia", HANDLE_GIA]
            self.long = {"a": ({"b": [HANDLE_GIA]},)}

    found = list(cac_chuoi(_Gia()))
    assert found.count(HANDLE_GIA) >= 2
