"""NGUỒN DUY NHẤT của bộ nhãn ý định — định nghĩa, ví dụ, tập lớp đã huấn luyện.

Trước 08/09/2026 bộ nhãn bị chép rải rác ở bốn chỗ (``intent.INTENT_LABELS``,
``train_intent.LABELS``, ``label_llm.LABEL_GUIDELINE`` và chuỗi cứng "6 lớp"
trong thông báo lỗi). Thêm một lớp phải sửa đủ bốn chỗ, quên một chỗ là pipeline
lặng lẽ từ chối nhãn mới. Từ nay MỌI nơi đọc bộ nhãn từ module này.

Hai tập lớp KHÁC NHAU và không được lẫn:

``INTENT_LABELS``
    Bộ nhãn GÁN NHÃN — những lớp người/LLM được phép gán. Đây là tập mở rộng
    được, và đã mở rộng sau live-fire 08/09 (docs/benchmarks/live-fire-achan.md).

``TRAINED_LABELS``
    Những lớp artifact ĐANG CHẠY thực sự dự đoán được (``intent_clf.joblib``).
    Luôn là tập con của ``INTENT_LABELS``. Chừng nào chưa có nhãn thật để huấn
    luyện lại, năm lớp mới nằm trong guideline nhưng KHÔNG có trong model —
    đó là trạng thái đúng, không phải thiếu sót: bịa nhãn cho lớp chưa có dữ
    liệu còn tệ hơn không đoán.
"""

from __future__ import annotations

INTENT_LABELS: tuple[str, ...] = (
    # --- năm ý định hành động + "khac", bộ tiền đăng ký ban đầu ---
    "hoi_gia",
    "hoi_size",
    "che_dat",
    "chot_don",
    "van_chuyen",
    # --- năm lớp bổ sung sau live-fire 08/09/2026 trên chat bán hàng thật ---
    "chao_hoi",
    "cam_on_khen",
    "hoi_sanpham",
    "hoi_daily",
    "bao_gia_shop",
    # --- lớp mở, luôn đứng cuối ---
    "khac",
)

TRAINED_LABELS: tuple[str, ...] = (
    "hoi_gia",
    "hoi_size",
    "che_dat",
    "chot_don",
    "van_chuyen",
    "khac",
)
"""Lớp của artifact đang đóng gói — phải khớp ``intent_clf.meta.json['labels']``."""


# ---------------------------------------------------------------------------
# Guideline một dòng mỗi lớp — nguồn cho prompt LLM và cho tài liệu
# ---------------------------------------------------------------------------

LABEL_GUIDELINE: dict[str, str] = {
    "hoi_gia": (
        "KHÁCH hỏi giá (giá bao nhiêu, nhiêu tiền, bn, báo giá đi) — người hỏi "
        "là khách, KHÔNG phải shop đang đọc bảng giá (xem bao_gia_shop)"
    ),
    "hoi_size": (
        "hỏi size / cân nặng / chiều cao / form dáng để CHỌN CỠ mặc — không phải "
        "mọi câu chứa chữ 'vừa' hay 'bao nhiêu'"
    ),
    "che_dat": (
        "chê GIÁ đắt / mắc / cao / trả giá xuống (phàn nàn về giá, KHÔNG phải hỏi "
        "giá, KHÔNG phải khen rẻ, KHÔNG phải 'cao' nghĩa chiều cao)"
    ),
    "chot_don": (
        "KHÁCH chốt đơn, đặt mua, order (hành động mua của chính người bình luận: "
        "'chốt', 'lấy 1', 'đặt hàng') — không phải shop hô hào 'cả nhà chốt đơn nha'"
    ),
    "van_chuyen": (
        "hỏi giao hàng / phí ship / COD / thời gian nhận / gửi đi tỉnh, nước ngoài, "
        "hoặc hối đơn đã đặt mà chưa nhận"
    ),
    "chao_hoi": (
        "chào hỏi, điểm danh, tạm biệt, chào người dẫn/khán giả khác "
        "('chào cả nhà', 'em chào a chan', 'hello') — không kèm ý định mua"
    ),
    "cam_on_khen": (
        "cảm ơn, chúc mừng, chúc sức khỏe, khen, cổ vũ, đồng tình, thả tim/cười "
        "— cảm xúc tích cực chung, không kèm ý định mua"
    ),
    "hoi_sanpham": (
        "hỏi VỀ SẢN PHẨM ngoài giá và size: còn hàng không, có bán món X không, "
        "hạn dùng, thành phần, xem hàng ở đâu, mua ở kênh nào"
    ),
    "hoi_daily": (
        "hỏi mở đại lý / chi nhánh / cộng tác viên / hợp tác phân phối "
        "— khách muốn BÁN CÙNG, không phải mua lẻ"
    ),
    "bao_gia_shop": (
        "SHOP/mod tự dán bảng giá, tên sản phẩm kèm giá, thông tin khuyến mãi "
        "(thường in hoa, lặp lại nhiều lần) — nguồn nhiễu, KHÔNG phải khách hỏi giá"
    ),
    "khac": (
        "mọi bình luận không thuộc các lớp trên: bàn luận ngoài lề, drama cộng "
        "đồng, spam số/emoji, thông tin lịch/sự kiện"
    ),
}


