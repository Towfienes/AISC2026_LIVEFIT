/**
 * copy.ts — "single source of truth" cho các CÂU-MỘT-DÒNG dùng thống nhất
 * toàn hệ thống (spec UX-FLOW mục 0, gói WIZARD).
 *
 * Vì sao phải là một file riêng: cùng một khái niệm (khối BẬT/TẮT, link đo,
 * màn hình người dẫn) từng được mỗi trang tự giải thích một kiểu — người dùng
 * đọc ba trang là gặp ba dị bản. Trang nào cần thì import từ đây; sửa lời là
 * sửa một chỗ và cả app đổi theo.
 */

export const CAU_MOT_DONG = {
  /** Khối BẬT/TẮT là gì — câu chuẩn duy nhất, cấm viết lại dị bản. */
  batTat:
    "Buổi live được chia thành từng khối ~5 phút, bốc thăm sẵn từ trước: " +
    "khối BẬT là lúc hệ thống được quyền chọn sản phẩm để ghim, khối TẮT là " +
    "lúc bạn bán như bình thường — so hai loại khối là biết hệ thống có thật " +
    "sự giúp thêm lượt nhấp hay không.",

  /** Màn hình người dẫn (bị làm mù — luật L6) tự giới thiệu bằng câu này. */
  manNguoiDan:
    "Màn hình này đặt trước mặt người dẫn: chỉ hiện SẢN PHẨM CẦN GIỚI THIỆU " +
    "NGAY, cố tình không hiện gì khác để người dẫn nói chuyện tự nhiên.",

  /** Link đo — biến kết quả chính của thí nghiệm, giải thích một câu. */
  linkDo:
    "Mỗi sản phẩm có một link ngắn dán vào bình luận ghim; mỗi lượt bấm của " +
    "người xem là một phiếu bầu — đây là con số hệ thống dùng để kết luận.",

  /** Phiên QUAN SÁT (buổi live của người khác / VOD nạp lại). */
  phienQuanSat:
    "Buổi live của người khác chỉ xem lại được: hệ thống mô tả buổi đó diễn " +
    "ra thế nào, không kết luận nhân quả.",
} as const;
