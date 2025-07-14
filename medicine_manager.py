import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QMessageBox, QHeaderView, QCompleter
)
from PyQt5.QtCore import Qt, QDate, QStringListModel
from PyQt5.QtGui import QFont, QColor
from datetime import datetime

DATA_FILE = 'data.json'
SALES_FILE = 'sales.json'

class MedicineManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần mềm quản lý thuốc Hồng Phúc")
        self.resize(1000, 600)

        self.medicines = []
        self.sales = []

        self.load_data()
        self.load_sales()

        self.init_ui()
        self.update_stock_table()
        self.update_profit_table()

    def init_ui(self):
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.init_sell_tab()
        self.init_stock_tab()
        self.init_profit_tab()

    def init_sell_tab(self):
        self.sell_tab = QWidget()
        sell_layout = QVBoxLayout(self.sell_tab)

        input_layout = QHBoxLayout()
        self.sell_name_input = QLineEdit()
        self.sell_name_input.setPlaceholderText("Nhập tên thuốc để bán")
        self.sell_quantity_input = QSpinBox()
        self.sell_quantity_input.setMinimum(1)
        self.sell_button = QPushButton("Bán thuốc")
        self.sell_button.clicked.connect(self.sell_medicine)

        input_layout.addWidget(self.sell_name_input)
        input_layout.addWidget(self.sell_quantity_input)
        input_layout.addWidget(self.sell_button)

        sell_layout.addLayout(input_layout)
        self.tabs.addTab(self.sell_tab, "Bán thuốc")

    def init_stock_tab(self):
        self.stock_tab = QWidget()
        stock_layout = QVBoxLayout(self.stock_tab)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tên thuốc")

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setDate(QDate.currentDate())

        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)

        stock_button = QPushButton("Nhập kho")
        stock_button.clicked.connect(self.add_medicine)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.date_input)
        input_layout.addWidget(self.quantity_input)
        input_layout.addWidget(stock_button)

        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(3)
        self.stock_table.setHorizontalHeaderLabels(["Tên thuốc", "Hạn sử dụng", "Số lượng"])
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        stock_layout.addLayout(input_layout)
        stock_layout.addWidget(self.stock_table)
        self.tabs.addTab(self.stock_tab, "Nhập kho")

    def init_profit_tab(self):
        self.profit_tab = QWidget()
        profit_layout = QVBoxLayout(self.profit_tab)

        self.total_label = QLabel("Tổng thu nhập: 0 đ")
        font = self.total_label.font()
        font.setPointSize(16)
        self.total_label.setFont(font)

        self.profit_table = QTableWidget()
        self.profit_table.setColumnCount(3)
        self.profit_table.setHorizontalHeaderLabels(["Tên thuốc", "SL", "Tổng tiền"])
        self.profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        profit_layout.addWidget(self.total_label)
        profit_layout.addWidget(self.profit_table)
        self.tabs.addTab(self.profit_tab, "Lợi nhuận")

    def add_medicine(self):
        name = self.name_input.text().strip()
        date = self.date_input.date().toString("dd/MM/yyyy")
        quantity = self.quantity_input.value()

        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc!")
            return

        for med in self.medicines:
            if med["name"] == name and med["expiry"] == date:
                med["quantity"] += quantity
                break
        else:
            self.medicines.append({"name": name, "expiry": date, "quantity": quantity})

        self.save_data()
        self.update_stock_table()
        self.name_input.clear()

    def sell_medicine(self):
        name = self.sell_name_input.text().strip()
        sell_qty = self.sell_quantity_input.value()

        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc để bán!")
            return

        # Tìm các thuốc có tên khớp
        matches = [med for med in self.medicines if med["name"].lower() == name.lower() and med["quantity"] > 0]
        if not matches:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy thuốc trong kho hoặc đã hết!")
            return

        matches.sort(key=lambda m: datetime.strptime(m["expiry"], "%d/%m/%Y"))  # Ưu tiên hết hạn sớm

        qty_left = sell_qty
        for med in matches:
            if qty_left == 0:
                break

            if med["quantity"] >= qty_left:
                med["quantity"] -= qty_left
                self.sales.append({
                    "name": med["name"],
                    "expiry": med["expiry"],
                    "quantity": qty_left,
                    "date": datetime.now().strftime("%d/%m/%Y")
                })
                qty_left = 0
            else:
                sold_qty = med["quantity"]
                med["quantity"] = 0
                qty_left -= sold_qty
                self.sales.append({
                    "name": med["name"],
                    "expiry": med["expiry"],
                    "quantity": sold_qty,
                    "date": datetime.now().strftime("%d/%m/%Y")
                })

        if qty_left > 0:
            QMessageBox.warning(self, "Lỗi", "Không đủ thuốc trong kho để bán toàn bộ số lượng yêu cầu!")

        self.save_data()
        self.save_sales()
        self.update_stock_table()
        self.update_profit_table()

    def update_stock_table(self):
        self.stock_table.setRowCount(len(self.medicines))
        for i, med in enumerate(self.medicines):
            self.stock_table.setItem(i, 0, QTableWidgetItem(med["name"]))
            self.stock_table.setItem(i, 1, QTableWidgetItem(med["expiry"]))
            self.stock_table.setItem(i, 2, QTableWidgetItem(str(med["quantity"])))

    def update_profit_table(self):
        total = 0
        self.profit_table.setRowCount(len(self.sales))
        for i, sale in enumerate(self.sales):
            self.profit_table.setItem(i, 0, QTableWidgetItem(sale["name"]))
            self.profit_table.setItem(i, 1, QTableWidgetItem(str(sale["quantity"])))
            total_price = sale["quantity"] * 1000
            total += total_price
            self.profit_table.setItem(i, 2, QTableWidgetItem(f"{total_price:,} đ"))
        self.total_label.setText(f"Tổng thu nhập: {total:,} đ")

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                self.medicines = json.load(f)

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.medicines, f, ensure_ascii=False, indent=2)

    def load_sales(self):
        if os.path.exists(SALES_FILE):
            with open(SALES_FILE, 'r', encoding='utf-8') as f:
                self.sales = json.load(f)

    def save_sales(self):
        with open(SALES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.sales, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineManager()
    window.show()
    sys.exit(app.exec_())