# Kết quả đánh giá bộ phân loại ý định — sinh tự động

*Sinh bởi `python -m livelift.nlp.eval_intent` · 2026-09-25T03:44:30+07:00*

> **Nguồn nhãn.** Nhãn tham chiếu của 393 dòng test do một tác tử AI (Claude) gán ngày 09/09/2026 trên bảng xáo trộn — chưa có nhãn người. Vì vậy mọi con số là mức đồng thuận với nhãn tham chiếu do AI gán, chưa phải độ chính xác so với con người.
> Nhãn train bổ sung kê khai riêng ở mục 1: 320 câu mẫu do AI (Claude) soạn ngày 01/09/2026; 1.800 nhãn train buổi thứ tư do LLM (Claude) gán, không có người duyệt.
>
> **Nguồn dữ liệu.** Bình luận công khai của các buổi live phát lại (VOD YouTube), lấy qua yt-dlp (dữ liệu quan sát, không phải API chính thức), đã lọc PII; lọc lại bằng bộ lọc hiện hành ngày 25/09/2026.
>
> Chia **leave-one-session-out theo buổi live** (không buổi nào nằm cả
> train lẫn test).
>
> B2 (artifact đang chạy) được chấm với bộ `tfidf_logreg` (`intent_clf.joblib`), scikit-learn 1.9.0.

## 1. Kiểm kê dữ liệu

| Nguồn | Số dòng | Ghi chú |
|---|---:|---|
| `data/labeling/lot2-da-nguon-10-09` — nhãn do tác tử AI gán, bảng xáo trộn, 11 lớp (chưa có nhãn người) | 393 | 3 buổi live · TEST theo leave-one-session-out; C1–C3 dùng hai buổi còn lại của mỗi fold làm train |
| `authored_11` | 320 | câu mẫu do AI (Claude) soạn 01/09, gán lại 11 lớp bằng bảng trong mã — CHỈ train |
| `llm_lot1` | 1800 | bình luận thật buổi thứ tư, nhãn do LLM (Claude) gán, không người duyệt — CHỈ train |

Phân bố nhãn của tập test (nhãn tham chiếu do tác tử AI gán):

| Lớp | Số dòng | Tỷ lệ |
|---|---:|---:|
| `khac` | 153 | 38,9% |
| `cam_on_khen` | 86 | 21,9% |
| `chao_hoi` | 42 | 10,7% |
| `chot_don` | 33 | 8,4% |
| `bao_gia_shop` | 32 | 8,1% |
| `hoi_gia` | 14 | 3,6% |
| `van_chuyen` | 14 | 3,6% |
| `hoi_sanpham` | 11 | 2,8% |
| `che_dat` | 5 | 1,3% |
| `hoi_size` | 3 | 0,8% |

| Buổi live | Dòng có nhãn | Tỷ lệ nền nhãn hành động (tầng ngẫu nhiên, nhãn AI) |
|---|---:|---:|
| `1NMt8BChQrI` | 147 | 0/72 = 0,0% |
| `47oGShxf80A` | 78 | 12/25 = 48,0% |
| `gT0LDiBta2k` | 168 | 7/103 = 6,8% |

## 2. Baseline trên chat thật (test = buổi live mô hình chưa từng thấy)

Ba baseline bắt buộc + artifact đang chạy. Tập test = 393 dòng có nhãn tham chiếu do tác tử AI gán, gộp từ ba fold leave-one-session-out.

| Hệ thống | macro-F1 (393 dòng) | KTC95 (bootstrap dòng) | macro-F1 (chỉ lớp có trong nhãn tham chiếu) | Accuracy | Precision nhãn hành động | macro-F1 tầng NGẪU NHIÊN (200) |
|---|---:|---|---:|---:|---:|---:|
| B0 · luôn đoán lớp đa số `khac` | **0,056** | [0,051; 0,063] | 0,056 | 0,389 | — (0 dự đoán) | 0,078 [0,070; 0,099] |
| B1 · từ khoá (tiền đăng ký) | **0,146** | [0,109; 0,180] | 0,146 | 0,387 | 0,209 (18/86) | 0,178 [0,086; 0,246] |
| B2 · TF-IDF+LogReg ĐANG CHẠY (`intent_clf.joblib`, abstain 0,45) | **0,211** | [0,172; 0,247] | 0,211 | 0,338 | 0,230 (54/235) | 0,208 [0,095; 0,286] |
| B3 · TF-IDF+LogReg train lại trên 320 câu biên soạn (6 lớp, không abstain) | **0,199** | [0,163; 0,234] | 0,199 | 0,303 | 0,219 (57/260) | 0,163 [0,089; 0,227] |

