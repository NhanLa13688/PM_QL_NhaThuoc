#Lệnh xuất file ra exe
# pip install pyinstaller
# pyinstaller --noconfirm --windowed --icon=icon.ico medicine_manager.py // có icon
# pyinstaller --noconfirm --windowed medicine_manager.py // chưa có icon

#
#
import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QMessageBox, QHeaderView, QCompleter,
    QDoubleSpinBox, QComboBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor, QBrush
from datetime import datetime

DATA_FILE = 'data.json'
SALES_FILE = 'sales.json'

def format_currency(value):
    return f"{int(value):,}".replace(",", ".")

class MedicineManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần mềm quản lý thuốc Hồng Phúc")
        self.resize(1100, 650)

        self.low_stock_threshold = 5
        self.medicines = []
        self.sales = []

        self.load_data()
        self.load_sales()

        self.init_ui()
        self.update_stock_table()
        self.update_profit_table()
        self.update_sell_history_table(self.sales)

    def init_ui(self):
        font = QFont()
        font.setPointSize(13)
        self.setFont(font)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.init_sell_tab()
        self.init_stock_tab()
        self.init_profit_tab()

        author_label = QLabel("Design by Nhan La | Phone: 0969168340 © 2025 Copyright Registered")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("color: gray; font-size: 10pt; margin-top: 10px;")
        layout.addWidget(author_label)

    def init_sell_tab(self):
        self.sell_tab = QWidget()
        sell_layout = QVBoxLayout(self.sell_tab)

        input_layout = QHBoxLayout()
        self.sell_name_input = QLineEdit()
        self.sell_name_input.setPlaceholderText("Nhập tên thuốc để bán")
        self.sell_quantity_input = QSpinBox()
        self.sell_quantity_input.setPrefix("SL: ")
        self.sell_quantity_input.setMinimum(1)
        self.sell_quantity_input.setMaximum(100_000_000)
        self.sell_quantity_input.setFixedWidth(100)
        self.sell_button = QPushButton("Bán thuốc")
        self.sell_button.setStyleSheet("background-color: green; color: white; font-weight: bold; font-size: 14pt; padding: 6px 12px; border-radius: 6px;")
        self.sell_button.clicked.connect(self.sell_medicine)

        input_layout.addWidget(self.sell_name_input)
        input_layout.addWidget(self.sell_quantity_input)
        input_layout.addWidget(self.sell_button)

        self.sell_history_table = QTableWidget()
        self.sell_history_table.setColumnCount(3)
        self.sell_history_table.setHorizontalHeaderLabels(["Tên thuốc", "Số lượng", "Thời gian bán"])
        self.sell_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        sell_layout.addLayout(input_layout)
        sell_layout.addWidget(self.sell_history_table)
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
        self.quantity_input.setPrefix("SL: ")
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(100_000_000)
        self.quantity_input.setFixedWidth(100)

        self.cost_input = QDoubleSpinBox()
        self.cost_input.setPrefix("Giá vốn: ")
        self.cost_input.setMaximum(100_000_000)
        self.cost_input.setDecimals(0)

        self.sell_input = QDoubleSpinBox()
        self.sell_input.setPrefix("Giá bán: ")
        self.sell_input.setMaximum(100_000_000)
        self.sell_input.setDecimals(0)

        stock_button = QPushButton("Nhập kho")
        stock_button.setStyleSheet("background-color: green; color: white; font-weight: bold; font-size: 14pt; padding: 6px 12px; border-radius: 6px;")
        stock_button.clicked.connect(self.add_medicine)

        delete_button = QPushButton("Xoá thuốc")
        delete_button.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 14pt; padding: 6px 12px; border-radius: 6px;")
        delete_button.clicked.connect(self.delete_selected_medicine)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.date_input)
        input_layout.addWidget(self.quantity_input)
        input_layout.addWidget(self.cost_input)
        input_layout.addWidget(self.sell_input)
        input_layout.addWidget(stock_button)
        input_layout.addWidget(delete_button)

        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(6)
        self.stock_table.setHorizontalHeaderLabels(["Tên thuốc", "Hạn sử dụng", "Số lượng", "Giá vốn", "Giá bán", "Ngày nhập"])
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stock_table.setEditTriggers(QTableWidget.NoEditTriggers)

        stock_layout.addLayout(input_layout)
        stock_layout.addWidget(self.stock_table)
        self.tabs.addTab(self.stock_tab, "Nhập kho")

    def init_profit_tab(self):
        self.profit_tab = QWidget()
        profit_layout = QVBoxLayout(self.profit_tab)

        filter_layout = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Tất cả", "Hôm nay", "Tuần này", "Tháng này", "Năm nay"])
        self.filter_combo.currentIndexChanged.connect(self.update_profit_table)
        filter_layout.addWidget(QLabel("Xem theo: "))
        filter_layout.addWidget(self.filter_combo)

        self.total_label = QLabel("Tổng lợi nhuận: 0 đ")
        font = self.total_label.font()
        font.setPointSize(16)
        self.total_label.setFont(font)

        self.profit_table = QTableWidget()
        self.profit_table.setColumnCount(6)
        self.profit_table.setHorizontalHeaderLabels(["Ngày", "Tên thuốc", "Số lượng", "Giá vốn", "Giá bán", "Lợi nhuận"])
        self.profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        profit_layout.addLayout(filter_layout)
        profit_layout.addWidget(self.total_label)
        profit_layout.addWidget(self.profit_table)
        self.tabs.addTab(self.profit_tab, "Lợi nhuận")

    def add_medicine(self):
        name = self.name_input.text().strip()
        date = self.date_input.date().toString("dd/MM/yyyy")
        quantity = self.quantity_input.value()
        cost = self.cost_input.value()
        sell = self.sell_input.value()
        import_date = datetime.now().strftime("%d/%m/%Y")

        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc!")
            return

        for med in self.medicines:
            if med["name"] == name and med["expiry"] == date:
                med["quantity"] += quantity
                med["cost_price"] = cost
                med["sell_price"] = sell
                break
        else:
            self.medicines.append({
                "name": name,
                "expiry": date,
                "quantity": quantity,
                "cost_price": cost,
                "sell_price": sell,
                "import_date": import_date
            })

        self.save_data()
        self.update_stock_table()
        self.name_input.clear()

    def sell_medicine(self):
        name = self.sell_name_input.text().strip()
        sell_qty = self.sell_quantity_input.value()

        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc để bán!")
            return

        matches = [m for m in self.medicines if m["name"].lower() == name.lower() and m["quantity"] > 0]
        if not matches:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy thuốc trong kho hoặc đã hết!")
            return

        matches.sort(key=lambda m: datetime.strptime(m["expiry"], "%d/%m/%Y"))
        qty_left = sell_qty
        for med in matches:
            if qty_left == 0:
                break
            sold = min(med["quantity"], qty_left)
            med["quantity"] -= sold
            qty_left -= sold
            self.sales.append({
                "name": med["name"],
                "expiry": med["expiry"],
                "quantity": sold,
                "cost_price": med["cost_price"],
                "sell_price": med["sell_price"],
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            })

        if qty_left > 0:
            QMessageBox.warning(self, "Lỗi", "Không đủ thuốc trong kho để bán toàn bộ số lượng yêu cầu!")

        self.save_data()
        self.save_sales()
        self.update_stock_table()
        self.update_profit_table()
        self.update_sell_history_table(self.sales)

    def delete_selected_medicine(self):
        row = self.stock_table.currentRow()
        if row < 0 or row >= len(self.medicines):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một thuốc để xoá.")
            return

        med = self.medicines[row]
        reply = QMessageBox.question(self, "Xác nhận xoá", f"Bạn có chắc muốn xoá thuốc '{med['name']}' hạn {med['expiry']}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.medicines[row]
            self.save_data()
            self.update_stock_table()

    def update_stock_table(self):
        self.medicines.sort(key=lambda m: datetime.strptime(m["expiry"], "%d/%m/%Y"))
        self.stock_table.setRowCount(len(self.medicines))
        for i, med in enumerate(self.medicines):
            self.stock_table.setItem(i, 0, QTableWidgetItem(med["name"]))
            expiry_item = QTableWidgetItem(med["expiry"])
            days_left = (datetime.strptime(med["expiry"], "%d/%m/%Y") - datetime.now()).days
            if days_left < 0:
                expiry_item.setBackground(QBrush(QColor("black")))
                expiry_item.setForeground(QBrush(QColor("white")))
            elif days_left <= 3:
                expiry_item.setBackground(QBrush(QColor("red")))
            elif days_left <= 7:
                expiry_item.setBackground(QBrush(QColor("orange")))
            self.stock_table.setItem(i, 1, expiry_item)
            qty_item = QTableWidgetItem(str(med["quantity"]))
            if med["quantity"] <= self.low_stock_threshold:
                qty_item.setBackground(QBrush(QColor("yellow")))
            self.stock_table.setItem(i, 2, qty_item)
            self.stock_table.setItem(i, 3, QTableWidgetItem(f"{format_currency(med['cost_price'])} đ"))
            self.stock_table.setItem(i, 4, QTableWidgetItem(f"{format_currency(med['sell_price'])} đ"))
            self.stock_table.setItem(i, 5, QTableWidgetItem(med.get("import_date", "-")))

        completer = QCompleter([m["name"] for m in self.medicines])
        self.sell_name_input.setCompleter(completer)
        self.name_input.setCompleter(completer)

    def update_profit_table(self):
        total_profit = 0
        self.profit_table.setRowCount(0)
        filtered_sales = []
        filter_option = self.filter_combo.currentText()
        for sale in self.sales:
            sale_dt = datetime.strptime(sale["date"], "%d/%m/%Y %H:%M:%S")
            now = datetime.now()
            add = filter_option == "Tất cả" or \
                  (filter_option == "Hôm nay" and sale_dt.date() == now.date()) or \
                  (filter_option == "Tuần này" and sale_dt.isocalendar()[1] == now.isocalendar()[1]) or \
                  (filter_option == "Tháng này" and sale_dt.month == now.month and sale_dt.year == now.year) or \
                  (filter_option == "Năm nay" and sale_dt.year == now.year)
            if add:
                filtered_sales.append(sale)

        self.profit_table.setRowCount(len(filtered_sales))
        for i, sale in enumerate(filtered_sales):
            self.profit_table.setItem(i, 0, QTableWidgetItem(sale["date"]))
            self.profit_table.setItem(i, 1, QTableWidgetItem(sale["name"]))
            self.profit_table.setItem(i, 2, QTableWidgetItem(str(sale["quantity"])))
            self.profit_table.setItem(i, 3, QTableWidgetItem(f"{format_currency(sale['cost_price'])} đ"))
            self.profit_table.setItem(i, 4, QTableWidgetItem(f"{format_currency(sale['sell_price'])} đ"))
            profit = (sale["sell_price"] - sale["cost_price"]) * sale["quantity"]
            total_profit += profit
            self.profit_table.setItem(i, 5, QTableWidgetItem(f"{format_currency(profit)} đ"))

        self.total_label.setText(f"Tổng lợi nhuận: {format_currency(total_profit)} đ")

    def update_sell_history_table(self, entries):
        self.sell_history_table.setRowCount(len(entries))
        for i, sale in enumerate(entries):
            self.sell_history_table.setItem(i, 0, QTableWidgetItem(sale["name"]))
            self.sell_history_table.setItem(i, 1, QTableWidgetItem(str(sale["quantity"])))
            self.sell_history_table.setItem(i, 2, QTableWidgetItem(sale["date"]))

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
