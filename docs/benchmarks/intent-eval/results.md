# Kết quả đánh giá bộ phân loại ý định — sinh tự động

*Sinh bởi `python -m livelift.nlp.eval_intent` · 2026-09-14T14:19:29+07:00*

> Mọi con số dưới đây đo trên **chat livestream THẬT đã gán nhãn tay**,
> chia **leave-one-session-out theo buổi live** (không buổi nào nằm cả
> train lẫn test). Nhãn test do người gán; nhãn train bổ sung do LLM gán
> được kê khai riêng.

## 1. Kiểm kê dữ liệu

| Nguồn | Số dòng | Ghi chú |
|---|---:|---|
| `data/labeling/lot2-da-nguon-10-09` — gán nhãn TAY, mù, 11 lớp | 393 | 3 buổi live · CHỈ dùng làm TEST |
| `authored_11` | 320 | tự biên soạn, đã gán lại theo 11 lớp — CHỈ train |
| `llm_lot1` | 1800 | bình luận thật buổi thứ tư, nhãn do LLM sinh — CHỈ train |

Phân bố nhãn của tập test (người gán):

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

| Buổi live | Dòng gán nhãn | Tỷ lệ ý định hành động THẬT (tầng ngẫu nhiên) |
|---|---:|---:|
| `1NMt8BChQrI` | 147 | 0/72 = 0,0% |
| `47oGShxf80A` | 78 | 12/25 = 48,0% |
| `gT0LDiBta2k` | 168 | 7/103 = 6,8% |

## 2. Baseline trên chat thật (test = buổi live mô hình chưa từng thấy)

Ba baseline bắt buộc + artifact đang chạy. Cột `n test` = 393 dòng gán nhãn tay, gộp từ ba fold leave-one-session-out.

| Hệ thống | macro-F1 (393 dòng) | KTC95 (bootstrap dòng) | macro-F1 (chỉ lớp có nhãn thật) | Accuracy | Precision nhãn hành động | macro-F1 tầng NGẪU NHIÊN (200) |
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

| Hệ thống | macro-F1 (393 dòng) | KTC95 (bootstrap dòng) | macro-F1 (chỉ lớp có nhãn thật) | Accuracy | Precision nhãn hành động | macro-F1 tầng NGẪU NHIÊN (200) |
|---|---:|---|---:|---:|---:|---:|
| C1 · TF-IDF 11 lớp, train = biên soạn(11) + gold 2 buổi | **0,557** | [0,487; 0,614] | 0,557 | 0,608 | 0,462 (43/93) | 0,451 [0,326; 0,540] |
| C2 · C1 + nhãn LLM trên buổi thứ tư | **0,565** | [0,491; 0,649] | 0,621 | 0,741 | 0,667 (40/60) | 0,519 [0,377; 0,664] |
| C3 · C2 + từ chối trả lời, ngưỡng chọn TRONG tập train | **0,492** | [0,440; 0,562] | 0,541 | 0,713 | 0,652 (30/46) | 0,541 [0,386; 0,682] |

macro-F1 từng buổi live (bất định thật nằm ở đây, không ở KTC bootstrap):

| Hệ thống | `1NMt8BChQrI` | `47oGShxf80A` | `gT0LDiBta2k` |
|---|---|---|---|
| C1 · TF-IDF 11 lớp, train = biên soạn(11) + gold 2 buổi | 0,326 | 0,623 | 0,497 |
| C2 · C1 + nhãn LLM trên buổi thứ tư | 0,372 | 0,635 | 0,525 |
| C3 · C2 + từ chối trả lời, ngưỡng chọn TRONG tập train | 0,372 | 0,445 | 0,525 |

## 4. Ablation

| Hệ thống | macro-F1 (393 dòng) | KTC95 (bootstrap dòng) | macro-F1 (chỉ lớp có nhãn thật) | Accuracy | Precision nhãn hành động | macro-F1 tầng NGẪU NHIÊN (200) |
|---|---:|---|---:|---:|---:|---:|
| A0 · đầy đủ (chuẩn hoá + phong cách + 11 lớp + mọi nguồn) | **0,565** | [0,491; 0,649] | 0,621 | 0,741 | 0,667 (40/60) | 0,519 [0,377; 0,664] |
| A1 · − chuẩn hoá văn bản (NFKC/teencode/emoji) | **0,564** | [0,489; 0,650] | 0,620 | 0,735 | 0,684 (39/57) | 0,500 [0,369; 0,651] |
| A2 · − đặc trưng phong cách (caps/giá/‖ → mô hình người nói) | **0,576** | [0,512; 0,682] | 0,633 | 0,735 | 0,643 (45/70) | 0,545 [0,397; 0,704] |
| A3 · − nhãn LLM buổi thứ tư | **0,557** | [0,487; 0,614] | 0,557 | 0,608 | 0,462 (43/93) | 0,451 [0,326; 0,540] |
| A4 · − bộ biên soạn (chỉ dữ liệu thật) | **0,365** | [0,321; 0,425] | 0,402 | 0,677 | 0,875 (7/8) | 0,331 [0,288; 0,447] |
| A5 · − gold 2 buổi train (chỉ biên soạn + LLM) | **0,582** | [0,505; 0,646] | 0,640 | 0,730 | 0,710 (44/62) | 0,429 [0,317; 0,584] |
| A6 · + từ chối trả lời (ngưỡng chọn trong train) | **0,492** | [0,440; 0,562] | 0,541 | 0,713 | 0,652 (30/46) | 0,541 [0,386; 0,682] |
| A7 · bộ nhãn 6 lớp (chấm trên không gian 6 lớp) | **0,574** | [0,463; 0,664] | 0,574 | 0,850 | 0,548 (40/73) | 0,455 [0,240; 0,683] |
| A8 · bộ nhãn 11 lớp, gộp về 6 khi chấm (cùng thang với A7) | **0,609** | [0,490; 0,700] | 0,609 | 0,880 | 0,667 (40/60) | 0,626 [0,317; 0,823] |