macro-F1 từng buổi live (bất định thật nằm ở đây, không ở KTC bootstrap):

| Hệ thống | `1NMt8BChQrI` | `47oGShxf80A` | `gT0LDiBta2k` |
|---|---|---|---|
| B0 · luôn đoán lớp đa số `khac` | 0,106 | 0,030 | 0,065 |
| B1 · từ khoá (tiền đăng ký) | 0,081 | 0,162 | 0,170 |
| B2 · TF-IDF+LogReg ĐANG CHẠY (`intent_clf.joblib`, abstain 0,45) | 0,064 | 0,412 | 0,138 |
| B3 · TF-IDF+LogReg train lại trên 320 câu biên soạn (6 lớp, không abstain) | 0,054 | 0,409 | 0,133 |

## 3. Sau cải tiến

Cùng tập test, cùng cách chia. Chỉ dữ liệu train và đặc trưng thay đổi.

| Hệ thống | macro-F1 (393 dòng) | KTC95 (bootstrap dòng) | macro-F1 (chỉ lớp có trong nhãn tham chiếu) | Accuracy | Precision nhãn hành động | macro-F1 tầng NGẪU NHIÊN (200) |
|---|---:|---|---:|---:|---:|---:|
| C1 · TF-IDF 11 lớp, train = biên soạn(11) + gold 2 buổi | **0,563** | [0,491; 0,621] | 0,563 | 0,611 | 0,472 (43/91) | 0,455 [0,330; 0,545] |
| C2 · C1 + nhãn LLM trên buổi thứ tư | **0,542** | [0,478; 0,625] | 0,597 | 0,730 | 0,655 (38/58) | 0,516 [0,375; 0,660] |
| C3 · C2 + từ chối trả lời, ngưỡng chọn TRONG tập train | **0,493** | [0,441; 0,562] | 0,542 | 0,707 | 0,667 (30/45) | 0,538 [0,382; 0,679] |

macro-F1 từng buổi live (bất định thật nằm ở đây, không ở KTC bootstrap):

| Hệ thống | `1NMt8BChQrI` | `47oGShxf80A` | `gT0LDiBta2k` |
|---|---|---|---|
| C1 · TF-IDF 11 lớp, train = biên soạn(11) + gold 2 buổi | 0,327 | 0,623 | 0,497 |
| C2 · C1 + nhãn LLM trên buổi thứ tư | 0,368 | 0,599 | 0,525 |
| C3 · C2 + từ chối trả lời, ngưỡng chọn TRONG tập train | 0,368 | 0,449 | 0,525 |

## 4. Ablation

| Hệ thống | macro-F1 (393 dòng) | KTC95 (bootstrap dòng) | macro-F1 (chỉ lớp có trong nhãn tham chiếu) | Accuracy | Precision nhãn hành động | macro-F1 tầng NGẪU NHIÊN (200) |
|---|---:|---|---:|---:|---:|---:|
| A0 · đầy đủ (chuẩn hoá + phong cách + 11 lớp + mọi nguồn) | **0,542** | [0,478; 0,625] | 0,597 | 0,730 | 0,655 (38/58) | 0,516 [0,375; 0,660] |
| A1 · − chuẩn hoá văn bản (NFKC/teencode/emoji) | **0,559** | [0,488; 0,643] | 0,615 | 0,735 | 0,650 (39/60) | 0,500 [0,369; 0,651] |
| A2 · − đặc trưng phong cách (caps/giá/‖ → mô hình người nói) | **0,576** | [0,512; 0,682] | 0,633 | 0,735 | 0,643 (45/70) | 0,545 [0,397; 0,704] |
| A3 · − nhãn LLM buổi thứ tư | **0,563** | [0,491; 0,621] | 0,563 | 0,611 | 0,472 (43/91) | 0,455 [0,330; 0,545] |
| A4 · − bộ biên soạn (chỉ dữ liệu thật) | **0,362** | [0,317; 0,423] | 0,398 | 0,672 | 0,875 (7/8) | 0,331 [0,288; 0,447] |
| A5 · − gold 2 buổi train (chỉ biên soạn + LLM) | **0,580** | [0,504; 0,666] | 0,638 | 0,728 | 0,710 (44/62) | 0,427 [0,314; 0,582] |
| A6 · + từ chối trả lời (ngưỡng chọn trong train) | **0,493** | [0,441; 0,562] | 0,542 | 0,707 | 0,667 (30/45) | 0,538 [0,382; 0,679] |
| A7 · bộ nhãn 6 lớp (chấm trên không gian 6 lớp) | **0,574** | [0,461; 0,665] | 0,574 | 0,850 | 0,548 (40/73) | 0,455 [0,240; 0,683] |
| A8 · bộ nhãn 11 lớp, gộp về 6 khi chấm (cùng thang với A7) | **0,572** | [0,471; 0,667] | 0,572 | 0,875 | 0,655 (38/58) | 0,626 [0,317; 0,823] |

