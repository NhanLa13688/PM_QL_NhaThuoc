import sys
import json
import os
from collections import OrderedDict
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QMessageBox, QHeaderView, QCompleter,
    QDoubleSpinBox, QComboBox, QInputDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor, QBrush
from datetime import datetime, date, timedelta
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

DATA_FILE = "data.json"
SALES_FILE = "sales.json"


def format_currency(value):
    try:
        return f"{int(round(value)):,}".replace(",", ".")
    except Exception:
        return str(value)


class MedicineManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần mềm quản lý thuốc Hồng Phúc")
        self.resize(1250, 750)

        self.low_stock_threshold = 5
        self.expiry_urgent_days = 7
        self.expiry_warn_days = 120

        self.medicines = []
        self.sales = []
        self.current_cart = []

        self.load_data()
        self.load_sales()

        self.init_ui()
        self.update_stock_table()
        self.update_profit_table()
        self.update_sell_history_table(self.sales)
        self.update_profit_chart()
        self.update_cart_table()

    # ===================== UI =====================
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

        author_label = QLabel("Design by Nhan La | Phone: 0969168340 © 2025")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("color: gray; font-size: 10pt; margin-top: 10px;")
        layout.addWidget(author_label)

    # ===================== TAB BÁN =====================
    def init_sell_tab(self):
        self.sell_tab = QWidget()
        sell_layout = QVBoxLayout(self.sell_tab)

        # Ô nhập tên khách
        self.customer_name_input = QLineEdit()
        self.customer_name_input.setPlaceholderText("Tên khách hàng")
        self.customer_name_input.setMinimumHeight(32)

        customer_layout = QVBoxLayout()
        customer_layout.addWidget(self.customer_name_input)

        hint_label = QLabel("Nếu không nhập tên thì mặc định là Khách lẻ")
        hint_label.setStyleSheet("color: gray; font-size: 10pt;")
        customer_layout.addWidget(hint_label)

        sell_layout.addLayout(customer_layout)

        # Nhập thuốc
        input_layout = QHBoxLayout()

        self.sell_name_input = QLineEdit()
        self.sell_name_input.setPlaceholderText("Nhập tên thuốc để bán")
        self.sell_name_input.setMinimumHeight(32)
        self.sell_name_input.textChanged.connect(self.auto_fill_unit)

        self.sell_quantity_input = QSpinBox()
        self.sell_quantity_input.setPrefix("SL: ")
        self.sell_quantity_input.setMinimum(1)
        self.sell_quantity_input.setMaximum(100_000_000)

        self.sell_unit_combo = QComboBox()
        self.sell_unit_combo.addItems(["Viên", "Hộp", "Bịt"])

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setPrefix("Giảm giá: ")
        self.discount_input.setMaximum(100_000_000)
        self.discount_input.setDecimals(0)

        self.add_cart_button = QPushButton("Thêm vào giỏ")
        self.add_cart_button.setStyleSheet("background-color: orange; color: white; font-weight: bold;")
        self.add_cart_button.clicked.connect(self.add_to_cart)

        self.confirm_button = QPushButton("Bán")
        self.confirm_button.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        self.confirm_button.clicked.connect(self.confirm_sale)

        input_layout.addWidget(self.sell_name_input)
        input_layout.addWidget(self.sell_quantity_input)
        input_layout.addWidget(self.sell_unit_combo)
        input_layout.addWidget(self.discount_input)
        input_layout.addWidget(self.add_cart_button)
        input_layout.addWidget(self.confirm_button)

        sell_layout.addLayout(input_layout)

        # Bảng giỏ hàng
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(4)
        self.cart_table.setHorizontalHeaderLabels(["Tên thuốc", "Số lượng", "Đơn vị", "Giảm giá"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Bảng lịch sử bán
        self.sell_history_table = QTableWidget()
        self.sell_history_table.setColumnCount(9)
        self.sell_history_table.setHorizontalHeaderLabels(
            ["Khách hàng", "Tên thuốc", "Số lượng", "Đơn vị", "Đơn giá",
             "Thành tiền", "Giảm giá", "Thời gian bán", "HSD"]
        )
        self.sell_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        sell_layout.addWidget(QLabel("Giỏ hàng hiện tại:"))
        sell_layout.addWidget(self.cart_table)
        sell_layout.addWidget(QLabel("Lịch sử bán:"))
        sell_layout.addWidget(self.sell_history_table)
        self.tabs.addTab(self.sell_tab, "Bán thuốc")

    # ===================== GIỎ HÀNG =====================
    def add_to_cart(self):
        raw = self.sell_name_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc!")
            return
        qty = self.sell_quantity_input.value()
        unit = self.sell_unit_combo.currentText()
        discount = self.discount_input.value()
        self.current_cart.append({
            "name": raw,
            "quantity": qty,
            "unit": unit,
            "discount": discount
        })
        self.update_cart_table()
        self.sell_name_input.clear()
        self.sell_quantity_input.setValue(1)
        self.discount_input.setValue(0)

    def update_cart_table(self):
        self.cart_table.setRowCount(len(self.current_cart))
        for i, item in enumerate(self.current_cart):
            self.cart_table.setItem(i, 0, QTableWidgetItem(item["name"]))
            self.cart_table.setItem(i, 1, QTableWidgetItem(str(item["quantity"])))
            self.cart_table.setItem(i, 2, QTableWidgetItem(item["unit"]))
            self.cart_table.setItem(i, 3, QTableWidgetItem(f"{format_currency(item['discount'])} đ"))

    def confirm_sale(self):
        if not self.current_cart:
            QMessageBox.warning(self, "Lỗi", "Giỏ hàng trống!")
            return

        customer_name = self.customer_name_input.text().strip() or "Khách lẻ"

        for item in self.current_cart:
            raw_name = item["name"]
            if " - " in raw_name:
                name, expiry = raw_name.split(" - ", 1)
            else:
                name, expiry = raw_name, None

            qty = item["quantity"]
            discount = item["discount"]

            matches = [m for m in self.medicines if m["name"] == name and m["quantity"] > 0]
            if expiry:
                matches = [m for m in matches if m["expiry"] == expiry]

            matches.sort(key=lambda m: datetime.strptime(m["expiry"], "%d/%m/%Y"))
            qty_left = qty

            for med in matches:
                if qty_left == 0:
                    break
                sold = min(med["quantity"], qty_left)
                med["quantity"] -= sold
                qty_left -= sold
                self.sales.append({
                    "customer": customer_name,
                    "name": med["name"],
                    "expiry": med["expiry"],
                    "quantity": sold,
                    "unit": med.get("unit", "Viên"),
                    "cost_price": med["cost_price"],
                    "sell_price": med["sell_price"],
                    "discount": discount if qty_left == 0 else 0,
                    "date": datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                })

            if qty_left > 0:
                QMessageBox.warning(self, "Lỗi", f"Không đủ {name} trong kho!")

        self.save_data()
        self.save_sales()
        self.update_stock_table()
        self.update_profit_table()
        self.update_sell_history_table(self.sales)
        self.update_profit_chart()
        self.current_cart = []
        self.update_cart_table()
        self.customer_name_input.clear()
        QMessageBox.information(self, "OK", f"Đã bán thành công cho khách: {customer_name}")

    # ===================== LỊCH SỬ BÁN =====================
    def update_sell_history_table(self, entries):
        reversed_entries = list(reversed(entries))
        self.sell_history_table.setRowCount(len(reversed_entries))
        for i, sale in enumerate(reversed_entries):
            self.sell_history_table.setItem(i, 0, QTableWidgetItem(sale.get("customer", "Khách lẻ")))
            self.sell_history_table.setItem(i, 1, QTableWidgetItem(sale.get("name", "")))
            qty_item = QTableWidgetItem(str(sale.get("quantity", 0))); qty_item.setTextAlignment(Qt.AlignCenter)
            self.sell_history_table.setItem(i, 2, qty_item)
            unit_item = QTableWidgetItem(sale.get("unit", "")); unit_item.setTextAlignment(Qt.AlignCenter)
            self.sell_history_table.setItem(i, 3, unit_item)
            unit_price_item = QTableWidgetItem(f"{format_currency(sale.get('sell_price', 0))} đ")
            unit_price_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 4, unit_price_item)
            total_price = float(sale.get("sell_price", 0)) * int(sale.get("quantity", 0))
            discount = float(sale.get("discount", 0))
            total_after_discount = total_price - discount
            total_item = QTableWidgetItem(f"{format_currency(total_after_discount)} đ"); total_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 5, total_item)
            discount_item = QTableWidgetItem(f"{format_currency(discount)} đ"); discount_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 6, discount_item)
            date_item = QTableWidgetItem(sale.get("date", "")); date_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 7, date_item)
            self.sell_history_table.setItem(i, 8, QTableWidgetItem(sale.get("expiry", "")))

    # ===================== TAB NHẬP =====================
    def init_stock_tab(self):
        self.stock_tab = QWidget()
        stock_layout = QVBoxLayout(self.stock_tab)

        form_layout = QHBoxLayout()
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("Tên thuốc")
        self.date_input = QDateEdit(); self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy"); self.date_input.setDate(QDate.currentDate())

        self.quantity_input = QSpinBox(); self.quantity_input.setPrefix("SL: ")
        self.quantity_input.setMinimum(1); self.quantity_input.setMaximum(100_000_000)

        self.unit_input = QComboBox(); self.unit_input.addItems(["Viên", "Hộp", "Bịt", "Thêm mới..."])
        self.unit_input.currentIndexChanged.connect(self.add_new_unit)

        self.cost_input = QDoubleSpinBox(); self.cost_input.setPrefix("Giá vốn: ")
        self.cost_input.setMaximum(100_000_000); self.cost_input.setDecimals(0)

        self.sell_input = QDoubleSpinBox(); self.sell_input.setPrefix("Giá bán: ")
        self.sell_input.setMaximum(100_000_000); self.sell_input.setDecimals(0)

        stock_button = QPushButton("Nhập kho")
        stock_button.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        stock_button.clicked.connect(self.add_medicine)

        edit_button = QPushButton("Sửa giá")
        edit_button.setStyleSheet("background-color:#0b74de; color: white; font-weight: bold;")
        edit_button.clicked.connect(self.edit_price_selected_medicine)

        edit_expiry_button = QPushButton("Sửa HSD")
        edit_expiry_button.setStyleSheet("background-color:#ff8800; color: white; font-weight: bold;")
        edit_expiry_button.clicked.connect(self.edit_expiry_selected_medicine)

        delete_button = QPushButton("Xoá thuốc")
        delete_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        delete_button.clicked.connect(self.delete_selected_medicine)

        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.date_input)
        form_layout.addWidget(self.quantity_input)
        form_layout.addWidget(self.unit_input)
        form_layout.addWidget(self.cost_input)
        form_layout.addWidget(self.sell_input)
        form_layout.addWidget(stock_button)
        form_layout.addWidget(edit_button)
        form_layout.addWidget(edit_expiry_button)
        form_layout.addWidget(delete_button)

        search_layout = QHBoxLayout()
        self.stock_search_input = QLineEdit()
        self.stock_search_input.setPlaceholderText("Tìm kiếm trong kho")
        try:
            self.stock_search_input.setClearButtonEnabled(True)
        except Exception:
            pass
        self.stock_search_input.textChanged.connect(self.update_stock_table)
        search_layout.addWidget(QLabel("Tìm:"))
        search_layout.addWidget(self.stock_search_input)

        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(7)
        self.stock_table.setHorizontalHeaderLabels(
            ["Tên thuốc", "HSD", "Số lượng", "Đơn vị", "Giá vốn", "Giá bán", "Ngày nhập"]
        )
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stock_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        stock_layout.addLayout(form_layout)
        stock_layout.addLayout(search_layout)
        stock_layout.addWidget(self.stock_table)
        self.tabs.addTab(self.stock_tab, "Nhập kho")

    def edit_expiry_selected_medicine(self):
        row = self.stock_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thuốc để sửa HSD.")
            return
        med = self.medicines[row]

        new_date, ok = QInputDialog.getText(self, "Sửa HSD",
                                            f"HSD mới cho '{med['name']}' (dd/MM/yyyy):",
                                            text=med['expiry'])
        if not ok or not new_date.strip():
            return
        try:
            datetime.strptime(new_date.strip(), "%d/%m/%Y")
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Định dạng ngày không hợp lệ (dd/MM/yyyy).")
            return

        med["expiry"] = new_date.strip()
        self.save_data()
        self.update_stock_table()
        QMessageBox.information(self, "Thành công", f"Đã cập nhật HSD mới: {new_date}")

    # ===================== TAB LỢI NHUẬN =====================
    def init_profit_tab(self):
        self.profit_tab = QWidget()
        profit_layout = QVBoxLayout(self.profit_tab)

        top_layout = QVBoxLayout()
        self.total_label = QLabel("Tổng lợi nhuận: 0 đ")
        f = self.total_label.font(); f.setPointSize(16)
        self.total_label.setFont(f)
        self.total_label.setStyleSheet("color:#ff6600;")

        self.sales_label = QLabel("Tổng doanh số: 0 đ")
        self.sales_label.setFont(self.total_label.font())
        self.sales_label.setStyleSheet("color:#0066cc;")

        self.capital_label = QLabel("Vốn đang bỏ ra: 0 đ")
        self.capital_label.setFont(self.total_label.font())
        self.capital_label.setStyleSheet("color:#333;")

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Xem theo:"))
        self.period_combo = QComboBox(); self.period_combo.addItems(["Ngày", "Tuần", "Tháng", "Năm"])
        self.period_combo.currentIndexChanged.connect(self.on_period_changed)
        filter_layout.addWidget(self.period_combo); filter_layout.addStretch()

        top_layout.addWidget(self.total_label, alignment=Qt.AlignLeft)
        top_layout.addWidget(self.sales_label, alignment=Qt.AlignLeft)
        top_layout.addWidget(self.capital_label, alignment=Qt.AlignLeft)
        top_layout.addLayout(filter_layout)

        self.profit_table = QTableWidget()
        self.profit_table.setColumnCount(7)
        self.profit_table.setHorizontalHeaderLabels(
            ["Ngày", "Tên thuốc", "Số lượng", "Đơn vị", "Giá vốn", "Giá bán", "Lợi nhuận"]
        )
        self.profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.figure = Figure(figsize=(6.2, 3.8))
        self.canvas = FigureCanvas(self.figure)

        profit_layout.addLayout(top_layout)
        profit_layout.addWidget(self.canvas)
        profit_layout.addWidget(self.profit_table)
        self.tabs.addTab(self.profit_tab, "Lợi nhuận")

    # ===================== HÀM QUẢN LÝ KHO =====================
    def add_new_unit(self):
        if self.unit_input.currentText() == "Thêm mới...":
            text, ok = QInputDialog.getText(self, "Thêm đơn vị mới", "Nhập đơn vị:")
            if ok and text.strip():
                self.unit_input.insertItem(self.unit_input.count() - 1, text.strip())
                self.unit_input.setCurrentText(text.strip())
            else:
                self.unit_input.setCurrentIndex(0)

    def add_medicine(self):
        name = self.name_input.text().strip()
        date_str = self.date_input.date().toString("dd/MM/yyyy")
        quantity = self.quantity_input.value()
        unit = self.unit_input.currentText()
        cost = self.cost_input.value()
        sell = self.sell_input.value()
        import_date = datetime.now().strftime("%d/%m/%Y")

        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc!")
            return

        for med in self.medicines:
            if med["name"] == name and med["expiry"] == date_str and med.get("unit", "Viên") == unit:
                med["quantity"] += quantity
                med["cost_price"] = cost
                med["sell_price"] = sell
                med["unit"] = unit
                break
        else:
            self.medicines.append({
                "name": name,
                "expiry": date_str,
                "quantity": quantity,
                "unit": unit,
                "cost_price": cost,
                "sell_price": sell,
                "import_date": import_date
            })

        self.save_data()
        self.update_stock_table()
        self.update_profit_table()
        self.update_profit_chart()
        self.name_input.clear()

    # ===================== GỢI Ý TÊN + HSD =====================
    def auto_fill_unit(self):
        text = self.sell_name_input.text().strip().lower()
        if not text:
            return
        matches = [m for m in self.medicines if text in m["name"].lower()]
        unique_labels = sorted({f"{m['name']} - {m['expiry']}" for m in matches})
        if len(unique_labels) == 1:
            chosen = unique_labels[0]
            self.sell_name_input.blockSignals(True)
            self.sell_name_input.setText(chosen)
            self.sell_name_input.blockSignals(False)
            for m in matches:
                if f"{m['name']} - {m['expiry']}" == chosen:
                    self.sell_unit_combo.setCurrentText(m.get("unit", "Viên"))
                    break

    # ===================== CHỈNH SỬA GIÁ =====================
    def edit_price_selected_medicine(self):
        row = self.stock_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thuốc để sửa giá.")
            return
        med = self.medicines[row]
        current_cost = float(med.get("cost_price", 0))
        current_sell = float(med.get("sell_price", 0))
        new_cost, ok1 = QInputDialog.getDouble(self, "Sửa giá vốn", f"Giá vốn mới cho {med['name']}:", current_cost, 0, 100_000_000, 0)
        if not ok1: return
        new_sell, ok2 = QInputDialog.getDouble(self, "Sửa giá bán", f"Giá bán mới cho {med['name']}:", current_sell, 0, 100_000_000, 0)
        if not ok2: return
        med["cost_price"] = new_cost
        med["sell_price"] = new_sell
        self.save_data()
        self.update_stock_table()
        self.update_profit_table()

    def delete_selected_medicine(self):
        row = self.stock_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thuốc để xoá.")
            return
        med = self.medicines[row]
        reply = QMessageBox.question(self, "Xác nhận", f"Xoá thuốc {med['name']} hạn {med['expiry']}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.medicines[row]
            self.save_data()
            self.update_stock_table()
            self.update_profit_table()
            self.update_profit_chart()

    def update_stock_table(self):
        q = self.stock_search_input.text().strip().lower() if hasattr(self, "stock_search_input") else ""
        rows = [m for m in self.medicines if q in m.get("name", "").lower()] if q else self.medicines
        self.stock_table.setRowCount(len(rows))
        for i, med in enumerate(rows):
            self.stock_table.setItem(i, 0, QTableWidgetItem(med["name"]))
            expiry_item = QTableWidgetItem(med["expiry"])
            try:
                expiry_date = datetime.strptime(med["expiry"], "%d/%m/%Y")
                days_left = (expiry_date - datetime.now()).days
            except:
                days_left = 999999
            if days_left < 0:
                expiry_item.setBackground(QBrush(QColor("black"))); expiry_item.setForeground(QBrush(QColor("white")))
            elif days_left <= self.expiry_urgent_days:
                expiry_item.setBackground(QBrush(QColor("red")))
            elif days_left <= self.expiry_warn_days:
                expiry_item.setBackground(QBrush(QColor("orange")))
            self.stock_table.setItem(i, 1, expiry_item)
            qty_item = QTableWidgetItem(str(med["quantity"]))
            if med["quantity"] <= self.low_stock_threshold:
                qty_item.setBackground(QBrush(QColor("yellow")))
            self.stock_table.setItem(i, 2, qty_item)
            self.stock_table.setItem(i, 3, QTableWidgetItem(med.get("unit", "Viên")))
            self.stock_table.setItem(i, 4, QTableWidgetItem(f"{format_currency(med['cost_price'])} đ"))
            self.stock_table.setItem(i, 5, QTableWidgetItem(f"{format_currency(med['sell_price'])} đ"))
            self.stock_table.setItem(i, 6, QTableWidgetItem(med.get("import_date", "-")))

        names = sorted({f"{m['name']} - {m['expiry']}" for m in self.medicines if m.get("name")})
        completer = QCompleter(names); completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains); completer.setCompletionMode(QCompleter.PopupCompletion)
        self.sell_name_input.setCompleter(completer)

        completer2 = QCompleter(sorted({m["name"] for m in self.medicines if m.get("name")}))
        completer2.setCaseSensitivity(Qt.CaseInsensitive)
        completer2.setFilterMode(Qt.MatchContains); completer2.setCompletionMode(QCompleter.PopupCompletion)
        self.name_input.setCompleter(completer2)

    # ===================== LỢI NHUẬN =====================
    def _calc_invested_capital(self):
        return sum(float(m.get("cost_price", 0)) * int(m.get("quantity", 0)) for m in self.medicines)

    def _period_key(self, dt: datetime, period: str) -> str:
        if period == "Ngày": return dt.strftime("%d/%m/%Y")
        elif period == "Tuần":
            iso_year, iso_week, _ = dt.isocalendar()
            return f"W{iso_week:02d}/{iso_year}"
        elif period == "Tháng": return dt.strftime("%m/%Y")
        else: return dt.strftime("%Y")

    def _filtered_sales_for_current_bucket(self):
        period = self.period_combo.currentText()
        today = datetime.now()
        target_key = self._period_key(today, period)
        filtered = []
        for s in self.sales:
            try: dt = datetime.strptime(s.get("date", ""), "%H:%M:%S %d/%m/%Y")
            except: continue
            if self._period_key(dt, period) == target_key:
                filtered.append(s)
        return filtered

    def update_profit_table(self):
        sales_in_bucket = self._filtered_sales_for_current_bucket()
        total_profit, total_sales_amount = 0.0, 0.0
        self.profit_table.setRowCount(len(sales_in_bucket))
        for i, sale in enumerate(sales_in_bucket):
            qty = int(sale.get("quantity", 0))
            unit_price = float(sale.get("sell_price", 0))
            discount = float(sale.get("discount", 0))
            cost_price = float(sale.get("cost_price", 0))
            sales_amount = unit_price * qty - discount
            total_sales_amount += sales_amount
            profit = sales_amount - (cost_price * qty)
            total_profit += profit
            self.profit_table.setItem(i, 0, QTableWidgetItem(sale.get("date", "")))
            self.profit_table.setItem(i, 1, QTableWidgetItem(sale.get("name", "")))
            self.profit_table.setItem(i, 2, QTableWidgetItem(str(qty)))
            self.profit_table.setItem(i, 3, QTableWidgetItem(sale.get("unit", "")))
            self.profit_table.setItem(i, 4, QTableWidgetItem(f"{format_currency(cost_price)} đ"))
            self.profit_table.setItem(i, 5, QTableWidgetItem(f"{format_currency(unit_price)} đ"))
            self.profit_table.setItem(i, 6, QTableWidgetItem(f"{format_currency(profit)} đ"))
        self.total_label.setText(f"Tổng lợi nhuận: {format_currency(total_profit)} đ")
        self.sales_label.setText(f"Tổng doanh số: {format_currency(total_sales_amount)} đ")
        self.capital_label.setText(f"Vốn đang bỏ ra: {format_currency(self._calc_invested_capital())} đ")

    def _iter_sales(self):
        for s in self.sales:
            try: dt = datetime.strptime(s.get("date", ""), "%H:%M:%S %d/%m/%Y")
            except: continue
            qty = int(s.get("quantity", 0))
            discount = float(s.get("discount", 0) or 0)
            revenue = float(s.get("sell_price", 0)) * qty - discount
            cost = float(s.get("cost_price", 0)) * qty
            profit = revenue - cost
            yield dt, profit

    def _gen_period_labels(self, period):
        today = date.today()
        if period == "Ngày":
            return [(today - timedelta(days=i)).strftime("%d/%m/%Y") for i in range(13, -1, -1)]
        elif period == "Tuần":
            labels, d, seen = [], today, 0
            while seen < 12:
                iso_y, iso_w, _ = d.isocalendar()
                lbl = f"W{iso_w:02d}/{iso_y}"
                if not labels or labels[-1] != lbl:
                    labels.append(lbl); seen += 1
                d -= timedelta(days=7)
            labels.reverse(); return labels
        elif period == "Tháng":
            labels, y, m = [], today.year, today.month
            for _ in range(12):
                labels.append(f"{m:02d}/{y}")
                m -= 1
                if m == 0: m = 12; y -= 1
            labels.reverse(); return labels
        else:
            return [str(today.year - i) for i in range(4, -1, -1)]

    def _aggregate_profit(self, period: str):
        labels = self._gen_period_labels(period)
        buckets = OrderedDict((k, 0.0) for k in labels)
        for dt, profit in self._iter_sales():
            if period == "Ngày": key = dt.strftime("%d/%m/%Y")
            elif period == "Tuần":
                iso_year, iso_week, _ = dt.isocalendar(); key = f"W{iso_week:02d}/{iso_year}"
            elif period == "Tháng": key = dt.strftime("%m/%Y")
            else: key = dt.strftime("%Y")
            if key in buckets: buckets[key] += profit
        return buckets

    def update_profit_chart(self):
        period = self.period_combo.currentText()
        agg = self._aggregate_profit(period)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        labels = list(agg.keys())
        values = [v for v in agg.values()]
        def money_fmt(x, _pos):
            try: return f"{int(round(x)):,}".replace(",", ".") + " đ"
            except: return str(x)
        ax.yaxis.set_major_formatter(FuncFormatter(money_fmt))
        ax.grid(True, axis='y', linestyle='--', linewidth=0.6, alpha=0.6)
        bars = ax.bar(range(len(values)), values)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45 if period != "Năm" else 0, ha="right")
        ax.set_ylabel("Lợi nhuận (đ)")
        ax.set_title(f"Lợi nhuận theo {period.lower()}")
        ymax = max(values) if values else 1.0
        ax.set_ylim(0, ymax * 1.15)
        for rect, val in zip(bars, values):
            ax.annotate(format_currency(val), xy=(rect.get_x() + rect.get_width()/2, rect.get_height()),
                        xytext=(0, 6), textcoords="offset points", ha='center', va='bottom', fontsize=9)
        self.figure.tight_layout()
        self.canvas.draw()

    def on_period_changed(self):
        self.update_profit_chart()
        self.update_profit_table()

    # ===================== LƯU / LOAD =====================
    def load_data(self):
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.medicines = json.load(f)
            except: self.medicines = []
        else: self.medicines = []
        changed = False
        for med in self.medicines:
            if "unit" not in med:
                med["unit"] = "Viên"; changed = True
        if changed: self.save_data()

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.medicines, f, ensure_ascii=False, indent=2)

    def load_sales(self):
        if os.path.exists(SALES_FILE) and os.path.getsize(SALES_FILE) > 0:
            try:
                with open(SALES_FILE, 'r', encoding='utf-8') as f:
                    self.sales = json.load(f)
            except: self.sales = []
        else: self.sales = []
        med_index = {(m.get("name",""), m.get("expiry","")): m.get("unit","Viên") for m in self.medicines}
        changed = False
        for s in self.sales:
            if "unit" not in s:
                s["unit"] = med_index.get((s.get("name",""), s.get("expiry","")), ""); changed = True
        if changed: self.save_sales()

    def save_sales(self):
        with open(SALES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.sales, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineManager()
    window.show()
    sys.exit(app.exec_())
