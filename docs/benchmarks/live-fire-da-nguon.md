# Live-fire đa nguồn: 16 buổi live THẬT qua chính API của hệ thống

*Đo ngày 10/09/2026 · 16 phiên `platform=replay` · **19.126 bình luận thật** ·
tất cả đi qua `POST /replays/youtube`, không có đường tắt nào*

> **Kết luận một dòng:** hệ thống **chạy đúng và chạy chắc** trên dữ liệu thật
> (16/17 video vào được, cô lập phiên hoàn hảo kể cả khi chạy song song, tái lập
> từng bit sau 2 ngày và 3 tiến trình khác nhau), nhưng **radar ý định KHÔNG có
> một mức chính xác duy nhất**: precision của các nhãn hành động dao động
> **1,3% → 67,9%** giữa các buổi. Nó không phụ thuộc vào model — nó phụ thuộc
> vào **tỷ lệ nền của ý định mua thật trong buổi đó**, và tệ nhất đúng ở những
> buổi mà chat chủ yếu là xã giao. Hai lỗi trung thực đã bị phát hiện và sửa
> tận gốc trong lần chạy này.

## Lệnh tái lập

```bash
cd d:/AISC2026/livelift

# 0. API sạch (in-memory store). Cổng 8010 vì cổng 8000 đang có một tiến trình
#    uvicorn cũ (khởi động 07/09) — trộn số của hai phiên bản mã là bẩn dữ liệu.
.venv/Scripts/python -m uvicorn livelift.api.main:app --host 127.0.0.1 --port 8010

# 1. Nạp một buổi live (ví dụ buổi khai trương Tuyên Quang)
curl -X POST http://127.0.0.1:8010/replays/youtube \
     -H "Content-Type: application/json" \
     -d '{"url":"https://www.youtube.com/watch?v=gT0LDiBta2k"}'
curl http://127.0.0.1:8010/replays/jobs/<job_id>          # queued→downloading→ingesting→done

# 2. Đọc lại đúng bằng API công khai
curl http://127.0.0.1:8010/sessions/<session_id>/comments  # chỉ text ĐÃ lọc PII
curl http://127.0.0.1:8010/sessions/<session_id>/signals   # ma trận tín hiệu
curl http://127.0.0.1:8010/sessions/<session_id>/ticks

# 3. Toàn bộ lô đo, bằng một script duy nhất trong repo
S=scripts/live_fire_da_nguon.py
.venv/Scripts/python $S nap  ZU_0QJzsR6w gT0LDiBta2k 1NMt8BChQrI 47oGShxf80A \
                            fhv_rKUeEIc d0x0Y-aBe0g MPJktS2rkzk XcMgd74q_LI \
                            z1gfKtekVwk 3eWncr8DSgk FWILs_jLe6I HK-s6Y0MgiQ \
                            qXdtBPs29xA jUMO3oUfVnE N_53eS6mKWc TdLWyV3hNao
.venv/Scripts/python $S bang                              # bảng mục 2
.venv/Scripts/python $S colap     ZU_0QJzsR6w gT0LDiBta2k # mục 3.2
.venv/Scripts/python $S song-song 1NMt8BChQrI fhv_rKUeEIc # mục 3.3

# 4. Số của mục 4 (gán nhãn tay MÙ) — lô nằm ngoài git theo chính sách PII
.venv/Scripts/python data/labeling/lot2-da-nguon-10-09/sample_gold.py   # rút lại mẫu
.venv/Scripts/python data/labeling/lot2-da-nguon-10-09/score_gold.py    # chấm

# 5. Cổng chất lượng
.venv/Scripts/python -m pytest -m "not slow" -q      # 598 passed
.venv/Scripts/python -m ruff check src tests scripts
```

Bảng gán nhãn mù, nhãn tay, khoá ghép và kết quả chấm nằm trong
`data/labeling/lot2-da-nguon-10-09/` (`to_label.txt` · `gold.txt` · `key.json` ·
`scored.json`) — **không vào git**, đúng chính sách "bình luận thật không nằm
trong repo". Seed rút mẫu: `SEED_A=20260910`, `SEED_B=4242`, xáo trộn `777`.

---

## 1. Chọn buổi live thế nào, và bao nhiêu buổi thật sự dùng được

Không chọn theo cảm tính. Hai nguồn:

1. **11 buổi đã tải sẵn** từ đợt 08/09 — chọn **6 buổi** có chat đáng kể để nạp.
2. **Tìm thêm bằng chính yt-dlp** để có ngành hàng khác: tìm kiếm YouTube sắp
   xếp theo ngày (`sp=CAI%3D`) với 4 truy vấn tiếng Việt về quần áo / mỹ phẩm /
   gia dụng, rồi lọc từng ứng viên xem còn track `live_chat` không → **77 video
   có track chat**, thử **11 video** qua API.

Tổng cộng **17 video** đi qua `POST /replays/youtube`.

**Con số cần nói thẳng: có track `live_chat` KHÔNG có nghĩa là có chat.**

| Kết cục khi nạp qua API | Số video | Ghi chú |
|---|---:|---|
| Vào được, có bình luận | 16 | 19.126 bình luận |
| Vào được nhưng chat **rỗng hoàn toàn** | 1 (`TdLWyV3hNao`) | 715 phút, 0 bình luận |
| Metadata báo có `live_chat` nhưng tải về không có | 1 (`tvagwnTvmA4`) | job → `error`, thông báo đúng |
| Có chat nhưng < 30 bình luận | 7 / 16 | không đủ để nói bất cứ điều gì |

