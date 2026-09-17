# Hướng dẫn sử dụng LiveLift — tự tay bấm thử từ đầu đến cuối

*Viết cho người dùng, không phải cho lập trình viên. Các bước gốc đã được bấm
thật trên hệ thống đang chạy ngày 11/09/2026 và chụp ảnh lại. Nếu bạn bấm ra
khác, đó là lỗi — báo lại để sửa.*

*Cập nhật 17/09/2026 sau đợt kiểm toán: nhãn nút, câu thông báo và ba mục mới
(mục 10 bộ thu bình luận · mục 11 nhập đơn hàng · mục 12 nguồn Mô phỏng) được
đối chiếu với mã nguồn, **chưa chụp ảnh lại**. Ảnh trong tài liệu là giao diện
ngày 11/09 — bố cục có thể đã khác, cứ bấm theo tên nút trong chữ.*

---

## 0. Trả lời thẳng trước khi bắt đầu

**LiveLift là một WEB APP — chạy trong trình duyệt.**

- **Không phải app điện thoại.** Không có trên CH Play hay App Store, không cài
  gì cả.
- Bạn mở nó như mở Facebook: gõ địa chỉ vào thanh địa chỉ của Chrome/Edge.
- Địa chỉ để mở: **http://localhost:3000**

Hệ thống có **hai phần** cùng chạy trên máy bạn:

| Phần | Là gì | Cổng | Bạn có mở trực tiếp không? |
|---|---|---|---|
| **Máy chủ (API)** | Nơi giữ dữ liệu, bốc thăm lịch, tính kết quả | `8000` | Không. Nó chạy ngầm. |
| **Giao diện web** | Những màn hình bạn nhìn và bấm | `3000` | **Có** — đây là thứ bạn mở |

Nếu máy chủ tắt, giao diện web vẫn mở được nhưng chỉ xem được dữ liệu mô phỏng:
trang chủ hiện dải đỏ *"Chưa kết nối được máy chủ — bạn vẫn xem thử được bằng dữ
liệu mô phỏng."*, và thẻ **03 · Phân tích video có sẵn** bị mờ đi kèm dòng
*"Tạm khoá: cần máy chủ LiveLift đang chạy để tải và phân tích video."*

### Máy nào cần gì

| Người | Thiết bị | Mở màn hình nào |
|---|---|---|
| **Chủ shop / người trợ live** | Laptop hoặc máy bàn, màn ≥ 1366×768 | `http://localhost:3000/desk` |
| **Người dẫn (host)** | Màn hình phụ / TV đặt trước mặt người dẫn | `http://localhost:3000/host?session=<mã phiên>` — mở bằng nút **"Mở màn hình người dẫn"** ở bước 4 của *Chuẩn bị phiên*, link đã gắn sẵn mã phiên |
| **Người xem** | Điện thoại của họ | Chỉ bấm **link đo** bạn dán vào bình luận ghim |

> **Chưa có đăng nhập.** Ai mở được địa chỉ này là vào thẳng. Vì vậy hiện chỉ
> nên chạy trên **máy cá nhân** hoặc **mạng nội bộ (Wi-Fi nhà/văn phòng)**, chưa
> được đưa lên Internet công khai. Xem mục 8.

---

## 1. Bật hệ thống lên (chỉ làm 1 lần mỗi ngày)

Mở **hai cửa sổ dòng lệnh**, mỗi cửa sổ chạy một lệnh rồi **để yên đó** (đóng
cửa sổ là tắt hệ thống).

**Cửa sổ 1 — máy chủ:**

```
cd D:\AISC2026\livelift
.venv\Scripts\python -m uvicorn livelift.api.main:app --port 8000
```

**Cửa sổ 2 — giao diện web:**

```
cd D:\AISC2026\livelift\web
npm run dev
```

> **Cách khác, một lệnh duy nhất (nếu máy đã cài Docker Desktop):**
> `cd D:\AISC2026\livelift` rồi `docker compose up -d`. Khi đó mở bằng địa chỉ
> **http://localhost** (không có `:3000`), và dữ liệu được lưu vào cơ sở dữ liệu
> thật nên **không mất khi tắt máy** — đây là cách nên dùng trước buổi trình bày.
> Mọi bước bấm nút dưới đây giống hệt nhau ở cả hai cách.

### Kiểm tra đã chạy chưa — không cần gõ lệnh

Mở **http://localhost:3000**. Bạn phải thấy đúng màn hình này:

![Trang chính LiveLift](img/l1-01-trang-chu.png)

Trang chủ có ba thẻ: **01 · Tôi có buổi live** (nút *"Trả lời 3 câu hỏi →"*),
**02 · Xem thử 30 giây** và **03 · Phân tích video có sẵn**. Dấu hiệu **máy chủ
đã chạy**: không có dải cảnh báo đỏ/cam nào, và ô nhập link YouTube ở thẻ **03**
gõ được (nút **"Phân tích →"** sáng lên khi đã dán link).

Trang chủ hỏi máy chủ đúng một câu (`/health`) và cho **ba câu trả lời khác
nhau** — đọc câu nào thì làm việc đó:

| Trang hiện gì | Nghĩa là | Việc cần làm |
|---|---|---|
| Không có dải cảnh báo nào, ô nhập ở thẻ **03** gõ được | **SỐNG** — máy chủ chạy, kho dữ liệu bình thường | dùng bình thường |
| Dải **cam**: *"Kho dữ liệu đang trục trặc — dữ liệu mới có thể không được lưu."* kèm câu *"Việc cần làm: chỉ xem thử, chưa lên sóng thật cho tới khi kho trở lại bình thường."* (bấm **"Chi tiết kỹ thuật (cho người quản trị máy chủ)"** để xem nguyên văn lý do máy chủ nói), và chip **KHO SUY GIẢM** ở góc phải thanh trên | **SUY GIẢM** — máy chủ vẫn trả lời nhưng dữ liệu mới có thể không lưu được. Thẻ 03 bị khoá; *"Bắt đầu xem thử"* chạy bản mô phỏng ngoại tuyến, không ghi gì xuống máy chủ | xem được, **đừng lên sóng thật**; nhờ người kỹ thuật bật lại cơ sở dữ liệu rồi tải lại trang |
| Dải **đỏ**: *"Chưa kết nối được máy chủ — bạn vẫn xem thử được bằng dữ liệu mô phỏng."* và chip **MẤT KẾT NỐI** | **CHẾT** — gọi hai lần, 4 giây mỗi lần, đều không ai trả lời | cửa sổ 1 chưa chạy — bật lại nó |

Dòng cam *"Máy chủ đang chạy bình thường — mọi chức năng sẵn sàng. Chỉ có điều nó
trả lời chậm (… giây)…"* là trạng thái **SỐNG**, chỉ là máy chậm — không phải mất
kết nối, không cần làm gì.

**Chip KHO ở góc phải thanh trên** cho biết kho đang chứa dữ liệu gì (có mặt ở
mọi trang, trừ màn người dẫn):

| Chip | Nghĩa là |
|---|---|
| **KHO TRỐNG** | Máy chủ chưa có phiên nào |
| **KHO: DỮ LIỆU MẪU** | Kho chỉ có dữ liệu mẫu (phiên mô phỏng, buổi nạp sẵn). Chip cũng giữ nhãn này khi chưa hỏi được máy chủ — nhãn an toàn, không phải xác nhận |
| **KHO: DỮ LIỆU THẬT** | Kho chỉ có phiên thật |
| **KHO: THẬT + MẪU** | Kho có cả hai — từng phiên mẫu đeo nhãn riêng (*dữ liệu mẫu* / *DEMO — dữ liệu mẫu*) |
| **KHO: CHƯA ĐẾM ĐƯỢC** | Kho dữ liệu không trả lời nên chưa đếm được phiên |

> ⚠️ **Quan trọng — dữ liệu có mất khi tắt máy chủ không?** Chạy bằng hai cửa
> sổ lệnh như trên thì kho nằm trong bộ nhớ, nhưng **ảnh chụp tự động đã bật sẵn**:
> cứ 30 giây máy chủ ghi toàn bộ dữ liệu ra `data/snapshot/livelift-store.json`
> và tự nạp lại khi bật lên. Tắt bằng **Ctrl+C** trong cửa sổ 1 thì máy chủ chụp
> lần cuối trước khi tắt; máy chủ chết đột ngột (đóng cửa sổ, mất điện, treo
> máy) thì **mất tối đa khoảng 30 giây** dữ liệu cuối. Buổi live thật nên chạy
> bằng Docker (cơ sở dữ liệu PostgreSQL) — đó mới là kho bền vững. Xem mục 8.

---

## 2. Bản đồ màn hình — thanh trên cùng

Mọi màn hình đều có thanh điều hướng ở trên cùng bên trái. Sáu chữ, bấm vào là
chuyển màn:

| Bấm | Mở màn hình gì | Dành cho ai |
|---|---|---|
| **Bắt đầu** | Màn hình bắt đầu, các cửa vào | Người mới |
| **Chuẩn bị phiên** | Wizard 4 bước chuẩn bị một buổi live thí nghiệm | Chủ shop |
| **Bàn trợ live** | Màn hình vận hành khi đang lên sóng | Người trợ live |
| **Xem lại phiên** | Tua lại một buổi đã xong | Ai cũng được |
| **Kết quả & chiến lược** | Con số khoa học tổng hợp | Chủ shop, giám khảo |