macro-F1 từng buổi live (bất định thật nằm ở đây, không ở KTC bootstrap):

| Hệ thống | `1NMt8BChQrI` | `47oGShxf80A` | `gT0LDiBta2k` |
|---|---|---|---|
| A0 · đầy đủ (chuẩn hoá + phong cách + 11 lớp + mọi nguồn) | 0,368 | 0,599 | 0,525 |
| A1 · − chuẩn hoá văn bản (NFKC/teencode/emoji) | 0,369 | 0,630 | 0,518 |
| A2 · − đặc trưng phong cách (caps/giá/‖ → mô hình người nói) | 0,419 | 0,642 | 0,592 |
| A3 · − nhãn LLM buổi thứ tư | 0,327 | 0,623 | 0,497 |
| A4 · − bộ biên soạn (chỉ dữ liệu thật) | 0,402 | 0,260 | 0,479 |
| A5 · − gold 2 buổi train (chỉ biên soạn + LLM) | 0,347 | 0,611 | 0,555 |
| A6 · + từ chối trả lời (ngưỡng chọn trong train) | 0,368 | 0,449 | 0,525 |
| A7 · bộ nhãn 6 lớp (chấm trên không gian 6 lớp) | 0,190 | 0,708 | 0,508 |
| A8 · bộ nhãn 11 lớp, gộp về 6 khi chấm (cùng thang với A7) | 0,239 | 0,729 | 0,556 |

## Đường đánh đổi độ phủ ↔ độ chính xác (tuỳ chọn từ chối trả lời)

| Ngưỡng | macro-F1 | Accuracy | Độ phủ nhãn hành động | Precision | KTC95 |
|---:|---:|---:|---:|---:|---|
| 0,00 | 0,542 | 0,730 | 0,148 | 0,655 | [0,527; 0,764] |
| 0,30 | 0,548 | 0,730 | 0,140 | 0,691 | [0,560; 0,797] |
| 0,40 | 0,522 | 0,730 | 0,125 | 0,735 | [0,597; 0,838] |
| 0,45 | 0,523 | 0,738 | 0,117 | 0,739 | [0,597; 0,844] |
| 0,50 | 0,523 | 0,733 | 0,112 | 0,750 | [0,606; 0,854] |
| 0,60 | 0,577 | 0,730 | 0,084 | 0,879 | [0,727; 0,952] |
| 0,70 | 0,545 | 0,700 | 0,076 | 0,900 | [0,744; 0,965] |
| 0,80 | 0,488 | 0,674 | 0,056 | 0,909 | [0,722; 0,975] |

## Nhãn hành động: precision VÀ recall

Nhãn hành động = `hoi_gia`, `hoi_size`, `che_dat`, `chot_don`, `van_chuyen`. Precision: trong các lần hệ thống gắn nhãn hành động, bao nhiêu lần đúng lớp. Recall: trong các dòng có nhãn tham chiếu thuộc nhóm hành động, bao nhiêu dòng được đoán đúng lớp. KTC95 Wilson. Tầng `predicted` (193 dòng) được rút theo nhãn v1 dự đoán nên số trên 393 dòng KHÔNG phải con số vận hành — đọc cột tầng ngẫu nhiên.

