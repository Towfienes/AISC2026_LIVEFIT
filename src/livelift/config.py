"""Application configuration, loaded from environment / .env.

All I/O-facing settings live here. Pure/statistical modules never read config —
they take explicit parameters, so they stay testable without an environment.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    livelift_env: str = "dev"
    # 127.0.0.1, NOT "localhost": on Windows localhost resolves to ::1 first
    # while Docker publishes only 127.0.0.1:5432, so psycopg waits out the
    # IPv6 connect timeout before falling back — measured 2m10s vs 0.5s
    # (incident 27/08). Every CLI looked hung.
    database_url: str = "postgresql://livelift:livelift@127.0.0.1:5432/livelift"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # --- Chống mất dữ liệu ở chế độ kho 'memory' (sự cố 11/09/2026) -------
    # Ngày 11/09/2026 tiến trình API khởi động lại lúc 13:05:53 và 13 phiên
    # live thật + 17.535 bình luận biến mất vĩnh viễn, vì kho chỉ nằm trong
    # RAM. Ảnh chụp định kỳ là lưới an toàn cho chế độ đó; nó KHÔNG thay thế
    # STORE_BACKEND=postgres cho phiên live thật.
    #
    # Mặc định BẬT: một cơ chế an toàn phải mặc định bảo vệ, người dùng phải
    # chủ động tắt mới mất. Chỉ áp dụng cho kho 'memory'.
    store_snapshot_enabled: bool = True
    store_snapshot_path: str = "data/snapshot/livelift-store.json"
    # 30 giây = mức mất tối đa khi tiến trình chết đột ngột. Tắt máy có trật
    # tự luôn chụp lần cuối nên không mất gì.
    store_snapshot_interval_s: float = 30.0

    # --- Hạn giờ khi cơ sở dữ liệu chết (sự cố 13/09/2026) ----------------
    # Ngày 13/09/2026 PostgreSQL chết hẳn giữa lúc hệ thống đang chạy. Mỗi lần
    # gọi GET /sessions treo ĐÚNG 30 GIÂY rồi trả "Internal Server Error" trần
    # (30s là ConnectionPool.timeout mặc định của psycopg_pool), còn /health thì
    # vẫn báo xanh vì nó chưa bao giờ hỏi cơ sở dữ liệu lấy một câu. Trang web
    # đặt hạn 2,5 giây cho phép thử nên nó luôn thất bại và báo "Chưa kết nối
    # được máy chủ" NGAY CẢ KHI API còn sống.
    #
    # Bốn hạn giờ dưới đây là bốn pha khác nhau, không thay được cho nhau:
    #   connect   — bắt tay TCP/TLS với máy chủ (libpq mặc định: chờ VÔ HẠN);
    #   pool      — chờ pool cấp một kết nối (mặc định 30,0 = con số đã đếm);
    #   statement — chờ máy chủ chạy xong truy vấn đã cầm được kết nối;
    #   ping      — hạn riêng, ngắn hơn, cho lần hỏi thăm của /health.
    # Hạn pool để 2,0 giây — NGẮN HƠN hạn 2,5 giây trang web đặt cho mỗi lời
    # gọi: máy chủ trả lời sau khi client đã bỏ cuộc thì câu 503 tiếng Việt
    # không đến được mắt ai.
    # libpq làm tròn connect_timeout < 2 lên 2 giây, nên 1 là vô nghĩa.
    store_connect_timeout_s: int = 3
    store_pool_timeout_s: float = 2.0
    store_statement_timeout_s: float = 8.0
    health_ping_timeout_s: float = 1.5
    # Trang web hỏi /health liên tục (nhiều tab, mỗi vài giây). Không đệm thì
    # chính cái đồng hồ đo sức khỏe lại đấm vào cơ sở dữ liệu. 5 giây: người
    # vận hành thấy DB chết gần như tức thì, mà 20 tab không thành 20 lần kết
    # nối mỗi giây. Đặt 0 để tắt đệm (ping thật ở mọi lần gọi).
    health_ping_cache_s: float = 5.0

    # --- Xác thực đường GHI (gói VÁ-XÁC-THỰC, 14/09/2026) ------------------
    # Bí mật dùng chung cho MỌI endpoint ghi, không chỉ comments/ticks: từ
    # 14/09 dependency require_write_auth được gắn ở CẤP ỨNG DỤNG nên nó che
    # cả 15 đường ghi (xem src/livelift/api/auth.py). Để trống (mặc định) =
    # tắt kiểm tra hoàn toàn — chế độ phát triển cục bộ và kiểm thử. Khi đặt,
    # ApiSink tự đính "Authorization: Bearer <token>".
    ingest_token: str = ""

    # Chế độ TRƯNG BÀY công khai. Khi ingest_token đã đặt, cờ này quyết định
    # một khách KHÔNG có token còn làm được gì:
    #   True  — được tạo phiên của riêng mình và thao tác trên phiên DEMO
    #           (wizard, lịch gán, phát, ghim, kết thúc), có giới hạn tần
    #           suất. Phiên do khách tạo được máy chủ ghi is_demo=True nên
    #           không bao giờ lọt vào kết quả khoa học thật.
    #   False — khoá sạch: mọi đường ghi đòi token.
    # Mặc định True là một ĐÁNH ĐỔI CÓ CHỦ Ý cho bản triển khai cho hội đồng
    # chấm: bán kính thiệt hại bị chặn bằng cấu trúc (khách không chạm được
    # vào phiên thật, không chạm được vào đường nạp dữ liệu của bộ thu, không
    # chạm được vào /replays/youtube), còn một bản trưng bày bị khoá sạch thì
    # thành ảnh tĩnh — hỏng đúng thứ nó sinh ra để chứng minh. Máy chủ chạy
    # thí nghiệm THẬT và không cần cho người lạ bấm thử: đặt False.
    public_demo_writes: bool = True
    # Trần tần suất cho đường ghi MỞ (chỉ áp cho yêu cầu KHÔNG có token —
    # bộ thu của đội bắn một bình luận mỗi giây và không bao giờ bị chặn).
    # Đặt 0 để tắt. 30/phút đủ rộng cho một người bấm wizard rất nhanh, đủ
    # hẹp để một vòng lặp curl không làm ngập buổi demo.
    write_rate_limit_per_min: int = 30
    # /demo/seed và /demo/seed-vang sinh hàng nghìn bản ghi mỗi lần gọi nên
    # có trần riêng, tính theo giờ.
    demo_seed_rate_limit_per_hour: int = 6
    # POST /sessions/{id}/orders/import: một lượt ghi tới hàng trăm đơn, nên
    # cũng có trần riêng theo giờ (kiểm toán 17/09/2026). Đặt 0 để tắt.
    order_import_rate_limit_per_hour: int = 12

    # --- Địa chỉ thật của người gọi sau proxy (kiểm toán 17/09/2026) --------
    # Chỉ tin X-Forwarded-For khi kết nối TRỰC TIẾP đến từ một proxy trong danh
    # sách này. Trước ngày 17/09 header được tin vô điều kiện (người gọi tự bịa
    # được địa chỉ, phá trần tần suất khi API lộ cổng trực tiếp), còn shortlink
    # /r/{code} thì bỏ hẳn header và băm địa chỉ của CADDY — mọi người xem sau
    # proxy chung một "vân tay", nên luật refractory/volume-cap gộp họ làm một
    # và đánh dấu click hợp lệ của người thứ hai là vô hiệu.
    # Mặc định: loopback + dải mạng riêng (mạng nội bộ Docker nơi Caddy sống).
    # Đứng sau Cloudflare thì thêm dải IP của Cloudflare vào đây.
    trusted_proxy_cidrs: str = (
        "127.0.0.1/32,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7"
    )

    # PREREGISTRATION.md §7 (no peeking): ISO date (YYYY-MM-DD, UTC). While the
    # current UTC date is BEFORE this date, /experiment/summary withholds every
    # inferential field (estimate, p, CI) and serves operational numbers only.
    # Empty (default) = no freeze (dev/demo). A malformed value fails CLOSED:
    # the lock stays on until the configuration is fixed.
    results_freeze_until: str = ""

    # Bộ thu chạy nền trong API (POST /sessions/{id}/ingest): danh sách bộ thu
    # đang bật được ghi ở đây để API khởi động lại thì TỰ NỐI LẠI cho phiên
    # chưa đóng, thay vì im lặng ngừng thu giữa buổi live.
    ingest_state_path: str = "data/ingest-jobs.json"

    youtube_api_key: str = ""
    # Which YouTube live-ingest path the runner uses:
    #   "api"   — livelift.ingest.youtube, needs YOUTUBE_API_KEY (default: old
    #             behavior is never changed by adding this setting);
    #   "ytdlp" — livelift.ingest.youtube_ytdlp, reads the public live chat via
    #             yt-dlp with NO key and no quota (higher delivery lag, see that
    #             module's docstring). This is the path a team without
    #             credentials can run a live session on today.
    ingest_youtube_backend: str = "api"
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    # Graph API version. v25.0 (released 18/02/2026, sunsets 29/07/2028) is the
    # newest version that has been stable for months; the previous default
    # v23.0 sunsets 08/10/2027 and is four releases behind. Nothing we read
    # (live_videos, comments, live_views) changed in v24–v26 — checked
    # 2026-09-09 against the v25.0/v26.0 changelogs.
    facebook_graph_version: str = "v25.0"
    # Optional, only for scripts/kiem_tra_facebook.py: with the app id+secret
    # the checker can call /debug_token and report the token's real expiry and
    # granted permissions. Never needed by the ingest runner itself — the
    # secret must NOT be deployed to the ingest host.
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    # Opt-in workaround for YouTube's anti-bot check on VOD replay analysis:
    # "chrome" / "edge" / "firefox" — yt-dlp reads the local browser's login
    # cookies (nothing leaves the machine except the normal YouTube request).
    ytdlp_cookies_from_browser: str = ""

    # Shopee Open Platform v2 (OFFICIAL API — hợp ToS). partner_id/partner_key
    # đến từ tài khoản Open Platform của nhóm; user_id/access_token đến từ luồng
    # ủy quyền OAuth của CHÍNH người phát. access_token chỉ sống 4 giờ và phải
    # làm mới bằng refresh_token — xem docs/nen-tang-ho-tro.md §4.
    shopee_partner_id: str = ""
    shopee_partner_key: str = ""
    # Mã tài khoản NGƯỜI PHÁT (sửa 17/09/2026). Mọi API v2.livestream.* là loại
    # "User": tài liệu gốc open.shopee.com ghi tham số chung partner_id,
    # timestamp, access_token, user_id, sign và chữ ký = HMAC-SHA256 của
    # partner_id + đường dẫn API + timestamp + access_token + user_id. Trước
    # 17/09 adapter ký bằng shop_id nên mọi lời gọi thật sẽ bị từ chối. Lấy giá
    # trị từ user_id_list trong phản hồi v2.public.get_access_token khi ủy quyền.
    # BẮT BUỘC cho đọc bình luận / người xem / chỉ số.
    shopee_user_id: str = ""
    # Mã shop: CHỈ cần cho ghim sản phẩm (update_show_item nhận shop_id trong
    # thân yêu cầu). Đọc bình luận và chỉ số KHÔNG cần.
    shopee_shop_id: str = ""
    shopee_access_token: str = ""
    shopee_refresh_token: str = ""
    # Cổng API theo vùng: "global" (gồm Việt Nam), "china", "brazil", "sandbox".
    # Shopee KHÔNG có host riêng cho .vn — VN đi qua partner.shopeemobile.com.
    shopee_region: str = "global"


def _prefer_ipv4_loopback(url: str) -> str:
    """Rewrite a ``localhost`` host to ``127.0.0.1``.

    On Windows ``localhost`` resolves to ``::1`` first, but Docker publishes
    only ``127.0.0.1:5432``; psycopg then waits out the full IPv6 connect
    timeout before falling back — measured 2m10s vs 0.5s (incident 27/08).
    Every CLI looked hung. The two spellings mean the same host here, so we
    normalize rather than let a stale .env cost two minutes per command.
    """
    return url.replace("@localhost:", "@127.0.0.1:").replace("//localhost:", "//127.0.0.1:")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    return s.model_copy(
        update={
            "database_url": _prefer_ipv4_loopback(s.database_url),
            "redis_url": _prefer_ipv4_loopback(s.redis_url),
        }
    )
