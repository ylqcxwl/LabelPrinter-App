from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QTextEdit, QGroupBox, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QTabWidget, QLabel, QFileDialog, QComboBox)
from PyQt5.QtCore import Qt
from src.database import Database
from src.config import DEFAULT_MAPPING
import json
import os

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5) # 减少顶部留白

        self.tabs = QTabWidget()
        
        self.tab_rules = QWidget()
        self.init_rules_tab()
        self.tabs.addTab(self.tab_rules, "1. 箱号规则")

        self.tab_mapping = QWidget()
        self.init_mapping_tab()
        self.tabs.addTab(self.tab_mapping, "2. 字段映射")
        
        self.tab_backup = QWidget()
        self.init_backup_tab()
        self.tabs.addTab(self.tab_backup, "3. 数据维护 & 设置")

        main_layout.addWidget(self.tabs)
        self.refresh_data()

    # --- 1. 箱号规则 ---
    def init_rules_tab(self):
        layout = QVBoxLayout(self.tab_rules)
        layout.setContentsMargins(10, 10, 10, 10)
        
        help_group = QGroupBox("规则编写向导")
        help_layout = QVBoxLayout(help_group)
        help_txt = QTextEdit()
        help_txt.setReadOnly(True)
        help_txt.setMaximumHeight(120)
        help_txt.setHtml("""
        <p style='font-size:12px'><b>变量代码：</b> {SN4}:SN前4位 | {Y1}:年1位 | {Y2}:年2位 | {M1}:月代码 | {MM}:月2位 | {DD}:日2位 | {SEQ5}:5位流水号</p>
        """)
        help_layout.addWidget(help_txt)
        layout.addWidget(help_group)

        # 添加区
        add_layout = QHBoxLayout()
        self.rule_name = QLineEdit()
        self.rule_name.setPlaceholderText("规则名称")
        self.rule_fmt = QLineEdit()
        self.rule_fmt.setPlaceholderText("规则格式")
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_rule)
        add_layout.addWidget(QLabel("名称:"))
        add_layout.addWidget(self.rule_name)
        add_layout.addWidget(QLabel("格式:"))
        add_layout.addWidget(self.rule_fmt)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(3)
        self.table_rules.setHorizontalHeaderLabels(["ID", "名称", "规则格式"])
        self.table_rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_rules.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_rules.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table_rules)
        
        btn_del = QPushButton("删除选中规则")
        btn_del.clicked.connect(self.delete_rule)
        layout.addWidget(btn_del)

    # --- 2. 字段映射 ---
    def init_mapping_tab(self):
        layout = QVBoxLayout(self.tab_mapping)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.table_map = QTableWidget()
        self.table_map.setColumnCount(2)
        self.table_map.setHorizontalHeaderLabels(["数据库源字段", "Bartender模板变量名"])
        self.table_map.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_map)
        
        btn_box = QHBoxLayout()
        btn_add_row = QPushButton("➕ 增加")
        btn_add_row.clicked.connect(self.add_mapping_row)
        btn_del_row = QPushButton("➖ 删除")
        btn_del_row.clicked.connect(self.remove_mapping_row)
        btn_save = QPushButton("💾 保存配置")
        btn_save.clicked.connect(self.save_mapping_table)
        
        btn_box.addWidget(btn_add_row)
        btn_box.addWidget(btn_del_row)
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    # --- 3. 数据维护 & 设置 ---
    def init_backup_tab(self):
        layout = QVBoxLayout(self.tab_backup)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 模板路径设置 (新增)
        tmpl_group = QGroupBox("Bartender 模板文件根目录")
        tmpl_layout = QHBoxLayout(tmpl_group)
        self.txt_tmpl_root = QLineEdit()
        self.txt_tmpl_root.setReadOnly(True)
        btn_tmpl_sel = QPushButton("选择目录")
        btn_tmpl_sel.clicked.connect(self.select_tmpl_root)
        tmpl_layout.addWidget(self.txt_tmpl_root)
        tmpl_layout.addWidget(btn_tmpl_sel)
        layout.addWidget(tmpl_group)

        # 备份路径
        path_group = QGroupBox("数据备份目录")
        path_layout = QHBoxLayout(path_group)
        self.txt_backup_path = QLineEdit()
        self.txt_backup_path.setReadOnly(True)
        btn_sel = QPushButton("选择目录")
        btn_sel.clicked.connect(self.select_backup_path)
        path_layout.addWidget(self.txt_backup_path)
        path_layout.addWidget(btn_sel)
        layout.addWidget(path_group)
        
        # 操作
        op_group = QGroupBox("数据库操作")
        op_layout = QHBoxLayout(op_group)
        btn_bk = QPushButton("立即备份")
        btn_bk.clicked.connect(self.do_backup)
        btn_rs = QPushButton("恢复数据")
        btn_rs.clicked.connect(self.do_restore)
        op_layout.addWidget(btn_bk)
        op_layout.addWidget(btn_rs)
        layout.addWidget(op_group)
        
        layout.addStretch()

    # --- 逻辑 ---
    def refresh_data(self):
        self.load_rules()
        self.load_mapping_to_table()
        self.txt_backup_path.setText(self.db.get_setting('backup_path'))
        self.txt_tmpl_root.setText(self.db.get_setting('template_root'))

    def load_rules(self):
        self.table_rules.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, rule_string FROM box_rules")
        for r, row in enumerate(cursor.fetchall()):
            self.table_rules.insertRow(r)
            for c, val in enumerate(row):
                self.table_rules.setItem(r, c, QTableWidgetItem(str(val)))

    def add_rule(self):
        name = self.rule_name.text()
        fmt = self.rule_fmt.text()
        if name and fmt:
            try:
                self.db.cursor.execute("INSERT INTO box_rules (name, rule_string) VALUES (?,?)", (name, fmt))
                self.db.conn.commit()
                self.rule_name.clear()
                self.load_rules()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def delete_rule(self):
        row = self.table_rules.currentRow()
        if row >= 0:
            rid = self.table_rules.item(row, 0).text()
            self.db.cursor.execute("DELETE FROM box_rules WHERE id=?", (rid,))
            self.db.conn.commit()
            self.load_rules()

    def add_mapping_row(self, internal_key=None, template_key=""):
        row = self.table_map.rowCount()
        self.table_map.insertRow(row)
        combo = QComboBox()
        sources = [
            ("name", "产品名称"), ("spec", "产品规格"), ("model", "产品型号"), 
            ("color", "产品颜色"), ("sn4", "SN前四位"), ("sku", "SKU"), 
            ("code69", "69码"), ("qty", "装箱数量"), ("weight", "产品重量"), 
            ("box_no", "箱号"), ("prod_date", "生产日期")
        ]
        for key, label in sources:
            combo.addItem(f"{label} ({key})", key)
        if internal_key:
            idx = combo.findData(internal_key)
            if idx >= 0: combo.setCurrentIndex(idx)
        self.table_map.setCellWidget(row, 0, combo)
        le = QLineEdit(str(template_key))
        self.table_map.setCellWidget(row, 1, le)

    def remove_mapping_row(self):
        row = self.table_map.currentRow()
        if row >= 0: self.table_map.removeRow(row)

    def save_mapping_table(self):
        new_mapping = {}
        for i in range(self.table_map.rowCount()):
            combo = self.table_map.cellWidget(i, 0)
            le = self.table_map.cellWidget(i, 1)
            if combo and le:
                internal = combo.currentData()
                external = le.text().strip()
                if external: new_mapping[internal] = external
        self.db.set_setting('field_mapping', json.dumps(new_mapping))
        QMessageBox.information(self, "成功", "已保存")

    def load_mapping_to_table(self):
        self.table_map.setRowCount(0)
        mapping = self.db.get_setting('field_mapping')
        if not isinstance(mapping, dict): mapping = DEFAULT_MAPPING
        for k, v in mapping.items():
            self.add_mapping_row(k, v)

    def select_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            self.db.set_setting('backup_path', path)
            self.txt_backup_path.setText(path)
            
    def select_tmpl_root(self):
        path = QFileDialog.getExistingDirectory(self, "选择模板根目录")
        if path:
            self.db.set_setting('template_root', path)
            self.txt_tmpl_root.setText(path)

    def do_backup(self):
        success, msg = self.db.backup_db()
        QMessageBox.information(self, "结果", msg)

    def do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择备份", "", "DB (*.db)")
        if path and QMessageBox.warning(self, "警告", "确定恢复?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            success, msg = self.db.restore_db(path)
            QMessageBox.information(self, "结果", msg)
