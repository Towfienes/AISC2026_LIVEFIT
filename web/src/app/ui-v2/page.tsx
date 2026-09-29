import styles from "./page.module.css";

type IconName =
  | "grid"
  | "video"
  | "chart"
  | "bag"
  | "users"
  | "settings"
  | "home"
  | "support"
  | "search"
  | "bell"
  | "calendar"
  | "eye"
  | "cube"
  | "revenue"
  | "chevron";

function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "grid":
      return (
        <svg {...common}>
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      );
    case "video":
      return (
        <svg {...common}>
          <rect x="3" y="6" width="13" height="12" rx="2" />
          <path d="m16 10 5-3v10l-5-3z" />
        </svg>
      );
    case "chart":
      return (
        <svg {...common}>
          <path d="M5 20V10M12 20V4M19 20v-7" />
        </svg>
      );
    case "bag":
      return (
        <svg {...common}>
          <path d="M6 8h12l1 12H5L6 8Z" />
          <path d="M9 8a3 3 0 0 1 6 0" />
        </svg>
      );
    case "users":
      return (
        <svg {...common}>
          <circle cx="9" cy="8" r="3" />
          <path d="M3.5 20a5.5 5.5 0 0 1 11 0M16 5.5a3 3 0 0 1 0 5.5M17.5 13.5a5 5 0 0 1 3 4.5" />
        </svg>
      );
    case "settings":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21H9.6v-.1A1.7 1.7 0 0 0 8.4 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H2.2V9.6h.1A1.7 1.7 0 0 0 4 8.4a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 8.4 4a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V2.2h4v.1A1.7 1.7 0 0 0 15 4a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 8.4a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1.1.4h.1v4h-.1A1.7 1.7 0 0 0 19.4 15Z" />
        </svg>
      );
    case "home":
      return (
        <svg {...common}>
          <path d="m3 11 9-8 9 8" />
          <path d="M5 10v10h14V10M9 20v-6h6v6" />
        </svg>
      );
    case "support":
      return (
        <svg {...common}>
          <rect x="3" y="4" width="18" height="14" rx="3" />
          <path d="M7 8h10M7 12h7M8 18l-2 3" />
        </svg>
      );
    case "search":
      return (
        <svg {...common}>
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-4-4" />
        </svg>
      );
    case "bell":
      return (
        <svg {...common}>
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
          <path d="M10 21h4" />
        </svg>
      );
    case "calendar":
      return (
        <svg {...common}>
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M16 3v4M8 3v4M3 10h18" />
        </svg>
      );
    case "eye":
      return (
        <svg {...common}>
          <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
          <circle cx="12" cy="12" r="2.5" />
        </svg>
      );
    case "cube":
      return (
        <svg {...common}>
          <path d="m12 2 8 4.5v11L12 22l-8-4.5v-11L12 2Z" />
          <path d="m4.5 7 7.5 4 7.5-4M12 11v11" />
        </svg>
      );
    case "revenue":
      return (
        <svg {...common}>
          <path d="M5 20V12M12 20V7M19 20V4" />
        </svg>
      );
    case "chevron":
      return (
        <svg {...common}>
          <path d="m9 6 6 6-6 6" />
        </svg>
      );
  }
}

const streams = [
  {
    title: "Chăm da cùng chuyên gia",
    date: "24.09.2026 · 20:00",
    views: "52,3K",
    orders: "3,1K",
    revenue: "128,4 triệu",
    status: "Đã kết thúc",
    statusTone: "done",
    image:
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=180&q=80",
  },
  {
    title: "Deal hot cuối tháng",
    date: "23.09.2026 · 19:30",
    views: "38,1K",
    orders: "1,9K",
    revenue: "76,2 triệu",
    status: "Đang live",
    statusTone: "live",
    image:
      "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=180&q=80",
  },
  {
    title: "Phụ kiện công nghệ",
    date: "22.09.2026 · 20:00",
    views: "24,6K",
    orders: "892",
    revenue: "42,1 triệu",
    status: "Đã kết thúc",
    statusTone: "done",
    image:
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=180&q=80",
  },
  {
    title: "Skincare mùa thu",
    date: "21.09.2026 · 19:30",
    views: "18,4K",
    orders: "621",
    revenue: "28,5 triệu",
    status: "Đã kết thúc",
    statusTone: "done",
    image:
      "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=180&q=80",
  },
];

function Brand() {
  return (
    <div className={styles.brand}>
      <span className={styles.brandMark} aria-hidden>
        <i />
        <i />
        <i />
      </span>
      <span>LiveLift</span>
    </div>
  );
}

function Sparkline({ tone = "lime" }: { tone?: "lime" | "violet" }) {
  return (
    <svg
      className={styles.sparkline}
      viewBox="0 0 320 70"
      preserveAspectRatio="none"
      aria-hidden
    >
      <path
        className={tone === "lime" ? styles.sparkLime : styles.sparkViolet}
        d="M0 50 C28 26 52 53 80 38 S126 14 157 34 204 18 230 32 271 15 320 26"
      />
    </svg>
  );
}

