/**
 * GÓI WIZARD — ma trận trả lời câu hỏi lớn nhất của người dùng:
 *
 *   "Tôi mở phiên live bất kỳ của nền tảng nào cũng được và sử dụng sản phẩm —
 *    có làm được không? Hiện tại nếu dùng thì dùng như nào?"
 *
 * Câu trả lời đã nằm trong `docs/nen-tang-ho-tro.md` và
 * `docs/mo-hinh-van-hanh-kol.md`, nhưng SẢN PHẨM thì không nói gì. Tệp này đưa
 * đúng những kết luận đã kiểm chứng ở hai tài liệu đó vào giao diện, theo đúng
 * 20 tổ hợp (5 nền tảng x của-ai x đang-phát/đã-kết-thúc).
 *
 * BA LUẬT KHI SỬA TỆP NÀY
 *
 * 1. KHÔNG BỊA. Mọi con số ở đây đều có nguồn trong hai tài liệu trên (phép đo
 *    thật ngày 10–11/09/2026). Chỗ nào nhóm chưa kiểm chứng thì phải ghi thẳng
 *    là "chưa kiểm chứng" — xem tổ hợp Facebook/của-tôi/đã-kết-thúc.
 * 2. KHÔNG HỨA HÃO. Tổ hợp nào không làm được thì `level: "khong"` và phần
 *    `blocked` phải nói VÌ SAO, rồi chỉ đường thay thế gần nhất trong `now`.
 * 3. MỖI TỔ HỢP MỘT CÂU TRẢ LỜI RIÊNG. Không có nhánh nào trả lời chung chung;
 *    `outcomeFor()` phân nhánh tới tận từng ô của ma trận.
 */

// ---------------------------------------------------------------------------
// Kiểu dữ liệu
// ---------------------------------------------------------------------------

export type Owner = "toi" | "nguoi-khac";
export type When = "dang-phat" | "da-ket-thuc";
export type Platform = "youtube" | "facebook" | "tiktok" | "shopee" | "khac";

/** Ba mức năng lực của LiveLift, cộng mức "không làm được gì". */
export type Level = "khong" | "quan-sat" | "de-xuat" | "thi-nghiem";

export const LEVEL_ORDER: Record<Level, number> = {
  khong: 0,
  "quan-sat": 1,
  "de-xuat": 2,
  "thi-nghiem": 3,
};

/** Nút bấm thẳng tới việc tiếp theo. `vod` mở ô dán link ngay tại chỗ. */
export type Action =
  | { kind: "link"; href: string; label: string }
  | { kind: "vod"; label: string };

export interface Block {
  body: string;
  bullets?: string[];
  action?: Action;
}

export interface Outcome {
  /** Mức đạt được HÔM NAY, với đúng những gì repo đang có (`.env` trống). */
  level: Level;
  /** Trần: mức cao nhất tổ hợp này chạm tới được sau khi chuẩn bị xong. */
  ceiling: Level;
  /** Một câu dứt khoát, đọc là biết ngay. */
  headline: string;
  now: Block;
  /** Cần gì để lên mức cao hơn. `time = null` nghĩa là không có đường lên. */
  upgrade: Block & { time: string | null; doc?: string };
  /** Không làm được gì, và vì sao. Luôn có ít nhất một mục. */
  blocked: { label: string; why: string }[];
}

// ---------------------------------------------------------------------------
// Nhãn tiếng Việt
// ---------------------------------------------------------------------------

export const OWNER_LABEL: Record<Owner, string> = {
  toi: "Của tôi",
  "nguoi-khac": "Của người khác",
};

export const WHEN_LABEL: Record<When, string> = {
  "dang-phat": "Đang phát",
  "da-ket-thuc": "Đã kết thúc",
};

export const PLATFORM_LABEL: Record<Platform, string> = {
  youtube: "YouTube",
  facebook: "Facebook",
  tiktok: "TikTok",
  shopee: "Shopee",
  khac: "Khác",
};

export const PLATFORM_NOTE: Record<Platform, string> = {
  youtube: "Kể cả YouTube Live và video live đã lưu lại",
  facebook: "Fanpage, Facebook Live",
  tiktok: "Kể cả TikTok Shop",
  shopee: "Shopee Live",
  khac: "Lazada, Instagram, Zalo, website riêng…",
};

export const PLATFORMS: Platform[] = ["youtube", "facebook", "tiktok", "shopee", "khac"];
export const OWNERS: Owner[] = ["toi", "nguoi-khac"];
export const WHENS: When[] = ["dang-phat", "da-ket-thuc"];

/**
 * Ba mức năng lực, giải thích NGẮN GỌN và KHÔNG THUẬT NGỮ. Đây là thứ người
 * dùng đọc đầu tiên khi họ chưa biết LiveLift là gì.
 */
export const LEVEL_META: Record<
  Level,
  { name: string; short: string; oneLiner: string; what: string; needs: string }
> = {
  khong: {
    name: "KHÔNG LÀM ĐƯỢC",
    short: "KHÔNG",
    oneLiner: "Nền tảng không mở đường nào.",
    what: "Không có dữ liệu nào chảy vào hệ thống, nên không có gì để hiển thị.",
    needs: "Xem phần “Không làm được gì, và vì sao” để biết đường thay thế gần nhất.",
  },
  "quan-sat": {
    name: "QUAN SÁT",
    short: "QUAN SÁT",
    oneLiner: "Xem lại chuyện đã xảy ra.",
    what:
      "Buổi live đó diễn ra thế nào: nhịp bình luận theo từng 30 giây, khán giả hỏi gì, " +
      "lúc nào bình luận vọt lên. Là bản mô tả — nó kể lại, không giải thích nguyên nhân.",
    needs: "Chỉ cần một nguồn bình luận đọc được. Không cần tài khoản, không cần đụng vào buổi live.",
  },
  "de-xuat": {
    name: "ĐỀ XUẤT",
    short: "ĐỀ XUẤT",
    oneLiner: "Máy gợi ý, bạn quyết định.",
    what:
      "Trong lúc phát, LiveLift chấm điểm từng sản phẩm và đưa ra tối đa 3 thẻ “nên ghim cái " +
      "này bây giờ”. Bạn bấm hay bỏ qua là quyền của bạn; mọi lựa chọn đều được ghi lại.",
    needs:
      "Một phiên do chính bạn vận hành, một lịch BẬT/TẮT đã bốc, và một người ngồi bấm. " +
      "Ba thứ đó chạy được trên MỌI nền tảng.",
  },
  "thi-nghiem": {
    name: "THÍ NGHIỆM",
    short: "THÍ NGHIỆM",
    oneLiner: "Con số nhân quả, có khoảng tin cậy.",
    what:
      "Trước khi lên sóng, hệ thống bốc thăm lịch BẬT/TẮT. Khoảng một nửa phiên nó cố ý " +
      "không giúp gì. Cuối phiên so hai nửa — bạn biết việc ghim theo hệ thống có THẬT SỰ " +
      "làm tăng nhấp hay không, kèm khoảng tin cậy 95%.",
    needs:
      "Đúng ba thứ, thiếu một là không có kết quả — xem ba thứ đó ở mục ngay bên dưới.",
  },
};