# ---------------------------------------------------------------------------
# Ví dụ THẬT (phiên b519f75c-09ab-4cb4-8dff-f5c492c142be, đã lọc PII)
# ---------------------------------------------------------------------------

LABEL_EXAMPLES_REAL: dict[str, tuple[str, ...]] = {
    "chao_hoi": (
        "Chao A Chan ! Chao Ca Nha !",
        "chào cả nhà buổi tối bình an",
        "Chào Achan, Chào cả nhà yêu",
        "xin chào chú báu chào cháu tuyên",
        "TINA NGUYEN : HELLO",
        "EM CHAO CA NHA",
        "xin chào cả gia đình thân thương của A chan",
        "Chào buổi tối em [TÊN] xinh đẹp",
    ),
    "cam_on_khen": (
        "Chúc mừng Achan shop hp",
        "cảm ơn a chan đưa sản phẩm Trà Măng Đen lên kệ",
        "chúc A chan ngày càng phát triển tốt",
        "Làm ít nhưng chất lượng là ok",
        "Xoài rẻ quá ạ",
        "MUA HÀNG ACHAN LÀ HOÀN TOÀN AN TÂM",
        "Tuyệt vời quá",
        "K5 đong gói hàng SIEU đẹp…SIEU chắc cú",
    ),
    "hoi_sanpham": (
        "có bán dầu dừa ạ",
        "còn sốt muối tắc chưa B",
        "Sản phẩm luồng khô chay chưa có hả achan xốp",
        "vào đâu để xem các mặt hàng nhỉ",
        "Thời hạn su dung bao nhiêu em",
        "có đủ hàng để bán ko",
    ),
    "hoi_daily": (
        "Tôi muốn mở đại lý ở [ĐỊA CHỈ] có được không bóng",
        "Mình ở quãng xương thanh hóa muốn mở chi nhánh a,chan shop có đc k bạn [TÊN] ơi?",
        "mở đại lý bên hàn được không em",
        "em có mở sốp Vũng Tàu ko",
        "CHỊ Ở [ĐỊA CHỈ] ! KO CÓ KÊNH YTB. CÓ MỞ ĐC KO ACHAN BÁU ƠI ?",
    ),
    "bao_gia_shop": (
        "LỤC TRÀ MĂNG ĐEN ACHAN TEA (HỘP 200G) GIÁ 400K",
        "MẮM RUỐC CHAY (200G) GIÁ 60K || SỐT MUỐI TẮC (200G) GIÁ 55K",
        "TRÀ SÂM NGỌC LINH || GIÁ 500K (HỘP 15 GÓI X 1.7G) || GIÁ 639K (HỘP 20 GÓI X 1.7G)",
        "COLLAGEN SÂM NGỌC LINH TỔ YẾN - HỘP 6 HŨ 50ML GIÁ 500K",
        "HỘP 5 MẶT NẠ DƯỠNG ẨM, LÀM DỊU DA COBOTE GIÁ 295K",
        "CHAI NƯỚC MÀU DỪA 100K, 2 CHAI 180K, 3 CHAI 280K, 6 CHAI 474K",
    ),
    # ``khac`` PHẢI lấy ví dụ thật, không lấy từ bộ biên soạn: 60 dòng khac ở đó
    # được viết khi chưa có chao_hoi/cam_on_khen/hoi_sanpham nên nay MÂU THUẪN
    # với guideline ("chào shop buổi tối", "chị chủ xinh quá" đang mang nhãn
    # khac). Đưa chúng vào prompt là dạy ngược cho bộ gán nhãn.
    "khac": (
        "TrD nó chạy sau A chan cắn càng",
        "77777778👍👍👍👍",
        "0h ngày 22/05 đến 0h ngày 24",
        "nó soi từng chút",
        "Kiện ra tòa quốc tế giống cuồn cuộn quá",
        "Bấm lai bấm lai khán giả ơi",
        "22 23 24 là 0h ngày 25 mới đủ 3 ngày",
        "làm sạch XH",
    ),
}
"""Ví dụ trích NGUYÊN VĂN từ phiên live-fire (docs/benchmarks/live-fire-achan.md).

Lớp nào có mặt ở đây thì ví dụ này THAY THẾ ví dụ từ bộ biên soạn, không phải
bổ sung — xem ``label_llm.load_seed_examples``."""


def labels_text() -> str:
    """Danh sách lớp dạng chuỗi, dùng trong thông báo lỗi và tài liệu."""
    return ", ".join(INTENT_LABELS)