function PerformanceChart() {
  return (
    <svg
      className={styles.chart}
      viewBox="0 0 760 330"
      preserveAspectRatio="none"
      role="img"
      aria-label="Biểu đồ hiệu suất livestream trong bảy ngày"
    >
      <defs>
        <linearGradient id="limeFillV2" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#b8ff65" stopOpacity=".18" />
          <stop offset="100%" stopColor="#b8ff65" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="violetFillV2" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#a56cff" stopOpacity=".15" />
          <stop offset="100%" stopColor="#a56cff" stopOpacity="0" />
        </linearGradient>
      </defs>

      {[48, 110, 172, 234, 296].map((y) => (
        <line key={"h" + y} x1="54" y1={y} x2="744" y2={y} className={styles.gridLine} />
      ))}
      {[54, 169, 284, 399, 514, 629, 744].map((x) => (
        <line key={"v" + x} x1={x} y1="32" x2={x} y2="296" className={styles.gridLine} />
      ))}

      <path
        d="M54 245 C95 220 130 230 169 204 S244 164 284 181 360 143 399 116 470 83 514 105 584 131 629 97 704 99 744 118 L744 296 L54 296 Z"
        fill="url(#limeFillV2)"
      />
      <path
        d="M54 272 C101 247 127 257 169 239 S242 221 284 234 357 212 399 181 468 145 514 163 584 206 629 171 705 178 744 188 L744 296 L54 296 Z"
        fill="url(#violetFillV2)"
      />
      <path
        d="M54 245 C95 220 130 230 169 204 S244 164 284 181 360 143 399 116 470 83 514 105 584 131 629 97 704 99 744 118"
        className={styles.lineLime}
      />
      <path
        d="M54 272 C101 247 127 257 169 239 S242 221 284 234 357 212 399 181 468 145 514 163 584 206 629 171 705 178 744 188"
        className={styles.lineViolet}
      />

      <line x1="514" y1="54" x2="514" y2="296" className={styles.focusLine} />
      <circle cx="514" cy="105" r="7" className={styles.pointLime} />
      <circle cx="514" cy="163" r="7" className={styles.pointViolet} />

      <g className={styles.axisLabels}>
        <text x="13" y="302">0</text>
        <text x="4" y="240">10M</text>
        <text x="4" y="178">20M</text>
        <text x="4" y="116">30M</text>
        <text x="4" y="54">40M</text>
        <text x="46" y="324">18.09</text>
        <text x="160" y="324">19.09</text>
        <text x="275" y="324">20.09</text>
        <text x="390" y="324">21.09</text>
        <text x="505" y="324">22.09</text>
        <text x="620" y="324">23.09</text>
        <text x="722" y="324">24.09</text>
      </g>
    </svg>
  );
}