| Hệ thống | Precision (393) | Recall (393) | Precision tầng ngẫu nhiên (200) | Recall tầng ngẫu nhiên (200) |
|---|---|---|---|---|
| B0 · luôn đoán lớp đa số `khac` | — (0) | 0,000 (0/69) [0,000; 0,053] | — (0) | 0,000 (0/19) [0,000; 0,168] |
| B1 · từ khoá (tiền đăng ký) | 0,209 (18/86) [0,137; 0,307] | 0,261 (18/69) [0,172; 0,375] | 0,222 (4/18) [0,090; 0,452] | 0,210 (4/19) [0,085; 0,433] |
| B2 · TF-IDF+LogReg ĐANG CHẠY (`intent_clf.joblib`, abstain 0,45) | 0,230 (54/235) [0,181; 0,288] | 0,783 (54/69) [0,672; 0,864] | 0,214 (9/42) [0,117; 0,359] | 0,474 (9/19) [0,273; 0,683] |
| B3 · TF-IDF+LogReg train lại trên 320 câu biên soạn (6 lớp, không abstain) | 0,219 (57/260) [0,173; 0,273] | 0,826 (57/69) [0,720; 0,898] | 0,179 (12/67) [0,105; 0,287] | 0,632 (12/19) [0,410; 0,808] |
| C1 · TF-IDF 11 lớp, train = biên soạn(11) + gold 2 buổi | 0,472 (43/91) [0,373; 0,574] | 0,623 (43/69) [0,505; 0,728] | 0,375 (9/24) [0,212; 0,573] | 0,474 (9/19) [0,273; 0,683] |
| C2 · C1 + nhãn LLM trên buổi thứ tư | 0,655 (38/58) [0,527; 0,764] | 0,551 (38/69) [0,434; 0,662] | 0,667 (6/9) [0,354; 0,879] | 0,316 (6/19) [0,154; 0,540] |
| C3 · C2 + từ chối trả lời, ngưỡng chọn TRONG tập train | 0,667 (30/45) [0,521; 0,786] | 0,435 (30/69) [0,324; 0,552] | 0,833 (5/6) [0,436; 0,970] | 0,263 (5/19) [0,118; 0,488] |

## F1 từng lớp và ma trận nhầm lẫn — cấu hình đóng gói thành v2

Hệ thống: **C2 · C1 + nhãn LLM trên buổi thứ tư**

Chọn TRƯỚC, không chọn theo điểm trên tập test: mục này trình bày C2 — đúng cấu hình được đóng gói thành `intent_clf_v2.joblib`. Dòng ablation nào có điểm cao hơn thì đọc kèm khoảng tin cậy ở mục 4; lấy nó làm "tốt nhất" là chọn trên chính tập test. A7/A8 chấm trên thang 6 lớp gộp, không so được với thang 11 lớp.

| Lớp | P | R | F1 | Nhãn tham chiếu | Lần dự đoán |
|---|---:|---:|---:|---:|---:|
| `hoi_gia` | 0,812 | 0,929 | **0,867** | 14 | 16 |
| `hoi_size` | 0,200 | 0,333 | **0,250** | 3 | 5 |
| `che_dat` | 0,167 | 0,200 | **0,182** | 5 | 6 |
| `chot_don` | 0,824 | 0,424 | **0,560** | 33 | 17 |
| `van_chuyen` | 0,643 | 0,643 | **0,643** | 14 | 14 |
| `chao_hoi` | 0,909 | 0,952 | **0,930** | 42 | 44 |
| `cam_on_khen` | 0,699 | 0,837 | **0,762** | 86 | 103 |
| `hoi_sanpham` | 0,333 | 0,182 | **0,235** | 11 | 6 |
| `hoi_daily` | 0,000 | 0,000 | **0,000** | 0 | 2 |
| `bao_gia_shop` | 0,812 | 0,812 | **0,812** | 32 | 32 |
| `khac` | 0,737 | 0,712 | **0,724** | 153 | 148 |

Ma trận nhầm lẫn (hàng = nhãn tham chiếu do tác tử AI gán, cột = nhãn đoán):

| tham chiếu \ đoán | `hoi_gia` | `hoi_size` | `che_dat` | `chot_don` | `van_chuyen` | `chao_hoi` | `cam_on_khen` | `hoi_sanpham` | `hoi_daily` | `bao_gia_shop` | `khac` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `hoi_gia` | 13 | · | · | · | · | · | · | · | · | · | 1 |
| `hoi_size` | · | 1 | · | · | · | · | · | · | · | · | 2 |
| `che_dat` | 1 | · | 1 | · | · | · | 1 | 1 | · | · | 1 |
| `chot_don` | · | · | · | 14 | · | · | · | · | · | 4 | 15 |
| `van_chuyen` | 1 | · | · | · | 9 | · | · | · | · | 1 | 3 |
| `chao_hoi` | · | · | · | · | · | 40 | 2 | · | · | · | · |
| `cam_on_khen` | · | 4 | · | · | · | · | 72 | · | 1 | · | 9 |
| `hoi_sanpham` | · | · | · | 2 | · | · | 1 | 2 | · | · | 6 |
| `bao_gia_shop` | 1 | · | 3 | · | · | · | · | · | · | 26 | 2 |
| `khac` | · | · | 2 | 1 | 5 | 4 | 27 | 3 | 1 | 1 | 109 |

