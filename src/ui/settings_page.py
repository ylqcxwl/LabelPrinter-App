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

        # 2. SN规则 (新)
        self.tab_sn_rules = QWidget()
        self.init_sn_rules_tab()
        self.tabs.addTab(self.tab_sn_rules, "2. SN规则")

        # 3. 字段映射
        self.tab_mapping = QWidget()
        self.init_mapping_tab()
        self.tabs.addTab(self.tab_mapping, "3. 字段映射")
        
        # 4. 数据维护
        self.tab_backup = QWidget()
        self.init_backup_tab()
        self.tabs.addTab(self.tab_backup, "4. 数据维护")

        main_layout.addWidget(self.tabs)
        self.refresh_data()

    # ================== 1. 箱号规则 (支持修改) ==================
    def init_rules_tab(self):
        layout = QVBoxLayout(self.tab_rules)
        
        # 说明
        help_txt = QTextEdit()
        help_txt.setReadOnly(True)
        help_txt.setMaximumHeight(120)
        help_txt.setHtml("""
        <style>code { background-color: #eee; color: #c0392b; font-weight: bold; }</style>
        <b>变量代码：</b> <code>{SN4}</code>:SN前4位 | <code>{Y1}/{Y2}</code>:年1/2位 | <code>{M1}/{MM}</code>:月代码/2位 | <code>{DD}</code>:日2位 | <code>{SEQ5}</code>:5位流水号
        <br><b>示例：</b> <code>MZXH{SN4}{Y1}{M1}{SEQ5}</code> -> MZXH80015B00001
        """)
        layout.addWidget(help_txt)

        # 编辑区
        edit_layout = QHBoxLayout()
        self.rule_name = QLineEdit()
        self.rule_name.setPlaceholderText("规则名称")
        self.rule_fmt = QLineEdit()
        self.rule_fmt.setPlaceholderText("规则格式")
        
        btn_add = QPushButton("添加规则")
        btn_add.clicked.connect(self.add_box_rule)
        btn_update = QPushButton("修改选中")
        btn_update.clicked.connect(self.update_box_rule)
        
        edit_layout.addWidget(QLabel("名称:"))
        edit_layout.addWidget(self.rule_name)
        edit_layout.addWidget(QLabel("格式:"))
        edit_layout.addWidget(self.rule_fmt)
        edit_layout.addWidget(btn_add)
        edit_layout.addWidget(btn_update)
        layout.addLayout(edit_layout)

        # 表格
        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(3)
        self.table_rules.setHorizontalHeaderLabels(["ID", "名称", "规则格式"])
        self.table_rules.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # 名称自适应
        self.table_rules.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # 格式拉伸
        self.table_rules.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_rules.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_rules.itemClicked.connect(self.on_box_rule_select) # 点击填充
        layout.addWidget(self.table_rules)
        
        btn_del = QPushButton("删除选中规则")
        btn_del.clicked.connect(self.delete_box_rule)
        layout.addWidget(btn_del)
        
        self.current_box_rule_id = None # 用于修改

    def on_box_rule_select(self, item):
        row = item.row()
        self.current_box_rule_id = self.table_rules.item(row, 0).text()
        self.rule_name.setText(self.table_rules.item(row, 1).text())
        self.rule_fmt.setText(self.table_rules.item(row, 2).text())

    # ================== 2. SN规则 (新功能) ==================
    def init_sn_rules_tab(self):
        layout = QVBoxLayout(self.tab_sn_rules)
        
        # 说明
        help_txt = QTextEdit()
        help_txt.setReadOnly(True)
        help_txt.setMaximumHeight(150)
        help_txt.setHtml("""
        <style>code { background-color: #eee; color: #2980b9; font-weight: bold; }</style>
        <h4>🔢 SN校验规则说明</h4>
        <p>打印时会根据此规则校验扫描的SN是否合法。</p>
        <ul>
            <li><code>{SN4}</code> : 必须匹配当前产品的SN前4位</li>
            <li><code>{BATCH}</code> : 必须匹配打印界面选择的批次号 (0-9)</li>
            <li><code>{SEQn}</code> : n位数字序列号 (忽略具体数值，只校验是否为数字)。例如 <code>{SEQ7}</code> 代表7位数字。</li>
            <li><b>固定字符</b> : 直接输入 (如 <code>/</code>, <code>2</code>, <code>C</code> 等)</li>
        </ul>
        <p><b>示例：</b> <code>{SN4}/2{BATCH}{SEQ7}</code> <br>
        <b>匹配：</b> 1234/200010001 (假设SN4=1234, 批次=0)</p>
        """)
        layout.addWidget(help_txt)

        # 编辑区
        edit_layout = QHBoxLayout()
        self.sn_rule_name = QLineEdit()
        self.sn_rule_name.setPlaceholderText("规则名称 (如: 音箱SN)")
        self.sn_rule_fmt = QLineEdit()
        self.sn_rule_fmt.setPlaceholderText("格式 (如: {SN4}/2{BATCH}{SEQ7})")
        self.sn_rule_len = QSpinBox()
        self.sn_rule_len.setRange(0, 50)
        self.sn_rule_len.setValue(14)
        
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_sn_rule)
        btn_update = QPushButton("修改")
        btn_update.clicked.connect(self.update_sn_rule)
        
        edit_layout.addWidget(QLabel("名称:"))
        edit_layout.addWidget(self.sn_rule_name)
        edit_layout.addWidget(QLabel("格式:"))
        edit_layout.addWidget(self.sn_rule_fmt)
        edit_layout.addWidget(QLabel("总长度(0不限):"))
        edit_layout.addWidget(self.sn_rule_len)
        edit_layout.addWidget(btn_add)
        edit_layout.addWidget(btn_update)
        layout.addLayout(edit_layout)

        # 表格
        self.table_sn_rules = QTableWidget()
        self.table_sn_rules.setColumnCount(4)
        self.table_sn_rules.setHorizontalHeaderLabels(["ID", "名称", "规则格式", "长度"])
        self.table_sn_rules.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_sn_rules.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sn_rules.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_sn_rules.itemClicked.connect(self.on_sn_rule_select)
        layout.addWidget(self.table_sn_rules)
        
        btn_del = QPushButton("删除选中SN规则")
        btn_del.clicked.connect(self.delete_sn_rule)
        layout.addWidget(btn_del)
        
        self.current_sn_rule_id = None

    def on_sn_rule_select(self, item):
        row = item.row()
        self.current_sn_rule_id = self.table_sn_rules.item(row, 0).text()
        self.sn_rule_name.setText(self.table_sn_rules.item(row, 1).text())
        self.sn_rule_fmt.setText(self.table_sn_rules.item(row, 2).text())
        self.sn_rule_len.setValue(int(self.table_sn_rules.item(row, 3).text()))

    # ================== CRUD 逻辑 ==================
    def refresh_data(self):
        self.load_box_rules()
        self.load_sn_rules()
        self.load_mapping_to_table()
        self.txt_backup_path.setText(self.db.get_setting('backup_path'))
        self.txt_tmpl_root.setText(self.db.get_setting('template_root'))

    # Box Rules
    def load_box_rules(self):
        self.table_rules.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, rule_string FROM box_rules")
        for r, row in enumerate(cursor.fetchall()):
            self.table_rules.insertRow(r)
            for c, val in enumerate(row):
                self.table_rules.setItem(r, c, QTableWidgetItem(str(val)))

    def add_box_rule(self):
        name = self.rule_name.text()
        fmt = self.rule_fmt.text()
        if name and fmt:
            try:
                self.db.cursor.execute("INSERT INTO box_rules (name, rule_string) VALUES (?,?)", (name, fmt))
                self.db.conn.commit()
                self.load_box_rules()
                self.rule_name.clear(); self.rule_fmt.clear()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def update_box_rule(self):
        if not self.current_box_rule_id: return
        name = self.rule_name.text()
        fmt = self.rule_fmt.text()
        try:
            self.db.cursor.execute("UPDATE box_rules SET name=?, rule_string=? WHERE id=?", 
                                   (name, fmt, self.current_box_rule_id))
            self.db.conn.commit()
            self.load_box_rules()
            QMessageBox.information(self, "成功", "箱号规则已修改")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def delete_box_rule(self):
        row = self.table_rules.currentRow()
        if row >= 0:
            rid = self.table_rules.item(row, 0).text()
            self.db.cursor.execute("DELETE FROM box_rules WHERE id=?", (rid,))
            self.db.conn.commit()
            self.load_box_rules()

    # SN Rules
    def load_sn_rules(self):
        self.table_sn_rules.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, rule_string, length FROM sn_rules")
        for r, row in enumerate(cursor.fetchall()):
            self.table_sn_rules.insertRow(r)
            for c, val in enumerate(row):
                self.table_sn_rules.setItem(r, c, QTableWidgetItem(str(val)))

    def add_sn_rule(self):
        name = self.sn_rule_name.text()
        fmt = self.sn_rule_fmt.text()
        length = self.sn_rule_len.value()
        if name and fmt:
            try:
                self.db.cursor.execute("INSERT INTO sn_rules (name, rule_string, length) VALUES (?,?,?)", 
                                       (name, fmt, length))
                self.db.conn.commit()
                self.load_sn_rules()
                self.sn_rule_name.clear(); self.sn_rule_fmt.clear()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def update_sn_rule(self):
        if not self.current_sn_rule_id: return
        name = self.sn_rule_name.text()
        fmt = self.sn_rule_fmt.text()
        length = self.sn_rule_len.value()
        try:
            self.db.cursor.execute("UPDATE sn_rules SET name=?, rule_string=?, length=? WHERE id=?", 
                                   (name, fmt, length, self.current_sn_rule_id))
            self.db.conn.commit()
            self.load_sn_rules()
            QMessageBox.information(self, "成功", "SN规则已修改")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def delete_sn_rule(self):
        row = self.table_sn_rules.currentRow()
        if row >= 0:
            rid = self.table_sn_rules.item(row, 0).text()
            self.db.cursor.execute("DELETE FROM sn_rules WHERE id=?", (rid,))
            self.db.conn.commit()
            self.load_sn_rules()

    # --- Mapping & Backup (Standard) ---
    def init_mapping_tab(self):
        layout = QVBoxLayout(self.tab_mapping)
        self.table_map = QTableWidget()
        self.table_map.setColumnCount(2)
        self.table_map.setHorizontalHeaderLabels(["数据库源字段", "Bartender模板变量名"])
        self.table_map.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_map)
        
        btn_box = QHBoxLayout()
        btn_add = QPushButton("➕ 增加"); btn_add.clicked.connect(self.add_mapping_row)
        btn_del = QPushButton("➖ 删除"); btn_del.clicked.connect(self.remove_mapping_row)
        btn_save = QPushButton("💾 保存配置"); btn_save.clicked.connect(self.save_mapping_table)
        btn_box.addWidget(btn_add); btn_box.addWidget(btn_del); btn_box.addStretch(); btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def init_backup_tab(self):
        layout = QVBoxLayout(self.tab_backup)
        
        grp1 = QGroupBox("Bartender 模板根目录")
        l1 = QHBoxLayout(grp1)
        self.txt_tmpl_root = QLineEdit(); self.txt_tmpl_root.setReadOnly(True)
        btn1 = QPushButton("选择"); btn1.clicked.connect(self.select_tmpl_root)
        l1.addWidget(self.txt_tmpl_root); l1.addWidget(btn1)
        layout.addWidget(grp1)

        grp2 = QGroupBox("数据备份目录")
        l2 = QHBoxLayout(grp2)
        self.txt_backup_path = QLineEdit(); self.txt_backup_path.setReadOnly(True)
        btn2 = QPushButton("选择"); btn2.clicked.connect(self.select_backup_path)
        l2.addWidget(self.txt_backup_path); l2.addWidget(btn2)
        layout.addWidget(grp2)
        
        grp3 = QGroupBox("操作")
        l3 = QHBoxLayout(grp3)
        b3 = QPushButton("立即备份"); b3.clicked.connect(self.do_backup)
        b4 = QPushButton("恢复数据"); b4.clicked.connect(self.do_restore)
        l3.addWidget(b3); l3.addWidget(b4)
        layout.addWidget(grp3)
        layout.addStretch()

    # Helpers
    def add_mapping_row(self, k=None, v=""):
        r = self.table_map.rowCount(); self.table_map.insertRow(r)
        cb = QComboBox(); 
        for s,l in [("name","名称"),("spec","规格"),("model","型号"),("color","颜色"),("sn4","SN前4"),("sku","SKU"),("code69","69码"),("qty","数量"),("weight","重量"),("box_no","箱号"),("prod_date","日期")]: cb.addItem(f"{l} ({s})", s)
        if k: cb.setCurrentIndex(cb.findData(k))
        self.table_map.setCellWidget(r, 0, cb); self.table_map.setCellWidget(r, 1, QLineEdit(str(v)))

    def remove_mapping_row(self):
        r = self.table_map.currentRow()
        if r>=0: self.table_map.removeRow(r)

    def save_mapping_table(self):
        m = {}
        for i in range(self.table_map.rowCount()):
            c = self.table_map.cellWidget(i,0); l = self.table_map.cellWidget(i,1)
            if c and l and l.text().strip(): m[c.currentData()] = l.text().strip()
        self.db.set_setting('field_mapping', json.dumps(m))
        QMessageBox.information(self, "成功", "已保存")

    def load_mapping_to_table(self):
        self.table_map.setRowCount(0)
        m = self.db.get_setting('field_mapping')
        if not isinstance(m, dict): m = DEFAULT_MAPPING
        for k,v in m.items(): self.add_mapping_row(k,v)

    def select_backup_path(self):
        p = QFileDialog.getExistingDirectory(self, "选择目录")
        if p: self.db.set_setting('backup_path', p); self.txt_backup_path.setText(p)
    def select_tmpl_root(self):
        p = QFileDialog.getExistingDirectory(self, "选择目录")
        if p: self.db.set_setting('template_root', p); self.txt_tmpl_root.setText(p)
    def do_backup(self):
        s, m = self.db.backup_db()
        QMessageBox.information(self, "结果", m)
    def do_restore(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择", "", "DB (*.db)")
        if p and QMessageBox.warning(self,"警告","覆盖?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
            s, m = self.db.restore_db(p); QMessageBox.information(self, "结果", m)