export default function UiV2PreviewPage() {
  return (
    <main className={styles.canvas}>
      <section className={styles.appShell}>
        <header className={styles.topbar}>
          <Brand />

          <nav className={styles.topNav} aria-label="Điều hướng chính">
            <a className={styles.navPillActive} href="/ui-v2">
              <Icon name="home" size={18} />
              Tổng quan
            </a>
            <a className={styles.navPill} href="/desk">
              <Icon name="video" size={18} />
              Livestream
            </a>
            <a className={styles.navPill} href="/ket-qua">
              <Icon name="chart" size={18} />
              Phân tích
            </a>
            <a className={styles.navPill} href="/bao-cao">
              <Icon name="support" size={18} />
              Hỗ trợ
            </a>
          </nav>

          <div className={styles.topActions}>
            <div className={styles.searchBox}>
              <Icon name="search" size={19} />
              <span>Tìm kiếm nội dung...</span>
            </div>
            <button className={styles.iconButton} aria-label="Thông báo">
              <Icon name="bell" size={19} />
              <span className={styles.notificationDot} />
            </button>
            <div className={styles.profile}>
              <img
                src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=96&q=80"
                alt=""
              />
              <div>
                <strong>Nguyễn Linh</strong>
                <span>Team LiveLift</span>
              </div>
              <span className={styles.profileChevron}>⌄</span>
            </div>
          </div>
        </header>

        <div className={styles.workspace}>
          <aside className={styles.iconRail} aria-label="Điều hướng nhanh">
            <a className={styles.railActive} href="/ui-v2" aria-label="Tổng quan">
              <Icon name="grid" />
            </a>
            <a className={styles.railButton} href="/desk" aria-label="Livestream">
              <Icon name="video" />
            </a>
            <a className={styles.railButton} href="/ket-qua" aria-label="Phân tích">
              <Icon name="chart" />
            </a>
            <a className={styles.railButton} href="/chay-phien" aria-label="Phiên live">
              <Icon name="calendar" />
            </a>
            <a className={styles.railButton} href="/bao-cao" aria-label="Khách hàng">
              <Icon name="users" />
            </a>
            <a className={styles.railButton} href="/" aria-label="Cài đặt">
              <Icon name="settings" />
            </a>
          </aside>

          <section className={styles.content}>
            <div className={styles.pageHeading}>
              <div>
                <h1>TỔNG QUAN LIVELIFT</h1>
                <p>Theo dõi hiệu suất livestream · Tối ưu doanh thu · Phát triển bền vững</p>
              </div>
              <button className={styles.datePill}>
                <Icon name="calendar" size={18} />
                7 ngày qua
                <span>⌄</span>
              </button>
            </div>

            <section className={styles.summaryGrid}>
              <article className={styles.summaryCard}>
                <div className={styles.cardTop}>
                  <div className={styles.metricLabel}>
                    <span className={styles.metricIconLime}>
                      <Icon name="revenue" size={18} />
                    </span>
                    Doanh số
                  </div>
                  <button className={styles.moreButton} aria-label="Thêm tùy chọn">•••</button>
                </div>
                <div className={styles.metricValueRow}>
                  <strong>128,6 triệu</strong>
                  <span className={styles.trend}>▲ 12%</span>
                </div>
                <p>So với 7 ngày trước</p>
                <Sparkline tone="lime" />
              </article>

              <article className={styles.summaryCard}>
                <div className={styles.cardTop}>
                  <div className={styles.metricLabel}>
                    <span className={styles.metricIconNeutral}>
                      <Icon name="eye" size={18} />
                    </span>
                    Lượt xem
                  </div>
                  <button className={styles.moreButton} aria-label="Thêm tùy chọn">•••</button>
                </div>
                <div className={styles.metricValueRow}>
                  <strong>256,4K</strong>
                  <span className={styles.trend}>▲ 18%</span>
                </div>
                <p>Tổng lượt xem livestream</p>
                <Sparkline tone="violet" />
              </article>

              <article className={styles.productCard}>
                <div className={styles.cardTop}>
                  <div className={styles.metricLabel}>
                    <span className={styles.metricIconNeutral}>
                      <Icon name="cube" size={18} />
                    </span>
                    Sản phẩm nổi bật
                  </div>
                  <button className={styles.moreButton} aria-label="Thêm tùy chọn">•••</button>
                </div>
                <div className={styles.productBody}>
                  <img
                    src="https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=280&q=80"
                    alt="Sản phẩm serum phục hồi da"
                  />
                  <div className={styles.productCopy}>
                    <strong>Serum phục hồi da</strong>
                    <span>Đang bán chạy</span>
                    <div className={styles.productMetric}>
                      <b>4.2K</b>
                      <span>đơn</span>
                      <em>▲ 25%</em>
                    </div>
                    <div className={styles.progressTrack}>
                      <span />
                    </div>
                  </div>
                </div>
              </article>
            </section>

            <section className={styles.mainGrid}>
              <article className={styles.chartCard}>
                <div className={styles.chartHeader}>
                  <div>
                    <div className={styles.sectionTitle}>
                      <span className={styles.sectionIcon}>
                        <Icon name="chart" size={18} />
                      </span>
                      <div>
                        <h2>Hiệu suất livestream</h2>
                        <p>Biểu đồ thể hiện doanh số và lượt xem theo thời gian</p>
                      </div>
                    </div>
                  </div>
                  <button className={styles.compactSelect}>
                    Theo ngày
                    <span>⌄</span>
                  </button>
                </div>

                <div className={styles.chartWrap}>
                  <PerformanceChart />
                  <div className={styles.tooltip}>
                    <span>22.09.2026</span>
                    <div><i className={styles.limeDot} />Doanh số <b>28,4M</b></div>
                    <div><i className={styles.violetDot} />Lượt xem <b>36,2K</b></div>
                  </div>
                </div>

                <div className={styles.legend}>
                  <span><i className={styles.limeDot} />Doanh số (VND)</span>
                  <span><i className={styles.violetDot} />Lượt xem</span>
                </div>
              </article>

              <article className={styles.recentCard}>
                <div className={styles.recentHeader}>
                  <div className={styles.sectionTitle}>
                    <span className={styles.sectionIcon}>
                      <Icon name="video" size={18} />
                    </span>
                    <h2>Livestream gần đây</h2>
                  </div>
                  <a href="/replay">Xem tất cả <Icon name="chevron" size={14} /></a>
                </div>

                <div className={styles.streamList}>
                  {streams.map((stream) => (
                    <a className={styles.streamRow} href="/replay" key={stream.title}>
                      <img src={stream.image} alt="" />
                      <div className={styles.streamMain}>
                        <strong>{stream.title}</strong>
                        <span>{stream.date}</span>
                        <div className={styles.streamStats}>
                          <span><Icon name="eye" size={14} />{stream.views}</span>
                          <span><Icon name="bag" size={14} />{stream.orders}</span>
                          <span><Icon name="cube" size={14} />{stream.revenue}</span>
                        </div>
                      </div>
                      <span
                        className={
                          stream.statusTone === "live"
                            ? styles.statusLive
                            : styles.statusDone
                        }
                      >
                        {stream.status}
                      </span>
                    </a>
                  ))}
                </div>
              </article>
            </section>
          </section>
        </div>
      </section>
    </main>
  );
}
