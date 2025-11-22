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
        
        self.tab_rules = QWidget(); self.init_rules_tab(); self.tabs.addTab(self.tab_rules, "1. 箱号规则")
        self.tab_sn = QWidget(); self.init_sn_tab(); self.tabs.addTab(self.tab_sn, "2. SN规则")
        self.tab_map = QWidget(); self.init_map_tab(); self.tabs.addTab(self.tab_map, "3. 字段映射")
        self.tab_sys = QWidget(); self.init_sys_tab(); self.tabs.addTab(self.tab_sys, "4. 系统维护")
        
        main_layout.addWidget(self.tabs)
        self.refresh_data()

    def init_rules_tab(self):
        l = QVBoxLayout(self.tab_rules)
        # 详细说明
        info = QTextEdit(); info.setReadOnly(True); info.setMaximumHeight(180)
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
        l.addWidget(info)
        
        # 编辑
        h = QHBoxLayout()
        self.bx_nm = QLineEdit(); self.bx_nm.setPlaceholderText("规则名")
        self.bx_fmt = QLineEdit(); self.bx_fmt.setPlaceholderText("规则格式")
        b_add = QPushButton("添加"); b_add.clicked.connect(self.add_box)
        b_upd = QPushButton("修改"); b_upd.clicked.connect(self.upd_box)
        h.addWidget(QLabel("名称")); h.addWidget(self.bx_nm)
        h.addWidget(QLabel("格式")); h.addWidget(self.bx_fmt)
        h.addWidget(b_add); h.addWidget(b_upd)
        l.addLayout(h)
        
        self.tb_box = QTableWidget(); self.tb_box.setColumnCount(3); self.tb_box.setHorizontalHeaderLabels(["ID","名称","格式"])
        self.tb_box.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tb_box.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb_box.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tb_box.itemClicked.connect(lambda i: self.fill_edit(i, self.tb_box, self.bx_nm, self.bx_fmt))
        l.addWidget(self.tb_box)
        
        b_del = QPushButton("删除选中"); b_del.clicked.connect(lambda: self.del_row(self.tb_box, "box_rules", self.load_box))
        l.addWidget(b_del)
        self.curr_box_id = None

    def init_sn_tab(self):
        l = QVBoxLayout(self.tab_sn)
        info = QTextEdit(); info.setReadOnly(True); info.setMaximumHeight(180)
        info.setHtml("""
        <h4>🔢 SN校验规则说明</h4>
        <ul>
        <li><code>{SN4}</code>: 匹配产品SN前4位</li>
        <li><code>{BATCH}</code>: 匹配当前批次号(0-9)</li>
        <li><code>{SEQn}</code>: 匹配n位数字 (如 {SEQ7} 匹配7位任意数字)</li>
        <li>固定字符直接写 (如 / - A)</li>
        </ul>
        <p>示例: <code>{SN4}/2{BATCH}{SEQ7}</code> => 匹配 1234/201234567</p>
        """)
        l.addWidget(info)
        
        h = QHBoxLayout()
        self.sn_nm = QLineEdit(); self.sn_nm.setPlaceholderText("规则名")
        self.sn_fmt = QLineEdit(); self.sn_fmt.setPlaceholderText("格式")
        self.sn_len = QSpinBox(); self.sn_len.setRange(0,99); self.sn_len.setValue(0)
        b_add = QPushButton("添加"); b_add.clicked.connect(self.add_sn)
        b_upd = QPushButton("修改"); b_upd.clicked.connect(self.upd_sn)
        h.addWidget(QLabel("名称")); h.addWidget(self.sn_nm)
        h.addWidget(QLabel("格式")); h.addWidget(self.sn_fmt)
        h.addWidget(QLabel("总长度(0不限)")); h.addWidget(self.sn_len)
        h.addWidget(b_add); h.addWidget(b_upd)
        l.addLayout(h)
        
        self.tb_sn = QTableWidget(); self.tb_sn.setColumnCount(4); self.tb_sn.setHorizontalHeaderLabels(["ID","名称","格式","长度"])
        self.tb_sn.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tb_sn.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb_sn.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tb_sn.itemClicked.connect(self.fill_sn_edit)
        l.addWidget(self.tb_sn)
        
        b_del = QPushButton("删除选中"); b_del.clicked.connect(lambda: self.del_row(self.tb_sn, "sn_rules", self.load_sn))
        l.addWidget(b_del)
        self.curr_sn_id = None

    def init_map_tab(self): # 简化展示，逻辑同前
        l = QVBoxLayout(self.tab_map); self.tb_map = QTableWidget(0,2); self.tb_map.setHorizontalHeaderLabels(["源","目标"])
        self.tb_map.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); l.addWidget(self.tb_map)
        h = QHBoxLayout(); b1=QPushButton("加"); b1.clicked.connect(self.add_map)
        b2=QPushButton("删"); b2.clicked.connect(self.del_map)
        b3=QPushButton("存"); b3.clicked.connect(self.save_map)
        h.addWidget(b1); h.addWidget(b2); h.addWidget(b3); l.addLayout(h)

    def init_sys_tab(self): # 简化展示
        l = QVBoxLayout(self.tab_sys)
        self.bk_path = QLineEdit(); self.tp_root = QLineEdit()
        l.addWidget(QLabel("模板根目录")); l.addWidget(self.tp_root)
        b1 = QPushButton("选"); b1.clicked.connect(lambda: self.sel_dir(self.tp_root, 'template_root')); l.addWidget(b1)
        l.addWidget(QLabel("备份目录")); l.addWidget(self.bk_path)
        b2 = QPushButton("选"); b2.clicked.connect(lambda: self.sel_dir(self.bk_path, 'backup_path')); l.addWidget(b2)
        h = QHBoxLayout(); b3=QPushButton("备份"); b3.clicked.connect(self.do_bk)
        b4=QPushButton("恢复"); b4.clicked.connect(self.do_rs); h.addWidget(b3); h.addWidget(b4); l.addLayout(h); l.addStretch()

    # 逻辑
    def refresh_data(self): self.load_box(); self.load_sn(); self.load_map(); 
    
    def load_box(self): 
        self.tb_box.setRowCount(0); c=self.db.conn.cursor(); c.execute("SELECT id,name,rule_string FROM box_rules")
        for r,row in enumerate(c.fetchall()): self.tb_box.insertRow(r); [self.tb_box.setItem(r,i,QTableWidgetItem(str(v))) for i,v in enumerate(row)]
    
    def add_box(self): self.db.cursor.execute("INSERT INTO box_rules (name,rule_string) VALUES (?,?)",(self.rule_name.text(),self.rule_fmt.text())); self.db.conn.commit(); self.load_box()
    def upd_box(self): 
        if self.curr_box_id: self.db.cursor.execute("UPDATE box_rules SET name=?,rule_string=? WHERE id=?",(self.rule_name.text(),self.rule_fmt.text(),self.curr_box_id)); self.db.conn.commit(); self.load_box()

    def load_sn(self):
        self.tb_sn.setRowCount(0); c=self.db.conn.cursor(); c.execute("SELECT id,name,rule_string,length FROM sn_rules")
        for r,row in enumerate(c.fetchall()): self.tb_sn.insertRow(r); [self.tb_sn.setItem(r,i,QTableWidgetItem(str(v))) for i,v in enumerate(row)]
    
    def add_sn(self): self.db.cursor.execute("INSERT INTO sn_rules (name,rule_string,length) VALUES (?,?,?)",(self.sn_nm.text(),self.sn_fmt.text(),self.sn_len.value())); self.db.conn.commit(); self.load_sn()
    def upd_sn(self): 
        if self.curr_sn_id: self.db.cursor.execute("UPDATE sn_rules SET name=?,rule_string=?,length=? WHERE id=?",(self.sn_nm.text(),self.sn_fmt.text(),self.sn_len.value(),self.curr_sn_id)); self.db.conn.commit(); self.load_sn()

    def fill_edit(self, item, table, name_le, fmt_le): 
        r = item.row(); self.curr_box_id = table.item(r,0).text()
        name_le.setText(table.item(r,1).text()); fmt_le.setText(table.item(r,2).text())
    
    def fill_sn_edit(self, item):
        r = item.row(); self.curr_sn_id = self.tb_sn.item(r,0).text()
        self.sn_nm.setText(self.tb_sn.item(r,1).text()); self.sn_fmt.setText(self.tb_sn.item(r,2).text())
        self.sn_len.setValue(int(self.tb_sn.item(r,3).text()))

    def del_row(self, table, tname, cb): 
        r = table.currentRow()
        if r>=0: self.db.cursor.execute(f"DELETE FROM {tname} WHERE id=?",(table.item(r,0).text(),)); self.db.conn.commit(); cb()

    # Map/Sys logic omitted for brevity, same as before but wired up
    def add_map(self): 
        r=self.tb_map.rowCount(); self.tb_map.insertRow(r)
        c=QComboBox(); c.addItems(["name","spec","model","color","sn4","sku","code69","qty","weight","box_no","prod_date"])
        self.tb_map.setCellWidget(r,0,c); self.tb_map.setCellWidget(r,1,QLineEdit())
    def del_map(self): self.tb_map.removeRow(self.tb_map.currentRow())
    def save_map(self): 
        m={}; 
        for i in range(self.tb_map.rowCount()): m[self.tb_map.cellWidget(i,0).currentText()]=self.tb_map.cellWidget(i,1).text()
        self.db.set_setting('field_mapping', json.dumps(m)); QMessageBox.information(self,"ok","saved")
    def load_map(self):
        self.tb_map.setRowCount(0); m = self.db.get_setting('field_mapping')
        if not isinstance(m,dict): m=DEFAULT_MAPPING
        for k,v in m.items(): self.add_map(); self.tb_map.cellWidget(self.tb_map.rowCount()-1,0).setCurrentText(k); self.tb_map.cellWidget(self.tb_map.rowCount()-1,1).setText(v)

    def sel_dir(self, le, key): p=QFileDialog.getExistingDirectory(); 
    def do_bk(self): self.db.backup_db(); QMessageBox.information(self,"ok","backups")
    def do_rs(self): QMessageBox.information(self,"ok","restore logic")
