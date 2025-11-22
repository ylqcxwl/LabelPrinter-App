from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QTextEdit, QGroupBox, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QTabWidget, QLabel, QFileDialog, QComboBox, QSpinBox)
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
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.tabs = QTabWidget()
        
        # 1. 箱号规则
        self.tab_rules = QWidget()
        self.init_rules_tab()
        self.tabs.addTab(self.tab_rules, "1. 箱号规则")

        # 2. SN规则
        self.tab_sn = QWidget()
        self.init_sn_tab()
        self.tabs.addTab(self.tab_sn, "2. SN规则")

        # 3. 字段映射
        self.tab_map = QWidget()
        self.init_map_tab()
        self.tabs.addTab(self.tab_map, "3. 字段映射")
        
        # 4. 系统维护
        self.tab_sys = QWidget()
        self.init_sys_tab()
        self.tabs.addTab(self.tab_sys, "4. 系统维护")
        
        main_layout.addWidget(self.tabs)
        
        # 初始化时加载所有数据
        self.refresh_data()

    # ================= 1. 箱号规则 =================
    def init_rules_tab(self):
        layout = QVBoxLayout(self.tab_rules)
        
        # 说明区
        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(150)
        info.setHtml("""
        <h4>📦 箱号规则编写说明</h4>
        <ul>
        <li><code>{SN4}</code>: SN前4位</li>
        <li><code>{Y1}/{Y2}</code>: 年1位/2位 (2025->5/25)</li>
        <li><code>{M1}</code>: 月代码 (1-9, A, B, C)</li>
        <li><code>{MM}/{DD}</code>: 月/日 (01-12, 01-31)</li>
        <li><code>{SEQ5}</code>: 5位流水号 (自动累计)</li>
        </ul>
        <p>示例: <code>MZXH{SN4}{Y1}{M1}{SEQ5}</code> => MZXH80015B00001</p>
        """)
        layout.addWidget(info)
        
        # 编辑区 (注意：这里定义了 self.box_name_edit 和 self.box_fmt_edit)
        h_layout = QHBoxLayout()
        self.box_name_edit = QLineEdit()
        self.box_name_edit.setPlaceholderText("规则名称")
        self.box_fmt_edit = QLineEdit()
        self.box_fmt_edit.setPlaceholderText("规则格式")
        
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_box_rule)
        btn_upd = QPushButton("修改选中")
        btn_upd.clicked.connect(self.update_box_rule)
        
        h_layout.addWidget(QLabel("名称:"))
        h_layout.addWidget(self.box_name_edit)
        h_layout.addWidget(QLabel("格式:"))
        h_layout.addWidget(self.box_fmt_edit)
        h_layout.addWidget(btn_add)
        h_layout.addWidget(btn_upd)
        layout.addLayout(h_layout)
        
        # 表格区
        self.table_box = QTableWidget()
        self.table_box.setColumnCount(3)
        self.table_box.setHorizontalHeaderLabels(["ID", "名称", "格式"])
        self.table_box.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_box.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_box.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_box.itemClicked.connect(self.on_box_table_click)
        layout.addWidget(self.table_box)
        
        btn_del = QPushButton("删除选中")
        btn_del.clicked.connect(self.delete_box_rule)
        layout.addWidget(btn_del)
        
        self.current_box_id = None

    def load_box_rules(self):
        self.table_box.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, rule_string FROM box_rules")
        for r_idx, row in enumerate(cursor.fetchall()):
            self.table_box.insertRow(r_idx)
            self.table_box.setItem(r_idx, 0, QTableWidgetItem(str(row[0])))
            self.table_box.setItem(r_idx, 1, QTableWidgetItem(str(row[1])))
            self.table_box.setItem(r_idx, 2, QTableWidgetItem(str(row[2])))

    def add_box_rule(self):
        name = self.box_name_edit.text().strip()
        fmt = self.box_fmt_edit.text().strip()
        if not name or not fmt: return
        try:
            self.db.cursor.execute("INSERT INTO box_rules (name, rule_string) VALUES (?,?)", (name, fmt))
            self.db.conn.commit()
            self.load_box_rules()
            self.box_name_edit.clear()
            self.box_fmt_edit.clear()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def update_box_rule(self):
        if not self.current_box_id: return
        try:
            self.db.cursor.execute("UPDATE box_rules SET name=?, rule_string=? WHERE id=?", 
                                   (self.box_name_edit.text(), self.box_fmt_edit.text(), self.current_box_id))
            self.db.conn.commit()
            self.load_box_rules()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def delete_box_rule(self):
        row = self.table_box.currentRow()
        if row >= 0:
            rid = self.table_box.item(row, 0).text()
            self.db.cursor.execute("DELETE FROM box_rules WHERE id=?", (rid,))
            self.db.conn.commit()
            self.load_box_rules()

    def on_box_table_click(self, item):
        row = item.row()
        self.current_box_id = self.table_box.item(row, 0).text()
        self.box_name_edit.setText(self.table_box.item(row, 1).text())
        self.box_fmt_edit.setText(self.table_box.item(row, 2).text())

    # ================= 2. SN规则 =================
    def init_sn_tab(self):
        layout = QVBoxLayout(self.tab_sn)
        
        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(150)
        info.setHtml("""
        <h4>🔢 SN校验规则说明</h4>
        <ul>
        <li><code>{SN4}</code>: 匹配SN前4位</li>
        <li><code>{BATCH}</code>: 匹配批次号(0-9)</li>
        <li><code>{SEQn}</code>: 匹配n位数字 (如 {SEQ7})</li>
        <li>固定字符: 如 / - A</li>
        </ul>
        <p>示例: <code>{SN4}/2{BATCH}{SEQ7}</code></p>
        """)
        layout.addWidget(info)
        
        h_layout = QHBoxLayout()
        self.sn_name_edit = QLineEdit()
        self.sn_name_edit.setPlaceholderText("规则名称")
        self.sn_fmt_edit = QLineEdit()
        self.sn_fmt_edit.setPlaceholderText("格式")
        self.sn_len_spin = QSpinBox()
        self.sn_len_spin.setRange(0, 99)
        
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_sn_rule)
        btn_upd = QPushButton("修改")
        btn_upd.clicked.connect(self.update_sn_rule)
        
        h_layout.addWidget(QLabel("名称:"))
        h_layout.addWidget(self.sn_name_edit)
        h_layout.addWidget(QLabel("格式:"))
        h_layout.addWidget(self.sn_fmt_edit)
        h_layout.addWidget(QLabel("长度(0不限):"))
        h_layout.addWidget(self.sn_len_spin)
        h_layout.addWidget(btn_add)
        h_layout.addWidget(btn_upd)
        layout.addLayout(h_layout)
        
        self.table_sn = QTableWidget()
        self.table_sn.setColumnCount(4)
        self.table_sn.setHorizontalHeaderLabels(["ID", "名称", "格式", "长度"])
        self.table_sn.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_sn.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sn.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_sn.itemClicked.connect(self.on_sn_table_click)
        layout.addWidget(self.table_sn)
        
        btn_del = QPushButton("删除选中")
        btn_del.clicked.connect(self.delete_sn_rule)
        layout.addWidget(btn_del)
        
        self.current_sn_id = None

    def load_sn_rules(self):
        self.table_sn.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, rule_string, length FROM sn_rules")
        for r_idx, row in enumerate(cursor.fetchall()):
            self.table_sn.insertRow(r_idx)
            for c_idx, val in enumerate(row):
                self.table_sn.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def add_sn_rule(self):
        name = self.sn_name_edit.text()
        fmt = self.sn_fmt_edit.text()
        length = self.sn_len_spin.value()
        if not name or not fmt: return
        try:
            self.db.cursor.execute("INSERT INTO sn_rules (name, rule_string, length) VALUES (?,?,?)", (name, fmt, length))
            self.db.conn.commit()
            self.load_sn_rules()
            self.sn_name_edit.clear()
            self.sn_fmt_edit.clear()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def update_sn_rule(self):
        if not self.current_sn_id: return
        try:
            self.db.cursor.execute("UPDATE sn_rules SET name=?, rule_string=?, length=? WHERE id=?", 
                                   (self.sn_name_edit.text(), self.sn_fmt_edit.text(), self.sn_len_spin.value(), self.current_sn_id))
            self.db.conn.commit()
            self.load_sn_rules()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def delete_sn_rule(self):
        row = self.table_sn.currentRow()
        if row >= 0:
            rid = self.table_sn.item(row, 0).text()
            self.db.cursor.execute("DELETE FROM sn_rules WHERE id=?", (rid,))
            self.db.conn.commit()
            self.load_sn_rules()

    def on_sn_table_click(self, item):
        row = item.row()
        self.current_sn_id = self.table_sn.item(row, 0).text()
        self.sn_name_edit.setText(self.table_sn.item(row, 1).text())
        self.sn_fmt_edit.setText(self.table_sn.item(row, 2).text())
        self.sn_len_spin.setValue(int(self.table_sn.item(row, 3).text()))

    # ================= 3. 字段映射 =================
    def init_map_tab(self):
        layout = QVBoxLayout(self.tab_map)
        self.table_map = QTableWidget()
        self.table_map.setColumnCount(2)
        self.table_map.setHorizontalHeaderLabels(["数据库源字段", "模板变量名"])
        self.table_map.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_map)
        
        h_layout = QHBoxLayout()
        b_add = QPushButton("增加")
        b_add.clicked.connect(self.add_map_row)
        b_del = QPushButton("删除")
        b_del.clicked.connect(self.del_map_row)
        b_save = QPushButton("保存配置")
        b_save.clicked.connect(self.save_map)
        h_layout.addWidget(b_add)
        h_layout.addWidget(b_del)
        h_layout.addStretch()
        h_layout.addWidget(b_save)
        layout.addLayout(h_layout)

    def load_map(self):
        self.table_map.setRowCount(0)
        mapping = self.db.get_setting('field_mapping')
        if not isinstance(mapping, dict): mapping = DEFAULT_MAPPING
        for k, v in mapping.items():
            self.add_map_row(k, v)

    def add_map_row(self, key=None, val=""):
        row = self.table_map.rowCount()
        self.table_map.insertRow(row)
        
        cb = QComboBox()
        items = [("name","名称"),("spec","规格"),("model","型号"),("color","颜色"),
                 ("sn4","SN前4"),("sku","SKU"),("code69","69码"),("qty","数量"),
                 ("weight","重量"),("box_no","箱号"),("prod_date","日期")]
        for k, l in items:
            cb.addItem(f"{l} ({k})", k)
        
        if key:
            idx = cb.findData(key)
            if idx >= 0: cb.setCurrentIndex(idx)
            
        self.table_map.setCellWidget(row, 0, cb)
        self.table_map.setCellWidget(row, 1, QLineEdit(str(val)))

    def del_map_row(self):
        self.table_map.removeRow(self.table_map.currentRow())

    def save_map(self):
        m = {}
        for i in range(self.table_map.rowCount()):
            c = self.table_map.cellWidget(i, 0)
            l = self.table_map.cellWidget(i, 1)
            if c and l and l.text().strip():
                m[c.currentData()] = l.text().strip()
        self.db.set_setting('field_mapping', json.dumps(m))
        QMessageBox.information(self, "成功", "映射保存成功")

    # ================= 4. 系统维护 =================
    def init_sys_tab(self):
        layout = QVBoxLayout(self.tab_sys)
        
        # 模板路径
        g1 = QGroupBox("模板根目录")
        l1 = QHBoxLayout(g1)
        self.path_tmpl_edit = QLineEdit()
        self.path_tmpl_edit.setReadOnly(True)
        b1 = QPushButton("选择")
        b1.clicked.connect(self.sel_tmpl_path)
        l1.addWidget(self.path_tmpl_edit)
        l1.addWidget(b1)
        layout.addWidget(g1)
        
        # 备份路径
        g2 = QGroupBox("备份目录")
        l2 = QHBoxLayout(g2)
        self.path_bk_edit = QLineEdit()
        self.path_bk_edit.setReadOnly(True)
        b2 = QPushButton("选择")
        b2.clicked.connect(self.sel_bk_path)
        l2.addWidget(self.path_bk_edit)
        l2.addWidget(b2)
        layout.addWidget(g2)
        
        # 按钮
        g3 = QGroupBox("操作")
        l3 = QHBoxLayout(g3)
        b3 = QPushButton("立即备份")
        b3.clicked.connect(self.do_backup)
        b4 = QPushButton("从文件恢复")
        b4.clicked.connect(self.do_restore)
        l3.addWidget(b3)
        l3.addWidget(b4)
        layout.addWidget(g3)
        
        layout.addStretch()

    def load_sys_paths(self):
        # 关键修复：刷新时加载路径到输入框
        p1 = self.db.get_setting('template_root')
        if p1: self.path_tmpl_edit.setText(p1)
        
        p2 = self.db.get_setting('backup_path')
        if p2: self.path_bk_edit.setText(p2)

    def sel_tmpl_path(self):
        p = QFileDialog.getExistingDirectory(self, "选择模板根目录")
        if p:
            self.db.set_setting('template_root', p)
            self.path_tmpl_edit.setText(p)

    def sel_bk_path(self):
        p = QFileDialog.getExistingDirectory(self, "选择备份目录")
        if p:
            self.db.set_setting('backup_path', p)
            self.path_bk_edit.setText(p)

    def do_backup(self):
        ok, msg = self.db.backup_db()
        QMessageBox.information(self, "结果", msg)

    def do_restore(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择数据库", "", "DB (*.db)")
        if p:
            if QMessageBox.warning(self, "警告", "恢复将覆盖当前数据，确定？", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                ok, msg = self.db.restore_db(p)
                QMessageBox.information(self, "结果", msg)

    # ================= 全局刷新 =================
    def refresh_data(self):
        self.load_box_rules()
        self.load_sn_rules()
        self.load_map()
        self.load_sys_paths() # 确保加载路径
