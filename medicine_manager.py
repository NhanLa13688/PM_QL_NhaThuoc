import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox,
    QDateEdit, QSpinBox, QCompleter, QHeaderView, QLabel
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor, QFont
from datetime import datetime

DATA_FILE = 'data.json'
SUGGESTION_FILE = 'suggestions.json'

class MedicineManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần mềm quản lý thuốc Hồng Phúc")
        self.resize(1000, 600)
        self.medicines = []
        self.filtered_medicines = []
        self.suggestions = []
        self.init_ui()
        self.load_data()
        self.load_suggestions()

    def init_ui(self):
        layout = QVBoxLayout()
        font = QFont()
        font.setPointSize(15)
        self.setFont(font)

        # Ô tìm kiếm
        search_layout = QHBoxLayout()
        search_label = QLabel("Tìm thuốc:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nhập tên thuốc để tìm...")
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Nhập dữ liệu thuốc
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tên thuốc")

        self.completer = QCompleter(self.suggestions)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.name_input.setCompleter(self.completer)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("dd/MM/yyyy")

        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(1000)
        self.quantity_input.setValue(1)

        add_button = QPushButton("Thêm thuốc")
        add_button.clicked.connect(self.add_medicine)
        add_button.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 5px;
        """)

        delete_button = QPushButton("Xoá thuốc đã chọn")
        delete_button.clicked.connect(self.delete_selected)
        delete_button.setStyleSheet("""
            background-color: #f44336;
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 5px;
        """)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.date_input)
        input_layout.addWidget(self.quantity_input)
        input_layout.addWidget(add_button)
        input_layout.addWidget(delete_button)
        layout.addLayout(input_layout)

        # Bảng thuốc
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Tên thuốc", "Hạn sử dụng", "Số lượng"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellChanged.connect(self.handle_cell_change)

        header = self.table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #D3D3D3;
                color: black;
                font-weight: bold;
                font-size: 16px;
                padding: 8px;
            }
        """)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def add_medicine(self):
        name = self.name_input.text().strip()
        date_str = self.date_input.date().toString("dd/MM/yyyy")
        quantity = self.quantity_input.value()

        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc!")
            return

        try:
            expiry_date = datetime.strptime(date_str, "%d/%m/%Y")
            if expiry_date < datetime.today():
                QMessageBox.warning(self, "Lỗi", "Hạn sử dụng phải lớn hơn hoặc bằng hôm nay!")
                return
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Định dạng ngày không hợp lệ! (dd/MM/yyyy)")
            return

        if name not in self.suggestions:
            self.suggestions.append(name)
            self.save_suggestions()
            self.completer.model().setStringList(self.suggestions)

        for med in self.medicines:
            if med["name"] == name and med["expiry"] == date_str:
                med["quantity"] += quantity
                self.save_data()
                self.update_table()
                self.name_input.clear()
                self.search_input.clear()
                return

        existing_names = [m["name"] for m in self.medicines]
        new_name = name
        suffix = 1
        while new_name in existing_names:
            suffix += 1
            new_name = f"{name} {suffix}"

        self.medicines.append({
            "name": new_name,
            "expiry": date_str,
            "quantity": quantity
        })

        self.save_data()
        self.update_table()
        self.name_input.clear()
        self.search_input.clear()

    def update_table(self):
        today = datetime.today()

        def priority(med):
            try:
                expiry = datetime.strptime(med["expiry"], "%d/%m/%Y")
                days_left = (expiry - today).days
                if days_left < 0:
                    return 0
                elif days_left <= 3:
                    return 1
                elif days_left <= 90:
                    return 2
                else:
                    return 3
            except:
                return 4

        self.medicines.sort(key=priority)
        self.filtered_medicines = self.medicines
        self.filter_table()

    def filter_table(self):
        keyword = self.search_input.text().strip().lower()
        today = datetime.today()
        filtered = [m for m in self.medicines if keyword in m["name"].lower()]

        self.table.blockSignals(True)
        self.table.setRowCount(len(filtered))

        for row, med in enumerate(filtered):
            name_item = QTableWidgetItem(med["name"])
            expiry_item = QTableWidgetItem(med["expiry"])
            quantity_item = QTableWidgetItem(str(med.get("quantity", 1)))

            try:
                expiry_date = datetime.strptime(med["expiry"], "%d/%m/%Y")
                days_left = (expiry_date - today).days

                if days_left < 0:
                    color = QColor(120, 120, 120)   # Hết hạn
                elif days_left <= 3:
                    color = QColor(255, 100, 100)   # Đỏ
                elif days_left <= 90:
                    color = QColor(255, 200, 0)     # Cam
                else:
                    color = QColor(255, 255, 255)   # Bình thường

                for item in [name_item, expiry_item, quantity_item]:
                    item.setBackground(color)

            except Exception as e:
                print("Lỗi ngày:", e)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, expiry_item)
            self.table.setItem(row, 2, quantity_item)

        self.table.blockSignals(False)

    def handle_cell_change(self, row, column):
        try:
            name = self.table.item(row, 0).text().strip()
            expiry = self.table.item(row, 1).text().strip()
            quantity = int(self.table.item(row, 2).text())

            actual_row = self.medicines.index(
                next(m for m in self.medicines if m["name"] == name)
            )
            self.medicines[actual_row] = {
                "name": name,
                "expiry": expiry,
                "quantity": quantity
            }

            self.save_data()
            self.update_table()
        except Exception as e:
            print("Lỗi chỉnh sửa ô:", e)

    def delete_selected(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            name = self.table.item(row, 0).text()
            self.medicines = [m for m in self.medicines if m["name"] != name]
            self.save_data()
            self.update_table()
        else:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn thuốc để xoá.")

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.medicines = json.load(f)
            except:
                self.medicines = []
        self.update_table()

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.medicines, f, ensure_ascii=False, indent=2)

    def load_suggestions(self):
        if os.path.exists(SUGGESTION_FILE):
            try:
                with open(SUGGESTION_FILE, 'r', encoding='utf-8') as f:
                    self.suggestions = json.load(f)
                    self.completer.model().setStringList(self.suggestions)
            except:
                self.suggestions = []

    def save_suggestions(self):
        with open(SUGGESTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.suggestions, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineManager()
    window.show()
    sys.exit(app.exec_())
