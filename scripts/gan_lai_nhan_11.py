#!/usr/bin/env python
"""Gán lại bộ 320 câu tự biên soạn từ bộ 6 lớp sang bộ 11 lớp.

    .venv/Scripts/python scripts/gan_lai_nhan_11.py            # ghi file
    .venv/Scripts/python scripts/gan_lai_nhan_11.py --kiem-tra # chỉ kiểm tra

TRẢ MÓN NỢ ĐÃ GHI SỔ. ``docs/benchmarks/intent-classifier.md`` §"Nợ bắt buộc
trả trước khi huấn luyện lại" và ``data/labeling/README.md`` đều ghi cùng một
việc: 60 dòng nhãn ``khac`` trong ``src/livelift/nlp/data/intent_dataset.jsonl``
được viết khi ``khac`` còn ôm cả chào hỏi / khen / hỏi sản phẩm. Sau khi bộ
nhãn mở rộng 6 → 11 lớp (08/09/2026), chúng **mâu thuẫn trực tiếp** với
guideline: ``chào shop buổi tối`` mang nhãn ``khac`` trong khi lớp ``chao_hoi``
đã tồn tại. Huấn luyện trên đó là dạy mô hình hai luật ngược nhau cùng lúc.

Script này KHÔNG sửa file gốc. ``intent_dataset.jsonl`` là **baseline tiền
đăng ký** — mọi con số cũ đo trên nó, xoá đi là xoá khả năng kiểm chứng. Bản
gán lại ghi ra ``intent_dataset_11.jsonl`` bên cạnh, và bảng ablation A7/A8
trong ``livelift.nlp.eval_intent`` so hai bản với nhau.

QUY TẮC GÁN LẠI (áp dụng cho đúng 60 dòng ``khac``, 260 dòng còn lại giữ
nguyên vì chúng đã khớp guideline 11 lớp):

* chào / điểm danh / báo có mặt                      -> ``chao_hoi``
* khen, chúc, cảm ơn, thả tim, cảm xúc tích cực      -> ``cam_on_khen``
* hỏi VỀ HÀNG ngoài giá và cỡ: còn hàng, chất liệu,
  HSD, công dụng, xuất xứ, bảo hành, xin xem lại,
  xin link/kênh bán, cách lấy mã giảm               -> ``hoi_sanpham``
* sự cố kỹ thuật buổi live, lịch phát, bàn luận
  ngoài lề, nói với khán giả khác                    -> giữ ``khac``

CÁC CA MƠ HỒ ĐÃ QUYẾT (ghi ra để người sau cãi được, không phải để giấu):

* ``ủng hộ shop nè`` -> ``cam_on_khen``, KHÔNG phải ``chot_don``: "ủng hộ"
  không kèm số lượng/đơn thì chưa phải hành động mua (quy ước 3 của guideline
  — lời cổ vũ không bao giờ là ý định mua).
* ``ai mua rồi cho xin review`` -> ``khac``: câu nói với KHÁN GIẢ KHÁC, không
  hỏi shop (quy ước 2 — ai đang nói quyết định nhãn).
* ``shop uy tín ko mọi người`` -> ``khac``: hỏi về uy tín NGƯỜI BÁN, không
  phải về sản phẩm.
* ``mã giảm nhập ở đâu`` -> ``hoi_sanpham``: câu hỏi thương mại ngoài 6 lớp
  cũ — đúng loại chiếm 6% chat thật mà live-fire 08/09 phát hiện bị bỏ sót.
* ``đổi trả thế nào nếu lỗi`` -> ``hoi_sanpham``, KHÔNG phải ``van_chuyen``:
  guideline ``van_chuyen`` chỉ gồm giao nhận/phí ship/hối đơn, không gồm
  chính sách đổi trả.
* Câu hỏi kích thước đồ gia dụng (``nồi này bao nhiêu lít``) giữ
  ``hoi_size``: đó vẫn là chọn cỡ, chỉ khác mặt hàng.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from livelift.console import configure as _configure_console  # noqa: E402
from livelift.nlp.labels import INTENT_LABELS  # noqa: E402

SRC = REPO / "src" / "livelift" / "nlp" / "data" / "intent_dataset.jsonl"
DST = REPO / "src" / "livelift" / "nlp" / "data" / "intent_dataset_11.jsonl"

#: ``văn bản gốc -> nhãn mới``. Khoá là VĂN BẢN chứ không phải số dòng: số dòng
#: đổi khi ai đó chèn một mẫu, văn bản thì không. Dòng nào không có mặt ở đây
#: giữ nguyên nhãn cũ.
RELABEL: dict[str, str] = {
    "chào shop buổi tối": "chao_hoi",
    "hello mọi người": "chao_hoi",
    "co ai o day ko": "chao_hoi",
    "follow shop lâu lắm rồi nay mới vô live": "chao_hoi",
    "sản phẩm dùng tốt lắm nha mọi người": "cam_on_khen",
    "chị chủ xinh quá": "cam_on_khen",
    "haha vui quá trời": "cam_on_khen",
    "ủng hộ shop nè": "cam_on_khen",
    "mình dùng rồi ok lắm": "cam_on_khen",
    "❤❤❤": "cam_on_khen",
    "chuc shop ban dat hang": "cam_on_khen",
    "sp bên này chất lượng nè": "cam_on_khen",
    "10 điểm cho shop": "cam_on_khen",
    "trời ơi dễ thương quá": "cam_on_khen",
    "chúc mọi người mua sắm vui vẻ": "cam_on_khen",
    "moi vao co gi hot ko": "hoi_sanpham",
    "cho em hỏi shop có cửa hàng ở đâu ko": "hoi_sanpham",
    "hàng này của nước nào vậy": "hoi_sanpham",
    "dùng có bền không mn": "hoi_sanpham",
    "công dụng sao shop nói lại đi": "hoi_sanpham",
    "cái này dùng cho da dầu đc ko": "hoi_sanpham",
    "em tới trễ, nãy giờ bán gì rồi ạ": "hoi_sanpham",
    "xin link fb shop": "hoi_sanpham",
    "hình như hết hàng rồi hả": "hoi_sanpham",
    "sp này có tem chống giả ko": "hoi_sanpham",
    "lam sao de nhan ma giam gia": "hoi_sanpham",
    "mã giảm nhập ở đâu vậy mn": "hoi_sanpham",
    "hạn sử dụng tới khi nào ạ": "hoi_sanpham",
    "thành phần có cồn không shop": "hoi_sanpham",
    "da nhạy cảm dùng được ko": "hoi_sanpham",
    "máy này bảo hành mấy năm": "hoi_sanpham",
    "cho e xem cận cái áo xíu": "hoi_sanpham",
    "quay lại mẫu ban nãy giúp em": "hoi_sanpham",
    "áo này giặt máy đc ko": "hoi_sanpham",
    "chất vải là cotton hả shop": "hoi_sanpham",
    "co mau nao khac ko": "hoi_sanpham",
    "đổi trả thế nào nếu lỗi ạ": "hoi_sanpham",
    "shop demo thử đi": "hoi_sanpham",
    "pin dùng được mấy tiếng": "hoi_sanpham",
    "son này lên môi có khô ko": "hoi_sanpham",
    "màu này còn hay hết rồi ạ": "hoi_sanpham",
    "cho xem lại đôi giày lúc nãy": "hoi_sanpham",
}
"""42 / 60 dòng ``khac`` đổi lớp. 18 dòng còn lại vẫn đúng là ``khac``: sự cố
kỹ thuật (``lag quá xem không được``), lịch phát (``mai live nữa ko shop``),
nói với khán giả khác (``ai mua rồi cho xin review``), bàn luận ngoài lề
(``tối nay ăn gì đây``)."""


def relabel(rows: list[dict]) -> tuple[list[dict], Counter]:
    """Hàm thuần: áp bảng gán lại, trả về dòng mới + số dòng đổi theo lớp."""
    changed: Counter = Counter()
    out = []
    for row in rows:
        new = RELABEL.get(row["text"], row["label"])
        if new != row["label"]:
            changed[f"{row['label']} -> {new}"] += 1
        out.append({"text": row["text"], "label": new})
    return out, changed


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kiem-tra", action="store_true", help="chỉ kiểm tra, không ghi")
    args = parser.parse_args(argv)

    rows = [json.loads(x) for x in SRC.read_text(encoding="utf-8").splitlines() if x.strip()]
    texts = {r["text"] for r in rows}
    orphans = sorted(set(RELABEL) - texts)
    if orphans:
        print("LỖI — bảng RELABEL có văn bản không tồn tại trong dataset gốc:")
        for o in orphans:
            print(f"  {o!r}")
        return 1
    bad = sorted({lb for lb in RELABEL.values() if lb not in INTENT_LABELS})
    if bad:
        print(f"LỖI — nhãn không thuộc bộ 11 lớp: {bad}")
        return 1

    new_rows, changed = relabel(rows)
    print(f"nguồn : {SRC.relative_to(REPO)} — {len(rows)} dòng")
    print(f"đổi   : {sum(changed.values())} dòng")
    for k, v in sorted(changed.items()):
        print(f"        {k}: {v}")
    print(f"trước : {dict(Counter(r['label'] for r in rows))}")
    print(f"sau   : {dict(Counter(r['label'] for r in new_rows))}")
    missing = [lb for lb in INTENT_LABELS if lb not in {r["label"] for r in new_rows}]
    if missing:
        print(f"CHƯA CÓ MẪU cho: {missing} — bộ biên soạn không dạy được các lớp này")

    if args.kiem_tra:
        return 0
    DST.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_rows), encoding="utf-8"
    )
    print(f"đã ghi: {DST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