/** Ba điều kiện của một thí nghiệm nhân quả thật — hiện ở cuối trang. */
export const THREE_REQUIREMENTS = [
  {
    n: "1",
    title: "Nguồn bình luận + người xem",
    body:
      "Bình luận là thứ radar ý định đọc; số người xem theo thời gian là MẪU SỐ của biến kết " +
      "quả (nhấp / 1.000 viewer-giây). Khối nào dưới 60 viewer-giây bị loại khỏi phân tích — " +
      "bị loại, chứ không bị tính là 0.",
  },
  {
    n: "2",
    title: "Một đường đo kết quả",
    body:
      "Link đo /r/{code} của chính bạn, hoặc API đơn hàng của sàn. Link đo BẮT BUỘC kèm " +
      "session_id: thiếu nó thì link vẫn chuyển hướng bình thường, người xem không thấy gì " +
      "lạ, nhưng cú bấm biến mất khỏi thí nghiệm (đã thử: bấm 2 link, phiên chỉ ghi nhận 1).",
  },
  {
    n: "3",
    title: "Người (hoặc máy) thực thi lịch BẬT/TẮT",
    body:
      "Phiên 90 phút có 8 khối BẬT — nghĩa là ai đó phải bấm 8 lần, đúng lúc, suốt phiên. " +
      "Hôm nay chưa có bộ thực thi tự động: nhãn “Tự động” được lưu và hiển thị, nhưng không " +
      "có tiến trình nào đọc nó để tự ghim.",
  },
];

// ---------------------------------------------------------------------------
// Những khối nội dung dùng lại giữa các tổ hợp
// ---------------------------------------------------------------------------

const VOD_ACTION: Action = { kind: "vod", label: "Dán link YouTube đã kết thúc" };
const RUN_ACTION: Action = { kind: "link", href: "/chay-phien", label: "Mở trang Chạy phiên" };

const VOD_CAVEAT = {
  label: "Có chat replay không có nghĩa là có chat",
  why:
    "Đo ngày 10/09 trên 17 video: 16 buổi vào được, nhưng chỉ 7 buổi đạt ≥ 100 bình luận, và " +
    "một buổi dài 715 phút có ĐÚNG 0 bình luận. Hãy tính thời gian tìm nguồn vào kế hoạch.",
};

const NO_VIEWERS_ON_VOD = {
  label: "Số người xem",
  why:
    "Buổi đã kết thúc không còn số người xem đồng thời — vĩnh viễn, không phải lỗi cài đặt. " +
    "Hệ thống ghi THIẾU, không ghi 0.",
};

const NO_CAUSAL_WITHOUT_DRAW = {
  label: "Mọi con số nhân quả",
  why:
    "Buổi phát gốc không có lịch bốc thăm BẬT/TẮT, nên không có gì để so sánh và không suy " +
    "diễn được một con số nhân quả nào. Hệ thống tự dán nhãn phiên này là QUAN SÁT và từ " +
    "chối in số nhân quả.",
};

const NO_PIN_FOR_YOU = {
  label: "Ghim hộ trên nền tảng",
  why:
    "LiveLift nói “ghim cái này bây giờ”; việc bấm ghim trên app vẫn là thao tác tay của con " +
    "người. Không nền tảng nào cho phép điều khiển việc ghim sản phẩm trong live qua API. " +
    "Đây là giới hạn không phần mềm nào vượt được.",
};

const COLLECTOR_IS_CLI = {
  label: "Bộ thu bình luận tự khởi động",
  why:
    "Hôm nay bộ thu là một lệnh chạy trong terminal và cần video id của buổi live; chưa có " +
    "nút trên giao diện. Cần một kỹ sư ngồi cạnh trong phiên đầu tiên.",
};

const FB_NO_TOKEN_EVIDENCE = [
  "Graph API không token → HTTP 400 “An access token is required to request this resource” (code 104); hỏi Page thì 403 “(#200) Provide valid app ID”.",
  "Trang video công khai (≈ 450 KB HTML) → đọc được tiêu đề và lượt xem đã làm tròn, nhưng chuỗi “comment_count” xuất hiện 0 lần và thân bình luận 0 lần.",
  "mbasic.facebook.com (cách scrape kinh điển) → HTTP 400 với MỌI URL đã thử.",
  "oembed_video không token → HTTP 200 nhưng chỉ trả thẻ nhúng, và trả 200 cả với video id BỊA — không phải nguồn dữ liệu.",
  "yt-dlp → tệp facebook.py không có _get_comments: yt-dlp chưa bao giờ đọc bình luận Facebook. Không phải “hỏng hôm nay mai sửa”.",
];

const TIKTOK_WALLS = [
  {
    label: "Tường 1 — bình luận live đang phát",
    why:
      "Bắt tay WebSocket theo giao thức Webcast bị từ chối HTTP 400, 10/10 lần, thu được 0 " +
      "bình luận. Đo ngày 09/09/2026.",
  },
  {
    label: "Tường 2 — nội dung đã kết thúc",
    why:
      "Trang hồ sơ và trang /live trả về đúng một trang thử thách WAF nặng 1.155–1.462 byte, " +
      "không có nội dung. api/comment/list trả status_code 5 = từ chối; thêm tham số web " +
      "chuẩn thì thân phản hồi 0 byte.",
  },
  {
    label: "Tường 3 — công cụ sẵn có cũng không có",
    why:
      "Tệp tiktok.py của yt-dlp KHÔNG có _get_comments. Kể cả nếu tường WAF mở ra ngày mai, " +
      "yt-dlp vẫn không đọc được bình luận TikTok — đây là tính năng chưa từng tồn tại.",
  },
  {
    label: "Tường 4 — đường chính thức không mở cho Việt Nam",
    why:
      "TikTok CÓ Research API với endpoint bình luận, nhưng điều kiện nguyên văn là tổ chức " +
      "học thuật ở Mỹ, EEA, Anh, Canada hoặc Thụy Sĩ. Việt Nam không nằm trong danh sách. " +
      "FAQ chỉ nói “hy vọng mở rộng” — một lời hứa, không phải lộ trình có ngày.",
  },
  {
    label: "Tường 5 — và đây là tường nặng nhất, không phải chuyện kỹ thuật",
    why:
      "Người mua trên TikTok Shop bấm giỏ hàng TRONG app. Biến kết quả chính của LiveLift " +
      "(nhấp qua link đo /r/{code}) không tồn tại trên kênh này. Nếu cố ép dán link ngoài để " +
      "đo, bạn đẩy khách ra khỏi phễu mua hàng của chính mình. Đừng đánh đổi doanh thu thật " +
      "lấy một phép đo.",
  },
];

const RESTREAM_NOTE =
  "Khán giả YouTube khác khán giả TikTok, nên kết luận chỉ áp cho luồng YouTube — phải nói rõ " +
  "điều đó trong báo cáo. Có bằng chứng đường này chạy được: một buổi [LAZLIVE] đã vào hệ " +
  "thống đúng bằng cách này.";

// ---------------------------------------------------------------------------
// MA TRẬN — 20 ô, mỗi ô một câu trả lời viết riêng
//
// Khoá là `nền-tảng|của-ai|khi-nào`. Kiểu `Record<ComboKey, Outcome>` khiến
// TypeScript CƯỠNG CHẾ đủ 20 ô: thêm một nền tảng mà quên viết câu trả lời cho
// một tổ hợp nào của nó là lỗi biên dịch, không phải một nhánh âm thầm rơi vào
// câu trả lời chung chung. Đó chính là lỗi mà trang này sinh ra để xoá bỏ.
// ---------------------------------------------------------------------------

type ComboKey = `${Platform}|${Owner}|${When}`;