Nói cách khác: **tìm được một buổi live bán hàng tiếng Việt có chat đủ dày là
việc khó**, và đó là ràng buộc thật của đề tài chứ không phải chi tiết kỹ thuật.
Trong 16 buổi vào được, chỉ **7 buổi** đạt ≥ 100 bình luận.

---

## 2. Bảng so sánh 16 buổi

Thời lượng = `end_ts − start_ts` do chính hệ thống dựng lại từ metadata video.
"Mật độ" = bình luận / phút. "Đỉnh" = `comment_rate` cao nhất trong các ô 30 s.
"Nạp" = thời gian lọc PII + phân loại ý định + ghi store, tách khỏi thời gian
tải. Với các buổi nhỏ, hai pha trôi qua nhanh hơn chu kỳ poll 0,4 s nên chỉ đo
được tổng — những ô đó ghi rõ "(tổng)".

| # | Video | Buổi live | Ngành hàng | Phút | Bình luận | Mật độ | Đỉnh /phút | Tải (s) | Nạp (s) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | `ZU_0QJzsR6w` | Mega Live: Achan Shop Hải Phòng | tạp hoá / thực phẩm | 117,0 | **6.586** | 56,3 | 144 | 68,8 | 7,89 |
| 2 | `gT0LDiBta2k` | MEGA LIVE: Khai trương Achan Shop Tuyên Quang | tạp hoá / khai trương | 119,1 | **5.492** | 46,1 | 126 | 55,8 | 5,95 |
| 3 | `1NMt8BChQrI` | Vừa trả đơn vừa tâm sự | tạp hoá / trả đơn | 106,4 | **4.079** | 38,3 | 118 | 42,6 | 4,52 |
| 4 | `47oGShxf80A` | Live Sale Tặng Hàng Giá Siêu Rẻ | quần áo / đồ rẻ | 348,6 | **1.567** | 4,5 | 30 | — | 20,6 (tổng) |
| 5 | `fhv_rKUeEIc` | Sâm Ngọc Linh 10g | dược liệu | 125,5 | 779 | 6,2 | **98** | 10,5 | 0,91 |
| 6 | `d0x0Y-aBe0g` | Nova_ đồ mới về mấy chị | quần áo nữ | 168,7 | 322 | 1,9 | 14 | — | 7,5 (tổng) |
| 7 | `MPJktS2rkzk` | Đấu giá đá quý | đá quý / đấu giá | 53,7 | 136 | 2,5 | 12 | — | 5,8 (tổng) |
| 8 | `XcMgd74q_LI` | Chốt đơn siêu nhanh | quần áo | 244,1 | 69 | 0,3 | — | — | 4,7 (tổng) |
| 9 | `z1gfKtekVwk` | Live đồng giá đồ đẹp | quần áo | 262,2 | 29 | 0,1 | — | — | 4,1 (tổng) |
| 10 | `3eWncr8DSgk` | Xả Mộc Hương, Nguyệt Quế | **cây cảnh / bonsai** | 70,4 | 23 | 0,3 | 4 | — | 4,1 (tổng) |
| 11 | `FWILs_jLe6I` | Cùng U90 bán chà bông cá | thực phẩm | 38,1 | 16 | 0,4 | — | — | 4,7 (tổng) |
| 12 | `HK-s6Y0MgiQ` | Đồ đẹp giá hạt dẻ | quần áo | 202,9 | 12 | 0,06 | — | — | 4,7 (tổng) |
| 13 | `qXdtBPs29xA` | Sắm gia dụng thông minh | gia dụng | 122,0 | 8 | 0,07 | — | — | 3,7 (tổng) |
| 14 | `jUMO3oUfVnE` | [LAZLIVE] Đại chiến thánh chốt đơn | sàn TMĐT | 136,1 | 5 | 0,04 | — | — | 4,5 (tổng) |
| 15 | `N_53eS6mKWc` | Lọc khí, bếp gas | gia dụng | 69,0 | 3 | 0,04 | — | — | 4,6 (tổng) |
| 16 | `TdLWyV3hNao` | Deal chạm đáy cùng KOSMEN | gia dụng / thương hiệu | 715,0 | **0** | 0 | 0 | — | 4,2 (tổng) |

### 2.1 Phân bố ý định (7 buổi ≥ 100 bình luận)

