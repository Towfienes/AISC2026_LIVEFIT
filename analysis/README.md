# analysis/ — Notebook phân tích

Quy tắc (HARNESS.md §6): notebook **không chứa logic** — logic ở `src/livelift/analysis/`,
notebook chỉ gọi hàm và vẽ. Strip output trước khi commit.

| Thư mục | Nội dung | Khóa theo tiền đăng ký? |
|---|---|---|
| `calibration/` | Hiệu chỉnh tuần 3: đo t_mix (impulse response sau bỏ ghim), phân phối thời gian ở lại, ICC cấp phiên, CV thực tế → chốt độ dài khối + burn-in, viết lại bảng lực | Quy trình có trong tiền đăng ký |
| `power/` | Bảng MDE hai kịch bản (không/có đối tác) từ `livelift.analysis.power` | Có |
| `confirmatory/` | Phân tích khẳng định sau đóng băng dữ liệu — chạy đúng theo PREREGISTRATION.md, ghi `analysis_run` vào DB kèm commit hash | **CÓ — không sửa sau tuần 6** |
| `exploration/` | Phân tích khám phá hậu nghiệm — mọi kết quả ở đây phải ghi nhãn "khám phá" | Không |

## Quy trình hiệu chỉnh tuần 3 (bốn phép đo — kế hoạch §7)

1. **t_mix / hàm suy giảm hiệu ứng lưu**: với mỗi lần bỏ ghim, vẽ CTR theo phút sau đó;
   thời điểm về mức nền = cận trên cho burn-in cần thiết.
2. **Phân phối thời gian ở lại**: trung vị + p75 (YouTube: ước lượng từ chuỗi
   `concurrentViewers` + luồng vào; ghi rõ phương pháp).
3. **ICC cấp phiên** (không phải tương quan khối liền kề — xem báo cáo nghiên cứu L8):
   mô hình thành phần phương sai y_khối = phiên + dư; ρ_phiên đưa vào design effect.
4. **CV trong-phiên của y theo khối**, riêng cho từng độ dài khối thử → nạp vào
   `livelift.analysis.power.PowerInputs` và tái sinh bảng MDE.

Sản phẩm bàn giao: `calibration/tuan3-hieu-chinh.ipynb` + quyết định độ dài khối/burn-in
ghi vào PREREGISTRATION.md trước tuần 6.