const MATRIX: Record<ComboKey, Outcome> = {
  "youtube|toi|dang-phat": {
    level: "de-xuat",
    ceiling: "thi-nghiem",
    headline: "Được — và đây là nền tảng hoàn chỉnh nhất để chạy một thí nghiệm thật.",
    now: {
      body:
        "Tạo sản phẩm, tạo phiên, bốc lịch BẬT/TẮT rồi mở Bàn điều khiển: chế độ ĐỀ XUẤT " +
        "chạy ngay hôm nay. Bạn thấy thẻ gợi ý “nên ghim cái này bây giờ”, và mọi quyết " +
        "định được ghi lại kèm xác suất đã bốc.",
      bullets: [
        "Bình luận chảy vào được ngay hôm nay qua yt-dlp — nhưng đó là đường TRÁI Điều khoản YouTube, chỉ nên dùng để kiểm thử kỹ thuật.",
        "Không có lịch gán thì API chặn phát sóng bằng lỗi 409. Đây là quy tắc bất biến duy nhất được cưỡng chế ở tầng API — và nó chính là thứ làm phép bốc thăm kiểm toán được.",
      ],
      action: RUN_ACTION,
    },
    upgrade: {
      time: "~10 phút cho khoá API · ~1 ngày cho tên miền",
      doc: "docs/nen-tang-ho-tro.md §2.2 · docs/mo-hinh-van-hanh-kol.md §5",
      body: "Bốn việc, xếp theo giá trị ÷ công sức, để lên mức THÍ NGHIỆM:",
      bullets: [
        "YOUTUBE_API_KEY — Google Cloud, MIỄN PHÍ, không cần thẻ, không cần xét duyệt, ~10 phút. Biến toàn bộ đường YouTube từ trái Điều khoản thành hợp lệ và hạ trễ từ ~24 giây xuống 2–5 giây. Rào cản duy nhất đang là chưa ai tạo project.",
        "Link đo /r/{code} cho từng sản phẩm, BẮT BUỘC kèm session_id. Đây là cái bẫy đắt nhất của cả hệ thống: thiếu session_id thì cú bấm biến mất khỏi thí nghiệm mà không ai thấy gì lạ.",
        "Máy chủ có tên miền thật (docker compose + Caddy đã sẵn sàng, chỉ thiếu VPS và DNS). Link localhost/r/{code} KHÔNG bấm được từ 4G trên điện thoại người xem — nghĩa là 0 nhấp, nghĩa là không có biến kết quả.",
        "Phiên ≥ 90 phút với khối 5 phút (16 khối: 8 BẬT / 8 TẮT). Đo thật: 30 phút chỉ được 4 khối và hệ thống cảnh báo kép; 60 phút vẫn cảnh báo; 90 phút mới đạt cả hai bảo đảm thiết kế.",
      ],
    },
    blocked: [
      {
        label: "Đơn hàng, doanh thu, GMV",
        why:
          "YouTube không có một tín hiệu thương mại nào — không đơn, không GMV. Nếu bạn bán " +
          "qua YouTube thì khách buộc phải rời nền tảng để mua, và đó chính là lý do link " +
          "đo hoạt động đúng bản chất ở đây.",
      },
      NO_PIN_FOR_YOU,
      COLLECTOR_IS_CLI,
    ],
  },

  "youtube|toi|da-ket-thuc": {
    level: "quan-sat",
    ceiling: "quan-sat",
    headline:
      "Được ngay, nhưng chỉ tới QUAN SÁT — buổi đã phát xong thì không bốc thăm ngược lại được.",
    now: {
      body:
        "Dán link buổi live của bạn vào ô dưới, y như với buổi của người khác: nhịp bình " +
        "luận, radar ý định, khoảnh khắc, sự kiện trả tiền công khai. 1–2 phút.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: "Chuẩn bị trước phiên: ~1 giờ, cộng ~10 phút xin khoá API",
      doc: "docs/mo-hinh-van-hanh-kol.md §5.2",
      body:
        "Không phải cho buổi NÀY — không có cách nào bốc thăm ngược về quá khứ. Nhưng cho " +
        "buổi SAU thì đường lên THÍ NGHIỆM rất rõ, và phải làm TRƯỚC khi lên sóng:",
      bullets: [
        "T−24h: chốt danh mục sản phẩm kèm URL trang sản phẩm thật, rồi tạo link đo /r/{code} có session_id cho từng sản phẩm. Mở thử từng link từ 4G trên điện thoại, không phải từ máy đang chạy hệ thống.",
        "T−1h: bốc lịch BẬT/TẮT và LƯU. Ghi lại seed và design_hash — ai giữ hash đó đều kiểm tra lại được là thiết kế đã chạy đúng là thiết kế đã công bố.",
        "T−15': mở màn hình host cho người dẫn, đặt bàn điều khiển KHUẤT tầm mắt người dẫn. Hỏng làm mù là lỗi không sửa được sau khi đã chạy.",
      ],
      action: RUN_ACTION,
    },
    blocked: [
      NO_VIEWERS_ON_VOD,
      {
        label: "Số nhấp sản phẩm của buổi này",
        why:
          "Buổi live này chưa đi qua link đo /r/{code} nào, nên không có cú bấm nào được ghi. " +
          "Không có cách gán ngược lượt nhấp cho một buổi đã phát.",
      },
      NO_CAUSAL_WITHOUT_DRAW,
      VOD_CAVEAT,
    ],
  },

  "youtube|nguoi-khac|dang-phat": {
    level: "khong",
    ceiling: "quan-sat",
    headline: "Chưa — sản phẩm cố ý không mở đường nạp buổi live ĐANG PHÁT của người khác.",
    now: {
      body:
        "Không có nút nào trong sản phẩm làm việc này. Đường gần nhất và hợp lệ: đợi buổi " +
        "live kết thúc rồi dán link vào ô dưới — nếu buổi đó còn chat replay thì bạn đọc " +
        "được toàn bộ, và chỉ mất 1–2 phút.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: null,
      body:
        "Về kỹ thuật thì yt-dlp ĐỌC ĐƯỢC chat của luồng đang phát — hôm 11/09 tìm thấy 6/6 " +
        "luồng đang phát có số người xem thật. Nhưng sản phẩm không mở đường đó, vì ba lý " +
        "do đều thật:",
      bullets: [
        "Trái Điều khoản YouTube: robots.txt chặn đúng hai đường yt-dlp gọi (/live_chat và /youtubei/).",
        "Trễ giao tin ~24 giây (p50) và 37 giây (p90) — đo thật. Ở nhịp live đó là quá chậm để ra quyết định.",
        "Là một lệnh chạy trong terminal, không có nút bấm nào.",
      ],
    },
    blocked: [
      NO_CAUSAL_WITHOUT_DRAW,
      {
        label: "Mọi mức trên QUAN SÁT",
        why:
          "Buổi live của người khác thì bạn không can thiệp được, không bốc thăm được. Trần " +
          "của tổ hợp này là QUAN SÁT, và chỉ sau khi buổi đó kết thúc.",
      },
      VOD_CAVEAT,
    ],
  },

  "youtube|nguoi-khac|da-ket-thuc": {
    level: "quan-sat",
    ceiling: "quan-sat",
    headline: "Làm được NGAY — dán link là xong. Đây là đường duy nhất không cần tài khoản gì.",
    now: {
      body:
        "Dán đường dẫn buổi live YouTube đã kết thúc vào ô dưới. 1–2 phút sau bạn có nhịp " +
        "bình luận theo từng 30 giây, radar ý định 11 lớp, các khoảnh khắc bình luận vọt " +
        "lên so với nền 5 phút trước đó, và cả sự kiện trả tiền công khai (Super Chat, quà, " +
        "hội viên) nếu buổi đó có.",
      bullets: [
        "Không cần khoá API, không cần tài khoản, không cần đụng vào buổi live của người ta.",
        "Chat thô chứa tên người bình luận nên bị lọc PII rồi XÓA ngay sau khi phân tích — không bao giờ nằm lại trên đĩa.",
      ],
      action: VOD_ACTION,
    },
    upgrade: {
      time: null,
      body:
        "Không có đường lên, và đây là giới hạn thật chứ không phải việc chưa làm. Bốc thăm " +
        "BẬT/TẮT phải xảy ra TRƯỚC khi phát sóng; buổi này đã phát xong và không phải của " +
        "bạn, nên không có gì để bốc và không có gì để can thiệp. Tổ hợp này dừng vĩnh viễn " +
        "ở mức QUAN SÁT.",
      bullets: [
        "Muốn lên ĐỀ XUẤT hoặc THÍ NGHIỆM thì buổi live phải là của chính bạn — đổi câu hỏi 1 sang “Của tôi”.",
      ],
    },
    blocked: [NO_VIEWERS_ON_VOD, {
      label: "Số nhấp sản phẩm",
      why: "Buổi live của người khác không đi qua link đo /r/{code} của bạn, nên không có cú bấm nào để đếm.",
    }, NO_CAUSAL_WITHOUT_DRAW, VOD_CAVEAT],
  },

  "facebook|toi|dang-phat": {
    level: "de-xuat",
    ceiling: "thi-nghiem",
    headline: "Chạy được, nhưng hôm nay MÙ bình luận — cần Page token, khoảng 25 phút.",
    now: {
      body:
        "Tạo phiên, bốc lịch BẬT/TẮT, mở Bàn điều khiển: chế độ ĐỀ XUẤT chạy được ngay. " +
        "Nhưng nói thẳng phần thiếu: khi chưa có token, thẻ gợi ý xếp hạng bằng prior chứ " +
        "không bằng dữ liệu của phiên, và radar ý định không có bình luận nào để đọc.",
      bullets: [
        "Hôm nay .env đang để FACEBOOK_PAGE_ACCESS_TOKEN trống, nên số bình luận đọc được là 0.",
      ],
      action: RUN_ACTION,
    },
    upgrade: {
      time: "~25 phút, KHÔNG cần App Review",
      doc: "docs/huong-dan-facebook-token.md · kiểm tra: scripts/kiem_tra_facebook.py",
      body:
        "Một Fanpage do bạn quản trị, một app Meta ở Development Mode, và một Page token dài " +
        "hạn. Page của chính mình thì KHÔNG cần App Review — đây là lý do đường này chỉ mất " +
        "25 phút thay vì 4–6 tuần.",
      bullets: [
        "Token phải có ĐỦ HAI quyền: pages_read_engagement VÀ pages_read_user_content.",
        "CÁI BẪY ĐẮT NHẤT: pages_read_engagement chỉ cho đọc nội dung Page TỰ ĐĂNG. Bình luận là nội dung NGƯỜI XEM. Thiếu pages_read_user_content thì đọc được đúng 0 bình luận — mà đó chính là biến kết quả của LiveLift.",
        "Kiểm tra bằng scripts/kiem_tra_facebook.py: phải in “KẾT LUẬN: SẴN SÀNG”, và nó in luôn Live video id để dán vào bộ thu.",
        "Sau đó vẫn cần đủ ba thứ của mức THÍ NGHIỆM: link đo /r/{code} có session_id, số người xem theo thời gian, và phiên ≥ 90 phút.",
      ],
    },
    blocked: [
      {
        label: "Đơn hàng, doanh thu, GMV",
        why: "Facebook không trả một tín hiệu thương mại nào cho live. Biến kết quả phải là nhấp qua link đo của bạn.",
      },
      {
        label: "Không biết trước dán link ngoài có bị hạ phân phối không",
        why:
          "Dán link đo vào bình luận trên Facebook CÓ THỂ làm buổi live bị hạ phân phối. " +
          "Nhóm CHƯA đo mức độ ảnh hưởng, nên không hứa gì ở đây — đây là câu hỏi cho chính " +
          "bạn với tư cách người bán, không phải cho kỹ sư.",
      },
      NO_PIN_FOR_YOU,
    ],
  },

  "facebook|toi|da-ket-thuc": {
    level: "khong",
    ceiling: "quan-sat",
    headline: "Chưa — và phải nói thẳng: nhóm CHƯA kiểm chứng được đường này.",
    now: {
      body:
        "Sản phẩm không có ô dán link Facebook. Đường thay thế gần nhất: nếu buổi đó có phát " +
        "song song lên YouTube và bản YouTube đã kết thúc còn chat replay, dán link YouTube " +
        "vào ô dưới là chạy được ngay.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: "~25 phút lấy token, rồi 5 phút là biết kết quả",
      doc: "docs/nen-tang-ho-tro.md §3.5",
      body:
        "Gần như chắc chắn CÓ, nhưng chưa ai chạy thử, nên đừng ghi vào hồ sơ như việc đã " +
        "chạy. Đây là ranh giới giữa cái đã xác nhận và cái chưa:",
      bullets: [
        "ĐÃ xác nhận: edge /{video-id}/comments có thật (phép thử phân biệt edge thật với edge bịa qua mã lỗi Graph).",
        "ĐÃ xác nhận: tài liệu lỗi của Meta cho edge này đòi đúng bộ quyền pages_read_engagement / pages_read_user_content — tức đúng bộ quyền đã dùng cho live.",
        "ĐÃ xác nhận: buổi live kết thúc đi qua LIVE → LIVE_STOPPED → PROCESSING → VOD; ở trạng thái VOD nó là một video của Page và bình luận vẫn nằm đó.",
        "CHƯA xác nhận: tài liệu live-video/comments không nói một chữ nào về việc edge còn dùng được sau khi phát xong (mục “Live vs. Ended” trống). Không có token nên không thử được.",
        "Cách biết dứt điểm: có token rồi thì phát live thử 2 phút, kết thúc, gọi /{video-id}/comments. 5 phút là biết.",
      ],
    },
    blocked: [
      {
        label: "Không được trình bày đường này như việc đã kiểm chứng",
        why:
          "Đây là tổ hợp DUY NHẤT trong cả ma trận mà câu trả lời trung thực là “chưa biết”. " +
          "Ghi nó vào hồ sơ như một khả năng đã chạy là điều dễ bị hội đồng bắt lỗi nhất — " +
          "và mất 5 phút để biến nó thành sự thật đã kiểm chứng.",
      },
      {
        label: "Không đọc được bình luận cho tới khi có token",
        why:
          "Hôm nay .env để FACEBOOK_PAGE_ACCESS_TOKEN trống, nên mọi đường dẫn tới bình luận " +
          "Facebook đều trả về rỗng, kể cả trên Page của chính bạn.",
      },
    ],
  },

  "facebook|nguoi-khac|dang-phat": {
    level: "khong",
    ceiling: "khong",
    headline: "Không — và chờ buổi live kết thúc cũng không mở thêm cánh cửa nào.",
    now: {
      body:
        "Không có gì. Đã thử THẬT 5 đường không token trên video công khai của chính Meta, và " +
        "không đường nào lấy được MỘT bình luận nào. Khả năng duy nhất còn lại nằm ngoài " +
        "Facebook: nếu người đó có phát song song lên YouTube, đợi bản YouTube ấy kết thúc rồi " +
        "dán link vào ô dưới.",
      bullets: FB_NO_TOKEN_EVIDENCE,
      action: VOD_ACTION,
    },
    upgrade: {
      time: "4–6 tuần, và phải có văn bản đồng ý của chủ Page",
      doc: "docs/nen-tang-ho-tro.md §3.6",
      body:
        "Có đường, nhưng nó dài và không nên là kế hoạch A: Advanced Access cho cả hai quyền, " +
        "kèm Business Verification của Meta phải xong TRƯỚC. Verification mất 10+ ngày; mỗi " +
        "quyền cần một video quay màn hình; hồ sơ sạch thì 2–7 ngày, bị trả lại thì ~20 ngày, " +
        "và mỗi lần bị từ chối là đếm lại từ đầu.",
      bullets: [
        "Đường thay thế NHANH HƠN NHIỀU: xin chủ Page thêm bạn làm quản trị viên. Buổi live lập tức thành “của tôi” và bạn về lại đường 25 phút.",
        "Ranh giới không được lách: chỉ thu thập trên Page mình sở hữu, hoặc Page đối tác đã có văn bản đồng ý kèm Advanced Access. Dùng token của người khác để đọc Page họ không đồng ý là vi phạm Điều khoản Nền tảng của Meta.",
      ],
    },
    blocked: [
      {
        label: "Bình luận theo thời gian thực — bằng mọi đường không token",
        why:
          "Facebook render bình luận SAU, bằng một truy vấn có xác thực. HTML công khai cho " +
          "biết video tên gì và bao nhiêu lượt xem (đã làm tròn), nhưng không chứa một chữ " +
          "nào của bình luận.",
      },
      {
        label: "Số người xem theo thời gian",
        why: "Cùng một cánh cổng, cùng một câu trả lời: không token thì không có.",
      },
      NO_CAUSAL_WITHOUT_DRAW,
    ],
  },

  "facebook|nguoi-khac|da-ket-thuc": {
    level: "khong",
    ceiling: "khong",
    headline: "Không. Buổi đã kết thúc của Page người khác vẫn nằm sau đúng cánh cổng đó.",
    now: {
      body:
        "Không có gì. Buổi live kết thúc sẽ thành một video của Page, và video của Page người " +
        "khác cũng đòi đúng bộ quyền như lúc đang phát — đã thử THẬT 5 đường không token, " +
        "không đường nào lấy được MỘT bình luận nào. Đường thay thế gần nhất: nếu buổi đó có " +
        "bản YouTube đã kết thúc còn chat replay, dán link YouTube vào ô dưới là ra kết quả " +
        "QUAN SÁT ngay.",
      bullets: FB_NO_TOKEN_EVIDENCE,
      action: VOD_ACTION,
    },
    upgrade: {
      time: "4–6 tuần, và phải có văn bản đồng ý của chủ Page",
      doc: "docs/nen-tang-ho-tro.md §3.6",
      body:
        "Có đường, nhưng nó dài và không nên là kế hoạch A: Advanced Access cho cả hai quyền, " +
        "kèm Business Verification của Meta phải xong TRƯỚC. Verification mất 10+ ngày; mỗi " +
        "quyền cần một video quay màn hình; hồ sơ sạch thì 2–7 ngày, bị trả lại thì ~20 ngày, " +
        "và mỗi lần bị từ chối là đếm lại từ đầu.",
      bullets: [
        "Đường thay thế NHANH HƠN NHIỀU: xin chủ Page thêm bạn làm quản trị viên. Buổi live lập tức thành “của tôi” và bạn về lại đường 25 phút.",
        "Ranh giới không được lách: chỉ thu thập trên Page mình sở hữu, hoặc Page đối tác đã có văn bản đồng ý kèm Advanced Access. Dùng token của người khác để đọc Page họ không đồng ý là vi phạm Điều khoản Nền tảng của Meta.",
      ],
    },
    blocked: [
      {
        label: "Bình luận của video đã kết thúc",
        why:
          "Edge /{video-id}/comments có thật, nhưng tài liệu lỗi của Meta cho edge này đòi " +
          "pages_read_engagement và/hoặc pages_read_user_content — tức vẫn phải là token của " +
          "Page đó. Không token thì kết quả y hệt lúc đang phát: rỗng.",
      },
      NO_VIEWERS_ON_VOD,
      NO_CAUSAL_WITHOUT_DRAW,
    ],
  },

  "tiktok|toi|dang-phat": {
    level: "khong",
    ceiling: "khong",
    headline:
      "Không — kể cả buổi live của CHÍNH BẠN. TikTok không mở một đường nào để đọc bình luận live.",
    now: {
      body:
        "Trên chính TikTok: không gì cả, và không có cách diễn đạt nào làm điều này dễ nghe " +
        "hơn. Đường THẬT duy nhất hôm nay là phát song song (restream) lên YouTube rồi chạy " +
        "LiveLift trên luồng YouTube đó — tạo phiên, bốc lịch, và chế độ ĐỀ XUẤT chạy bình " +
        "thường trên luồng ấy.",
      bullets: [RESTREAM_NOTE],
      action: RUN_ACTION,
    },
    upgrade: {
      time: "30 phút để có kết luận dứt điểm",
      doc: "docs/nen-tang-ho-tro.md §6.4",
      body:
        "Chưa có đường lên, nhưng CÓ một việc đáng làm và nó đang là việc số 1 trong lộ " +
        "trình: dò danh mục TikTok Shop Partner API. Hôm nay CHƯA dò được, và phải nói rõ " +
        "là chưa dò được chứ không phải không có:",
      bullets: [
        "Cổng open-api.tiktokglobalshop.com xác nhận app_key là tham số có thật (400, “Invalid credentials”).",
        "Nhưng đường live/... là do ĐOÁN TÊN, và đối chứng đường bịa cũng trả 404 — nên 404 ở đây chỉ có nghĩa “đoán sai tên”, KHÔNG có nghĩa “không tồn tại”.",
        "Phải đăng nhập Partner Center đọc danh mục v2 mới biết. Nếu có module live như Shopee thì đó là nguồn dữ liệu giá trị nhất của cả đề tài — nền tảng live-commerce số 1 Việt Nam, và hoàn toàn hợp Điều khoản vì là API chính thức cho shop của chính mình.",
      ],
    },
    blocked: TIKTOK_WALLS,
  },

  "tiktok|toi|da-ket-thuc": {
    level: "khong",
    ceiling: "khong",
    headline: "Không. Nội dung TikTok đã kết thúc còn bị chặn chặt hơn cả live đang phát.",
    now: {
      body:
        "Không có gì trên TikTok. Đường thay thế duy nhất: nếu buổi đó có bản restream trên " +
        "YouTube và bản đó đã kết thúc còn chat replay, dán link YouTube vào ô dưới → QUAN " +
        "SÁT ngay, không cần tài khoản gì.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: null,
      body:
        "Không có đường lên cho nội dung đã kết thúc. Việc đáng làm duy nhất là dò danh mục " +
        "TikTok Shop Partner API (30 phút) để đóng dứt điểm câu hỏi này — nhưng kể cả nếu " +
        "có, Partner API là API cho shop của chính mình theo thời gian thực, không phải kho " +
        "lưu trữ bình luận cũ.",
      bullets: [
        "Đừng đầu tư thêm một giờ nào vào đường không chính thức: thư viện TikTokLive là dịch ngược giao thức Webcast, dùng nó có thể vi phạm Điều khoản TikTok và còn đẩy lưu lượng qua proxy bên thứ ba.",
      ],
    },
    blocked: TIKTOK_WALLS,
  },

  "tiktok|nguoi-khac|dang-phat": {
    level: "khong",
    ceiling: "khong",
    headline: "Không — và khác với live của chính bạn, ở đây không còn cả đường restream.",
    now: {
      body:
        "Không có gì. Đường phát song song lên YouTube cần CHÍNH BẠN là người phát; buổi live " +
        "của người khác thì bạn không dựng được luồng song song. Chỉ còn một khả năng, và nó " +
        "không nằm trong tay bạn: chính người đó có phát song song lên YouTube — đợi buổi ấy " +
        "kết thúc rồi dán link YouTube vào ô dưới.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: null,
      body:
        "Không có đường lên. Đây là giao điểm của hai điều không thể: nền tảng không cho đọc " +
        "bình luận live, và bạn không can thiệp được vào buổi phát nên cũng không bốc thăm " +
        "được. Kể cả nếu TikTok Shop Partner API có module live, nó là API cho shop của chính " +
        "mình — không mở buổi live của người khác.",
    },
    blocked: TIKTOK_WALLS,
  },

  "tiktok|nguoi-khac|da-ket-thuc": {
    level: "khong",
    ceiling: "khong",
    headline: "Không. Đây là ô kín nhất trong cả bảng — không một đường nào, kể cả đường vòng.",
    now: {
      body:
        "Không có gì trên TikTok: trang hồ sơ và trang /live chỉ trả về trang thử thách WAF " +
        "1.155–1.462 byte. Và bạn cũng không có quyền gì với buổi phát để bù lại. Khả năng " +
        "duy nhất: chính người đó có phát song song lên YouTube và bản YouTube còn chat replay " +
        "— dán link YouTube vào ô dưới thì đọc được.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: null,
      body:
        "Không có đường lên, và đừng đầu tư thêm một giờ nào vào đường không chính thức: thư " +
        "viện TikTokLive là dịch ngược giao thức Webcast, dùng nó có thể vi phạm Điều khoản " +
        "TikTok và còn đẩy lưu lượng qua proxy bên thứ ba.",
    },
    blocked: TIKTOK_WALLS,
  },

  "shopee|toi|dang-phat": {
    level: "de-xuat",
    ceiling: "thi-nghiem",
    headline:
      "Chưa đọc được hôm nay — nhưng đây là nền tảng ĐÁNG ĐẦU TƯ NHẤT: API chính thức có cả bình luận LẪN đơn hàng.",
    now: {
      body:
        "Chế độ ĐỀ XUẤT chạy được ngay như mọi nền tảng khác: tạo phiên, bốc lịch BẬT/TẮT, " +
        "mở Bàn điều khiển và bấm thẻ. Phần đọc Shopee thì chưa — .env chưa có " +
        "SHOPEE_PARTNER_ID. Nhưng bộ đọc đã viết xong và có 26 test xanh, nên khi có danh " +
        "tính là chạy ngay, không phải viết thêm dòng nào.",
      action: RUN_ACTION,
    },
    upgrade: {
      time: "Vài ngày chờ duyệt tài khoản",
      doc: "docs/nen-tang-ho-tro.md §4 · scripts/kiem_tra_shopee.py",
      body:
        "Hai bước, và đổi lại là thứ không nền tảng nào khác cho: vừa biến can thiệp (shop " +
        "tự chạy phiên của mình nên bốc thăm được) vừa biến kết quả thương mại thật.",
      bullets: [
        "Đăng ký tài khoản Shopee Open Platform (open.shopee.com) → partner_id + partner_key.",
        "Chủ shop chạy luồng ủy quyền OAuth → shop_id + access_token + refresh_token.",
        "Được gì: get_latest_comment_list (bình luận) và get_session_metric (gmv · orders · atc · ctr · ccu · likes · shares · views · thời lượng xem trung bình). Mọi dòng tài liệu đều ghi rõ có VN.",
        "CHƯA xác minh được: thời gian duyệt tài khoản Open Platform và hạn mức gọi API. Phải đọc trong Partner Portal sau khi đăng ký — không bịa số.",
      ],
    },
    blocked: [
      {
        label: "Không chạy được một phiên dài rồi bỏ mặc kết nối",
        why:
          "access_token của Shopee chỉ sống 4 GIỜ. Phiên live dài PHẢI làm mới token bằng " +
          "refresh_token giữa chừng, nếu không nguồn đứt giữa phiên. Đây là khác biệt lớn " +
          "so với Page token Facebook, thứ không hết hạn.",
      },
      {
        label: "Không poll chậm hơn 8 giây được — và không sửa lại được về sau",
        why:
          "get_latest_comment_list chỉ trả bình luận của 10 giây gần nhất và không có con " +
          "trỏ lùi, nên poll chậm hơn là MẤT VĨNH VIỄN. Bộ đọc vì thế ném lỗi ngay nếu nhịp " +
          "poll > 8 giây, thay vì chạy rồi âm thầm bỏ sót bình luận trong một thí nghiệm " +
          "nhân quả.",
      },
      {
        label: "Không lấy thẳng được số liệu theo từng khối BẬT/TẮT",
        why:
          "get_session_metric trả số cộng dồn từ đầu phiên, không phải sự kiện có dấu thời " +
          "gian. Muốn số theo khối thì phải lấy HIỆU giữa hai mốc đầu/cuối khối — và phải " +
          "khai báo trong phương pháp rằng biến kết quả là sai phân của một bộ đếm cộng " +
          "dồn. Thêm nữa, ranh giới khối có jitter ±30 giây nên lịch gọi API phải bám ranh " +
          "giới THẬT, không phải ranh giới danh nghĩa. Đây là điểm chắc chắn bị phản biện hỏi.",
      },
      NO_PIN_FOR_YOU,
    ],
  },

  "shopee|toi|da-ket-thuc": {
    level: "khong",
    ceiling: "quan-sat",
    headline: "Bình luận thì KHÔNG lấy lại được. Số tổng của phiên thì có — sau khi có tài khoản.",
    now: {
      body:
        "Hôm nay: không có gì, .env chưa có SHOPEE_PARTNER_ID. Và kể cả khi có, buổi đã kết " +
        "thúc vẫn không trả lại bình luận — xem phần dưới.",
    },
    upgrade: {
      time: "Vài ngày chờ duyệt tài khoản",
      doc: "docs/nen-tang-ho-tro.md §4.1",
      body:
        "Có tài khoản Open Platform + shop ủy quyền thì đọc được phần metadata của buổi đã " +
        "kết thúc, nhưng hãy biết chính xác mình nhận được gì:",
      bullets: [
        "get_session_detail → tiêu đề, trạng thái (2 = đã kết thúc), giờ bắt đầu, giờ kết thúc, share_url.",
        "get_session_metric → gmv, orders, atc, ctr, ccu, likes, views của CẢ PHIÊN. Đó là một con số tổng, không phải chuỗi theo thời gian.",
        "Muốn có bình luận và số theo khối thì phải bám phiên NGAY LÚC ĐANG PHÁT — đổi câu hỏi 3 sang “Đang phát”.",
      ],
    },
    blocked: [
      {
        label: "Bình luận của buổi đã kết thúc",
        why:
          "get_latest_comment_list chỉ trả 10 giây gần nhất và không có con trỏ lùi. Không " +
          "có đường nào đọc ngược về quá khứ — bình luận không thu lúc đang phát là mất " +
          "vĩnh viễn.",
      },
      {
        label: "Số liệu theo từng khối BẬT/TẮT",
        why:
          "get_session_metric là bộ đếm cộng dồn; buổi đã kết thúc chỉ còn đúng một con số " +
          "cuối cùng, không tách ngược về từng khối được. Không có số theo khối thì không " +
          "có phép so sánh, và không có phép so sánh thì không có thí nghiệm.",
      },
    ],
  },

  "shopee|nguoi-khac|dang-phat": {
    level: "khong",
    ceiling: "khong",
    headline:
      "Không. Shopee Live trên web công khai là “xem thì mở app” — không có chat, đã thử có đối chứng.",
    now: {
      body:
        "Không có gì, và đừng tìm nữa. Đây là kết quả thật của từng đường đã thử ngày " +
        "11/09/2026:",
      bullets: [
        "live.shopee.vn/share?… → HTTP 200 nhưng dữ liệu trang rỗng (“sessionid”: null) — đây là màn hình đẩy sang app, không phải trình phát.",
        "live.shopee.vn/api/v1/session/1 → HTTP 403, is_login: false.",
        "Grep 12.971.905 byte bundle JS của live.shopee.vn: tìm thấy ~50 đường API của sàn và hàng chục đường phía NGƯỜI PHÁT, nhưng KHÔNG có endpoint bình luận phía người xem và KHÔNG có một URL wss:// nào.",
        "Đối chứng mạng: shopee.vn/api/v4/pages/get_homepage_category_list → HTTP 200 kèm dữ liệu thật. Mạng không bị chặn — 403 ở trên là CHÍNH SÁCH, không phải sự cố.",
      ],
    },
    upgrade: {
      time: "Chỉ khi chủ shop tự ủy quyền cho bạn",
      doc: "docs/nen-tang-ho-tro.md §4.2",
      body:
        "Đường duy nhất là chủ shop chạy luồng ủy quyền OAuth cho ứng dụng của bạn, kèm văn " +
        "bản đồng ý. Khi đó buổi live thành “của tôi” về mặt quyền truy cập và bạn về lại " +
        "đường Shopee đầy đủ — nền tảng duy nhất có cả bình luận lẫn đơn hàng.",
      bullets: [
        "Ranh giới: chỉ đọc shop đã ủy quyền. Đọc shop chưa đồng ý là vi phạm, và cũng không có cách kỹ thuật nào để làm.",
      ],
    },
    blocked: [
      {
        label: "Bình luận, người xem, đơn hàng — tất cả",
        why: "Không có tài khoản đã ủy quyền thì không một endpoint nào trả dữ liệu.",
      },
      NO_CAUSAL_WITHOUT_DRAW,
    ],
  },

  "shopee|nguoi-khac|da-ket-thuc": {
    level: "khong",
    ceiling: "khong",
    headline: "Không — và buổi đã kết thúc còn ít hơn nữa: không bình luận, cũng không số theo khối.",
    now: {
      body:
        "Không có gì. Web công khai của Shopee Live vốn đã không có chat (bằng chứng bên " +
        "dưới), và buổi đã kết thúc thì ngay cả chủ shop có tài khoản hợp lệ cũng không lấy " +
        "lại được bình luận — API chỉ trả 10 giây gần nhất và không có con trỏ lùi.",
      bullets: [
        "live.shopee.vn/share?… → HTTP 200 nhưng dữ liệu trang rỗng (“sessionid”: null) — đây là màn hình đẩy sang app, không phải trình phát.",
        "live.shopee.vn/api/v1/session/1 → HTTP 403, is_login: false.",
        "Grep 12.971.905 byte bundle JS của live.shopee.vn: tìm thấy ~50 đường API của sàn và hàng chục đường phía NGƯỜI PHÁT, nhưng KHÔNG có endpoint bình luận phía người xem và KHÔNG có một URL wss:// nào.",
        "Đối chứng mạng: shopee.vn/api/v4/pages/get_homepage_category_list → HTTP 200 kèm dữ liệu thật. Mạng không bị chặn — 403 ở trên là CHÍNH SÁCH, không phải sự cố.",
      ],
    },
    upgrade: {
      time: "Chỉ khi chủ shop tự ủy quyền cho bạn — và vẫn không có bình luận",
      doc: "docs/nen-tang-ho-tro.md §4.1",
      body:
        "Kể cả khi chủ shop ủy quyền OAuth cho bạn, buổi ĐÃ KẾT THÚC chỉ trả về phần " +
        "metadata: get_session_detail (tiêu đề, trạng thái, giờ bắt đầu/kết thúc) và " +
        "get_session_metric (gmv, orders, atc, ccu, views) của cả phiên. Đó là một con số " +
        "tổng, không phải chuỗi theo thời gian, và không có một bình luận nào.",
      bullets: [
        "Muốn có bình luận thì phải bám phiên NGAY LÚC ĐANG PHÁT — không có đường đọc ngược về quá khứ.",
      ],
    },
    blocked: [
      {
        label: "Bình luận của buổi đã kết thúc",
        why:
          "get_latest_comment_list chỉ trả 10 giây gần nhất và không có con trỏ lùi. Bình " +
          "luận không thu lúc đang phát là mất vĩnh viễn — với chủ shop cũng vậy, với người " +
          "ngoài thì càng không.",
      },
      {
        label: "Số liệu theo từng khối BẬT/TẮT",
        why:
          "get_session_metric là bộ đếm cộng dồn; buổi đã kết thúc chỉ còn đúng một con số " +
          "cuối cùng, không tách ngược về từng khối được.",
      },
      NO_CAUSAL_WITHOUT_DRAW,
    ],
  },

  "khac|toi|dang-phat": {
    level: "de-xuat",
    ceiling: "thi-nghiem",
    headline: "Được nhiều hơn bạn tưởng — LiveLift không cần đọc nền tảng để chạy chế độ ĐỀ XUẤT.",
    now: {
      body:
        "LiveLift không cắm vào nền tảng để đưa ra thẻ gợi ý. Nó chỉ cần ba thứ: một phiên, " +
        "một lịch BẬT/TẮT đã bốc, và một người ngồi bấm. Ba thứ đó chạy trên MỌI nền tảng — " +
        "kể cả nền tảng LiveLift không đọc được bình luận.",
      bullets: [
        "Hệ thống chấm điểm sản phẩm bằng hậu nghiệm Gamma-Poisson và, khi thật sự không chắc, nó BỐC THĂM giữa các ứng viên rồi ghi lại xác suất đã bốc. Đó là thứ không công cụ thương mại nào ghi.",
        "Không có lịch gán thì API chặn phát sóng bằng 409 — kể cả trên nền tảng “khác”.",
      ],
      action: RUN_ACTION,
    },
    upgrade: {
      time: "Phụ thuộc kênh bán của bạn — có kênh thì không cần API nào cả",
      doc: "docs/mo-hinh-van-hanh-kol.md §4.1",
      body:
        "Và đây là điều ít người nghĩ tới: nếu bạn bán qua WEBSITE RIÊNG hoặc qua INBOX " +
        "(Messenger, Zalo) thì link đo /r/{code} hoạt động HOÀN HẢO — đó là ca lý tưởng của " +
        "thiết kế, và bạn không cần API của nền tảng nào cả.",
      bullets: [
        "Website riêng / landing page: /r/{code} trỏ thẳng trang sản phẩm của bạn. Đúng bản chất một cú nhấp.",
        "Inbox (m.me/… hoặc zalo.me/…): bấm là mở chat, và ta đếm được cú bấm. Rất hợp thị trường Việt Nam.",
        "Còn thiếu đúng một mảnh: SỐ NGƯỜI XEM THEO THỜI GIAN — mẫu số của biến kết quả. Nền tảng “khác” không có bộ thu, nên phải nhập qua POST /ticks. Khối nào dưới 60 viewer-giây bị LOẠI khỏi phân tích, không bị tính là 0.",
        "Và phiên ≥ 90 phút: dưới mức đó hệ thống vẫn chạy nhưng nói thẳng trước khi lên sóng rằng bảo đảm thiết kế không đạt.",
      ],
    },
    blocked: [
      {
        label: "Đọc bình luận tự động",
        why:
          "Bộ thu chỉ nhận youtube, facebook và shopee. Tạo phiên với nền tảng khác thì vẫn " +
          "tạo được, nhưng phiên sẽ rỗng nếu không có nguồn nào bơm dữ liệu vào.",
      },
      {
        label: "Nhập bình luận và người xem bằng tay",
        why:
          "Được về kỹ thuật (POST /comments và POST /ticks nhận dữ liệu nhập tay), KHÔNG " +
          "được về thực tế: phải gõ liên tục suốt phiên, và giao diện web không có ô nhập — " +
          "chỉ làm được bằng lệnh. Không ai làm nổi ở nhịp live thật.",
      },
      {
        label: "Lazada (LazLive) — chưa kết luận được, và nói rõ là chưa",
        why:
          "Cổng api.lazada.vn kiểm app_key TRƯỚC KHI định tuyến: đường thật và đường bịa trả " +
          "y hệt một lỗi InvalidAppKey. Nên chưa là ISV đã đăng ký thì KHÔNG dò được có API " +
          "livestream hay không. Đường vòng rẻ tiền: nhiều shop Lazada phát song song lên " +
          "YouTube — một buổi [LAZLIVE] đã vào hệ thống đúng bằng đường đó.",
      },
      {
        label: "Instagram và Zalo",
        why:
          "Instagram đi qua đúng cánh cổng Meta như Facebook và không mở thêm khả năng nào, " +
          "trong khi thị phần live-commerce ở Việt Nam nhỏ hơn hẳn — nếu đã phải làm App " +
          "Review thì làm cho Facebook. Zalo Official Account xoay quanh tin nhắn, không có " +
          "module livestream: KHÔNG ÁP DỤNG.",
      },
      NO_PIN_FOR_YOU,
    ],
  },

  "khac|toi|da-ket-thuc": {
    level: "khong",
    ceiling: "quan-sat",
    headline: "Buổi đã kết thúc trên một nền tảng LiveLift không đọc được thì không còn gì để nạp.",
    now: {
      body:
        "Một đường duy nhất, và nó thật: nếu buổi đó có phát song song lên YouTube và bản " +
        "YouTube đã kết thúc còn chat replay, dán link vào ô dưới → QUAN SÁT ngay, không " +
        "cần tài khoản gì. Đây chính là cách một buổi [LAZLIVE] đã vào hệ thống.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: "Chuẩn bị trước phiên: ~1 giờ",
      doc: "docs/mo-hinh-van-hanh-kol.md §5.2",
      body:
        "Không phải cho buổi này. Nhưng cho buổi SAU, nếu bạn bán qua website riêng hoặc " +
        "inbox thì bạn đi thẳng lên được mức THÍ NGHIỆM mà không cần API của nền tảng nào:",
      bullets: [
        "Tạo sản phẩm kèm URL thật → tạo link đo /r/{code} CÓ session_id → tạo phiên ≥ 90 phút → bốc lịch BẬT/TẮT → lên sóng.",
        "Thiếu mảnh nào thì hệ thống tuyên bố THIẾU và từ chối trả số, chứ không bịa.",
      ],
      action: RUN_ACTION,
    },
    blocked: [
      {
        label: "Bình luận của buổi đã kết thúc",
        why:
          "Không có bộ thu cho nền tảng ngoài youtube / facebook / shopee, và buổi đã phát " +
          "xong thì cũng không còn nguồn nào để bơm vào.",
      },
      NO_VIEWERS_ON_VOD,
      NO_CAUSAL_WITHOUT_DRAW,
    ],
  },

  "khac|nguoi-khac|dang-phat": {
    level: "khong",
    ceiling: "khong",
    headline: "Không — buổi live của người khác, trên nền tảng không có API công khai.",
    now: {
      body:
        "Không có đường nào, và cũng không nên có: không nền tảng nào cho phép đọc buổi live " +
        "của người lạ mà không xin phép. Đó là THIẾT KẾ, không phải trở ngại kỹ thuật. Khả " +
        "năng duy nhất còn lại: người đó có phát song song lên YouTube — đợi buổi ấy kết thúc " +
        "rồi dán link YouTube vào ô dưới.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: null,
      body:
        "Không có đường lên. Mọi dịch vụ trôi nổi bán “API bình luận” cho nền tảng khác đều " +
        "là scraping có rủi ro pháp lý. LiveLift chọn không lách — và đó là một luận điểm, " +
        "không phải một lời xin lỗi.",
      bullets: [
        "Đường thay thế duy nhất có thật: xin chủ buổi live cho bạn quyền (làm quản trị viên Page, hoặc ủy quyền OAuth shop). Khi đó buổi live thành “của tôi” và mọi cánh cửa mở lại.",
      ],
    },
    blocked: [
      {
        label: "Bình luận, người xem, nhấp — tất cả",
        why: "Không có nguồn nào, nên không có gì để hiển thị và cũng không có gì để đo.",
      },
      NO_CAUSAL_WITHOUT_DRAW,
    ],
  },

  "khac|nguoi-khac|da-ket-thuc": {
    level: "khong",
    ceiling: "khong",
    headline: "Không. Chỉ còn đúng một khả năng: bản YouTube đã kết thúc của chính buổi đó.",
    now: {
      body:
        "Nếu người đó có phát song song lên YouTube và bản YouTube còn chat replay, dán link " +
        "vào ô dưới là ra kết quả QUAN SÁT ngay — không cần tài khoản gì. Ngoài đường đó ra " +
        "thì không còn gì: buổi đã phát xong, trên một nền tảng không có API công khai, và " +
        "bạn cũng không có quyền gì với nó.",
      action: VOD_ACTION,
    },
    upgrade: {
      time: null,
      body:
        "Không có đường lên. Buổi đã kết thúc thì không còn nguồn nào để bơm dữ liệu vào, và " +
        "buổi của người khác thì không bốc thăm được — hai điều đó cộng lại là một ngõ cụt, " +
        "không phải một việc chưa làm.",
    },
    blocked: [
      {
        label: "Bình luận của buổi đã kết thúc",
        why:
          "Bộ thu chỉ nhận youtube, facebook và shopee; ngoài ba nền tảng đó không có đường " +
          "nạp nào, và buổi đã phát xong cũng không còn luồng để bám.",
      },
      NO_VIEWERS_ON_VOD,
      NO_CAUSAL_WITHOUT_DRAW,
    ],
  },

};

/** Câu trả lời cho ĐÚNG một tổ hợp. Không có nhánh mặc định chung chung. */
export function outcomeFor(platform: Platform, owner: Owner, when: When): Outcome {
  return MATRIX[`${platform}|${owner}|${when}`];
}

/** Đọc lựa chọn từ query string — trang này deep-link được cho từng tổ hợp. */
export function parseQuery(search: string): {
  owner: Owner | null;
  platform: Platform | null;
  when: When | null;
} {
  const q = new URLSearchParams(search);
  const owner = q.get("cua");
  const platform = q.get("nen");
  const when = q.get("khi");
  return {
    owner: OWNERS.includes(owner as Owner) ? (owner as Owner) : null,
    platform: PLATFORMS.includes(platform as Platform) ? (platform as Platform) : null,
    when: WHENS.includes(when as When) ? (when as When) : null,
  };
}