| Video | `khac` | `chot_don` | `hoi_gia` | `che_dat` | `van_chuyen` | `hoi_size` | Tỷ lệ nhãn hành động |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ZU_0QJzsR6w` | 5.654 | 608 | 108 | 102 | 98 | 16 | 14,2% |
| `gT0LDiBta2k` | 4.585 | 646 | 86 | 98 | 72 | 5 | 16,5% |
| `1NMt8BChQrI` | 3.473 | 440 | 75 | 40 | 29 | 22 | 14,9% |
| `47oGShxf80A` | 1.237 | 268 | 13 | 7 | 39 | 3 | **21,1%** |
| `fhv_rKUeEIc` | 646 | 122 | 1 | 4 | 5 | 1 | 17,1% |
| `d0x0Y-aBe0g` | 257 | 34 | 14 | 2 | 6 | 9 | 20,2% |
| `MPJktS2rkzk` | 119 | 15 | 0 | 1 | 0 | 1 | 12,5% |

Tỷ lệ nhãn hành động **rất ổn định** (12,5% – 21,1%) giữa mọi buổi, mọi ngành.
Mục 4 cho thấy sự ổn định đó là **ổn định của một thói quen, không phải của một
phép đo**: model gắn nhãn hành động cho khoảng 1/6 số dòng bất kể buổi đó thật
sự có bao nhiêu ý định mua.

### 2.2 Độ tự tin

| Video | trung vị | p10 | p90 | min | max | < 0,45 (ngưỡng abstain) |
|---|---:|---:|---:|---:|---:|---:|
| `ZU_0QJzsR6w` | 0,443 | 0,328 | 0,719 | 0,208 | 0,974 | 51,6% |
| `gT0LDiBta2k` | 0,443 | 0,329 | 0,723 | 0,214 | 0,985 | 51,7% |
| `1NMt8BChQrI` | 0,422 | 0,331 | 0,692 | 0,206 | 0,973 | 56,7% |
| `47oGShxf80A` | **0,387** | 0,297 | 0,653 | 0,214 | 0,982 | **71,0%** |
| `fhv_rKUeEIc` | 0,431 | 0,332 | 0,740 | 0,207 | 0,972 | 54,3% |
| `d0x0Y-aBe0g` | 0,417 | 0,293 | 0,747 | 0,224 | 0,982 | 61,5% |
| `MPJktS2rkzk` | 0,404 | 0,319 | 0,696 | 0,242 | 0,951 | 71,3% |
| `3eWncr8DSgk` | 0,400 | 0,321 | 0,706 | 0,298 | 0,794 | 65,2% |

Trung vị nằm **dưới ngưỡng abstain 0,45 ở cả 8 buổi**. Trên toàn bộ dữ liệu
này, **quá nửa đến gần ba phần tư** đầu ra của model là một lần **từ chối phán
đoán**, không phải một phán đoán. Đây là tính chất của model trên chat thật, lặp
lại nhất quán ở mọi nguồn — không phải đặc thù của buổi Achan.

### 2.3 PII bị che

| Video | Bình luận bị che | Tỷ lệ | `name` | `address` | `social` | `phone` | `order` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ZU_0QJzsR6w` | 588 | 8,9% | 270 | 209 | 123 | 1 | 6 |
| `gT0LDiBta2k` | 618 | 11,3% | 296 | 206 | 108 | 2 | 15 |
| `1NMt8BChQrI` | 647 | **15,9%** | 228 | 53 | 108 | **271** | 1 |
| `47oGShxf80A` | 60 | 3,8% | 10 | 55 | 0 | 0 | 0 |
| `fhv_rKUeEIc` | 173 | **22,2%** | 78 | 4 | 18 | **73** | 1 |
| `d0x0Y-aBe0g` | 5 | 1,6% | 1 | 3 | 1 | 0 | 0 |
| `MPJktS2rkzk` | 6 | 4,4% | 5 | 0 | 0 | 1 | 0 |
| `3eWncr8DSgk` | 1 | 4,3% | 0 | 0 | 0 | 1 | 0 |

Cột "bình luận bị che" đếm **bình luận có ít nhất một loại**; các cột loại đếm
**cặp (bình luận, loại)**. Số placeholder trong text còn cao hơn nữa vì một bình
luận có thể chứa hai tên. Ví dụ `gT0LDiBta2k`: 618 bình luận · 627 cặp · **635
placeholder**.

> **Đính chính tài liệu cũ.** `live-fire-achan.md` §3.3 viết "đếm placeholder
> trong text khớp chính xác: `[TÊN]` 270 · `[ĐỊA CHỈ]` 209". Chạy lại đúng phiên
> đó hôm nay: số **cặp** là 270/209 nhưng số **placeholder** là **278/216**.
> Câu "khớp chính xác" là sai; ba con số 270/209/588 thì đúng.

---

## 3. Tái lập và cô lập — phần hệ thống làm ĐÚNG

### 3.1 Tái lập từng bit

Buổi Achan Hải Phòng được **chạy lại từ đầu** (tải mới từ YouTube) trên tiến
trình sạch, 2 ngày sau lần đo gốc:

| Chỉ số | 08/09 (tài liệu cũ) | 10/09 (chạy lại) |
|---|---:|---:|
| Bình luận | 6.586 | **6.586** |
| `khac` / `chot_don` / `hoi_gia` / `che_dat` / `van_chuyen` / `hoi_size` | 5654/608/108/102/98/16 | **giống hệt** |
| Độ tự tin trung vị · p10 · p90 | 0,443 · 0,328 · 0,719 | **0,4434 · 0,3284 · 0,7192** |
| Số dự đoán dưới ngưỡng 0,45 | 3.397 | **3.397** |
| Bình luận có PII | 588 | **588** |

Không lệch một dòng nào. Chat replay của YouTube ổn định, và đường ống
tải → lọc PII → phân loại → ghi store là **tất định**.

### 3.2 Cô lập giữa các phiên — đối chiếu với sự thật gốc

Không chỉ kiểm "phiên A có `session_id` của A". Kiểm mạnh hơn: đọc lại toàn bộ
bình luận của mỗi phiên **qua API**, so với tập bình luận parse trực tiếp từ
file chat gốc của **đúng video đó** rồi lọc PII bằng cùng hàm `scrub`. Rò rỉ
tồn tại khi và chỉ khi hai tập không bằng nhau.