Màn hình cỡ lớn cho **người dẫn** không nằm trên thanh trên cùng nữa (để người
vận hành khỏi mở nhầm màn bị làm mù): mở nó bằng nút **"Mở màn hình người
dẫn"** ở bước 4 của wizard Chuẩn bị phiên. Nút này mở địa chỉ
`/host?session=<mã phiên>` — màn người dẫn chỉ chiếu **đúng** phiên đó (xem bước
3.8).

---

## 3. LUỒNG 1 — Xem thử 30 giây (làm cái này trước tiên)

Mục đích: thấy hệ thống chạy ra sao mà chưa cần lên sóng thật.

### Bước 1.1 — Mở trang chính

**Bấm gì:** gõ `localhost:3000` vào thanh địa chỉ, Enter.
**Chuyện gì xảy ra:** hiện 3 thẻ đánh số 01–02–03 (ảnh ở mục 1 là bản cũ, thứ
tự thẻ đã đổi).

### Bước 1.2 — Bấm nút "Bắt đầu xem thử"

**Bấm gì:** nút **"Bắt đầu xem thử"** (lúc trang vừa mở, nút tạm ghi *"Đang
kiểm tra máy chủ…"* — chờ vài giây).
**Ở đâu:** thẻ giữa, **02 · Xem thử 30 giây**.

**Chuyện gì xảy ra:** nút đổi chữ thành **"Đang tạo dữ liệu…"** và bị mờ đi —
đó là dấu hiệu hệ thống đang làm việc, đừng bấm lại. Máy chủ tạo vài phiên
**dữ liệu mẫu** (đã kết thúc) và một phiên mẫu *đang phát*.

![Nút đang tạo dữ liệu](img/l1-02-dang-tao-du-lieu.png)

**Nếu lỗi:** hiện dòng đỏ *"Không tạo được dữ liệu mô phỏng — kiểm tra máy chủ
rồi thử lại."* ⇒ cửa sổ 1 (máy chủ) đã tắt. Bật lại rồi tải lại trang. (Khi máy
chủ tắt hoặc kho đang suy giảm, nút mở thẳng bản phát lại mô phỏng ngoại tuyến
thay vì tạo dữ liệu.)

### Bước 1.3 — Trang tự chuyển sang màn Xem lại phiên

Sau khoảng 5–10 giây trang **tự nhảy** sang màn **Xem lại phiên**, mở đúng một
phiên mẫu vừa tạo. Bạn không phải bấm gì.

![Màn phát lại vừa mở](img/l1-03-phat-lai-mo-phong.png)

*(Ảnh trên là bản 11/09, khi đó thanh thời gian còn đứng ở `00:00` và các khung
trống.)* Nay khi mở:

- Cạnh tiêu đề có huy hiệu **DEMO — dữ liệu mẫu** và dải cam *"PHÁT LẠI DỮ LIỆU
  MẪU — phiên mô phỏng, không phải buổi live thật"* — phiên do máy sinh ra,
  không phải buổi live nào.
- Thanh thời gian đã **tự tua** tới phút đầu tiên có số liệu, dòng nhắc dưới
  hàng điều khiển ghi *"Đã tua sẵn tới …, phút đầu có số liệu — bấm Phát để xem
  tiếp."*

### Bước 1.4 — Bấm "Phát" để xem nó chạy

**Bấm gì:** nút **▶ Phát**. Tốc độ mặc định là **30x**; muốn nhanh hơn thì bấm
**60x** (một buổi 60 phút xem hết trong khoảng 1 phút). Các nút tốc độ: 1x · 4x ·
16x · 30x · 60x.
**Ở đâu:** hàng điều khiển ngay dưới tiêu đề, cạnh ô chọn phiên.

**Chuyện gì xảy ra:** đồng hồ chạy, nút đổi thành **❚❚ Tạm dừng**, biểu đồ
**NHỊP PHIÊN (BẢN GHI)** vẽ tiếp đường, và vạch vị trí trên dải **BẬT/TẮT** trượt
dần sang phải theo thời gian.

![Phát lại đang chạy](img/l1-04-phat-lai-dang-chay.png)

**Đọc màn này thế nào:**

- **Dải BẬT/TẮT** (dải ô tím/xám): mỗi ô là một *khối* khoảng 5 phút. Tím = khối
  **BẬT** (hệ thống được phép điều khiển việc ghim sản phẩm); xám = khối **TẮT**
  (đội vận hành làm như thường lệ). Chính việc bốc thăm tím/xám này biến buổi
  live thành thí nghiệm.
- **HÀNH ĐỘNG GỢI Ý**: các thẻ đề xuất "nên ghim sản phẩm nào". Ở màn phát lại
  chúng chỉ để xem (ghi chú *"Bản ghi phát lại"*), không bấm được.
- **Khung "Thử: nếu hết hàng"** (cạnh cột thẻ): tick vào một sản phẩm là coi như
  nó **hết hàng** (dòng đó gạch ngang, ghi **HẾT HÀNG**), thẻ gợi ý xếp lại ngay
  — không đụng gì tới dữ liệu gốc. Khung không có sản phẩm nào thì nó nói lý do
  (ví dụ *"Danh mục chưa có sản phẩm nào."*).
- **RADAR BÌNH LUẬN** (5 phút quanh vị trí phát): phân loại bình luận theo ý
  định (hỏi giá, chốt đơn…). Chưa tua tới bình luận đầu tiên thì khung ghi
  *"Chưa tới bình luận đầu tiên — bản ghi có bình luận từ …"* kèm nút **Tua tới
  …**; buổi không có bình luận nào thì ghi *"Buổi này không ghi lại bình luận
  nào."* Muốn thấy radar trên chat thật, làm Luồng 2.

> **Dải cam cạnh tiêu đề** luôn hiện để bạn không nhầm bản ghi với buổi đang
> phát trực tiếp — và nó nói đúng loại dữ liệu đang xem: *"PHÁT LẠI DỮ LIỆU
> THẬT — ghi ngày …"* với phiên thật, *"PHÁT LẠI DỮ LIỆU MẪU — phiên mô phỏng,
> không phải buổi live thật"* với phiên mẫu, và *"PHÁT LẠI DỮ LIỆU MÔ PHỎNG — …"*
> khi trang đang chạy bản ghi mô phỏng ngoại tuyến (chưa kết nối được máy chủ,
> hoặc chưa có buổi nào kết thúc).

---

## 4. LUỒNG 2 — Phân tích một buổi live YouTube có sẵn

Mục đích: đưa một buổi live **của bất kỳ ai** (đã kết thúc, còn chat replay) vào
hệ thống để xem nhịp bình luận và radar ý định trên **dữ liệu thật**.

> Kết quả luồng này luôn được dán nhãn **QUAN SÁT** — mô tả buổi đó, **không**
> có con số nhân quả. Lý do: không ai can thiệp ngược thời gian vào một video đã
> quay xong được, nên không có nhánh đối chứng để so.

### Bước 2.1 — Dán đường dẫn

**Bấm gì:** bấm vào ô nhập của thẻ **03**, dán link YouTube.
**Ở đâu:** thẻ **03 · Phân tích video có sẵn** (bên phải), ô có chữ mờ
`https://www.youtube.com/watch?v=…`.

Ví dụ đã thử thật: `https://www.youtube.com/watch?v=ZU_0QJzsR6w`

![Đã dán link vào ô](img/l2-01-dan-link.png)

### Bước 2.2 — Bấm "Phân tích"

**Bấm gì:** nút **"Phân tích →"** ngay dưới ô nhập (nút chỉ sáng khi ô đã có
link).

**Chuyện gì xảy ra:** nút đổi thành **"Đang xử lý…"**, và ngay dưới hiện một dòng
trạng thái có chấm nhấp nháy chạy lần lượt qua các chặng:
*Đang xếp hàng… → **Đang tải chat…** → Đang phân tích… → Xong — đang mở kết
quả…*.

![Đang tải chat](img/l2-02-dang-xu-ly.png)

**Chờ bao lâu:** buổi live nhiều bình luận thì lâu hơn. Buổi trong ảnh
(6.586 bình luận / 117 phút) mất khoảng **một phút**. Cứ để yên trang.

**Nếu lỗi:**

| Dòng chữ bạn thấy | Nghĩa là | Làm gì |
|---|---|---|
| *"Máy chủ không nhận yêu cầu — kiểm tra lại đường dẫn: phải là một buổi live YouTube ĐÃ KẾT THÚC."* | Máy chủ đang chạy nhưng link sai, hoặc buổi live chưa kết thúc | Kiểm tra link |
| *"Không gửi được yêu cầu vì máy chủ không trả lời — bật lại tiến trình API rồi thử lại."* | Máy chủ tắt | Bật lại cửa sổ 1 |
| Dòng đỏ có chữ *không có chat* | Video không có chat replay | Chọn video khác |
| *"YouTube yêu cầu xác minh không phải bot"* | YouTube chặn | Xem `docs/HUONG-DAN-TEST.md` mục 4 |

### Bước 2.3 — Trang tự nhảy sang Xem lại phiên, đúng buổi vừa phân tích

Khi xong, trang tự chuyển sang màn **Xem lại phiên** với địa chỉ
`/replay?session=<mã buổi>` — và mở **đúng buổi bạn vừa phân tích**. Ô chọn buổi
ở góc trái đứng sẵn ở dòng **"Phân tích: …"** kèm tên buổi live.

