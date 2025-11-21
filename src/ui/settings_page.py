from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QTextEdit, QGroupBox, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QTabWidget, QLabel, QFileDialog)
from PyQt5.QtCore import Qt
from src.database import Database
import json
import os

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 使用 TabWidget 分页
        self.tabs = QTabWidget()
        
        # 1. 箱号规则 Tab
        self.tab_rules = QWidget()
        self.init_rules_tab()
        self.tabs.addTab(self.tab_rules, "箱号规则")

        # 2. 字段映射 Tab
        self.tab_mapping = QWidget()
        self.init_mapping_tab()
        self.tabs.addTab(self.tab_mapping, "字段映射")
        
        # 3. 数据维护 Tab (备份恢复)
        self.tab_backup = QWidget()
        self.init_backup_tab()
        self.tabs.addTab(self.tab_backup, "数据维护")

        main_layout.addWidget(self.tabs)
        
        self.refresh_data()

    # ------------------ 1. 箱号规则页面 ------------------
    def init_rules_tab(self):
        layout = QVBoxLayout(self.tab_rules)
        
        # 添加区域
        form_group = QGroupBox("添加新规则")
        form_layout = QFormLayout(form_group)
        
        self.rule_name = QLineEdit()
        self.rule_fmt = QLineEdit()
        self.rule_fmt.setPlaceholderText("例如: MZXH{SN4}{Y1}{M1}{SEQ5}")
        
        form_layout.addRow("规则名称:", self.rule_name)
        form_layout.addRow("规则格式:", self.rule_fmt)
        
        btn_add = QPushButton("添加规则")
        btn_add.setStyleSheet("background-color: #28a745; color: white;")
        btn_add.clicked.connect(self.add_rule)
        form_layout.addRow(btn_add)
        layout.addWidget(form_group)

        # 列表区域
        list_group = QGroupBox("已有规则列表")
        list_layout = QVBoxLayout(list_group)
        
        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(3)
        self.table_rules.setHorizontalHeaderLabels(["ID", "名称", "规则格式"])
        self.table_rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_rules.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_rules.setSelectionMode(QAbstractItemView.SingleSelection)
        
        btn_del = QPushButton("删除选中规则")
        btn_del.setStyleSheet("background-color: #dc3545; color: white;")
        btn_del.clicked.connect(self.delete_rule)
        
        list_layout.addWidget(self.table_rules)
        list_layout.addWidget(btn_del)
        layout.addWidget(list_group)
        
        # 说明
        rule_help = QTextEdit()
        rule_help.setReadOnly(True)
        rule_help.setMaximumHeight(100)
        rule_help.setHtml("<b>说明:</b> {SN4}=SN前4位, {Y1}=年1位, {M1}=月代码, {SEQ5}=5位流水号")
        layout.addWidget(rule_help)

    # ------------------ 2. 字段映射页面 ------------------
    def init_mapping_tab(self):
        layout = QVBoxLayout(self.tab_mapping)
        
        help_lbl = QLabel("说明: 左侧为数据库字段，右侧输入Bartender模板中的子字符串名称")
        help_lbl.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(help_lbl)
        
        self.mapping_inputs = {}
        form_layout = QFormLayout()
        
        fields = [("名称", "name"), ("规格", "spec"), ("型号", "model"), ("颜色", "color"),
                  ("SN前4", "sn4"), ("SKU", "sku"), ("69码", "code69"),
                  ("数量", "qty"), ("重量", "weight"), ("箱号", "box_no")]
        
        for lbl, key in fields:
            le = QLineEdit()
            self.mapping_inputs[key] = le
            form_layout.addRow(lbl, le)
            
        btn_save = QPushButton("保存映射配置")
        btn_save.setMinimumHeight(40)
        btn_save.setStyleSheet("background-color: #007bff; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_mapping)
        
        layout.addLayout(form_layout)
        layout.addWidget(btn_save)
        layout.addStretch()

    # ------------------ 3. 数据维护页面 ------------------
    def init_backup_tab(self):
        layout = QVBoxLayout(self.tab_backup)
        
        # 路径设置
        path_group = QGroupBox("备份设置")
        path_layout = QHBoxLayout(path_group)
        self.txt_backup_path = QLineEdit()
        self.txt_backup_path.setReadOnly(True)
        btn_sel_path = QPushButton("选择路径")
        btn_sel_path.clicked.connect(self.select_backup_path)
        path_layout.addWidget(QLabel("备份目录:"))
        path_layout.addWidget(self.txt_backup_path)
        path_layout.addWidget(btn_sel_path)
        layout.addWidget(path_group)
        
        # 操作按钮
        op_group = QGroupBox("操作")
        op_layout = QVBoxLayout(op_group)
        
        btn_backup_now = QPushButton("立即备份数据")
        btn_backup_now.setMinimumHeight(40)
        btn_backup_now.clicked.connect(self.do_backup)
        
        btn_restore = QPushButton("从备份文件恢复数据")
        btn_restore.setMinimumHeight(40)
        btn_restore.setStyleSheet("color: #c0392b;")
        btn_restore.clicked.connect(self.do_restore)
        
        op_layout.addWidget(btn_backup_now)
        op_layout.addWidget(btn_restore)
        layout.addWidget(op_group)
        
        layout.addStretch()

    # ------------------ 逻辑处理 ------------------
    def refresh_data(self):
        self.load_rules()
        self.load_mapping()
        self.load_backup_path()

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
            if QMessageBox.question(self, "确认", "确定删除?") == QMessageBox.Yes:
                self.db.cursor.execute("DELETE FROM box_rules WHERE id=?", (rid,))
                self.db.conn.commit()
                self.load_rules()

    def load_mapping(self):
        m = self.db.get_setting('field_mapping')
        for k, v in self.mapping_inputs.items():
            v.setText(m.get(k, ''))

    def save_mapping(self):
        m = {k: v.text() for k, v in self.mapping_inputs.items() if v.text()}
        self.db.set_setting('field_mapping', json.dumps(m))
        QMessageBox.information(self, "成功", "映射已保存")

    def load_backup_path(self):
        path = self.db.get_setting('backup_path')
        self.txt_backup_path.setText(path)

    def select_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择备份目录")
        if path:
            self.db.set_setting('backup_path', path)
            self.txt_backup_path.setText(path)

    def do_backup(self):
        success, msg = self.db.backup_db()
        if success:
            QMessageBox.information(self, "成功", msg)
        else:
            QMessageBox.critical(self, "失败", msg)

    def do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择备份文件", "", "Database Files (*.db)")
        if path:
            if QMessageBox.warning(self, "警告", "恢复数据将覆盖当前所有数据！\n确定继续吗？", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                success, msg = self.db.restore_db(path)
                if success:
                    QMessageBox.information(self, "成功", msg)
                else:
                    QMessageBox.critical(self, "失败", msg)