```
OK  1NMt8BChQrI  api= 4079  file= 4079  extra=0 missing=0  one_session_id=True
OK  3eWncr8DSgk  api=   23  file=   23  extra=0 missing=0  one_session_id=True
OK  fhv_rKUeEIc  api=  779  file=  779  extra=0 missing=0  one_session_id=True
OK  gT0LDiBta2k  api= 5492  file= 5492  extra=0 missing=0  one_session_id=True
OK  MPJktS2rkzk  api=  136  file=  136  extra=0 missing=0  one_session_id=True
OK  ZU_0QJzsR6w  api= 6586  file= 6586  extra=0 missing=0  one_session_id=True
comment_id collisions across sessions: 0
ISOLATION: PASS
```

### 3.3 Hai job CHỒNG NHAU, không chỉ nối tiếp

`_run_job` là hàm đồng bộ chạy trong `BackgroundTasks`, nên FastAPI đẩy nó vào
thread pool: **hai phân tích thật sự chạy song song**, dùng chung một store và
một registry job cấp module. Bắn hai POST cùng lúc qua `threading.Barrier`:

```
fhv_rKUeEIc  xong ở t+12,0s   n=779
1NMt8BChQrI  xong ở t+48,6s   n=4079     ← thật sự chồng lấn
OK  fhv_rKUeEIc  api=779   file=779   identical=True
OK  1NMt8BChQrI  api=4079  file=4079  identical=True
CONCURRENT ISOLATION: PASS
```

Và kết quả **trùng từng bit** với lần chạy tuần tự trước đó (cùng phân bố ý
định, cùng phân bố PII) — chạy song song không đổi một con số nào.

### 3.4 Hiệu năng

Toàn bộ thời gian chờ là **tải từ YouTube** (10 – 69 s, phụ thuộc mạng). Giai
đoạn nạp — lọc PII + phân loại ý định + ghi store — chạy **835 – 923 bình
luận/giây** (4 buổi lớn, một tiến trình, in-memory store). Buổi dài nhất
(6.586 bình luận / 117 phút) mất **7,9 giây** để nạp. Ở quy mô thí điểm, xử lý
không phải nút thắt.

---

## 4. Radar ý định: đo THẬT trên 3 buổi mới

### 4.1 Giao thức — chặt hơn lần 08/09

Lần 08/09 gán nhãn theo từng tầng, tức người gán biết mình đang soi lớp nào.
Lần này:

- **Mù**: 393 dòng của cả hai mẫu được **gộp và xáo trộn** trước khi in ra;
  bảng gán nhãn chỉ có `uid` + văn bản, **không có dự đoán, không có lớp, không
  có tên phiên**. Ghép ngược lại sau khi đã gán xong.
- **Mẫu A (precision)**: tối đa 15 dòng mỗi lớp hành động được dự đoán, cho mỗi
  buổi → **193 dòng**.
- **Mẫu B (prevalence)**: **200 dòng ngẫu nhiên đơn giản** từ 11.138 bình luận
  gộp của 3 buổi (tỷ lệ theo kích thước phiên).
- Guideline 11 lớp trong `src/livelift/nlp/labels.py`. Quy tắc định trước cho ca
  mơ hồ: **chọn lớp hành động** — tức mọi con số dưới đây là **cận trên có lợi
  cho model**.
- **Giới hạn giữ nguyên từ lần trước:** một người gán nhãn, không đo được κ.

### 4.2 Precision của nhãn hành động — dao động 50 lần giữa các buổi

| Buổi | Lớp | Đúng/mẫu | Precision | KTC95 (Wilson) | Số dự đoán cả phiên | Ước số ĐÚNG |
|---|---|---:|---:|---|---:|---:|
| `1NMt8BChQrI` | `chot_don` | 0/15 | **0,0%** | 0 – 20,4% | 440 | ~0 |
| | `hoi_gia` | 0/15 | 0,0% | 0 – 20,4% | 75 | ~0 |
| | `che_dat` | 0/15 | 0,0% | 0 – 20,4% | 40 | ~0 |
| | `hoi_size` | 0/15 | 0,0% | 0 – 20,4% | 22 | ~0 |
| | `van_chuyen` | 1/15 | 6,7% | 1,2 – 29,8% | 29 | ~2 |
| | **gộp** | **1/75** | **1,3%** | **0,2 – 7,2%** | **606** | **~2** |
| `gT0LDiBta2k` | `chot_don` | 3/15 | 20,0% | 7,0 – 45,2% | 646 | ~129 |
| | `che_dat` | 2/15 | 13,3% | 3,7 – 37,9% | 98 | ~13 |
| | `hoi_gia` | 2/15 | 13,3% | 3,7 – 37,9% | 86 | ~12 |
| | `van_chuyen` | 1/15 | 6,7% | 1,2 – 29,8% | 72 | ~5 |
| | `hoi_size` | 0/5 | 0,0% | 0 – 43,4% | 5 | 0 |
| | **gộp** | **8/65** | **12,3%** | **6,4 – 22,5%** | **907** | **~159** |
| `47oGShxf80A` | `hoi_size` | 3/3 | 100,0% | 43,8 – 100% | 3 | 3 |
| | `chot_don` | 13/15 | **86,7%** | 62,1 – 96,3% | 268 | ~232 |
| | `hoi_gia` | 10/13 | 76,9% | 49,7 – 91,8% | 13 | ~10 |
| | `van_chuyen` | 9/15 | 60,0% | 35,7 – 80,2% | 39 | ~23 |
| | `che_dat` | 1/7 | 14,3% | 2,6 – 51,3% | 7 | ~1 |
| | **gộp** | **36/53** | **67,9%** | **54,5 – 78,9%** | **330** | **~270** |
| **Gộp 3 buổi** | | **45/193** | **23,3%** | **17,9 – 29,8%** | | |

