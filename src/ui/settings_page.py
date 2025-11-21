from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QTextEdit, QGroupBox, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QTabWidget, QLabel, QFileDialog, QComboBox, QSplitter)
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
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.tabs = QTabWidget()
        
        self.tab_rules = QWidget()
        self.init_rules_tab()
        self.tabs.addTab(self.tab_rules, "1. 箱号规则")

        self.tab_mapping = QWidget()
        self.init_mapping_tab()
        self.tabs.addTab(self.tab_mapping, "2. 字段映射")
        
        self.tab_backup = QWidget()
        self.init_backup_tab()
        self.tabs.addTab(self.tab_backup, "3. 数据维护")

        main_layout.addWidget(self.tabs)
        self.refresh_data()

    # --- 1. 箱号规则 ---
    def init_rules_tab(self):
        layout = QVBoxLayout(self.tab_rules)
        
        # 帮助说明
        help_group = QGroupBox("规则编写向导")
        help_layout = QVBoxLayout(help_group)
        help_txt = QTextEdit()
        help_txt.setReadOnly(True)
        help_txt.setMaximumHeight(150)
        help_txt.setHtml("""
        <p><b>可用变量代码：</b></p>
        <ul>
        <li><b>{SN4}</b> : 产品SN前四位</li>
        <li><b>{Y1}</b> : 年份最后1位 (如: 2025 -> 5)</li>
        <li><b>{Y2}</b> : 年份后2位 (如: 2025 -> 25)</li>
        <li><b>{M1}</b> : 月份代码 (1-9, A, B, C)</li>
        <li><b>{MM}</b> : 月份数字 (01-12)</li>
        <li><b>{DD}</b> : 日期数字 (01-31)</li>
        <li><b>{SEQ5}</b> : 5位流水号 (00001) - <i>自动累加</i></li>
        </ul>
        <p><b>示例：</b> <span style='color:blue'>MZXH{SN4}{Y1}{M1}{SEQ5}</span> -> MZXH80015A00001</p>
        """)
        help_layout.addWidget(help_txt)
        layout.addWidget(help_group)

        # 添加区
        add_layout = QHBoxLayout()
        self.rule_name = QLineEdit()
        self.rule_name.setPlaceholderText("规则名称")
        self.rule_fmt = QLineEdit()
        self.rule_fmt.setPlaceholderText("规则格式 (例: {SN4}{SEQ5})")
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_rule)
        add_layout.addWidget(QLabel("名称:"))
        add_layout.addWidget(self.rule_name)
        add_layout.addWidget(QLabel("格式:"))
        add_layout.addWidget(self.rule_fmt)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        # 列表
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

    # --- 2. 动态字段映射 (表格版) ---
    def init_mapping_tab(self):
        layout = QVBoxLayout(self.tab_mapping)
        
        layout.addWidget(QLabel("说明：左侧选择数据库中的源数据，右侧填写Bartender模板中对应的具名数据源名称。"))
        
        # 映射表格
        self.table_map = QTableWidget()
        self.table_map.setColumnCount(2)
        self.table_map.setHorizontalHeaderLabels(["数据库源字段 (内部)", "模板变量名 (外部)"])
        self.table_map.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_map)
        
        # 按钮组
        btn_box = QHBoxLayout()
        btn_add_row = QPushButton("➕ 增加一行")
        btn_add_row.clicked.connect(self.add_mapping_row)
        btn_del_row = QPushButton("➖ 删除选中行")
        btn_del_row.clicked.connect(self.remove_mapping_row)
        btn_save = QPushButton("💾 保存映射配置")
        btn_save.setStyleSheet("background-color: #007bff; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_mapping_table)
        
        btn_box.addWidget(btn_add_row)
        btn_box.addWidget(btn_del_row)
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def add_mapping_row(self, internal_key=None, template_key=""):
        row = self.table_map.rowCount()
        self.table_map.insertRow(row)
        
        # 左侧下拉框
        combo = QComboBox()
        # 定义所有可用内部字段
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
        
        # 右侧输入框
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
                if external:
                    new_mapping[internal] = external
        
        try:
            self.db.set_setting('field_mapping', json.dumps(new_mapping))
            QMessageBox.information(self, "成功", "映射配置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def load_mapping_to_table(self):
        # 清空
        self.table_map.setRowCount(0)
        mapping = self.db.get_setting('field_mapping')
        if not isinstance(mapping, dict): mapping = DEFAULT_MAPPING
        
        # 排序方便查看
        for k, v in mapping.items():
            self.add_mapping_row(k, v)

    # --- 3. 备份恢复 (保持不变) ---
    def init_backup_tab(self):
        layout = QVBoxLayout(self.tab_backup)
        self.txt_backup_path = QLineEdit()
        self.txt_backup_path.setReadOnly(True)
        btn_sel = QPushButton("选择路径")
        btn_sel.clicked.connect(self.select_backup_path)
        
        h = QHBoxLayout()
        h.addWidget(QLabel("备份目录:"))
        h.addWidget(self.txt_backup_path)
        h.addWidget(btn_sel)
        layout.addLayout(h)
        
        btn_bk = QPushButton("立即备份")
        btn_bk.clicked.connect(self.do_backup)
        btn_rs = QPushButton("从文件恢复")
        btn_rs.clicked.connect(self.do_restore)
        layout.addWidget(btn_bk)
        layout.addWidget(btn_rs)
        layout.addStretch()

    # --- 逻辑 ---
    def refresh_data(self):
        self.load_rules()
        self.load_mapping_to_table()
        self.txt_backup_path.setText(self.db.get_setting('backup_path'))

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
                QMessageBox.information(self, "成功", "规则已添加")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def delete_rule(self):
        row = self.table_rules.currentRow()
        if row >= 0:
            rid = self.table_rules.item(row, 0).text()
            self.db.cursor.execute("DELETE FROM box_rules WHERE id=?", (rid,))
            self.db.conn.commit()
            self.load_rules()

    def select_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            self.db.set_setting('backup_path', path)
            self.txt_backup_path.setText(path)

    def do_backup(self):
        success, msg = self.db.backup_db()
        QMessageBox.information(self, "结果", msg)

    def do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择备份", "", "DB (*.db)")
        if path and QMessageBox.warning(self, "警告", "确定恢复覆盖?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            success, msg = self.db.restore_db(path)
            QMessageBox.information(self, "结果", msg)
