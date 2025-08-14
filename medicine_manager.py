import sys
import json
import os
from collections import OrderedDict
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QMessageBox, QHeaderView, QCompleter,
    QDoubleSpinBox, QComboBox, QInputDialog, QSizePolicy,
    QGridLayout, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor, QBrush
from datetime import datetime, date, timedelta

# ---- matplotlib embed for PyQt5 ----
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

DATA_FILE = 'data.json'
SALES_FILE = 'sales.json'


def format_currency(value):
    try:
        return f"{int(round(value)):,}".replace(",", ".")
    except Exception:
        return str(value)


class MedicineManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần mềm quản lý thuốc Hồng Phúc")
        self.resize(1200, 700)

        self.low_stock_threshold = 5
        self.medicines = []
        self.sales = []

        # Load (with migration)
        self.load_data()
        self.load_sales()

        self.init_ui()
        self.update_stock_table()
        self.update_profit_table()
        self.update_sell_history_table(self.sales)
        self.update_profit_chart()

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

        input_layout = QGridLayout()
        input_layout.setHorizontalSpacing(16)
        input_layout.setVerticalSpacing(6)

        self.sell_name_input = QLineEdit()
        self.sell_name_input.setPlaceholderText("Nhập tên thuốc để bán")
        self.sell_name_input.setMinimumWidth(180)
        self.sell_name_input.setMinimumHeight(32)
        self.sell_name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sell_name_input.textChanged.connect(self.auto_fill_unit)
        self.sell_name_input.returnPressed.connect(self.sell_medicine)

        self.sell_quantity_input = QSpinBox()
        self.sell_quantity_input.setPrefix("SL: ")
        self.sell_quantity_input.setMinimum(1)
        self.sell_quantity_input.setMaximum(100_000_000)
        self.sell_quantity_input.setMinimumWidth(90)
        self.sell_quantity_input.setMinimumHeight(32)
        self.sell_quantity_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.sell_unit_combo = QComboBox()
        self.sell_unit_combo.addItems(["Viên", "Hộp", "Bịt"])
        self.sell_unit_combo.setMinimumWidth(90)
        self.sell_unit_combo.setMinimumHeight(32)
        self.sell_unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setPrefix("Giảm giá: ")
        self.discount_input.setMaximum(100_000_000)
        self.discount_input.setDecimals(0)
        self.discount_input.setMinimumWidth(100)
        self.discount_input.setMinimumHeight(32)
        self.discount_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.sell_button = QPushButton("Bán thuốc")
        self.sell_button.setStyleSheet(
            "background-color: green; color: white; font-weight: bold; "
            "font-size: 14pt; padding: 6px 12px; border-radius: 6px;"
        )
        self.sell_button.setMinimumWidth(110)
        self.sell_button.setMinimumHeight(36)
        self.sell_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.sell_button.clicked.connect(self.sell_medicine)  # GẮN SỰ KIỆN

        # Đặt các widget vào lưới
        input_layout.addWidget(self.sell_name_input, 0, 0)
        input_layout.addWidget(self.sell_quantity_input, 0, 1)
        input_layout.addWidget(self.sell_unit_combo, 0, 2)
        input_layout.addWidget(self.discount_input, 0, 3)
        input_layout.addWidget(self.sell_button, 0, 4)

        # Thêm spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        input_layout.addWidget(spacer, 0, 5)

        # Giãn cột
        input_layout.setColumnStretch(0, 2)
        input_layout.setColumnStretch(1, 1)
        input_layout.setColumnStretch(2, 1)
        input_layout.setColumnStretch(3, 1)
        input_layout.setColumnStretch(4, 0)
        input_layout.setColumnStretch(5, 3)

        self.sell_history_table = QTableWidget()
        self.sell_history_table.setColumnCount(8)
        self.sell_history_table.setHorizontalHeaderLabels(
            ["Tên thuốc", "Số lượng", "Đơn vị", "Đơn giá", "Thành tiền", "Giảm giá", "Thời gian bán", "HSD"]
        )
        self.sell_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        sell_layout.addLayout(input_layout)
        sell_layout.addWidget(self.sell_history_table)
        self.tabs.addTab(self.sell_tab, "Bán thuốc")

    # ===================== TAB NHẬP =====================
    def init_stock_tab(self):
        self.stock_tab = QWidget()
        stock_layout = QVBoxLayout(self.stock_tab)

        # Hàng nhập liệu
        form_layout = QHBoxLayout()
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("Tên thuốc")
        self.date_input = QDateEdit(); self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy"); self.date_input.setDate(QDate.currentDate())

        self.quantity_input = QSpinBox(); self.quantity_input.setPrefix("SL: ")
        self.quantity_input.setMinimum(1); self.quantity_input.setMaximum(100_000_000)
        self.quantity_input.setFixedWidth(100)

        self.unit_input = QComboBox(); self.unit_input.addItems(["Viên", "Hộp", "Bịt", "Thêm mới..."])
        self.unit_input.setFixedWidth(120); self.unit_input.currentIndexChanged.connect(self.add_new_unit)

        self.cost_input = QDoubleSpinBox(); self.cost_input.setPrefix("Giá vốn: ")
        self.cost_input.setMaximum(100_000_000); self.cost_input.setDecimals(0)

        self.sell_input = QDoubleSpinBox(); self.sell_input.setPrefix("Giá bán: ")
        self.sell_input.setMaximum(100_000_000); self.sell_input.setDecimals(0)

        stock_button = QPushButton("Nhập kho")
        stock_button.setStyleSheet("background-color: green; color: white; font-weight: bold; font-size: 14pt; padding: 6px 12px; border-radius: 6px;")
        stock_button.clicked.connect(self.add_medicine)

        delete_button = QPushButton("Xoá thuốc")
        delete_button.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 14pt; padding: 6px 12px; border-radius: 6px;")
        delete_button.clicked.connect(self.delete_selected_medicine)

        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.date_input)
        form_layout.addWidget(self.quantity_input)
        form_layout.addWidget(self.unit_input)
        form_layout.addWidget(self.cost_input)
        form_layout.addWidget(self.sell_input)
        form_layout.addWidget(stock_button)
        form_layout.addWidget(delete_button)

        # Ô TÌM KIẾM
        search_layout = QHBoxLayout()
        self.stock_search_input = QLineEdit()
        self.stock_search_input.setPlaceholderText("Tìm kiếm trong kho (Tên thuốc / Đơn vị / HSD)")
        try:
            self.stock_search_input.setClearButtonEnabled(True)
        except Exception:
            pass
        self.stock_search_input.textChanged.connect(self.update_stock_table)
        search_layout.addWidget(QLabel("Tìm:"))
        search_layout.addWidget(self.stock_search_input)

        # Bảng kho
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(7)
        self.stock_table.setHorizontalHeaderLabels(
            ["Tên thuốc", "Hạn sử dụng", "Số lượng", "Đơn vị", "Giá vốn", "Giá bán", "Ngày nhập"]
        )
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stock_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # đúng enum

        stock_layout.addLayout(form_layout)
        stock_layout.addLayout(search_layout)
        stock_layout.addWidget(self.stock_table)
        self.tabs.addTab(self.stock_tab, "Nhập kho")

    # ===================== TAB LỢI NHUẬN =====================
    def init_profit_tab(self):
        self.profit_tab = QWidget()
        profit_layout = QVBoxLayout(self.profit_tab)

        top_layout = QVBoxLayout()
        self.total_label = QLabel("Tổng lợi nhuận: 0 đ")
        f = self.total_label.font(); f.setPointSize(16); self.total_label.setFont(f)
        self.capital_label = QLabel("Vốn đang bỏ ra: 0 đ")
        cf = self.capital_label.font(); cf.setPointSize(16); self.capital_label.setFont(cf)
        self.capital_label.setStyleSheet("color:#333;")

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Xem theo:"))
        self.period_combo = QComboBox(); self.period_combo.addItems(["Ngày", "Tuần", "Tháng", "Năm"])
        self.period_combo.currentIndexChanged.connect(self.update_profit_chart)
        filter_layout.addWidget(self.period_combo); filter_layout.addStretch()

        top_layout.addWidget(self.total_label, alignment=Qt.AlignLeft)
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

    # ===================== XỬ LÝ =====================
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
        self.name_input.clear()

    def sell_medicine(self):
        raw = self.sell_name_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thuốc để bán!")
            return

        query = raw.lower()
        candidate_names = sorted({m["name"] for m in self.medicines if query in m["name"].lower()})
        if not candidate_names:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy thuốc trong kho!")
            return

        if len(candidate_names) == 1:
            chosen_name = candidate_names[0]
        else:
            chosen_name, ok = QInputDialog.getItem(
                self, "Chọn thuốc", "Có nhiều kết quả, chọn đúng tên:", candidate_names, 0, False
            )
            if not ok:
                return

        sell_qty = self.sell_quantity_input.value()
        discount = self.discount_input.value()
        matches = [med for med in self.medicines if med["name"] == chosen_name and med["quantity"] > 0]
        if not matches:
            QMessageBox.warning(self, "Lỗi", "Thuốc đã hết trong kho!")
            return

        self.sell_name_input.setText(chosen_name)
        self.sell_unit_combo.setCurrentText(matches[0].get("unit", "Viên"))

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
                "unit": med.get("unit", "Viên"),
                "cost_price": med["cost_price"],
                "sell_price": med["sell_price"],
                "discount": discount if qty_left == 0 else 0,  # giảm giá cho dòng cuối cùng
                "date": datetime.now().strftime("%H:%M:%S %d/%m/%Y")
            })

        if qty_left > 0:
            QMessageBox.warning(self, "Lỗi", "Không đủ thuốc trong kho để bán toàn bộ số lượng yêu cầu!")

        self.save_data()
        self.save_sales()
        self.update_stock_table()
        self.update_profit_table()
        self.update_sell_history_table(self.sales)
        self.update_profit_chart()

    def auto_fill_unit(self):
        text = self.sell_name_input.text().strip().lower()
        if not text:
            return
        matches = [m for m in self.medicines if text in m["name"].lower()]
        unique_names = sorted({m["name"] for m in matches})
        if len(unique_names) == 1:
            chosen = unique_names[0]
            self.sell_name_input.blockSignals(True)
            self.sell_name_input.setText(chosen)
            self.sell_name_input.blockSignals(False)
            for m in matches:
                if m["name"] == chosen:
                    self.sell_unit_combo.setCurrentText(m.get("unit", "Viên"))
                    break

    def delete_selected_medicine(self):
        row = self.stock_table.currentRow()

        # Dựng lại danh sách hiển thị (kể cả đang lọc)
        try:
            q = self.stock_search_input.text().strip().lower()
        except Exception:
            q = ""
        if q:
            rows = [
                m for m in self.medicines
                if q in m.get("name", "").lower()
                or q in m.get("unit", "").lower()
                or q in m.get("expiry", "").lower()
            ]
        else:
            rows = list(self.medicines)

        if row < 0 or row >= len(rows):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một thuốc để xoá.")
            return

        med = rows[row]
        reply = QMessageBox.question(
            self, "Xác nhận xoá",
            f"Bạn có chắc muốn xoá thuốc '{med['name']}' hạn {med['expiry']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            idx = self.medicines.index(med)  # index thực
            del self.medicines[idx]
            self.save_data()
            self.update_stock_table()
            self.update_profit_table()
            self.update_profit_chart()

    # ===================== CẬP NHẬT BẢNG (CÓ LỌC) =====================
    def update_stock_table(self):
        # đọc từ ô tìm kiếm
        q = ""
        try:
            q = self.stock_search_input.text().strip().lower()
        except Exception:
            q = ""

        # áp filter theo tên / đơn vị / hạn sử dụng
        if q:
            rows = [
                m for m in self.medicines
                if q in m.get("name", "").lower()
                or q in m.get("unit", "").lower()
                or q in m.get("expiry", "").lower()
            ]
        else:
            rows = list(self.medicines)

        self.stock_table.setRowCount(len(rows))
        for i, med in enumerate(rows):
            self.stock_table.setItem(i, 0, QTableWidgetItem(med["name"]))

            expiry_item = QTableWidgetItem(med["expiry"])
            try:
                expiry_date = datetime.strptime(med["expiry"], "%d/%m/%Y")
                days_left = (expiry_date - datetime.now()).days
            except Exception:
                days_left = 999999
            if days_left < 0:
                expiry_item.setBackground(QBrush(QColor("black"))); expiry_item.setForeground(QBrush(QColor("white")))
            elif days_left <= 3:
                expiry_item.setBackground(QBrush(QColor("red")))
            elif days_left <= 7:
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

        # Completer cho Bán & Nhập
        names = sorted({m["name"] for m in self.medicines if m.get("name")})
        completer = QCompleter(names); completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains); completer.setCompletionMode(QCompleter.PopupCompletion)
        self.sell_name_input.setCompleter(completer)

        completer2 = QCompleter(names); completer2.setCaseSensitivity(Qt.CaseInsensitive)
        completer2.setFilterMode(Qt.MatchContains); completer2.setCompletionMode(QCompleter.PopupCompletion)
        self.name_input.setCompleter(completer2)

    def _calc_invested_capital(self):
        total = 0.0
        for m in self.medicines:
            try:
                total += float(m.get("cost_price", 0)) * int(m.get("quantity", 0))
            except Exception:
                pass
        return total

    def update_profit_table(self):
        total_profit = 0
        self.profit_table.setRowCount(len(self.sales))
        for i, sale in enumerate(self.sales):
            self.profit_table.setItem(i, 0, QTableWidgetItem(sale.get("date", "")))
            self.profit_table.setItem(i, 1, QTableWidgetItem(sale.get("name", "")))
            self.profit_table.setItem(i, 2, QTableWidgetItem(str(sale.get("quantity", 0))))
            self.profit_table.setItem(i, 3, QTableWidgetItem(sale.get("unit", "")))
            cost = float(sale.get("cost_price", 0)) * int(sale.get("quantity", 0))
            revenue = float(sale.get("sell_price", 0)) * int(sale.get("quantity", 0)) - float(sale.get("discount", 0))
            profit = revenue - cost
            total_profit += profit
            self.profit_table.setItem(i, 4, QTableWidgetItem(f"{format_currency(sale.get('cost_price', 0))} đ"))
            self.profit_table.setItem(i, 5, QTableWidgetItem(f"{format_currency(sale.get('sell_price', 0))} đ"))
            self.profit_table.setItem(i, 6, QTableWidgetItem(f"{format_currency(profit)} đ"))

        self.total_label.setText(f"Tổng lợi nhuận: {format_currency(total_profit)} đ")
        capital = self._calc_invested_capital()
        self.capital_label.setText(f"Vốn đang bỏ ra: {format_currency(capital)} đ")

    def update_sell_history_table(self, entries):
        reversed_entries = list(reversed(entries))
        self.sell_history_table.setRowCount(len(reversed_entries))
        for i, sale in enumerate(reversed_entries):
            self.sell_history_table.setItem(i, 0, QTableWidgetItem(sale.get("name", "")))
            qty_item = QTableWidgetItem(str(sale.get("quantity", 0))); qty_item.setTextAlignment(Qt.AlignCenter)
            self.sell_history_table.setItem(i, 1, qty_item)
            unit_item = QTableWidgetItem(sale.get("unit", "")); unit_item.setTextAlignment(Qt.AlignCenter)
            self.sell_history_table.setItem(i, 2, unit_item)
            unit_price_item = QTableWidgetItem(f"{format_currency(sale.get('sell_price', 0))} đ")
            unit_price_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 3, unit_price_item)
            total_price = float(sale.get("sell_price", 0)) * int(sale.get("quantity", 0))
            discount = float(sale.get("discount", 0))
            total_after_discount = total_price - discount
            total_item = QTableWidgetItem(f"{format_currency(total_after_discount)} đ"); total_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 4, total_item)
            discount_item = QTableWidgetItem(f"{format_currency(discount)} đ"); discount_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 5, discount_item)
            date_item = QTableWidgetItem(sale.get("date", "")); date_item.setTextAlignment(Qt.AlignRight)
            self.sell_history_table.setItem(i, 6, date_item)
            self.sell_history_table.setItem(i, 7, QTableWidgetItem(sale.get("expiry", "")))

    # ===================== BIỂU ĐỒ / TỔNG HỢP =====================
    def _iter_sales(self):
        for s in self.sales:
            try:
                dt = datetime.strptime(s.get("date", ""), "%H:%M:%S %d/%m/%Y")
            except Exception:
                continue
            qty = int(s.get("quantity", 0))
            discount = float(s.get("discount", 0) or 0)
            revenue = float(s.get("sell_price", 0)) * qty - discount
            cost = float(s.get("cost_price", 0)) * qty
            profit = revenue - cost
            yield dt, profit

    def _gen_period_labels(self, period):
        today = date.today()
        if period == "Ngày":
            labels = [(today - timedelta(days=i)).strftime("%d/%m/%Y") for i in range(13, -1, -1)]
        elif period == "Tuần":
            labels, d, seen = [], today, 0
            while seen < 12:
                iso_y, iso_w, _ = d.isocalendar()
                lbl = f"W{iso_w:02d}/{iso_y}"
                if not labels or labels[-1] != lbl:
                    labels.append(lbl); seen += 1
                d -= timedelta(days=7)
            labels.reverse()
        elif period == "Tháng":
            labels, y, m = [], today.year, today.month
            for _ in range(12):
                labels.append(f"{m:02d}/{y}")
                m -= 1
                if m == 0: m = 12; y -= 1
            labels.reverse()
        else:
            labels = [str(today.year - i) for i in range(4, -1, -1)]
        return labels

    def _aggregate_profit(self, period: str):
        labels = self._gen_period_labels(period)
        buckets = OrderedDict((k, 0.0) for k in labels)
        for dt, profit in self._iter_sales():
            if period == "Ngày":
                key = dt.strftime("%d/%m/%Y")
            elif period == "Tuần":
                iso_year, iso_week, _ = dt.isocalendar()
                key = f"W{iso_week:02d}/{iso_year}"
            elif period == "Tháng":
                key = dt.strftime("%m/%Y")
            else:
                key = dt.strftime("%Y")
            if key in buckets:
                buckets[key] += profit
        return buckets

    def update_profit_chart(self):
        period = self.period_combo.currentText()
        agg = self._aggregate_profit(period)
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        labels = list(agg.keys())
        values = [v for v in agg.values()]

        def money_fmt(x, _pos):
            try:
                return f"{int(round(x)):,}".replace(",", ".") + " đ"
            except Exception:
                return str(x)

        ax.yaxis.set_major_formatter(FuncFormatter(money_fmt))
        ax.grid(True, axis='y', linestyle='--', linewidth=0.6, alpha=0.6)

        bars = ax.bar(range(len(values)), values)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=0 if period == "Năm" else 45, ha="right")
        ax.set_ylabel("Lợi nhuận (đ)")
        ax.set_title(f"Lợi nhuận theo {period.lower()}")  # đúng API

        ymax = max(values) if values else 1.0
        ax.set_ylim(0, ymax * 1.15)

        for rect, val in zip(bars, values):
            ax.annotate(
                format_currency(val),
                xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
                xytext=(0, 6),
                textcoords="offset points",
                ha='center', va='bottom',
                fontsize=9, clip_on=False
            )

        self.figure.tight_layout()
        self.canvas.draw()

    # ===================== LƯU / LOAD + MIGRATION =====================
    def load_data(self):
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.medicines = json.load(f)
            except json.JSONDecodeError:
                self.medicines = []
        else:
            self.medicines = []

        changed = False
        for med in self.medicines:
            if "unit" not in med:
                med["unit"] = "Viên"; changed = True
        if changed:
            self.save_data()

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.medicines, f, ensure_ascii=False, indent=2)

    def load_sales(self):
        if os.path.exists(SALES_FILE) and os.path.getsize(SALES_FILE) > 0:
            try:
                with open(SALES_FILE, 'r', encoding='utf-8') as f:
                    self.sales = json.load(f)
            except json.JSONDecodeError:
                self.sales = []
        else:
            self.sales = []

        med_index = {(m.get("name",""), m.get("expiry","")): m.get("unit","Viên") for m in self.medicines}
        changed = False
        for s in self.sales:
            if "unit" not in s:
                s["unit"] = med_index.get((s.get("name",""), s.get("expiry","")), ""); changed = True
        if changed:
            self.save_sales()

    def save_sales(self):
        with open(SALES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.sales, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineManager()
    window.show()
    sys.exit(app.exec_())