![Sau khi phân tích xong, đang mở nhầm buổi mô phỏng](img/l2-03-sau-khi-xong.png)

*(Ảnh trên chụp ngày 11/09, lúc còn lỗi: địa chỉ đúng nhưng ô chọn vẫn ở buổi
mô phỏng. Lỗi này — giới hạn #5 cũ — đã sửa, xem mục 8.)*

Nếu link trỏ tới một buổi không có hoặc chưa kết thúc, trang **không lặng lẽ đổi
buổi** mà ghi rõ, ví dụ *"Không tìm thấy buổi trong link — đang mở buổi đã kết
thúc gần nhất."*

### Bước 2.4 — Muốn xem buổi khác: chọn trong ô thả xuống

**Bấm gì:** ô thả xuống ở **góc trái** hàng điều khiển, ngay bên trái nút "Phát".
Buổi phân tích là dòng bắt đầu bằng **"Phân tích: …"**; phiên mẫu có đuôi
*"· dữ liệu mẫu"*. Chọn buổi khác thì địa chỉ trên thanh URL đổi theo — chép link
đó gửi người khác là mở đúng buổi.

![Đã chọn đúng buổi vừa phân tích](img/l2-04-chon-buoi-trong-dropdown.png)

Đúng buổi rồi thì: tổng thời lượng bên phải khớp buổi đó (ví dụ `01:58:00`), và
khung **Radar bình luận** có bình luận tiếng Việt thật.

### Bước 2.5 — Kéo thanh thời gian tới phút đông khách

**Bấm gì:** kéo **thanh trượt dài** ở giữa hàng điều khiển sang phải; hoặc bấm
**"Phát"** rồi để nó chạy.

![Tua tới phút 53 — radar và feed có dữ liệu thật](img/l2-05-tua-den-phut-dong-khach.png)

Giờ bạn thấy đủ:

- **NHỊP PHIÊN**: đường xanh lá = số bình luận mỗi phút. Chỗ nhô cao là lúc
  khách sôi nổi nhất.
- **RADAR BÌNH LUẬN**: cột màu chồng, mỗi màu một ý định (Hỏi giá / Hỏi size /
  Chê đắt / Chốt đơn / Vận chuyển / Khác).
- **Bình luận trực tiếp**: từng dòng chat thật, mỗi dòng có nhãn ý định bên
  phải. Dòng nào có huy hiệu **"PII đã ẩn"** nghĩa là hệ thống đã **che số điện
  thoại / địa chỉ / tên riêng** trước khi lưu — bản gốc không bao giờ chạm ổ
  cứng.
- Nút **"Tạm dừng cuộn"** ở góc phải khung chat: bấm để giữ màn hình đứng yên
  khi bạn đang đọc.

> **Biểu đồ không vẽ đường "Người xem" và "Lượt bấm"** cho buổi này — thay vào
> đó là dải **THIẾU nguồn** kèm lý do: buổi live của người khác không cho biết số
> người xem, và buổi đó không đi qua link đo nào của bạn. Đây là *thiếu nguồn*,
> không phải bằng 0 — xem mục Ma trận tín hiệu ở Luồng 4.

### Bước 2.6 — Mở báo cáo của đúng buổi đó

**Bấm gì:** nút **"Báo cáo phiên →"** ở **góc phải trên cùng**.
Chi tiết cách đọc báo cáo ở **Luồng 4**.

---

## 5. LUỒNG 3 — Chạy một phiên thí nghiệm thật của bạn

Đây là phần chính của sản phẩm. Từ 09/2026 trang này là **wizard từng-bước-một**:
màn hình chỉ hiện MỘT bước mỗi lúc, có dải 4 chấm tiến độ ở trên (bước xong bấm
lại được để sửa). Bốn bước **phải theo đúng thứ tự** — vì lịch bốc thăm BẬT/TẮT
bắt buộc phải sinh **trước khi** lên sóng thì kết quả mới kiểm chứng được. Mỗi
bước có dòng **"Vì sao cần bước này?"** bấm vào là ra giải thích ngắn. Lỡ tắt
tab giữa chừng cũng không mất: mở lại trang là wizard tự nhảy về đúng bước của
phiên đang chuẩn bị.

> Ảnh chụp trong mục này thuộc giao diện bản trước (4 thẻ trải dọc) — bố cục đã
> đổi thành từng-bước-một nhưng **tên các nút giữ nguyên**, bấm theo tên nút là
> đúng.

**Bấm gì để vào:** chữ **"Chuẩn bị phiên"** trên thanh trên cùng.

### Bước 3.1 — Khai báo sản phẩm sẽ bán

![Bước 1 — danh mục sản phẩm](img/l3-01-buoc1-danh-muc.png)

**Ở đâu:** bước **1/4 — Sản phẩm**.

Nếu bạn đã bấm "Xem thử" ở Luồng 1 thì đã có sẵn vài sản phẩm mẫu. Thêm sản phẩm
của bạn (mọi ô đều có nhãn; **không còn ô "Mã SP"** — mã hệ thống tự sinh từ
tên, ví dụ "Áo khoác dù 2 lớp" → `ao-khoac-du-2-lop`):

**Bấm gì:** điền form "Thêm sản phẩm mới" rồi bấm **"Thêm sản phẩm"**. Chưa có
gì để điền thì bấm **"Dùng sản phẩm mẫu"** — form tự điền một sản phẩm demo.

| Ô | Điền gì | Ví dụ |
|---|---|---|
| Tên sản phẩm * | tên hiển thị, có dấu | `Áo thun cotton 100%` |
| Giá bán (đ) | số, không dấu chấm | `199000` |
| Link trang sản phẩm thật | trang Shopee/website của bạn | `https://shopee.vn/ao-thun` |
| Giá vốn, Tồn kho | trong mục "Thêm chi tiết — tuỳ chọn" | `80000`, `50` |

![Đã điền 5 ô sản phẩm](img/l3-02-them-san-pham.png)

### Bước 3.2 — Dán link trang sản phẩm thật (bước hay bị bỏ quên)

Sau khi thêm, sản phẩm hiện thành một dòng kèm chip trạng thái: **"✓ link đo
sẵn sàng"** (xanh) hoặc **"⚠ chưa có link"** (vàng, kèm câu *"sản phẩm này sẽ
không đo được lượt nhấp"*) — thiếu link là biết NGAY LÚC NHẬP, không đợi tới
lúc lên sóng. Bên dưới mỗi dòng có một ô nhập dài.

**Bấm gì:** bấm vào ô đó, dán **địa chỉ trang bán sản phẩm thật** của bạn
(Shopee / TikTok Shop / website riêng). Phải bắt đầu bằng `http://` hoặc
`https://`.

![Đã dán link trang sản phẩm](img/l3-03-link-san-pham.png)

**Vì sao bắt buộc:** hệ thống sẽ sinh một **link đo** riêng cho từng sản phẩm.
Bạn dán link đo (không phải link gốc) vào bình luận ghim; mỗi lượt khách bấm
được ghi lại và quy về đúng khối BẬT/TẮT đang chạy. **Đó chính là con số quyết
định kết quả thí nghiệm.** Sản phẩm không có link ⇒ không đo được gì.

**Nếu lỗi:** ô viền đỏ + dòng *"Link không hợp lệ — cần URL đầy đủ bắt đầu bằng
http:// hoặc https://"* ⇒ bạn quên phần `https://` ở đầu.

**Xong bước 1:** bấm **"Xong, sang bước 2"**.

### Bước 3.3 — Thông tin buổi live (tạo phiên)

![Bước 2 — tạo phiên live](img/l3-04-buoc2-tao-phien.png)

Ở bước **2/4 — Buổi live**, ba lựa chọn đều là **thẻ bấm** (không còn dropdown),
xong bấm **"Tạo phiên"**:

| Mục | Chọn/điền gì |
|---|---|
| Tên buổi live | tuỳ chọn, ví dụ `Phiên live tối thứ Bảy` |
| Nền tảng | thẻ `YouTube Live` hoặc `Facebook Live` |
| Thời lượng | nút `30/60/90/120 phút` — **90 phút gắn nhãn "khuyên dùng"** |
| Chế độ | thẻ **Tự ghim** (khuyên dùng) hoặc **Chỉ gợi ý** |

> **Hai chế độ nghĩa là gì (giải thích ngay trên thẻ):**
> - **Tự ghim** — hệ thống tự ghim sản phẩm tốt nhất khi đến lượt khối BẬT
>   (bộ thực thi tự động phía máy chủ, có từ 12/09); bạn chỉ theo dõi. Ở chế độ
>   này nút *Thực hiện* trên thẻ gợi ý bị khoá — vì máy đã bấm thay bạn:
>
> ![Chế độ Tự động — nút Thực hiện bị mờ, không bấm được](img/l3-08b-che-do-tu-dong-nut-mo.png)
>
> - **Chỉ gợi ý** — hệ thống chỉ đề xuất, sản phẩm chỉ được ghim khi bạn bấm
>   *Thực hiện* trên bàn trợ live. Dùng khi live nhờ phòng đối tác.
>
> Chế độ **không đổi được sau khi đã tạo phiên** — muốn đổi thì bấm "Huỷ phiên
> nháp, sửa lại" (chỉ được trước khi lên sóng).

> **Vì sao nên ≥ 90 phút:** phiên càng ngắn càng ít khối, kết quả càng yếu.
> Chọn dưới 90 phút, wizard cảnh báo **ngay lúc chọn**, và khi bốc thăm máy chủ
> sẽ nói thẳng mức đảm bảo thật của lịch:
>
> ![Cảnh báo lịch quá ngắn khi chọn 30 phút](img/l3-05b-canh-bao-phien-ngan.png)

### Bước 3.4 — Bốc thăm lịch BẬT/TẮT (trước khi lên sóng)

**Ở đâu:** bước **3/4 — Bốc thăm**.

**Bấm gì:** đúng MỘT nút **"Bốc thăm lịch"** (tên đầy đủ: *Bốc thăm lịch
BẬT/TẮT*). Muốn chỉnh **Độ dài khối (phút)** hay **Mã bốc thăm (seed)** thì mở
mục **"Tuỳ chọn nâng cao — mặc định là đủ"** trước khi bốc (điền seed `42` nếu
muốn lịch lặp lại được y hệt cho lần sau).

![Lịch đã bốc — 16 khối, BẬT 8 / TẮT 8, seed 42](img/l3-05-buoc3-lich-da-boc.png)

**Chuyện gì xảy ra:** hiện dòng tóm tắt `16 khối, phần lớn ~5 phút · BẬT 8 /
TẮT 8`, dải
khối tím/xám — toàn bộ kịch bản BẬT/TẮT của buổi live, **đã khoá** — và một
khung **"Mã bằng chứng"**: dấu kiểm chứng của lịch, chốt TRƯỚC giờ phát; ai
cũng có thể sinh lại lịch và đối chiếu mã này — khớp nghĩa là **không ai sửa
lịch giữa chừng** (đây là bằng chứng giám khảo sẽ hỏi). Dòng mờ bên dưới ghi
*mã kiểm chứng lịch (seed)*.

**Nếu thấy khung cam "Máy chủ lưu ý về lịch vừa bốc":** hệ thống đang nói thật
rằng lịch này quá ngắn để đảm bảo cân bằng, kèm gợi ý sửa (phiên dài hơn hoặc
khối ngắn hơn). Bấm "Bốc lại lịch khác" sau khi chỉnh, hoặc chấp nhận và đi
tiếp.

### Bước 3.5 — Checklist trước giờ G & Bắt đầu phát sóng

Ở bước **4/4 — Lên sóng**, wizard soát hộ bạn một checklist trước giờ G:

- **Lịch BẬT/TẮT đã bốc và niêm phong** — kèm số khối;
- **Link đo** — tạo sẵn cho mọi sản phẩm có link, mỗi dòng kèm nút
  **"Chép link"** (bấm xong đổi thành *"Đã chép ✓"*), và một ô tự đánh dấu
  *"Tôi đã dán (hoặc sẽ dán ngay khi lên sóng) link đo vào bình luận ghim"*;
- **Nguồn bình luận** — khung **Bộ thu bình luận** ngay trong checklist: chọn
  nền tảng, dán link buổi live, bấm **"Bật bộ thu"**. Bật trước giờ phát cũng
  được — bộ thu chờ buổi live bắt đầu. Chi tiết ở **mục 10**;
- **Màn hình người dẫn** — nút **"Mở màn hình người dẫn ↗"** (mở
  `/host?session=<mã phiên>` ở tab mới) kèm hướng dẫn kéo sang màn phụ/TV, bấm
  F11;
- **Dữ liệu hệ thống sẽ ghi lại** — các nguồn còn lại (ví dụ số người xem, đơn
  hàng, tim và quà): trạng thái thật lúc này bằng lời thường (trước giờ phát,
  các dữ liệu này chưa có là bình thường).

Cạnh nút phát có dòng đếm *"Còn N việc chưa xong"* — chỉ để nhắc, không chặn bấm.

![Bước 4 — đang phát, có link đo](img/l3-06-buoc4-dang-phat-va-link-do.png)

**Bấm gì:** nút **"▶ Bắt đầu phát sóng"**. Trang tự chuyển sang **bàn trợ live**
đúng phiên vừa tạo — không phải tìm phiên trong danh sách.

> **Dòng "N/M sản phẩm chưa có link trang sản phẩm nên không đo được lượt bấm
> (…) — bổ sung ở bước 1."** là bình thường nếu bạn cố ý bỏ trống: chỉ những sản
> phẩm đã dán link ở bước 3.2 mới có link đo.

> ⚠️ **Link đang là `http://localhost:8000/r/…`** — địa chỉ này **chỉ mở được
> trên chính máy bạn**. Khách xem live ở nhà họ bấm sẽ không vào được. Wizard tự
> cảnh báo ngay dưới danh sách link: *"Link đang trỏ về máy này — chỉ mở được
> trên máy này. …"*. Muốn đo thật, cần đặt một địa chỉ công khai (xem mục 8,
> giới hạn #9).

**Kết thúc phiên ở đâu?** Trên bàn trợ live (nút "Kết thúc phiên" ở thanh trạng
thái — bước 3.9). Mở lại trang Chuẩn bị phiên khi đang phát sẽ thấy hai nút
**"Mở bàn trợ live →"** và **"Mở màn hình người dẫn ↗"**.

### Bước 3.6 — Mở Bàn trợ live

**Bấm gì:** wizard đã tự chuyển bạn sang đây sau khi bấm "Bắt đầu phát sóng";
nếu lỡ đóng, bấm nút **"Mở bàn trợ live"** ở bước 4 của wizard (hoặc chữ **"Bàn
trợ live"** trên thanh trên cùng).

![Bàn điều khiển đang chạy phiên thật](img/l3-07-ban-dieu-khien.png)

*(Ảnh trên là bàn trợ live bản 11/09; bố cục nay đã đổi — đọc theo mô tả dưới.)*

**Đọc từ trên xuống:**

**a) Thanh trạng thái (trên cùng)**
- Đèn **ĐANG PHÁT** và đồng hồ cả buổi, ví dụ `00:02:06 / 01:30:00`.
- Ô chọn phiên (**"Phiên đang xem"**) — mỗi dòng in tên phiên · giờ · nền tảng ·
  trạng thái, phiên mẫu có thêm *"dữ liệu mẫu"*. Bàn mở nhầm buổi thì đổi ở đây.
- **TRỰC TIẾP** = đang nối được máy chủ (*"TRỰC TIẾP (đang nối lại)"* = đang
  nối lại).
- Công tắc **Gợi ý / Tự động** = chế độ.
- Nút đỏ **"Kết thúc phiên"** ở mép phải.

**b) KHỐI HIỆN TẠI + LỊCH BẬT/TẮT — thứ bạn phải liếc thường xuyên nhất**
- Thẻ lớn bên trái ghi **TẮT** hoặc **BẬT** (kèm hình dạng riêng để người mù
  màu vẫn phân biệt được), số khối và pha (*đầu / giữa / cuối phiên*).