macro-F1 từng buổi live (bất định thật nằm ở đây, không ở KTC bootstrap):

| Hệ thống | `1NMt8BChQrI` | `47oGShxf80A` | `gT0LDiBta2k` |
|---|---|---|---|
| A0 · đầy đủ (chuẩn hoá + phong cách + 11 lớp + mọi nguồn) | 0,372 | 0,635 | 0,525 |
| A1 · − chuẩn hoá văn bản (NFKC/teencode/emoji) | 0,367 | 0,630 | 0,518 |
| A2 · − đặc trưng phong cách (caps/giá/‖ → mô hình người nói) | 0,419 | 0,642 | 0,592 |
| A3 · − nhãn LLM buổi thứ tư | 0,326 | 0,623 | 0,497 |
| A4 · − bộ biên soạn (chỉ dữ liệu thật) | 0,412 | 0,260 | 0,479 |
| A5 · − gold 2 buổi train (chỉ biên soạn + LLM) | 0,352 | 0,611 | 0,555 |
| A6 · + từ chối trả lời (ngưỡng chọn trong train) | 0,372 | 0,445 | 0,525 |
| A7 · bộ nhãn 6 lớp (chấm trên không gian 6 lớp) | 0,189 | 0,708 | 0,513 |
| A8 · bộ nhãn 11 lớp, gộp về 6 khi chấm (cùng thang với A7) | 0,239 | 0,788 | 0,556 |

## Đường đánh đổi độ phủ ↔ độ chính xác (tuỳ chọn từ chối trả lời)

| Ngưỡng | macro-F1 | Accuracy | Độ phủ nhãn hành động | Precision | KTC95 |
|---:|---:|---:|---:|---:|---|
| 0,00 | 0,565 | 0,741 | 0,153 | 0,667 | [0,541; 0,773] |
| 0,30 | 0,570 | 0,741 | 0,145 | 0,702 | [0,573; 0,805] |
| 0,40 | 0,587 | 0,741 | 0,132 | 0,750 | [0,618; 0,848] |
| 0,45 | 0,560 | 0,741 | 0,120 | 0,745 | [0,605; 0,848] |
| 0,50 | 0,523 | 0,733 | 0,112 | 0,750 | [0,606; 0,854] |
| 0,60 | 0,577 | 0,730 | 0,084 | 0,879 | [0,727; 0,952] |
| 0,70 | 0,545 | 0,700 | 0,076 | 0,900 | [0,744; 0,965] |
| 0,80 | 0,488 | 0,674 | 0,056 | 0,909 | [0,722; 0,975] |

## F1 từng lớp — hệ thống tốt nhất

Hệ thống: **A8 · bộ nhãn 11 lớp, gộp về 6 khi chấm (cùng thang với A7)**

| Lớp | P | R | F1 | Nhãn thật | Lần dự đoán |
|---|---:|---:|---:|---:|---:|
| `hoi_gia` | 0,812 | 0,929 | **0,867** | 14 | 16 |
| `hoi_size` | 0,333 | 0,667 | **0,444** | 3 | 6 |
| `che_dat` | 0,167 | 0,200 | **0,182** | 5 | 6 |
| `chot_don` | 0,833 | 0,455 | **0,588** | 33 | 18 |
| `van_chuyen` | 0,643 | 0,643 | **0,643** | 14 | 14 |
| `khac` | 0,919 | 0,944 | **0,931** | 324 | 333 |

Ma trận nhầm lẫn (hàng = nhãn thật, cột = nhãn đoán):

| thật \ đoán | `hoi_gia` | `hoi_size` | `che_dat` | `chot_don` | `van_chuyen` | `khac` |
|---|---|---|---|---|---|---|
| `hoi_gia` | 13 | · | · | · | · | 1 |
| `hoi_size` | · | 2 | · | · | · | 1 |
| `che_dat` | 1 | · | 1 | · | · | 3 |
| `chot_don` | · | · | · | 15 | · | 18 |
| `van_chuyen` | 1 | · | · | · | 9 | 4 |
| `khac` | 1 | 4 | 5 | 3 | 5 | 306 |