Đối chiếu buổi Achan Hải Phòng (08/09, cùng phương pháp, mẫu 136 dòng):
precision gộp **11,0%**.

**Bốn buổi, bốn con số: 1,3% · 11,0% · 12,3% · 67,9%.** Không có "độ chính xác
của radar ý định". Có **độ chính xác trên một buổi cụ thể**, và nó chênh nhau
**hơn 50 lần**.

### 4.3 Vì sao — tỷ lệ nền, không phải model

Mẫu B trả lời trực tiếp: trong 200 dòng ngẫu nhiên, bao nhiêu dòng **thật sự**
mang ý định hành động?

| Buổi | n | Ý định hành động THẬT | KTC95 | Model gắn nhãn hành động | Hệ số thổi phồng |
|---|---:|---:|---|---:|---:|
| `1NMt8BChQrI` | 72 | **0** (0,0%) | 0 – 5,1% | 13 (18,1%) | **∞** |
| `gT0LDiBta2k` | 103 | 7 (6,8%) | 3,3 – 13,4% | 21 (20,4%) | **3,0×** |
| `47oGShxf80A` | 25 | 12 (**48,0%**) | 30,0 – 66,5% | 8 (32,0%) | **0,7×** (đếm THIẾU) |
| `ZU_0QJzsR6w` (08/09) | 200 | 1 (0,5%) | 0,09 – 2,78% | 17 (8,5%) | **17×** |

(Hàng cuối lấy từ `live-fire-achan.md` §4.2; trên *toàn* phiên đó model gắn nhãn
hành động cho 14,2% số dòng, tức hệ số thổi phồng ở cấp phiên còn cao hơn nữa.)

Đặt hai bảng cạnh nhau, quy luật hiện ra và nó rất sạch:

| Buổi | Prevalence thật | Precision đo được |
|---|---:|---:|
| `1NMt8BChQrI` | 0,0% | 1,3% |
| `ZU_0QJzsR6w` | 0,5% | 11,0% |
| `gT0LDiBta2k` | 6,8% | 12,3% |
| `47oGShxf80A` | 48,0% | 67,9% |

**Precision đi theo tỷ lệ nền, đúng như một bộ phân loại nhiễu phải làm.** Model
gắn nhãn hành động cho ~1/6 số dòng ở *mọi* buổi (mục 2.1: 12,5% – 21,1%). Khi
buổi đó thật sự có 48% ý định mua, cái thói quen đó tình cờ đúng — thậm chí còn
**bỏ sót**. Khi buổi đó chỉ có 0,5%, cùng thói quen ấy sinh ra 28 lần số lượng
thật.

Buổi `47oGShxf80A` khác ở đâu? Đó là live kiểu **"comment mã để chốt đơn"**:
khách gõ thẳng `mã 12, 3 cái`, `m18 2 cây son`, `mã15 khăn 3 cái`. Chat gần như
là một biểu mẫu đặt hàng. Buổi `1NMt8BChQrI` ("vừa trả đơn vừa tâm sự") thì
ngược hẳn: chat là drama cộng đồng và xã giao, **không một dòng nào** trong 72
dòng ngẫu nhiên là ý định mua thật.

### 4.4 Chất lượng tổng thể trên mẫu ngẫu nhiên (200 dòng, 3 buổi)

| Chỉ số | Bộ biên soạn (5-fold CV) | Chat thật 08/09 (1 buổi) | **Chat thật 10/09 (3 buổi)** |
|---|---:|---:|---:|
| macro-F1 (6 lớp đã huấn luyện) | 0,870 | 0,271 | **0,386** |
| Accuracy | 0,866 | 0,920 | **0,785** |
| Accuracy của baseline `return "khac"` | — | 0,995 | **0,905** |

F1 từng lớp: `khac` 0,873 · `hoi_gia` 0,667 · `van_chuyen` 0,500 ·
`chot_don` 0,279 · `che_dat` **0** · `hoi_size` **0**.

**Model vẫn thua một dòng `return "khac"`** (0,785 so với 0,905), lặp lại kết
luận 08/09 trên tập dữ liệu rộng gấp ba và đa dạng hơn hẳn. macro-F1 cao hơn
0,271 chỉ vì tập gộp này có nhiều `chot_don` thật hơn (nhờ buổi `47oGShxf80A`),
không phải vì model tốt lên.

### 4.5 Bộ 6 lớp bỏ sót cái gì — đo lại trên nguồn khác

Phân bố nhãn tay của 200 dòng ngẫu nhiên:

| Nhóm | Số / 200 | Tỷ lệ |
|---|---:|---:|
| `khac` (bàn luận, drama, spam số/emoji) | 91 | 45,5% |
| `cam_on_khen` | 53 | **26,5%** |
| `chao_hoi` | 27 | **13,5%** |
| `chot_don` (thật) | 15 | 7,5% |
| `hoi_sanpham` | 5 | 2,5% |
| `bao_gia_shop` | 5 | 2,5% |
| `hoi_gia` (thật) | 2 | 1,0% |
| `van_chuyen` (thật) | 2 | 1,0% |