- Số lớn **"CHUYỂN KHỐI SAU"** = còn bao lâu nữa đổi khối. Khi còn **≤ 30
  giây**, số chuyển màu hổ phách và hiện chip **"⚠ Sắp đổi khối — chuẩn bị thao
  tác"**.
- Thẻ **Lịch BẬT / TẮT** bên phải: dải ô tím/xám = toàn bộ lịch, có vạch vị trí
  hiện tại, dòng **"Đang ghim:"** và **"Mã bằng chứng lịch"** (dấu kiểm chứng
  của lịch, để đối chiếu).

**c) Cột KPI (trái)** — **Người xem · Bình luận / phút · Lượt bấm / phút · Ý
định mua (radar)**, cộng một dòng gọn **Tim & quà**. Ô nào không có nguồn thì
ghi **"THIẾU nguồn"** kèm lý do, **chứ không in số 0 giả**; có nguồn mà chưa có
điểm đo thì ghi **—**. Ô Bình luận ghi THIẾU nguồn thì kèm luôn cách sửa: *"Bật
ở khung “Bộ thu bình luận”: chọn nền tảng, dán link buổi live rồi bấm “Bật bộ
thu”."* (mục 10). Ở ảnh chụp 11/09, đồng hồ khối còn in số 0 người xem cạnh ô
THIẾU nguồn — lỗi đó (giới hạn #7 cũ) đã sửa: đồng hồ khối không còn in số người
xem.

**d) Cột giữa** — khung **Bộ thu bình luận** (đầu cột, chỉ hiện khi bàn nối
được máy chủ thật và phiên chưa đóng), rồi **Nhịp phiên** và **Radar bình
luận**.

**e) HÀNH ĐỘNG GỢI Ý (cột phải)** — các thẻ `#1 #2 #3` đề xuất ghim sản phẩm
nào, kèm nút **"Thực hiện"** và **"Bỏ qua"** (chế độ Gợi ý). Ngay dưới là khung
**Tự lái phía máy chủ** nếu phiên chạy chế độ Tự động.

### Bước 3.7 — Bấm "Thực hiện" để ghim sản phẩm

**Bấm gì:** nút xanh **"Thực hiện"** trên thẻ bạn muốn.
**Ở đâu:** góc phải dưới của mỗi thẻ, cột **HÀNH ĐỘNG GỢI Ý**.

**Nếu đang ở khối BẬT (ô lớn ghi BẬT):** thẻ mờ đi, hai nút biến mất và thay
bằng chữ xanh **"✓ Đã thực hiện"**; dòng **"Đang ghim:"** ở thẻ *Lịch BẬT / TẮT*
hiện tên sản phẩm, và **màn hình host đổi ngay**.

