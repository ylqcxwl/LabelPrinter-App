from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QListWidget, QPushButton, QComboBox, QDateEdit, QGroupBox,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QGridLayout, QFrame)
from PyQt5.QtCore import QDate, Qt
from src.database import Database
from src.box_rules import BoxRuleEngine
from src.bartender import BartenderPrinter
from src.config import DEFAULT_MAPPING
import datetime
import os
import traceback

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
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 1. 顶部搜索
        top_layout = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 输入69码或名称筛选...")
        self.input_search.textChanged.connect(self.filter_products)
        
        self.table_product = QTableWidget()
        self.table_product.setColumnCount(4)
        self.table_product.setHorizontalHeaderLabels(["名称", "69码", "SN前4", "整箱数"])
        self.table_product.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_product.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_product.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_product.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_product.setMaximumHeight(100)
        self.table_product.itemClicked.connect(self.on_product_select)
        
        top_split = QVBoxLayout()
        top_split.addWidget(self.input_search)
        top_split.addWidget(self.table_product)
        main_layout.addLayout(top_split)

        # 2. 详情
        details_group = QGroupBox("当前产品详情")
        details_layout = QGridLayout(details_group)
        details_layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_name = QLabel("--"); self.lbl_spec = QLabel("--")
        self.lbl_model = QLabel("--"); self.lbl_color = QLabel("--")
        self.lbl_sn4 = QLabel("--"); self.lbl_sku = QLabel("--")
        self.lbl_code69 = QLabel("--"); self.lbl_qty = QLabel("--")
        
        val_style = "color: #2980b9; font-weight: bold;"
        for l in [self.lbl_name, self.lbl_spec, self.lbl_model, self.lbl_color, self.lbl_sn4, self.lbl_sku, self.lbl_code69, self.lbl_qty]:
            l.setStyleSheet(val_style)

        details_layout.addWidget(QLabel("名称:"), 0, 0); details_layout.addWidget(self.lbl_name, 0, 1)
        details_layout.addWidget(QLabel("规格:"), 0, 2); details_layout.addWidget(self.lbl_spec, 0, 3)
        details_layout.addWidget(QLabel("型号:"), 0, 4); details_layout.addWidget(self.lbl_model, 0, 5)
        details_layout.addWidget(QLabel("颜色:"), 0, 6); details_layout.addWidget(self.lbl_color, 0, 7)
        details_layout.addWidget(QLabel("SN前4:"), 1, 0); details_layout.addWidget(self.lbl_sn4, 1, 1)
        details_layout.addWidget(QLabel("SKU:"), 1, 2); details_layout.addWidget(self.lbl_sku, 1, 3)
        details_layout.addWidget(QLabel("69码:"), 1, 4); details_layout.addWidget(self.lbl_code69, 1, 5)
        details_layout.addWidget(QLabel("整箱数:"), 1, 6); details_layout.addWidget(self.lbl_qty, 1, 7)

        main_layout.addWidget(details_group)
        
        # 3. 控制
        ctrl_layout = QHBoxLayout()
        self.date_prod = QDateEdit(QDate.currentDate())
        self.date_prod.setCalendarPopup(True)
        self.combo_repair = QComboBox()
        self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.currentIndexChanged.connect(self.safe_update_box_preview)
        
        self.lbl_daily_count = QLabel("今日已包: 0")
        self.lbl_daily_count.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        
        ctrl_layout.addWidget(QLabel("生产日期:"))
        ctrl_layout.addWidget(self.date_prod)
        ctrl_layout.addWidget(QLabel("批次:"))
        ctrl_layout.addWidget(self.combo_repair)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.lbl_daily_count)
        main_layout.addLayout(ctrl_layout)

        # 4. 作业
        work_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        self.lbl_box_no = QLabel("当前箱号: --")
        self.lbl_box_no.setStyleSheet("font-size: 20px; color: #c0392b; font-weight: bold; margin: 5px 0;")
        
        self.input_sn = QLineEdit()
        self.input_sn.setPlaceholderText("在此扫描SN...")
        self.input_sn.setStyleSheet("font-size: 18px; padding: 10px; border: 2px solid #3498db;")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        
        left_panel.addWidget(self.lbl_box_no)
        left_panel.addWidget(self.input_sn)
        left_panel.addStretch()
        
        right_panel = QVBoxLayout()
        btn_row = QHBoxLayout()
        btn_sel_all = QPushButton("全选")
        btn_sel_all.clicked.connect(self.select_all_sn)
        btn_del_sn = QPushButton("删除选中")
        btn_del_sn.setStyleSheet("color: red;")
        btn_del_sn.clicked.connect(self.delete_selected_sn)
        btn_row.addWidget(QLabel("SN列表"))
        btn_row.addStretch()
        btn_row.addWidget(btn_sel_all)
        btn_row.addWidget(btn_del_sn)
        
        self.list_sn = QListWidget()
        self.list_sn.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        right_panel.addLayout(btn_row)
        right_panel.addWidget(self.list_sn)
        
        work_layout.addLayout(left_panel, 4)
        work_layout.addLayout(right_panel, 6)
        main_layout.addLayout(work_layout)

        self.btn_print = QPushButton("手动打印 / 强制封箱")
        self.btn_print.setStyleSheet("background-color: #e67e22; color: white; font-size: 16px; font-weight: bold; padding: 10px;")
        self.btn_print.clicked.connect(self.execute_print)
        main_layout.addWidget(self.btn_print)

    def refresh_data(self):
        self.products_cache = []
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT * FROM products ORDER BY name ASC")
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            for row in rows:
                p = dict(zip(cols, row))
                self.products_cache.append(p)
            self.filter_products()
        except Exception as e:
            print(f"Error loading products: {e}")

    def filter_products(self):
        keyword = self.input_search.text().strip().lower()
        self.table_product.setRowCount(0)
        for p in self.products_cache:
            name_match = keyword in str(p.get('name', '')).lower()
            code_match = keyword in str(p.get('code69', '')).lower()
            if not keyword or name_match or code_match:
                row = self.table_product.rowCount()
                self.table_product.insertRow(row)
                
                item_name = QTableWidgetItem(str(p.get('name', '')))
                item_name.setData(Qt.UserRole, p) 
                
                self.table_product.setItem(row, 0, item_name)
                self.table_product.setItem(row, 1, QTableWidgetItem(str(p.get('code69', ''))))
                self.table_product.setItem(row, 2, QTableWidgetItem(str(p.get('sn4', ''))))
                self.table_product.setItem(row, 3, QTableWidgetItem(str(p.get('qty', ''))))

    def on_product_select(self, item):
        try:
            row = item.row()
            p = self.table_product.item(row, 0).data(Qt.UserRole)
            if not p: return
            
            self.current_product = p
            
            # 更新UI，使用 .get() 防止字段缺失导致的崩溃
            self.lbl_name.setText(str(p.get('name', '')))
            self.lbl_spec.setText(str(p.get('spec', '')))
            self.lbl_model.setText(str(p.get('model', '')))
            self.lbl_color.setText(str(p.get('color', '')))
            self.lbl_sn4.setText(str(p.get('sn4', '')))
            self.lbl_sku.setText(str(p.get('sku', '')))
            self.lbl_code69.setText(str(p.get('code69', '')))
            self.lbl_qty.setText(str(p.get('qty', '')))
            
            self.current_sn_list = []
            self.list_sn.clear()
            self.update_box_number_preview()
            self.update_daily_count()
            self.input_sn.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择产品时出错: {str(e)}\n请检查产品数据完整性。")
            traceback.print_exc()

    def safe_update_box_preview(self):
        if self.current_product:
            self.update_box_number_preview()

    def update_daily_count(self):
        if not self.current_product: 
            self.lbl_daily_count.setText("今日已包: 0")
            return
        today_str = datetime.datetime.now().strftime("%Y-%m-%d") + "%"
        try:
            cursor = self.db.conn.cursor()
            # 修正计数逻辑：根据SN前4位统计，比名称更准
            sn_prefix = self.current_product.get('sn4', '')
            sql = "SELECT COUNT(DISTINCT box_no) FROM records WHERE sn LIKE ? AND print_date LIKE ?"
            cursor.execute(sql, (f"{sn_prefix}%", today_str))
            count = cursor.fetchone()[0]
            self.lbl_daily_count.setText(f"今日已包: {count}")
        except Exception as e:
            print(f"Count error: {e}")

    def update_box_number_preview(self):
        if not self.current_product:
            self.lbl_box_no.setText("当前箱号: --")
            return
        try:
            rule_id = self.current_product.get('rule_id', 0)
            repair_lvl = int(self.combo_repair.currentText())
            preview_str, _ = self.rule_engine.generate_box_no(rule_id, self.current_product, repair_lvl)
            self.current_box_no = preview_str
            self.lbl_box_no.setText(f"当前箱号: {preview_str}")
        except Exception as e:
            self.lbl_box_no.setText("规则错误")
            print(f"Rule error: {e}")

    def on_sn_scan(self):
        if not self.current_product:
            QMessageBox.warning(self, "提示", "请先选择产品")
            return
        sn = self.input_sn.text().strip().upper()
        self.input_sn.clear()
        if not sn: return
        
        target_prefix = str(self.current_product.get('sn4', '')).upper()
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
        
        target_qty = int(self.current_product.get('qty', 0))
        if len(self.current_sn_list) >= target_qty:
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
        
        p = self.current_product
        
        mapping_config = self.db.get_setting('field_mapping')
        if not isinstance(mapping_config, dict): mapping_config = DEFAULT_MAPPING

        source_data = {
            "name": p.get('name', ''), "spec": p.get('spec', ''), "model": p.get('model', ''), 
            "color": p.get('color', ''), "sn4": p.get('sn4', ''), "sku": p.get('sku', ''), 
            "code69": p.get('code69', ''), "qty": len(self.current_sn_list), 
            "weight": p.get('weight', ''), "box_no": self.current_box_no,
            "prod_date": self.date_prod.text()
        }

        data_map = {}
        for internal_key, template_key in mapping_config.items():
            if internal_key in source_data:
                data_map[template_key] = source_data[internal_key]
        for i, (sn, _) in enumerate(self.current_sn_list):
            data_map[str(i+1)] = sn

        tmpl_root = self.db.get_setting('template_root')
        tmpl_filename = p.get('template_path', '')
        if tmpl_root and tmpl_filename:
            full_path = os.path.join(tmpl_root, tmpl_filename)
        else:
            full_path = tmpl_filename 

        success, msg = self.printer.print_label(full_path, data_map)
        
        if success:
            # 构建列表用于保存记录
            p_list = [0, p.get('name'), p.get('spec'), p.get('model'), p.get('color'), 0, 0, p.get('code69')]
            self.save_records(p_list, self.current_box_no)
            
            rule_id = p.get('rule_id', 0)
            self.rule_engine.commit_sequence(rule_id, int(self.combo_repair.currentText()))
            
            QMessageBox.information(self, "成功", "打印成功")
            self.current_sn_list = []
            self.update_sn_list_ui()
            self.update_box_number_preview()
            self.update_daily_count()
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
