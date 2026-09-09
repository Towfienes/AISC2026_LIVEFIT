# TOPIC 4 — Platform APIs & Competitive Landscape (verified Aug 2026)

## (a) YouTube Live Streaming API — live chat ingestion

**Current model (2025–2026).** Two ways to read live chat:

1. **`liveChatMessages.list`** — classic polling. `GET https://www.googleapis.com/youtube/v3/liveChat/messages?liveChatId=...&part=id,snippet,authorDetails`. Response includes `pollingIntervalMillis` — you MUST wait that long before the next call or you get `rateLimitExceeded`. `maxResults` 200–2000 (default 500). ([liveChatMessages.list docs](https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list))
2. **`liveChatMessages.streamList`** — the newer, recommended method: a long-lived server-streaming HTTP connection that **pushes messages as they arrive** ("the most efficient way to consume live chat messages… helps to avoid exceeding your quota"). Resume after disconnect via `pageToken=nextPageToken`. Guidance for it was added to the docs **July 14, 2025** ([revision history](https://developers.google.com/youtube/v3/live/revision_history); [streamList docs](https://developers.google.com/youtube/v3/live/docs/liveChatMessages/streamList)).

**Quota.** Default project quota: **10,000 units/day**, and (per the 2025 quota restructure) separate caps of 100 `search.list` and 100 `videos.insert` calls/day; resets midnight PT ([determine_quota_cost, updated 2026-06-01](https://developers.google.com/youtube/v3/determine_quota_cost)). Gotcha: **Google no longer publishes the per-call cost of `liveChatMessages` in the public table** — community measurements historically put `list` at ~5 units/call. Worst case for LiveLift: 90 min polling at 5 s intervals = 1,080 calls ≈ 5,400 units — **over half your daily quota for one session**. Action: **use `streamList`, not `list`** (one connection per session instead of ~1,000 calls), verify actual consumption in Google Cloud Console quota dashboard during a dry run, and get the broadcast's `activeLiveChatId` via `liveBroadcasts.list` (cheap, own channel). Do **not** use `search.list` to discover your own stream (it burns the 100-call cap).

**What to change in LiveLift:** implement the YouTube adapter on `streamList` with auto-reconnect (`pageToken` resume) and a fallback to `list` honoring `pollingIntervalMillis`. Timestamp every message server-side on arrival so block attribution (5–15 min blocks) doesn't depend on YouTube's delivery latency.

## (b) Facebook Graph API — reading live comments on your own Page

**Endpoints (Graph v25/v26, current):**
- `GET /{page-id}/live_videos?broadcast_status=["LIVE"]` to find the active live video ([Page Live Videos reference](https://developers.facebook.com/docs/graph-api/reference/page/live_videos/)).
- `GET /{live-video-id}/comments?order=reverse_chronological&live_filter=...&since=...` — official best practice is now **"continually poll for comments in reverse_chronological ordering"** ([Live Video Comments reference](https://developers.facebook.com/docs/graph-api/reference/live-video/comments/)). **The old SSE live-comments stream is gone — plan for polling, not push.** Use `since` cursors to de-duplicate; note `live_filter` drops "low quality" comments **by default** — for PhoBERT intent mining you likely want it off so you see everything.

> **Đính chính 09/09/2026 (đối chiếu lại tài liệu):** câu "SSE đã chết" là **nói quá**.
> Meta vẫn tài liệu hóa `GET /{live-video-id}/live_comments` trên
> `streaming-graph.facebook.com` ở guide
> [Interacting with Viewers](https://developers.facebook.com/documentation/live-video-api/interact-with-viewers),
> nhưng giới thiệu nó cho **client trình duyệt**; polling vẫn là đường phía máy chủ và
> là lựa chọn của LiveLift (chịu được mất kết nối, không cần giữ kết nối dài).
> Ba điểm khác cần sửa so với bản ghi 24/08: (1) `filter` mặc định là `toplevel` nên
> **mất hết bình luận trả lời** — phải đặt `filter=stream`; (2) `order` chỉ là *gợi ý*
> ("if the comments can be ranked, the order will always be ranked regardless of this
> modifier") nên không được giả định thứ tự; (3) phải đi theo `paging.next`, vì một
> trang chỉ chứa `limit` bình luận và con trỏ `since` sẽ nhảy qua phần dư.
> Chi tiết + cách vận hành: [docs/huong-dan-facebook-token.md](../huong-dan-facebook-token.md).

**Permissions.** With a **Page access token** for your own Page: `pages_show_list`, `pages_read_engagement` (Page's own content/metadata), and — the classic gotcha — **`pages_read_user_content`** for content *other users* post on your Page, which is exactly what viewer comments are. The Live Video API *feature* review (`publish_video`, `pages_manage_posts`, `pages_read_engagement`) is only needed if you **publish/control broadcasts via API** ([Live Video API docs](https://developers.facebook.com/docs/live-video-api/)) — LiveLift only needs to *read*, so skip it.

**The decisive practical point for a student team:** an app in **Development Mode** can use all permissions **without App Review** for users who hold a role on the app. Make every team member an app admin/developer/tester and admin of the Live Lab Page → you can read your own live comments **today, zero review**. App Review (Advanced Access) is only needed when serving Pages you don't own.

**Meta App Review checklist (if/when you go beyond your own Page):**
1. **Business Verification first** — prerequisite for Advanced Access; forum reports show it alone can sit "in review" 10+ days ([Meta Community Forums, 2026](https://communityforums.atmeta.com/discussions/Questions_Discussions/business-verification-in-review-10-days-%E2%80%94-blocking-app-review-submission/1372323)).
2. One screencast per permission showing the real flow; privacy policy naming each data type + deletion; live API calls within the last 30 days; request only minimum permissions ([Meta App Approval Guide, 2025](https://www.saurabhdhar.com/blog/meta-app-approval-guide)).
3. Timeline: officially "up to a few days"; practitioner reports in 2026 say **2–7 business days for clean submissions, up to ~20 days** and each rejection restarts the clock ([bundle.social, 2026](https://bundle.social/blog/meta-app-review-20-days); [singhamandeep.com, 2026](https://singhamandeep.com/meta-app-review-how-long-does-it-take/)). **Budget 4–6 weeks with one rejection cycle** — if you want reviewed access for the Nov 2026 final, submit by September.

## (c) TikTok — TikTokLive library status & risk

**Status: alive and actively maintained as of mid-2026** (releases through July 2026; v6.x on PyPI). Connects anonymously to any public LIVE by `@unique_id` — no login, no credentials ([GitHub — isaackogan/TikTokLive](https://github.com/isaackogan/TikTokLive); [PyPI 6.0.3](https://pypi.org/project/TikTokLive/6.0.3)). Websocket signing is outsourced to a third-party sign server (**Euler Stream**) with free community rate limits; a paid API key raises them.

**Risk assessment (honest):**
- **ToS/legal:** it's explicitly "not a production-ready API… a reverse engineering project" — unofficial Webcast protocol access; TikTok can break it without notice. Account-ban risk to the *viewer* side is low (read-only, anonymous), but the **shop/creator account is your asset — don't attach automation to it**.
- **Operational:** dependency on Euler Stream's uptime + TikTok protocol changes = **real risk of a dead adapter on demo day**. TikTok Shop's official Partner Center APIs (orders/products) exist, but there is **no official third-party API for reading live comments** ([TikTok Shop developer docs](https://partner.tiktokshop.com/docv2/page/developer)).

**What to do:** run the Live Lab's *instrumented* experiments on **YouTube + Facebook** (stable, official APIs); ship the TikTok adapter as "best-effort" behind the same internal event interface, with a manual-logging fallback (operator tablet) so a mid-competition break doesn't kill the switchback (blocks and pin decisions are yours; only comment intent degrades). State this platform-risk tiering explicitly in your write-up — judges reward realism.

## (d) Competitive landscape — is anyone doing causal measurement?

**China ecosystem — descriptive, not causal.** Chanmama (蝉妈妈) and Feigua (飞瓜) are the deepest live-commerce analytics for Douyin: real-time stream monitoring, GMV estimation, KOL/product rankings, ROI dashboards ([Enlybee tools overview](https://www.enlybee.com/top-useful-china-tiktokdouyin-data-analysis-tools/); [Feigua profile](https://coinstori.com/feigua-data-chinas-leading-short-video-live-commerce-analytics/)). All **observational**: they tell you *what happened*, correlating spikes with events.

**TikTok Shop ecosystem (Kalodata, FastMoss, EchoTik) — same story.** 2026 comparisons position Kalodata on product/trend discovery, FastMoss on competitive monitoring + LIVE performance history, EchoTik on live-session monitoring and "tying revenue spikes back to creator or product activity" ([Dashboardly FastMoss vs Kalodata, 2026](https://www.dashboardly.io/compare/fastmoss-vs-kalodata); [EchoTik comparison, 2026](https://echotik.live/guides/echotik-vs-kalodata-vs-fastmoss)). Attribution is retrospective and correlational; **no randomization, no propensity logging, nothing new in 2025–2026 on experimentation**.

**Western tools.** Bambuser (enterprise live shopping events), Firework (shoppable video + AI assistant claiming 13–17% conversion — a *claim*, not a controlled estimate), CommentSold (comment-to-checkout automation) are **commerce infrastructure**, with at most marketing-style A/B of layouts/replay funnels — not in-session randomized decisions ([Immerss comparison, 2026](https://www.immerss.live/content/firework-alternative-video-commerce-live-selling/); [ecommerceguide Bambuser review](https://ecommerceguide.com/apps/bambuser/)). StreamYard is production tooling only. A 2026 survey of live-shopping A/B practice confirms testing happens **across streams** (formats, hosts), never within-session ([Shopify A/B testing guide](https://www.shopify.com/blog/ab-testing-how-retailers-can-optimize-their-sales-with-experimentation)).

**The one adjacent precedent is academic:** *"AI Assistant in Online Shopping: A Randomized Field Experiment on a Livestream Selling Platform,"* Information Systems Research, 2025 ([INFORMS](https://pubsonline.informs.org/doi/10.1287/isre.2023.0103)) — proof that randomized field experiments on livestream platforms are feasible and publishable, but it's a one-off platform study, not a product.

**Updated positioning statement (use this):**
> Every live-commerce analytics tool on the market — Chanmama, Feigua, Kalodata, FastMoss, EchoTik in Asia; Bambuser, Firework, CommentSold in the West — answers *"what happened during my stream?"* by observation. None answers *"what would have happened had I pinned differently?"* As of 2026, no commercial tool runs randomized in-session experiments or logs propensities for causal effect estimation; the only randomized livestream-selling experiment we found is a 2025 academic study (ISR). LiveLift's two-tier switchback is, to our knowledge, the first control-desk that turns each livestream into its own experiment — a methodological moat, not a feature gap competitors can close with another dashboard.

**Cite the ISR paper in your related-work section** — it legitimizes the approach and sharpens the "research-grade rigor, operator-grade tooling" story.