![Đã ghim thành công trong khối BẬT](img/l3-10-ghim-thanh-cong.png)

> **Có thể hệ thống ghim một sản phẩm khác với thẻ bạn bấm** (trong ảnh: bấm thẻ
> #1 *Mặt nạ giấy*, hệ thống ghim *Son kem lì đỏ cam*). Đây **không phải lỗi**:
> khi hai sản phẩm chưa phân biệt được về mặt thống kê, hệ thống bốc thăm giữa
> chúng và **ghi lại xác suất bốc** — đó là phần "khám phá có kiểm soát" giúp dữ
> liệu về sau vẫn phân tích được. Khi đó bàn hiện một khung ⓘ ngay trên cột thẻ
> nói rõ sản phẩm nào đã được ghim. **Cứ đọc tên ở dòng "Đang ghim:"** — đó là
> sản phẩm thật sự đang lên màn hình host.

**Nếu đang ở khối TẮT:** hệ thống **không cho ghim, và đó là đúng** — khối TẮT
là nhánh đối chứng, hệ thống không được can thiệp, nếu không thí nghiệm mất giá
trị. Nay thẻ gợi ý trong khối TẮT **không còn nút Thực hiện**: chỗ nút được thay
bằng dòng khoá *"Khối TẮT — vận hành như thường lệ"* (khoảng trôi giữa hai khối
ghi *"Khoảng trôi — chờ khối BẬT kế tiếp"*, ngoài lịch ghi *"Ngoài lịch khối —
chưa ghim được"*).

![Bấm Thực hiện trong khối TẮT — hệ thống từ chối](img/l3-08-khoi-tat-tu-choi-ghim.png)

*(Ảnh trên chụp ngày 11/09, khi nút còn bấm được và báo sai "kiểm tra kết nối
API" — giới hạn #6 cũ, đã sửa.)* Nếu máy chủ vẫn từ chối một lệnh, khung đỏ trên
thanh trạng thái in **nguyên văn lý do của máy chủ**; lời dặn "kiểm tra kết nối"
chỉ xuất hiện khi thật sự mất mạng.

**Khi nào thì tới khối BẬT?** Nhìn dải ô: ô tím đầu tiên nằm ở đâu. Đồng hồ
*"CHUYỂN KHỐI SAU"* đếm ngược tới lần đổi kế tiếp.

### Bước 3.8 — Mở màn hình người dẫn trên máy người dẫn

**Bấm gì:** nút **"Mở màn hình người dẫn ↗"** ở bước 4 của wizard Chuẩn bị phiên
— kéo cửa sổ sang màn phụ/TV, bấm F11 để toàn màn hình.

**Tự gõ địa chỉ** (ví dụ mở lại sau khi lỡ đóng tab): gõ đúng địa chỉ có mã
phiên, **`http://localhost:3000/host?session=<mã phiên>`**. Mã phiên lấy từ thanh
địa chỉ của tab mà nút *"Mở màn hình người dẫn ↗"* đã mở, hoặc của bàn trợ live
ngay sau khi wizard chuyển sang (`/desk?session=<mã phiên>`). Mở từ một máy
*khác* thì trình duyệt máy đó phải nối được máy chủ API — mặc định giao diện gọi
`localhost:8000` của chính máy đang mở, nên cần người kỹ thuật đặt
`NEXT_PUBLIC_API_URL` trước.

- Có `?session=` — màn chỉ chiếu **đúng phiên đó**. Sai mã thì màn ghi *"Không
  tìm thấy phiên trong link"*, không lặng lẽ chiếu phiên khác.
- Mở `/host` trơn — màn tự chọn phiên **đang phát**; mở trước khi bấm phát vẫn
  tự bắt được phiên vừa lên sóng. Đã chiếu một phiên thì **giữ nguyên** phiên đó
  tới khi nó kết thúc (không tự nhảy sang phiên mới hơn), và có phiên thật đang
  phát thì bỏ qua phiên mẫu. Có từ 2 phiên cùng đang phát thì màn báo để bạn
  dùng link có `?session=`.
- Phiên trong link đã kết thúc, đã huỷ hoặc chưa lên sóng thì màn **không** hiện
  hàng ghim cũ mà ghi rõ lý do; phiên chưa lên sóng tự hiện hàng khi bấm phát.
- Phiên dữ liệu mẫu có huy hiệu **DEMO — dữ liệu mẫu** ở góc trên.

Khi chưa ghim gì, màn này chỉ có đồng hồ và dòng chữ **"Chưa ghim sản phẩm"** —
đúng như thiết kế, không phải màn hình lỗi:

![Màn hình host khi chưa ghim](img/l3-09-host-chua-ghim.png)

Sau khi bạn bấm "Thực hiện" ở bàn điều khiển, màn này hiện **đúng 4 thứ, cỡ rất
lớn** để người dẫn liếc từ xa 2 mét vẫn đọc được: *Sản phẩm đang ghim* · *Giá* ·
*Tồn kho* · *Thời gian phát*.

![Màn hình host sau khi ghim](img/l3-11-host-da-ghim.png)

> **Màn host cố tình "thiếu" thông tin — đây là thiết kế, không phải bug.** Nó
> **không bao giờ** hiện khối BẬT/TẮT. Nếu người dẫn biết mình đang ở nhánh nào,
> họ sẽ vô thức nói năng khác đi, và thí nghiệm sẽ đo cả tâm lý người dẫn thay
> vì đo tác động của hệ thống. Xem mục 7.

### Bước 3.9 — Kết thúc phiên

**Bấm gì:** nút đỏ **"Kết thúc phiên"** ở góc phải thanh trạng thái của *Bàn
trợ live*.

**Chuyện gì xảy ra:** ngay tại chỗ nút hiện câu hỏi lại *"⚠ Kết thúc thật? Khối
chưa chạy sẽ không được tính."* kèm hai nút **"Kết thúc ngay"** và **"Huỷ"**
(con trỏ đứng sẵn ở *Huỷ* để lỡ tay Enter không kết thúc buổi live; không bấm gì
trong 10 giây thì câu hỏi tự rút) → bấm **Kết thúc ngay**.

Sau đó trạng thái phiên đổi thành **"đã kết thúc"**, nút đỏ biến mất, thẻ khối
ghi **ĐÃ KẾT THÚC** kèm nút **"Xem báo cáo phiên →"**, và phiên xuất hiện trong
danh sách *Báo cáo từng phiên* ở trang **Kết quả & chiến lược**. Bộ thu bình
luận của phiên tự dừng.

Mở lại bàn trợ live khi không còn phiên nào đang live thì bàn hiện màn hình trống
có hướng dẫn — **đây là trạng thái đúng, không phải hỏng**:

![Bàn điều khiển sau khi kết thúc phiên](img/l3-12-sau-khi-ket-thuc.png)

Các đường đi tiếp từ đây: **"Chuẩn bị phiên mới"** · **"Xem thử với dữ liệu
mẫu"** · **"Về trang chính"** · dòng gạch chân **"Vẫn mở Bàn trợ live với phiên
đã kết thúc"** (mở lại bàn trên một buổi cũ để xem lại).

---

## 6. LUỒNG 4 — Đọc kết quả

### 6.1 — Trang "Kết quả" (tổng hợp mọi phiên)

**Bấm gì:** chữ **"Kết quả & chiến lược"** trên thanh trên cùng.

![Trang Kết quả](img/l4-01-ket-qua.png)

Đọc theo thứ tự này:

| Ô | Nghĩa là gì (nói đơn giản) |
|---|---|
| **TÁC ĐỘNG ƯỚC LƯỢNG** `-0.184` | Khối BẬT tạo thêm (hay bớt) bao nhiêu lượt nhấp so với khối TẮT |
| **KTC 95% [-0.665 … 0.250]** | Khoảng mà giá trị thật gần như chắc chắn nằm trong |
| **MỨC Ý NGHĨA** `p = 0.4655` | Khả năng chênh lệch này chỉ là may rủi |
| **CỠ MẪU** `42 khối` | Đã gom được bao nhiêu dữ liệu |

**Câu quan trọng nhất nằm ở khung "Đọc thế nào:".** Ở ảnh trên nó viết: *khoảng
tin cậy vẫn chứa 0, nghĩa là **chưa kết luận được**.* Nghĩa là: **chưa đủ dữ
liệu để nói hệ thống có tác dụng hay không** — đây là một kết quả **hợp lệ**, hệ
thống không bịa ra con số đẹp.

- **Bảng MDE** bên dưới trả lời "cần chạy bao nhiêu phiên nữa thì mới đo nổi".
- **TỶ LỆ TUÂN THỦ** = trong các khối BẬT, bao nhiêu phần trăm thực sự được bấm
  *Thực hiện*. Thấp thì kết quả bị loãng.

> **Nếu trang báo "Chưa đủ dữ liệu để kết luận"**: bình thường khi bạn mới chạy
> vài phiên. Chạy thêm phiên thật.

### 6.2 — Mở báo cáo của một buổi cụ thể

**Bấm gì:** cuộn xuống cuối trang Kết quả tới mục **"BÁO CÁO TỪNG PHIÊN"**, bấm
nút **"Báo cáo phiên"** ở dòng bạn muốn.

![Danh sách báo cáo từng phiên](img/l4-02-ket-qua-bao-cao-tung-phien.png)

### 6.3 — Đọc báo cáo sau phiên

![Báo cáo sau phiên — tổng quan và ma trận tín hiệu](img/l4-03-bao-cao-tong-quan.png)

**Huy hiệu cạnh tiêu đề** cho biết loại buổi:
- **PHIÊN QUAN SÁT** (xám) = buổi live của người khác nạp vào ⇒ **không có số
  nhân quả**, chỉ mô tả.
- **PHIÊN THÍ NGHIỆM** (xanh) = buổi bạn tự chạy có bốc thăm lịch ⇒ có mục kết
  quả nhân quả.

**TỔNG QUAN** — 6 ô. Ô nào không đo được thì ghi **"THIẾU"** kèm lý do bằng
tiếng Việt, **không bao giờ in số 0**. Ví dụ trong ảnh: *Người xem đồng thời →
THIẾU, vì video đã kết thúc không còn lộ số người xem*.

**MA TRẬN TÍN HIỆU** — bảng "buổi này đo được gì": mỗi dòng là một nguồn dữ liệu
với nhãn **CÓ / SUY GIẢM / THIẾU** và lý do. Đây là chỗ trả lời câu "sao chỗ này
trống?". Ví dụ dòng lượt bấm: phiên chưa tạo link đo ghi THIẾU *"chưa tạo link
đo cho phiên này…"*; phiên đã có link mà chưa ai bấm ghi SUY GIẢM *"đã tạo N
link đo, chưa ai bấm — …"*.

**ĐƠN HÀNG CỦA PHIÊN** (ngay dưới ma trận) — tổng đơn, tổng sản phẩm, doanh thu
của phiên, và ô nhập tệp đơn CSV. Chưa nhập đơn nào thì doanh thu ghi THIẾU,
không phải 0. Cách nhập: **mục 11**.

![Khoảnh khắc nổi bật, phân bố ý định, kết quả](img/l4-04-bao-cao-khoanh-khac-y-dinh.png)

**KHOẢNH KHẮC NỔI BẬT** — các phút mà nhịp bình luận vọt lên so với nền. Dùng để
xem lại băng đoạn đó. Mỗi dòng đều kết thúc bằng *"quan sát, chưa kiểm chứng
nhân quả"* — đúng như nó là.

**PHÂN BỐ Ý ĐỊNH** — chat được chia theo ý định. **Đọc kèm khung cam phía trên**:
độ chính xác của nhãn phụ thuộc nặng vào từng buổi, đã đo thật trên 19.126 bình
luận và chênh nhau tới 50 lần giữa các buổi. Đừng dùng con số này để ra quyết
định lớn.

**KẾT QUẢ THÍ NGHIỆM** — với phiên quan sát, mục này chỉ ghi *"Phiên quan sát —
không có số nhân quả"*. Với phiên bạn tự chạy, nó hiện tác động + khoảng tin cậy.

**GỢI Ý CHIẾN THUẬT CHO PHIÊN SAU** — vài câu rút ra từ buổi đó.

**Nút "In / lưu PDF"** ở đầu trang để lưu báo cáo gửi cho người khác.

---

## 7. Ai dùng màn nào — và vì sao màn host bị "làm mù"

| | **Bàn điều khiển** (`/desk`) | **Màn hình host** (`/host`) | **Người xem** |
|---|---|---|---|
| Ai nhìn | Chủ shop / người trợ live | Người dẫn đang nói trước máy quay | Khách xem live |
| Đặt ở đâu | Laptop ngồi cạnh, ngoài khung hình | Màn phụ / TV trước mặt người dẫn | Điện thoại của khách |
| Thấy khối BẬT/TẮT | **Có** | **KHÔNG BAO GIỜ** | Không |
| Thấy đồng hồ đếm ngược khối | Có | Không | Không |
| Thấy thẻ gợi ý, nút Thực hiện | Có | Không | Không |
| Thấy gì | Toàn bộ | Đúng 4 thứ: sản phẩm đang ghim · giá · tồn kho · thời gian phát | Chỉ link đo trong bình luận ghim |

### Vì sao phải làm mù người dẫn

Thí nghiệm so **khối BẬT** với **khối TẮT**. Nếu người dẫn biết "đang BẬT", họ
sẽ tự nhiên nói hăng hơn, nhắc sản phẩm nhiều hơn. Khi đó chênh lệch đo được
không còn là tác động của **hệ thống** nữa mà lẫn cả **phản ứng tâm lý của người
dẫn** — và con số mất giá trị.

Việc làm mù này được ép ở tầng kiến trúc, không phải "nhớ đừng hiện": màn host
dùng một luồng dữ liệu riêng chỉ chứa đúng 4 trường, nên **kể cả lập trình viên
muốn cũng không hiện khối lên đó được**. Bạn kiểm chứng bằng mắt: mở `/host`,
không có dải tím/xám ở bất kỳ đâu.

Dòng chữ nhỏ ngay dưới dải khối trên bàn trợ live nhắc lại điều này: *"Chỉ hiện
trên bàn trợ live — màn người dẫn không thấy khối"*.

---

## 8. Giới hạn hiện tại — nói thật

*Cập nhật 17/09/2026. Dòng ghi **ĐÃ SỬA** giữ lại số thứ tự cũ để ai đã đọc bản
trước đối chiếu được; chỉ ghi "đã sửa" với thứ đã có trong mã.*

| # | Giới hạn | Ảnh hưởng tới bạn | Cách sống chung |
|---|---|---|---|
| 1 | **Chưa có đăng nhập, chưa có mật khẩu** | Ai vào được địa chỉ là dùng được toàn quyền; không có tài khoản riêng, danh mục sản phẩm dùng chung | Chỉ chạy trên **máy cá nhân** hoặc **Wi-Fi nội bộ**. Bản đưa lên Internet phải đặt `INGEST_TOKEN` (người kỹ thuật làm) — khi đó trình duyệt không gửi token nên một số nút ghi bị máy chủ từ chối (xem #10, #11) |
| 2 | **Chạy bằng hai cửa sổ lệnh thì kho nằm trong bộ nhớ, có ảnh chụp tự động** | Ảnh chụp **bật mặc định**, 30 giây một lần, tự nạp lại khi bật máy chủ; tắt bằng Ctrl+C thì chụp lần cuối. Máy chủ chết đột ngột (đóng cửa sổ, mất điện, treo máy) thì **mất tối đa khoảng 30 giây** dữ liệu cuối | Buổi live thật: chạy bằng Docker (PostgreSQL) — đó mới là kho **bền vững**. Người kỹ thuật kiểm bằng `/health`: `storage_mode` là `memory+snapshot` (có ảnh chụp) hay `postgres` |
| 3 | **Chế độ "Tự ghim" và bộ thu bình luận cần máy chủ chạy đúng 1 tiến trình** | Trước 12/09 chế độ Tự ghim chưa có bộ thực thi (không gì được ghim); nay bộ thực thi tự động chạy phía máy chủ, nhưng tắt được bằng biến môi trường và chỉ an toàn với 1 worker. Bộ thu bình luận (mục 10) cũng sống trong tiến trình máy chủ, cùng quy tắc | Nếu bàn trợ live báo **"Bộ thực thi tự động ĐANG TẮT"** hoặc phiên auto im lặng quá 5 phút thì ghim tay ngay theo cảnh báo trên bàn |
| 4 | **Điện thoại chưa dùng được cho Bàn trợ live** | Màn `/desk` được thiết kế và soát cho màn ≥ 1366×768; màn hẹp hơn các khung xếp thành một cột dài, phải cuộn nhiều khi đang live | Dùng laptop cho `/desk`. Màn `/host` và trang báo cáo thì xem tạm được trên màn nhỏ |
| 5 | **ĐÃ SỬA** — link `?session=` ở màn Xem lại phiên từng bị bỏ qua | Nay link mở **đúng buổi** (bước 2.3); chọn buổi khác thì địa chỉ đổi theo | Link sai mã hoặc buổi chưa kết thúc: trang nói rõ lý do và mở buổi đã kết thúc gần nhất |
| 6 | **ĐÃ SỬA** — báo lỗi sai khi bấm Thực hiện trong khối TẮT | Nay trong khối TẮT (và khoảng trôi, ngoài lịch) thẻ **không còn nút Thực hiện**, thay bằng dòng lý do, ví dụ *"Khối TẮT — vận hành như thường lệ"*. Lệnh bị máy chủ từ chối thì báo nguyên văn lý do; chỉ lỗi mạng thật mới kèm lời dặn kiểm tra kết nối | — |
| 7 | **ĐÃ SỬA** — đồng hồ khối in số 0 người xem cạnh ô "THIẾU nguồn" | Đồng hồ khối không còn in số người xem. Ô **Người xem** ở cột KPI ghi *THIẾU nguồn* khi không có nguồn, **—** khi có nguồn mà chưa có điểm đo | — |
| 8 | **ĐÃ SỬA** — lượt bấm ghi "không có link đo" dù đã tạo link | Phiên có link mà chưa ai bấm: ma trận tín hiệu ghi **SUY GIẢM** *"đã tạo N link đo, chưa ai bấm — …"*; chỉ phiên chưa tạo link nào mới ghi *"chưa tạo link đo cho phiên này"* | Đã lên sóng mà vẫn 0 lượt bấm: kiểm tra link đo đã dán vào bình luận ghim chưa |
| 9 | **Link đo trỏ về `localhost`** | Khách xem live **không mở được** | Cần một địa chỉ công khai (tên miền thật hoặc tunnel) đặt vào `NEXT_PUBLIC_PUBLIC_API_BASE` — nhờ người kỹ thuật làm 1 lần |
| 10 | **Bộ thu bình luận: bật bằng nút, nhưng cần khoá của nền tảng trên máy chủ** | Nút **"Bật bộ thu"** ở Bàn trợ live và bước 4 *Chuẩn bị phiên* (mục 10). Máy chủ thiếu khoá thì nút bị khoá và ghi tên biến còn thiếu. TikTok không có API bình luận live. Máy chủ đặt `INGEST_TOKEN` thì lệnh bật từ trình duyệt bị từ chối (*"Thiếu hoặc sai token ingest…"*) | Chưa có khoá: phiên **chạy thử** hoặc phiên **dữ liệu mẫu** dùng nguồn **Mô phỏng (kiểm thử)** — dữ liệu tổng hợp, mục 12. Muốn xem radar trên chat thật mà chưa có khoá: Luồng 2 (buổi YouTube đã kết thúc) |
| 11 | **Đơn hàng: nhập được bằng tệp CSV, chưa tự về** | Trang **Báo cáo phiên** có ô nhập tệp đơn xuất từ Seller Center (mục 11). Không nền tảng nào tự đẩy đơn vào LiveLift; chưa nhập thì doanh thu ghi THIẾU. Máy chủ đặt `INGEST_TOKEN` thì trình duyệt không nhập được vào phiên thật (chỉ vào phiên dữ liệu mẫu, và chỉ khi chế độ trưng bày công khai đang bật) | Đơn hàng là **chỉ số phụ** — chỉ tiêu chính vẫn là **lượt nhấp** link đo |
| 12 | **Một số việc vẫn phải gõ lệnh** | Chấm chất lượng dữ liệu (`livelift-qc`), mô phỏng kiểm định | Xem `docs/HUONG-DAN-TEST.md` |

---

## 9. Gặp lỗi thì làm gì

| Bạn thấy | Nguyên nhân hay gặp nhất | Làm gì |
|---|---|---|
| Trang trắng / không mở được `localhost:3000` | Cửa sổ 2 (`npm run dev`) chưa chạy | Bật lại cửa sổ 2, chờ dòng `Ready` |
| Thẻ **03** ở trang chính bị mờ, ghi *"Tạm khoá…"* | Máy chủ (cửa sổ 1) chưa chạy, hoặc kho dữ liệu đang suy giảm | Đọc dải cảnh báo đỏ/cam ở trên (mục 1) |
| Bàn trợ live hiện *"Chưa có phiên nào đang chạy"* | Không có phiên nào ở trạng thái *đang live* | Bấm **"Chuẩn bị phiên mới"**, **"Xem thử với dữ liệu mẫu"**, hoặc **"Vẫn mở Bàn trợ live với phiên đã kết thúc"** |
| Bàn hiện **sai buổi** | Bàn tự chọn một buổi *đang live* | Đổi ở ô chọn phiên (**"Phiên đang xem"**) trên thanh trạng thái |
| Khung cam *"Dữ liệu suy giảm"* trên bàn | Một nguồn dữ liệu tạm hỏng | Bàn vẫn chạy với nguồn còn lại; nếu kéo dài thì xem cửa sổ 1 |
| Radar / feed trống trên buổi có hàng nghìn bình luận | Vừa đổi buổi, chưa poll xong | Chờ ~5 giây; nếu vẫn trống, tải lại trang (Ctrl+R) |
| Thẻ gợi ý không có nút *Thực hiện*, ghi *"Khối TẮT — vận hành như thường lệ"* | Đang ở khối **TẮT** — đúng thiết kế | Chờ khối BẬT (đồng hồ *"Chuyển khối sau"*) |
| Khung đỏ *"Không thực hiện được thẻ …"* | Máy chủ từ chối lệnh (lý do in nguyên văn) hoặc mất mạng | Đọc lý do; chỉ khi câu có *"kiểm tra kết nối"* mới là lỗi mạng |
| Nút **"Bật bộ thu"** mờ, dòng *"⚠ Máy chủ chưa có khoá cho …: thiếu …"* | Máy chủ chưa có khoá của nền tảng đó | Mục 10 — nhờ người kỹ thuật điền tên biến còn thiếu vào `.env` rồi khởi động lại máy chủ |
| Bộ thu ghi *"✕ Bộ thu dừng vì lỗi"* | Lỗi cấu hình (khoá sai, token hết hạn, thiếu quyền…) | Đọc dòng lý do ngay dưới, sửa rồi bật lại |
| Nhập đơn báo *"Tệp CSV thiếu cột bắt buộc: …"* | Tệp không có cột thời gian đặt đơn hoặc cột tổng tiền đặt đúng tên | Mục 11 — đổi tên cột rồi nhập lại |
| Số liệu cũ, không nhúc nhích | Trình duyệt cache | `Ctrl + Shift + R` |
| Phân tích YouTube báo lỗi | Video không có chat replay, hoặc YouTube chặn | Đổi video; hoặc xem `docs/HUONG-DAN-TEST.md` mục 4 |

Mọi lỗi từng gặp và cách sửa tận gốc: [`docs/incident-log.md`](incident-log.md).
Hướng dẫn kiểm thử bằng lệnh cho người kỹ thuật:
[`docs/HUONG-DAN-TEST.md`](HUONG-DAN-TEST.md).

---

## 10. Bật bộ thu bình luận

> Chưa có khoá của nền tảng? Cách lấy từng loại khoá, điền vào `.env` và kiểm tra nằm ở
> **[HUONG-DAN-LAY-KHOA-API.md](HUONG-DAN-LAY-KHOA-API.md)**. LiveLift chỉ đọc bình luận qua API
> chính thức, trên tài khoản của nhóm hoặc đối tác đã đồng ý — không đọc kiểu người xem.

Không có bộ thu thì ô **Bình luận / phút** và **Người xem** ghi *THIẾU nguồn*,
radar trống. Từ 17/09/2026 bộ thu chạy ngay trong máy chủ — **bấm nút là thu**,
không phải mở cửa sổ lệnh. Văn bản bình luận được lọc thông tin cá nhân trước
khi lưu.

**Ở đâu** (hai chỗ, cùng điều khiển một bộ thu của phiên):

- **Chuẩn bị phiên → bước 4/4 — Lên sóng**, dòng **"Nguồn bình luận"** trong
  checklist. Bật **trước giờ phát** cũng được: bộ thu sẽ chờ buổi live bắt đầu.
- **Bàn trợ live**, khung **"Bộ thu bình luận"** ở đầu cột giữa. Khung chỉ hiện
  khi bàn nối được máy chủ thật và phiên chưa kết thúc.

**Bấm gì:**

1. Ô **Nền tảng**: chọn nền tảng (mặc định là nền tảng của phiên). Dòng nào có
   đuôi *"— chưa sẵn sàng"* là máy chủ còn thiếu khoá cho nền tảng đó.
2. Ô **Link hoặc mã buổi live** — chữ mờ trong ô nhắc đúng loại cần dán:
   - *YouTube Live*: link video **đang live** (`youtube.com/watch?v=…`,
     `youtu.be/…` hoặc `youtube.com/live/…`; link kênh chưa được hỗ trợ);
   - *Facebook Live (Page của bạn)*: **để trống** để tự tìm buổi đang phát trên
     Page, hoặc dán live-video id (một dãy số);
   - *Shopee Live (shop của bạn)*: session_id của buổi live (một dãy số).
3. Bấm **"Bật bộ thu"** (nút đổi thành *"Đang bật…"*).

Muốn dừng: bấm **"Tắt bộ thu"**. Trên bàn trợ live, sau khi bộ thu đã dừng có nút
**"Bật lại"**. Kết thúc phiên thì bộ thu **tự dừng**; máy chủ khởi động lại thì
bộ thu của phiên chưa kết thúc **tự nối lại**.

**Dòng trạng thái đọc thế nào** — mỗi trạng thái có một ký hiệu riêng, không chỉ
màu:

| Ký hiệu | Chữ trên màn hình | Nghĩa là | Việc cần làm |
|---|---|---|---|
| **●** | *Đang thu bình luận* | Đang chạy. Bên cạnh là số bình luận, số người xem (nếu nền tảng cho đọc) và *"mới nhất … giây trước"* | Không cần làm gì |
| **◐** | *Đang kết nối* | Vừa bật, đang mở kết nối tới nền tảng | Chờ vài giây |
| **◐** | *Chờ buổi live bắt đầu* | Nền tảng báo buổi live chưa phát; bộ thu tự dò lại, không tính là lỗi | Không cần làm gì — bấm phát trên nền tảng như bình thường |
| **↻** | *Mất kết nối — đang thử lại* | Lỗi tạm thời (mạng, nền tảng trả lỗi); bộ thu tự thử lại | Để yên; kéo dài thì kiểm tra mạng của máy chủ |
| **✕** | *Bộ thu dừng vì lỗi* | Lỗi không tự khắc phục được (khoá sai, token hết hạn, thiếu quyền…) — lý do in ngay dưới | Đọc lý do, sửa, rồi bật lại |
| **○** | *Chưa bật bộ thu* · *Đã tắt bộ thu* · *Phiên đã kết thúc — bộ thu tự dừng* · *Buổi live đã tắt — bộ thu dừng* | Không thu | Bật khi cần. *"Buổi live đã tắt"* mà buổi vẫn đang phát thì kiểm tra lại link đã dán |

Đang thu mà hai phút không có bình luận mới, khung ghi thêm *"⚠ Hai phút không có
bình luận mới — kiểm tra buổi live còn phát và còn người bình luận."*

**Thiếu khoá thì làm gì.** Ngay dưới nút hiện dòng *"⚠ Máy chủ chưa có khoá cho
<nền tảng>: thiếu <TÊN_BIẾN>. Nhờ người kỹ thuật điền vào tệp .env rồi khởi
động lại máy chủ."* và nút **"Bật bộ thu"** bị khoá. Muốn biết trước máy chủ đang
có khoá gì: trang chủ → thẻ **01** → **"Trả lời 3 câu hỏi →"** → khối **"Máy chủ
này thu được bình luận từ đâu"** (mỗi nền tảng một dòng: *Sẵn sàng* / *Thiếu
khoá* / *Thiếu cài đặt* / *Không hỗ trợ*, kèm tên biến còn thiếu — máy chủ không
bao giờ hiện giá trị khoá).

| Nền tảng | Máy chủ cần (tên biến trong `.env`) |
|---|---|
| YouTube Live | `YOUTUBE_API_KEY` (đường chính thức). Đường dự phòng yt-dlp không cần khoá nhưng trái Điều khoản YouTube — **không dùng cho buổi live thật** |
| Facebook Live (Page của bạn) | `FACEBOOK_PAGE_ID` và `FACEBOOK_PAGE_ACCESS_TOKEN` — token cần quyền `pages_read_engagement` **và** `pages_read_user_content` |
| Shopee Live (shop của bạn) | `SHOPEE_PARTNER_ID`, `SHOPEE_PARTNER_KEY`, `SHOPEE_USER_ID`, `SHOPEE_ACCESS_TOKEN` (token Shopee chỉ sống 4 giờ) |
| TikTok LIVE | Không có — TikTok không có API công khai cho bình luận live |

Chưa có khoá nào mà muốn thử trọn đường đi của bình luận: dùng nguồn **Mô phỏng**
ở mục 12. Máy chủ có đặt `INGEST_TOKEN` (bản công khai) thì lệnh bật từ trình
duyệt bị từ chối với câu *"Thiếu hoặc sai token ingest…"* — giới hạn #10.

---

## 11. Nhập đơn hàng từ Seller Center

Đơn hàng là **chỉ số phụ** — chỉ số chính của thí nghiệm vẫn là lượt nhấp link
đo. Nhưng có đơn thì báo cáo đối chiếu được doanh thu theo từng khối. Chưa nhập
đơn nào thì doanh thu ghi **THIẾU**, không phải 0.

**Ở đâu:** trang **Báo cáo phiên** của đúng buổi đó (vào từ *Kết quả & chiến
lược* → **"Báo cáo phiên"**, hoặc nút **"Báo cáo phiên →"** trên bàn trợ live /
màn Xem lại phiên), mục **"Đơn hàng của phiên"** ngay dưới Ma trận tín hiệu.

**Bấm gì:**

1. Trên Seller Center của nền tảng, xuất danh sách đơn của buổi live ra tệp. Mở
   bằng Excel, **lưu lại dạng CSV UTF-8**.
2. Kiểm tra **dòng đầu** của tệp là tên cột (không phân biệt hoa thường):
   - **Bắt buộc** — thời gian đặt đơn: cột tên `thời gian` hoặc `thời gian đặt
     hàng` hoặc `ts` (máy chủ cũng nhận `ngày đặt hàng`, `created_time`, `order
     creation time`). Viết dạng `17/09/2026 20:05` (hiểu là giờ Việt Nam) hoặc
     ISO 8601;
   - **Bắt buộc** — số tiền của đơn: cột `tổng tiền` hoặc `doanh thu` hoặc
     `gross` (máy chủ cũng nhận `tổng giá trị đơn hàng`, `order amount`,
     `total`). `1.250.000 ₫` hay `1,250,000` đều đọc được;
   - **Nên có** — `mã đơn` hoặc `order_id` (máy chủ cũng nhận `mã đơn hàng`,
     `order id`): đây là thứ chống tính trùng;
   - Tuỳ chọn: `số lượng`, `phí sàn`, mã sản phẩm (`sku`, `mã sản phẩm` — phải
     trùng mã có trong danh mục, không thì dòng đó báo lỗi).
   Không cần cột tên, số điện thoại hay địa chỉ người mua — có cũng bị bỏ qua,
   không lưu.
3. Bấm **"Chọn tệp CSV trên máy"** — trình duyệt chỉ **đọc chữ** trong tệp rồi đổ
   vào ô bên dưới, tệp không bị tải lên. Hoặc dán thẳng nội dung vào ô **"Hoặc dán
   nội dung CSV"**.
4. Liếc lại nội dung trong ô, bấm **"Nhập đơn"** (nút đổi thành *"Đang nhập…"*).

**Đọc kết quả:** một hàng ba con số — **✓ Nhập mới N đơn** · **= Trùng mã, bỏ qua
N đơn** · **⚠ Lỗi N dòng** — và danh sách lỗi theo dòng, ví dụ *"Dòng 5: không
đọc được thời gian …"*. Ô tổng đơn / tổng sản phẩm / doanh thu phía trên cập nhật
ngay.

- **Chống trùng:** nhập lại cùng một tệp **không** nhân đôi doanh thu — những đơn
  đã có mã sẽ rơi vào *"Trùng mã, bỏ qua"*. Điều này **chỉ đúng khi tệp có cột mã
  đơn**: không có mã đơn thì mỗi lần nhập là một lượt đơn mới.
- **Lỗi theo dòng:** dòng hỏng bị bỏ qua, các dòng tốt vẫn được nhập. Sửa đúng
  những dòng được liệt kê rồi nhập lại **cả tệp** — dòng đã nhập (có mã đơn) tự
  rơi vào trùng. Máy chủ chỉ liệt kê tối đa 50 lỗi đầu tiên.
- **Lỗi cả tệp:** thiếu cột bắt buộc thì không dòng nào được nhập — khung đỏ ghi
  *"Tệp CSV thiếu cột bắt buộc: …"*.
- **Giới hạn mỗi lần:** tệp tối đa 2 MB và 5.000 dòng — lớn hơn thì chia nhỏ.
- Đơn được gán vào khối theo **thời điểm đặt đơn**, không theo lúc nhập — nhập
  sau khi buổi live đã kết thúc là bình thường. Đơn đặt ngoài giờ phát không
  thuộc khối nào.

---

## 12. Kiểm thử không cần nền tảng: nguồn Mô phỏng

Nguồn **Mô phỏng (kiểm thử)** trong ô *Nền tảng* của bộ thu bình luận phát lại
một kịch bản bình luận **tổng hợp** — do tác tử AI soạn ngày 17/09/2026, không
chép từ người thật, **không phải khách thật** — theo nhịp thời gian thật, kèm số
người xem sinh sẵn. Nó đi trọn đường của một buổi live thật: lọc thông tin cá
nhân → phân loại ý định → radar và feed trên bàn trợ live. Dùng để tập vận hành
hoặc kiểm tra hệ thống khi chưa có khoá nền tảng nào.

**Chỉ dùng được trên hai loại phiên** — để dữ liệu tổng hợp không bao giờ trộn
vào dữ liệu thật:

- **Phiên dữ liệu mẫu** (có nhãn *dữ liệu mẫu* / *DEMO — dữ liệu mẫu*). Cách có
  một phiên mẫu **đang phát**: trang chủ → **"Bắt đầu xem thử"** (mục 3) — máy
  chủ tạo kèm một phiên *"Phiên đang phát (mô phỏng) · gieo …"*.
- **Phiên chạy thử** (`dry_run`) — phiên thật được khai là tập dượt ngay lúc tạo,
  bị loại khỏi mẫu phân tích. Tạo ở wizard *Chuẩn bị phiên*, bước 2, câu *"Buổi
  này có tính vào kết quả không?"* → chọn **"Chạy thử (không tính vào kết
  quả)"**. Dùng sản phẩm mẫu với link example.com thì wizard chọn sẵn ô này.

Với phiên thật, *Mô phỏng* không hiện trong ô Nền tảng, và máy chủ cũng từ chối
nếu ai gọi thẳng: *"Nguồn mô phỏng chỉ dùng cho phiên chạy thử hoặc phiên mẫu —
không trộn vào dữ liệu thật. …"*

**Bấm gì:**

1. Mở **Bàn trợ live**, chọn phiên mẫu đang phát (hoặc phiên chạy thử) ở ô chọn
   phiên trên thanh trạng thái.
2. Khung **Bộ thu bình luận** → ô **Nền tảng** chọn **Mô phỏng (kiểm thử)**.
3. Ô **Link hoặc mã buổi live**: **để trống** để phát cả buổi mẫu theo nhịp thật;
   gõ **`ngắn x10`** để phát 3 phút đầu nhanh gấp 10 lần (thử nhanh).
4. Bấm **"Bật bộ thu"** — trạng thái chuyển sang **● Đang thu bình luận**, radar
   và feed bắt đầu có bình luận.

Bật tắt nhiều lần vào cùng một phiên không nhân đôi bình luận. Trên trang Bắt
đầu, dòng *Mô phỏng (kiểm thử)* luôn đeo nhãn **"Dữ liệu tổng hợp — chỉ để kiểm
thử"**. Mọi con số sinh ra từ nguồn này **không được** dùng để nói về khách thật
hay tác động thật.
