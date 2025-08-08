# PM_QL_NhaThuoc
Đây là phần phềm giúp quản lý các loại thuốc, cảnh báo hạn sử dung ...
Mở CMD tại thư mục chứa file .py.

Cài PyInstaller:

bash
Sao chép
Chỉnh sửa
pip install pyinstaller
Đóng gói:

bash
Sao chép
Chỉnh sửa
pyinstaller --onefile --noconsole medicine_manager.py
Vào thư mục dist/ lấy file .exe mang sang máy khác.

Nếu muốn dữ liệu mới → xóa data.json và sales.json trước khi chạy.
