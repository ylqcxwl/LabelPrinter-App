from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QListWidget, QPushButton, QComboBox, QDateEdit, QGroupBox,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView)
from PyQt5.QtCore import QDate, Qt
from src.database import Database
from src.box_rules import BoxRuleEngine
from src.bartender import BartenderPrinter
from src.config import DEFAULT_MAPPING
import datetime

class PrintPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.rule_engine = BoxRuleEngine(self.db)
        self.printer = BartenderPrinter()
        
        self.current_product = None
        self.current_sn_list = [] 
        self.current_box_no = ""
        
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # --- 1. 产品选择区 ---
        top_group = QGroupBox("1. 产品选择 (不可修改)")
        top_layout = QVBoxLayout(top_group)
        
        search_layout = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("输入 69码 或 产品名称 进行筛选...")
        self.input_search.textChanged.connect(self.filter_products)
        search_layout.addWidget(QLabel("🔍 搜索:"))
        search_layout.addWidget(self.input_search)
        top_layout.addLayout(search_layout)
        
        # 产品表格
        self.table_product = QTableWidget()
        self.table_product.setColumnCount(5)
        self.table_product.setHorizontalHeaderLabels(["ID", "名称", "69码", "SN前4", "整箱数"])
        self.table_product.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_product.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_product.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_product.setEditTriggers(QAbstractItemView.NoEditTriggers) # 完全只读
        self.table_product.setMaximumHeight(120)
        self.table_product.itemClicked.connect(self.on_product_select)
        top_layout.addWidget(self.table_product)
        
        # 日期与批次
        setting_layout = QHBoxLayout()
        self.date_prod = QDateEdit(QDate.currentDate())
        self.date_prod.setCalendarPopup(True)
        
        self.combo_repair = QComboBox()
        self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.currentIndexChanged.connect(self.update_box_number_preview)
        
        setting_layout.addWidget(QLabel("生产日期:"))
        setting_layout.addWidget(self.date_prod)
        setting_layout.addWidget(QLabel("批次/返修:"))
        setting_layout.addWidget(self.combo_repair)
        
        # --- 新增：今日打包数量显示 ---
        self.lbl_daily_count = QLabel("今日已包: 0 箱")
        self.lbl_daily_count.setStyleSheet("color: green; font-weight: bold; font-size: 14px; margin-left: 20px;")
        setting_layout.addWidget(self.lbl_daily_count)
        
        setting_layout.addStretch()
        top_layout.addLayout(setting_layout)
        
        main_layout.addWidget(top_group)

        # --- 2. 作业区 ---
        bottom_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        
        self.lbl_info = QLabel("未选择产品")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #2980b9;")
        
        self.lbl_box_no = QLabel("当前箱号: --")
        self.lbl_box_no.setStyleSheet("font-size: 18px; color: #c0392b; font-weight: bold;")
        
        self.input_sn = QLineEdit()
        self.input_sn.setPlaceholderText("在此扫描SN...")
        self.input_sn.setStyleSheet("font-size: 16px; padding: 10px; border: 2px solid #3498db; border-radius: 5px;")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        
        left_panel.addWidget(self.lbl_info)
        left_panel.addWidget(self.lbl_box_no)
        left_panel.addWidget(self.input_sn)
        left_panel.addStretch()
        
        right_panel = QVBoxLayout()
        list_btns = QHBoxLayout()
        btn_sel_all = QPushButton("全选")
        btn_sel_all.clicked.connect(self.select_all_sn)
        btn_del_sn = QPushButton("删除选中")
        btn_del_sn.setStyleSheet("color: red;")
        btn_del_sn.clicked.connect(self.delete_selected_sn)
        list_btns.addWidget(QLabel("SN列表:"))
        list_btns.addStretch()
        list_btns.addWidget(btn_sel_all)
        list_btns.addWidget(btn_del_sn)
        
        self.list_sn = QListWidget()
        self.list_sn.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        right_panel.addLayout(list_btns)
        right_panel.addWidget(self.list_sn)

        bottom_layout.addLayout(left_panel, 4)
        bottom_layout.addLayout(right_panel, 6)
        main_layout.addLayout(bottom_layout)

        self.btn_print = QPushButton("手动打印 / 强制封箱")
        self.btn_print.setStyleSheet("background-color: #e67e22; color: white; font-size: 16px; font-weight: bold; padding: 10px;")
        self.btn_print.clicked.connect(self.execute_print)
        main_layout.addWidget(self.btn_print)

    def refresh_data(self):
        self.products_cache = []
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT id, name, code69, sn4, qty, rule_id FROM products ORDER BY name ASC")
            self.products_cache = cursor.fetchall()
            self.filter_products()
        except Exception as e:
            print(f"Error loading products: {e}")

    def filter_products(self):
        keyword = self.input_search.text().strip().lower()
        self.table_product.setRowCount(0)
        for p in self.products_cache:
            name_match = keyword in str(p[1]).lower()
            code_match = keyword in str(p[2]).lower()
            if not keyword or name_match or code_match:
                row = self.table_product.rowCount()
                self.table_product.insertRow(row)
                item_id = QTableWidgetItem(str(p[0]))
                item_id.setData(Qt.UserRole, p) 
                self.table_product.setItem(row, 0, item_id)
                self.table_product.setItem(row, 1, QTableWidgetItem(str(p[1])))
                self.table_product.setItem(row, 2, QTableWidgetItem(str(p[2])))
                self.table_product.setItem(row, 3, QTableWidgetItem(str(p[3])))
                self.table_product.setItem(row, 4, QTableWidgetItem(str(p[4])))

    def on_product_select(self, item):
        row = item.row()
        p_data = self.table_product.item(row, 0).data(Qt.UserRole)
        
        self.current_product = {
            "id": p_data[0],
            "name": p_data[1],
            "sn4": p_data[3],
            "qty": p_data[4],
            "rule_id": p_data[5]
        }
        
        self.lbl_info.setText(f"当前产品: {p_data[1]}\nSN前四位: {p_data[3]}\n整箱数量: {p_data[4]}")
        self.current_sn_list = []
        self.list_sn.clear()
        
        self.update_box_number_preview()
        self.update_daily_count() # 更新单日计数
        self.input_sn.setFocus()

    def update_daily_count(self):
        if not self.current_product: 
            self.lbl_daily_count.setText("今日已包: 0 箱")
            return
        
        today_str = datetime.datetime.now().strftime("%Y-%m-%d") + "%"
        try:
            cursor = self.db.conn.cursor()
            # 统计今日该产品名称下生成的唯一箱号数量
            sql = "SELECT COUNT(DISTINCT box_no) FROM records WHERE name=? AND print_date LIKE ?"
            cursor.execute(sql, (self.current_product['name'], today_str))
            count = cursor.fetchone()[0]
            self.lbl_daily_count.setText(f"今日已包: {count} 箱")
        except Exception as e:
            print(f"Count error: {e}")

    def update_box_number_preview(self):
        if not self.current_product:
            self.lbl_box_no.setText("当前箱号: --")
            return
        rule_id = self.current_product.get('rule_id', 0)
        repair_lvl = int(self.combo_repair.currentText())
        preview_str, _ = self.rule_engine.generate_box_no(rule_id, self.current_product, repair_lvl)
        self.current_box_no = preview_str
        self.lbl_box_no.setText(f"当前箱号: {preview_str}")

    def on_sn_scan(self):
        if not self.current_product:
            QMessageBox.warning(self, "提示", "请先选择产品")
            return
        sn = self.input_sn.text().strip().upper()
        self.input_sn.clear()
        if not sn: return
        
        target_prefix = str(self.current_product['sn4']).upper()
        if not sn.startswith(target_prefix):
            QMessageBox.warning(self, "错误", f"SN前缀不符! 需: {target_prefix}")
            return
        if sn in [x[0] for x in self.current_sn_list]:
            QMessageBox.warning(self, "错误", "当前箱已扫描此SN")
            return
        if self.db.check_sn_exists(sn):
            QMessageBox.warning(self, "错误", "SN已存在历史记录")
            return

        self.current_sn_list.append((sn, datetime.datetime.now()))
        self.update_sn_list_ui()
        if len(self.current_sn_list) >= self.current_product['qty']:
            self.execute_print()

    def update_sn_list_ui(self):
        self.list_sn.clear()
        for i, (sn, _) in enumerate(self.current_sn_list):
            self.list_sn.addItem(f"{i+1}. {sn}")
        self.list_sn.scrollToBottom()

    def select_all_sn(self):
        self.list_sn.selectAll()

    def delete_selected_sn(self):
        selected_items = self.list_sn.selectedItems()
        if not selected_items: return
        sn_to_remove = [item.text().split(". ")[1] for item in selected_items]
        self.current_sn_list = [x for x in self.current_sn_list if x[0] not in sn_to_remove]
        self.update_sn_list_ui()

    def execute_print(self):
        if not self.current_product or not self.current_sn_list: return
        
        # 重新获取产品完整数据
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (self.current_product['id'],))
        p_row = cursor.fetchone() # id, name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id
        
        # 动态字段映射
        mapping_config = self.db.get_setting('field_mapping') # 此时是字典 {"internal": "external"}
        if not isinstance(mapping_config, dict): mapping_config = DEFAULT_MAPPING

        # 构建可用数据源
        source_data = {
            "name": p_row[1], "spec": p_row[2], "model": p_row[3], "color": p_row[4],
            "sn4": p_row[5], "sku": p_row[6], "code69": p_row[7],
            "qty": len(self.current_sn_list), "weight": p_row[9], 
            "box_no": self.current_box_no,
            "prod_date": self.date_prod.text()
        }

        # 组装打印数据
        data_map = {}
        for internal_key, template_key in mapping_config.items():
            if internal_key in source_data:
                data_map[template_key] = source_data[internal_key]
        
        # 加上SN列表 (1, 2, 3...)
        for i, (sn, _) in enumerate(self.current_sn_list):
            data_map[str(i+1)] = sn

        template_path = p_row[10]
        success, msg = self.printer.print_label(template_path, data_map)
        
        if success:
            self.save_records(p_row, self.current_box_no)
            self.rule_engine.commit_sequence(p_row[11], int(self.combo_repair.currentText()))
            QMessageBox.information(self, "成功", "打印成功")
            self.current_sn_list = []
            self.update_sn_list_ui()
            self.update_box_number_preview()
            self.update_daily_count() # 打印成功后更新计数
        else:
            QMessageBox.critical(self, "打印失败", msg)

    def save_records(self, p_row, box_no):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prod_date = self.date_prod.text()
        for i, (sn, _) in enumerate(self.current_sn_list):
            try:
                self.db.cursor.execute('''
                    INSERT INTO records (box_sn_seq, name, spec, model, color, code69, sn, box_no, prod_date, print_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                ''', (i+1, p_row[1], p_row[2], p_row[3], p_row[4], p_row[7], sn, box_no, prod_date, now_str))
            except: pass
        self.db.conn.commit()