**40,0% là xã giao** (`cam_on_khen` 26,5% + `chao_hoi` 13,5%). Buổi Achan 08/09
đo được cùng mức 40,0%, tuy chia hơi khác (chào hỏi 10% + cảm ơn/khen 28% + kêu
gọi tương tác 2%). Hai lô đo độc lập, ba người bán khác nhau, cùng ra ~40%: đây
là **tính chất chung của chat bán hàng livestream tiếng Việt**, không phải đặc
thù một kênh. Nó xác nhận quyết định mở bộ nhãn lên 11 lớp là đúng hướng.

### 4.6 Độ tự tin dùng được để làm gì, và KHÔNG dùng được để làm gì

- **Trong một phiên: dùng được.** Trên 193 dự đoán hành động đã gán nhãn tay,
  độ tự tin trung vị là **0,660 khi đúng** và **0,539 khi sai**; AUC phân biệt
  đúng/sai = **0,696**. Đủ tín hiệu để xếp hạng, để chọn dòng gửi đi gán nhãn
  (đúng như `label_llm` đang dùng).
- **Giữa các phiên: KHÔNG dùng được.** Buổi có precision cao nhất
  (`47oGShxf80A`, 67,9%) lại có **độ tự tin trung vị THẤP nhất** (0,387) và tỷ
  lệ abstain **cao nhất** (71,0%). Spearman(precision, độ tự tin trung vị) trên
  4 buổi = **−0,40** — với n=4 thì **không kết luận thống kê được**, nhưng đủ để
  cấm một cách dùng: **không được lấy độ tự tin trung bình của phiên làm chỉ báo
  "phiên này radar đáng tin"**. Nó có thể chỉ đúng hướng ngược lại.

---

## 5. Kiểm sức bền — ba ca khó

### 5.1 Chat cực thưa và chat RỖNG

`3eWncr8DSgk` (23 bình luận / 70 phút, cây cảnh): mọi endpoint trả **HTTP 200**,
không vỡ, `/signals` mô tả đúng trạng thái, `/report` giữ nhãn "phân tích quan
sát — không phải thí nghiệm". Đạt.

`TdLWyV3hNao` (**0 bình luận** / 715 phút) thì **không đạt**, và làm lộ hai lỗi
trung thực — xem mục 6. Sau khi sửa:

```
job:  done, n_comments=0,
      detail="Chat replay tải về KHÔNG có bình luận nào — phiên phân tích rỗng…"
/signals: comments → missing · ticks → missing
          TẤT CẢ 5 năng lực → missing
```

### 5.2 Buổi đấu giá — chat toàn chữ số

`MPJktS2rkzk` (136 bình luận): **42 dòng (30,9%) là chuỗi số trần trụi** —
`40`, `49`, `50`, `53`, `141` — tức những lượt trả giá.

- **Không sinh nhãn vô nghĩa hàng loạt.** 40/42 số trần được đẩy về `khac` với
  độ tự tin nằm trong khoảng 0,276 – 0,49, phần lớn **dưới ngưỡng abstain 0,45**
  — cơ chế abstain làm đúng việc của nó. Chỉ **2/42** bị gắn nhãn hành động, và
  cả hai là cùng một chuỗi `141` → `chot_don` 0,49 (ngay trên ngưỡng).
- **Nhưng đó là đúng vì lý do sai.** Trong một phiên đấu giá, *mỗi con số là một
  lượt trả giá, tức một ý định mua*. Hệ thống bỏ sót **40/42** trong số đó. Nói
  cho gọn: nó không tạo ra rác, nó **mù** với định dạng này — và cái "mù" ấy che
  mất đúng 31% nội dung có giá trị nhất của buổi. LiveLift **chưa hỗ trợ live
  đấu giá**, và không nên giả vờ ngược lại.
- **Lời chào vẫn thành `chot_don` với độ tự tin cao**: `Chào em` 0,763 ·
  `chào shop nha` 0,686 · `em chào bác [TÊN]` 0,669. Đây là **cùng một cơ chế
  lỗi** đã ghi ở live-fire 08/09, tái hiện trên một người bán khác, một ngành
  khác. Xác nhận: đó là lỗi hệ thống của bộ nhãn, không phải nhiễu của một buổi.

### 5.3 Rò rỉ giữa hai phiên

Đã kiểm nối tiếp (mục 3.2) và song song (mục 3.3): **không rò rỉ**, kể cả giữa
hai buổi của **cùng một cửa hàng, cùng tập khán giả**: `ZU_0QJzsR6w` và
`gT0LDiBta2k` có **213 văn bản (sau lọc PII) trùng khít nhau** (`Hi`, `11111111`,
`chào em [TÊN]`, chuỗi tim…) — đúng chỗ một lỗi khoá theo nội dung sẽ lộ ra.
`comment_id` không đụng nhau lần nào.

---

## 6. Hai lỗi phát hiện trong lần chạy này — đã sửa tận gốc

### 6.1 Ma trận tín hiệu nhận vơ năng lực "người xem theo thời gian"

**Triệu chứng.** Phiên `TdLWyV3hNao` có **0 bình luận, 0 người xem, 1.430 dòng
tick toàn số 0**. `/signals` báo:

```
ticks → ok  "1430 điểm đo, phủ 100%"
năng lực "nhịp phiên (người xem theo thời gian)" → ok  "đủ tín hiệu"
```

Một phiên **rỗng hoàn toàn** được quảng cáo là có năng lực chạy được. Cùng lỗi
đó bật lên ở **mọi** phiên replay, kể cả 6.586 bình luận của Achan.

**Root cause.** `assess()` chấm tín hiệu `ticks` bằng *số dòng tick*. Nhưng
`ticks` theo định nghĩa là **telemetry NGƯỜI XEM**. Đường replay ghi mỗi 30 s
một dòng để mang **nhịp bình luận**, và điền `viewers = 0.0` vì VOD đã kết thúc
không còn lộ số người xem — đúng như docstring
`synth_ticks_from_comments` đã cảnh báo ("must be labeled as unavailable in any
UI. Do not fabricate a viewers curve"). Lớp signals đọc số dòng, không đọc nội
dung, nên chỗ trống thành phép đo. Nó còn mâu thuẫn thẳng với hợp đồng đã ghi
trong `youtube_ytdlp.iter_viewers`: không có số người xem thì `ticks` phải
`missing`.

**Sửa.** `assess()` nhận thêm tham số **bắt buộc** `n_ticks_with_viewers`
(bắt buộc, không mặc định — để mọi caller phải khai đã đo cái gì). Không dòng
nào có người xem → `ticks = missing` kèm giải thích tiếng Việt; một phần có →
`degraded`. Route `/signals` đếm `viewers > 0` từ store.

**Test hồi quy:** `test_comment_tempo_ticks_are_not_counted_as_viewer_telemetry`,
`test_partially_missing_viewer_numbers_degrade_the_ticks_signal`,
`test_signals_endpoint_refuses_to_claim_viewers_from_tempo_only_ticks`.

### 6.2 Phiên rỗng được báo "done" trong im lặng

**Triệu chứng.** `POST /replays/youtube` với `TdLWyV3hNao` trả
`status=done, n_comments=0, detail=null`. Người vận hành nhận một phiên trông
khoẻ mạnh và rỗng không.

**Root cause.** `_run_job` chỉ đặt `detail` cho trường hợp cắt bớt; nhánh "tải
được nhưng chat rỗng" rơi vào `detail=None` chung với nhánh thành công bình
thường. Metadata YouTube quảng cáo track `live_chat` không bảo đảm track đó có
nội dung — một trạng thái thật mà mã chưa có tên gọi.

**Sửa.** Hằng `EMPTY_CHAT_DETAIL`, đặt khi `not comments`. Vẫn là `done` (tải
thành công, kết quả rỗng là kết quả hợp lệ) nhưng **nói ra**.

**Test hồi quy:** `test_replay_route_says_so_when_the_chat_replay_is_empty` —
kiểm cả job detail lẫn ma trận tín hiệu của phiên rỗng.

---

## 7. Bộ lọc PII — phần mạnh nhất, và một cảnh báo về cách đọc số

### 7.1 Bắt được ca khó thật

Trên chat thật, bộ lọc bắt đúng những dạng che giấu mà một regex số điện thoại
thường bỏ lọt:

| Nguyên văn (rút gọn) | Sau khi lọc | Cơ chế |
|---|---|---|
| `SĐT : KHÔNG TÁM HAI HAI NĂM NĂM BẢY BẢY HAI MỘT` | `SĐT : [SĐT]` | `SPELLED_PHONE_RE` |
| `08 HAI HAI 55 BẢY BẢY 21` | `[SĐT]` | `MIXED_PHONE_RE` |
| `điện thoại K BA BỐN SÁU SÁU BỐN NĂM HAI SÁU` | `điện thoại K [SĐT]` | `MIXED_PHONE_RE` |
| `@ chín 16.798.168` | `@ [SĐT]` | `MIXED_PHONE_RE` |
| `Củ sâm 25gram giá 3.740.625 … hotline 0837153…` | giá **giữ nguyên**, hotline → `[SĐT]` | phân biệt đúng tiền và số điện thoại |

Dòng cuối quan trọng: trong buổi sâm và buổi đấu giá, **giá tiền 7–8 chữ số
không bị nhầm thành số điện thoại**. Ca `@ chín 16.798.168` là ranh giới thật —
đọc là `0916798168` thì là số điện thoại, đọc là `16.798.168 đồng` thì là một
lượt trả giá; bộ lọc chọn phương án **che**, tức sai về phía an toàn. Đúng
hướng.

### 7.2 Một dương tính giả đã tìm thấy

`Đây mình là ng nhà shop đây` → `Đây mình là [TÊN] shop đây`. `ng nhà` là viết
tắt của "người nhà", không phải tên riêng; câu bị che mất nghĩa. Chưa sửa: sửa
`NAME_*` là đụng vào cổng recall ≥95% của quy tắc bất di bất dịch 1.4, cần một
lô đo riêng chứ không phải một dòng regex vá vội.

### 7.3 CẢNH BÁO: "tỷ lệ PII theo ngành hàng" là một cái bẫy

Đọc bảng 2.3 một cách ngây thơ sẽ ra kết luận "khách ngành dược liệu để lộ số
điện thoại nhiều gấp 70 lần khách ngành quần áo". **Sai.** Đếm số văn bản DUY
NHẤT trong các bình luận bị bắt `phone`:

| Video | Lượt bắt `phone` | Văn bản duy nhất | Trông như hotline shop/cộng tác viên | Bản lặp nhiều nhất |
|---|---:|---:|---:|---:|
| `1NMt8BChQrI` | 271 | **36** | 241 (89%) | 31 lần |
| `fhv_rKUeEIc` | 73 | **26** | 73 (100%) | 15 lần |
| `ZU_0QJzsR6w` | 1 | 1 | 1 | 1 |
| `gT0LDiBta2k` | 2 | 2 | 2 | 1 |
| `MPJktS2rkzk` | 1 | 1 | 0 | 1 |

271 lượt bắt trong `1NMt8BChQrI` **không phải 271 khách để lộ số của mình** —
đó là **36 mẫu quảng cáo của shop/cộng tác viên dán đi dán lại**, một mẫu tới 31
lần. Vậy chỉ số "tỷ lệ PII của phiên" đang đo **cường độ spam liên kết**, không
đo hành vi của khách. Trong toàn bộ 19.126 bình luận, số điện thoại **do chính
khách gõ** đếm trên đầu ngón tay.

Hệ quả bắt buộc: **không được dùng tỷ lệ PII làm biến so sánh giữa các phiên**
nếu chưa khử trùng lặp. Ngược lại, điều này lại củng cố lý do bộ lọc phải tồn
tại: đúng những dòng lặp đi lặp lại đó mới là thứ tràn vào store nếu không lọc.

---

## 8. Kết luận trung thực về năng lực THẬT

**Hệ thống làm được, đã chứng minh trên 19.126 bình luận thật:**

1. Nạp buổi live công khai bất kỳ qua một endpoint, **không cần API key**, với
   thông báo lỗi tiếng Việt đúng cho từng kiểu hỏng (không có chat / chat rỗng /
   video riêng tư).
2. **Cô lập phiên tuyệt đối** — nối tiếp và song song, đối chiếu với sự thật
   gốc, 0 rò rỉ, 0 va chạm `comment_id`.
3. **Tất định**: chạy lại sau 2 ngày trên tiến trình khác cho **đúng từng con
   số**.
4. **Lọc PII hoạt động đúng thiết kế trên chat thật**, kể cả số điện thoại viết
   bằng chữ và trộn chữ–số, và không nhầm giá tiền thành số điện thoại.
5. **Nói thật khi thiếu dữ liệu** — sau khi sửa hai lỗi ở mục 6, một phiên rỗng
   báo rỗng và một phiên không có người xem không được nhận là có.
6. Xử lý ~**900 bình luận/giây**; nút thắt là mạng, không phải tính toán.

**Hệ thống KHÔNG làm được, cũng đã chứng minh:**

1. **Radar ý định không có một độ chính xác dùng được để phát biểu.** 1,3% ·
   11,0% · 12,3% · 67,9% trên bốn buổi. Không được nêu bất kỳ con số nào trong
   đó như "độ chính xác của LiveLift".
2. **Nó tệ nhất đúng ở chỗ cần nhất.** Buổi mà bàn trung control cần được giúp
   nhất — chat đông nhưng thưa ý định mua — là buổi radar sai gần như hoàn toàn
   (`1NMt8BChQrI`: 606 nhãn hành động, ước ~2 nhãn đúng).
3. **Vẫn thua `return "khac"`** về accuracy (0,785 so với 0,905) trên mẫu ngẫu
   nhiên gộp 3 buổi.
4. **Không đọc được live đấu giá** (chuỗi trả giá thuần số).
5. **Không có dữ liệu người xem cho VOD** — vĩnh viễn, không phải lỗi cài đặt.
   Mọi phát biểu về "nhịp phiên" trên phân tích replay là về **nhịp bình luận**.
6. **Chưa chạm được nhân quả trên các buổi này**: không có gán ngẫu nhiên, không
   có link đo. Toàn bộ 16 phiên là **quan sát**, và hệ thống tự dán nhãn như vậy.

**Điều lần đo này thay đổi so với 08/09:** kết luận cũ ("radar ý định gần như là
nhiễu") là **đúng nhưng chưa đủ**. Bản đầy đủ: *radar ý định là một bộ đếm gắn
nhãn hành động cho khoảng 1/6 số dòng bất kể nội dung; nó trở nên hữu ích khi và
chỉ khi buổi live vốn đã có mật độ ý định mua cao, và trở nên nguy hiểm đúng
theo tỷ lệ nghịch.* Trước khi huấn luyện lại, đây là câu phải nói mỗi lần trình
bày con số.

## 9. Việc tiếp theo

1. Đưa **prevalence ý định thật của phiên** thành một con số hệ thống tự ước
   lượng và hiển thị cạnh radar — người dùng phải thấy "buổi này radar đáng tin
   tới đâu", vì độ tự tin trung vị **không** trả lời được (mục 4.6).
2. Gán nhãn lại + huấn luyện 11 lớp; báo cáo song song **bốn** con số buổi thật,
   không phải một.
3. Khử trùng lặp trước khi báo bất kỳ tỷ lệ PII cấp phiên nào (mục 7.3).
4. Sửa dương tính giả `ng nhà` → `[TÊN]` kèm một lô đo recall riêng (mục 7.2).
5. Quyết định rõ: hoặc hỗ trợ live đấu giá tử tế (parser trả giá riêng), hoặc
   ghi thẳng vào tài liệu là **ngoài phạm vi**. Hiện tại đang ở giữa.
